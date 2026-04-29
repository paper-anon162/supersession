"""Seed construction module (data_plan §1, §11).

Authors describe a sample compactly via :class:`SeedSpec`; this module
materializes the spec into a fully-validated :class:`pipeline.schema.Sample`,
applying the structural conventions enforced elsewhere:

  - active / outdated status is derived from ``subtype`` and the ordered
    ``versions`` list (no manual flagging — easy to get wrong by hand).
  - reverted samples use 3 version entries (X, Y, X) where the third entry
    is the *active* "return to original value".
  - ``violation_predicate`` and ``recall_query`` are auto-built.
  - metadata token counts are computed from the realized history.

Authoring convention: one seed per Python module under ``seeds/``, using
:func:`register_seed` so :func:`load_all_seeds` can collect them automatically.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from pipeline.schema import (
    GoldBundle,
    GoldTargetType,
    Metadata,
    Polarity,
    Rule,
    Sample,
    SampleType,
    ScoringMode,
    SemanticSpine,
    Session,
    SignalStrength,
    SupersessionSubtype,
    Turn,
    VersionState,
    ViolationPredicate,
)
from pipeline.construction.recall_query_gen import attach_recall_query


# ---------------------------------------------------------------------------
# Spec datatypes
# ---------------------------------------------------------------------------


@dataclass
class TurnSpec:
    role: Literal["user", "assistant"]
    text: str


@dataclass
class SessionSpec:
    session_id: str
    turns: list[TurnSpec]
    timestamp: str | None = None


@dataclass
class VersionSpec:
    """One version of the user's state on the target slot.

    For ``subtype == "reverted"``, supply *three* VersionSpecs: the original
    (X), the intermediate (Y), and the reverted (X). The third entry is the
    one that ends up labeled ``active``.
    """

    value: str
    polarity: Polarity
    session_introduced: int  # 1-indexed in the SeedSpec.sessions list


@dataclass
class SeedSpec:
    sample_id: str
    sample_type: SampleType  # supersession / carryover / stress
    target_type: GoldTargetType
    domain: str
    target_description: str
    target_slot_id: str
    topic: str
    versions: list[VersionSpec]
    sessions: list[SessionSpec]
    current_query: str
    required_behavior: str
    invalid_behavior: list[str]
    subtype: SupersessionSubtype | None = None
    signal_strength: SignalStrength | None = "strong"
    scoring: ScoringMode = "binary"
    violation_rule_types: list[str] = field(
        default_factory=lambda: [
            "must_include_active_value",
            "must_not_include_outdated_value",
            "must_not_mix",
            "must_address_target_slot",
        ]
    )
    check_scope: str = "full_response"
    notes: str = ""
    # Phase 2 metadata (audit P1) — propagated into Metadata at materialize().
    horizon: str | None = None
    failure_patterns: list[str] = field(default_factory=list)
    construction_source: str | None = None
    skeleton_source: str | None = None
    # Matched-triples design (protocol §9.2.2) — shared id across the
    # spine's compact / standard / hard realizations.
    triple_id: str | None = None
    # Codex P0 / 2026-04-26 audit: mark a seed as having known-weak
    # active-evidence so it falls out of the headline manifest. The
    # standard reason is "ambiguous_active_evidence"; reason captures
    # the specific defect (e.g. "active value surfaced only by a
    # third-party action in the active session").
    ambiguity_class: str | None = None
    ambiguity_reason: str | None = None


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------


def _approx_token_count(text: str) -> int:
    """Cheap whitespace + punctuation token counter. Adequate for metadata."""
    return len(re.findall(r"\w+|[^\w\s]", text))


def _history_token_count(sessions: list[Session]) -> int:
    return sum(
        _approx_token_count(t.text) for s in sessions for t in s.turns
    )


def _assign_statuses(
    versions: list[VersionSpec], subtype: SupersessionSubtype | None
) -> list[Literal["active", "outdated"]]:
    """For supersession samples: only the *last* version is active.

    Reverted is encoded as [v1, v2, v1] with three entries — the third is
    active. This matches data_plan §3.1.
    """
    n = len(versions)
    if n == 0:
        return []
    statuses: list[Literal["active", "outdated"]] = ["outdated"] * n
    statuses[-1] = "active"
    return statuses


def _build_version_states(spec: SeedSpec) -> list[VersionState]:
    statuses = _assign_statuses(spec.versions, spec.subtype)
    states: list[VersionState] = []
    for i, (vs, status) in enumerate(zip(spec.versions, statuses)):
        states.append(
            VersionState(
                version_id=f"v{i + 1}",
                topic=spec.topic,
                value=vs.value,
                polarity=vs.polarity,
                session_introduced=vs.session_introduced,
                status=status,
            )
        )
    return states


def _build_sessions(spec: SeedSpec) -> list[Session]:
    out: list[Session] = []
    for s in spec.sessions:
        out.append(
            Session(
                session_id=s.session_id,
                timestamp=s.timestamp,
                turns=[Turn(role=t.role, text=t.text) for t in s.turns],
            )
        )
    return out


def _update_to_query_distance(
    sessions: list[Session], active_version_session_idx: int
) -> int:
    """Token distance from the end of the session that introduced the active
    version to the end of the history (where the current query attaches)."""
    if not sessions:
        return 0
    if active_version_session_idx < 1 or active_version_session_idx > len(sessions):
        return 0
    distance = 0
    for s in sessions[active_version_session_idx:]:
        for t in s.turns:
            distance += _approx_token_count(t.text)
    return distance


def materialize(spec: SeedSpec) -> Sample:
    if spec.sample_type == "supersession":
        if spec.subtype is None:
            raise ValueError(
                f"seed {spec.sample_id}: supersession sample must have a subtype"
            )
        if len(spec.versions) < 2:
            raise ValueError(
                f"seed {spec.sample_id}: supersession needs ≥ 2 versions"
            )

    sessions = _build_sessions(spec)
    versions = _build_version_states(spec)
    must_honor = next(v for v in versions if v.status == "active")
    # Reverted-style multi_version chains (A → B → C → A) repeat the active
    # value at an earlier index. Drop any outdated entry whose value collapses
    # to the active value — otherwise must_not_honor literally contradicts
    # must_honor and any judge inspecting the gold gets confused.
    must_not_honor = [
        v for v in versions
        if v.status == "outdated" and v.value.strip() != must_honor.value.strip()
    ]

    predicate = ViolationPredicate(
        must_honor=must_honor,
        must_not_honor=must_not_honor,
        violation_rules=[
            Rule(
                rule_type=rt,  # type: ignore[arg-type]
                check_scope=spec.check_scope,  # type: ignore[arg-type]
            )
            for rt in spec.violation_rule_types
        ],
        partial_credit=False,
        scoring=spec.scoring,
    )

    spine = SemanticSpine(
        target_description=spec.target_description,
        target_slot_id=spec.target_slot_id,
        old_state=spec.versions[0].value if spec.versions else "",
        new_state=must_honor.value,
        required_behavior=spec.required_behavior,
        invalid_behavior=list(spec.invalid_behavior),
    )

    metadata = Metadata(
        session_count=len(sessions),
        history_token_count=_history_token_count(sessions),
        update_to_query_token_distance=_update_to_query_distance(
            sessions, must_honor.session_introduced
        ),
        number_of_revisions=max(0, len(versions) - 1),
        supersession_subtype=spec.subtype,
        signal_strength=spec.signal_strength
        if spec.sample_type == "supersession"
        else None,
        domain=spec.domain,
        gold_target_type=spec.target_type,
        competing_versions_count=len(versions),
        horizon=spec.horizon,
        failure_patterns=list(spec.failure_patterns),
        construction_source=spec.construction_source,
        skeleton_source=spec.skeleton_source,
        triple_id=spec.triple_id,
        ambiguity_class=spec.ambiguity_class,
        ambiguity_reason=spec.ambiguity_reason,
    )

    gold = GoldBundle(
        target_versions=versions,
        violation_predicate=predicate,
        gold_target_type=spec.target_type,
        metadata=metadata,
        semantic_spine=spine,
        reverted_probe=None,
    )

    sample = Sample.model_validate(
        {
            "sample_id": spec.sample_id,
            "history": [s.model_dump() for s in sessions],
            "current_query": spec.current_query,
            "sample_type": spec.sample_type,
            "_gold": gold.model_dump(),
        }
    )
    return attach_recall_query(sample)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_SEED_REGISTRY: list[SeedSpec] = []


def register_seed(spec: SeedSpec) -> SeedSpec:
    if any(existing.sample_id == spec.sample_id for existing in _SEED_REGISTRY):
        raise ValueError(f"duplicate sample_id {spec.sample_id!r}")
    # Gold-vs-history consistency gate at registration time. Fail loudly
    # on cluster A (gold tokens missing from history) and B
    # (session_introduced mismatch) — those are clear authoring bugs.
    # Cluster C (drift weak user-agency) and D (narrowing label) are
    # surfaced as warnings only, since some authored seeds intentionally
    # carry weak active evidence (and self-flag with ambiguity_class).
    #
    # Gate applies to seeds authored under the Phase 2 audit framework
    # (sample_id starts with `p2`, `f-`, or `h-`). Phase 0/1 legacy
    # seeds (carryover, interpersonal_boundary, conceptual_stance,
    # procedural_constraint, object_preference, stress, etc.) predate
    # this audit and bypass the gate even if they retroactively gained
    # `horizon` / `failure_patterns` metadata.
    is_audit_scoped = spec.sample_id.startswith(("p2", "f-", "h-"))
    if is_audit_scoped and spec.ambiguity_class is None:
        # Materialize a Sample on the fly to run the audit; if the spec
        # already self-declares ambiguity, skip the gate (the author
        # opted in to a known-weak-evidence sample).
        try:
            s = materialize(spec)
        except Exception:  # noqa: BLE001
            # Materialization failure is surfaced elsewhere; don't
            # mask it with a gate failure.
            _SEED_REGISTRY.append(spec)
            return spec
        from pipeline.construction.audit_gold_consistency import audit_sample
        findings = audit_sample(s)
        # A/B/E are pure authoring bugs (gold tokens absent from history,
        # session_introduced mismatch, chunked over-specification) — raise.
        # G/H are drift-form bugs that the Bedrock realizer can fix
        # automatically on retry, but a hand-authored seed cannot. Keep
        # them as hard fails for SeedSpec authoring with one escape
        # hatch: auto-flag the seed as ambiguous_active_evidence so the
        # module import doesn't abort. The seed lands in the registry
        # but is excluded from the canonical manifest until edited. Emit
        # a warning so the issue is visible. C/D/F stay advisory.
        hard_fail = [f for f in findings if f.cluster in ("A", "B", "E")]
        soft_fail = [f for f in findings if f.cluster in ("G", "H")]
        warning = [f for f in findings if f.cluster in ("C", "D", "F")]
        if hard_fail:
            reasons = "; ".join(
                f"cluster {f.cluster}: {f.reason}" for f in hard_fail
            )
            raise ValueError(
                f"register_seed({spec.sample_id!r}) failed gold-consistency "
                f"gate. {reasons}. Either fix the seed (edit gold value to "
                f"match the realized session text, or fix session_introduced) "
                f"or set ambiguity_class='ambiguous_active_evidence' to opt out."
            )
        if soft_fail:
            reasons = "; ".join(
                f"cluster {f.cluster}: {f.reason}" for f in soft_fail
            )
            spec.ambiguity_class = "ambiguous_active_evidence"
            spec.ambiguity_reason = (
                spec.ambiguity_reason
                or f"auto-flagged at register_seed: {reasons}"
            )
            import warnings as _warnings
            _warnings.warn(
                f"register_seed({spec.sample_id!r}): drift-form gate failed "
                f"({reasons}); auto-flagged ambiguous_active_evidence so the "
                f"sample is excluded from the canonical manifest. Edit the "
                f"seed to clear the gate to re-include.",
                stacklevel=2,
            )
        if warning:
            import warnings as _warnings
            for f in warning:
                _warnings.warn(
                    f"register_seed({spec.sample_id!r}): cluster {f.cluster} "
                    f"warning — {f.reason}",
                    stacklevel=2,
                )
    _SEED_REGISTRY.append(spec)
    return spec


def clear_registry() -> None:
    _SEED_REGISTRY.clear()


def load_all_seeds(package: str = "seeds") -> list[SeedSpec]:
    """Import every module under ``seeds/`` so each can register its specs."""
    clear_registry()
    pkg = importlib.import_module(package)
    for mod in pkgutil.walk_packages(pkg.__path__, prefix=f"{package}."):
        importlib.import_module(mod.name)
    return list(_SEED_REGISTRY)


def materialize_all(specs: list[SeedSpec]) -> list[Sample]:
    return [materialize(s) for s in specs]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "SeedSpec",
    "SessionSpec",
    "TurnSpec",
    "VersionSpec",
    "clear_registry",
    "load_all_seeds",
    "materialize",
    "materialize_all",
    "register_seed",
    "utc_now_iso",
]
