"""LLM-assisted seed realization (data_plan §1, §13).

Authors compose a *thin spine* (target / versions / current_query /
required-and-invalid behavior). The LLM expands the spine into a multi-
session history under the spine's constraints, producing a full
:class:`SeedSpec` ready to feed into :func:`materialize`.

Robustness contract:

  - Every realization output is parsed and validated against the spine.
  - On parse / structural failure, the helper retries up to ``max_retries``
    times with a sharpened error message.
  - The output is required to materialize cleanly (schema + same-target +
    leakage gauntlet) before being accepted; otherwise we retry.

The helper does NOT generate the ``current_query`` — that is author-
locked, because the leakage filter and gold semantic anchor depend on
it being precisely controlled.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jinja2 import Template

from pipeline.construction.leakage_filter import filter_sample
from pipeline.construction.same_target_checker import check_sample
from pipeline.construction.seeds import (
    SeedSpec,
    SessionSpec,
    TurnSpec,
    VersionSpec,
    materialize,
)
from pipeline.schema import (
    GoldTargetType,
    Sample,
    SampleType,
    ScoringMode,
    SignalStrength,
    SupersessionSubtype,
)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "seed_realization.jinja"


@dataclass
class ThinSpine:
    sample_id: str
    sample_type: SampleType
    target_type: GoldTargetType
    domain: str
    target_description: str
    target_slot_id: str
    topic: str
    versions: list[VersionSpec]
    current_query: str
    required_behavior: str
    invalid_behavior: list[str]
    n_sessions: int = 5
    subtype: SupersessionSubtype | None = None
    signal_strength: SignalStrength | None = "strong"
    scoring: ScoringMode = "binary"
    notes: str = ""
    violation_rule_types: list[str] = field(
        default_factory=lambda: [
            "must_include_active_value",
            "must_not_include_outdated_value",
            "must_not_mix",
            "must_address_target_slot",
        ]
    )


# ---------------------------------------------------------------------------
# Prompt rendering & parsing
# ---------------------------------------------------------------------------


def render_realization_prompt(thin: ThinSpine) -> str:
    template = Template(PROMPT_PATH.read_text())
    return template.render(
        target_description=thin.target_description,
        target_type=thin.target_type,
        domain=thin.domain,
        versions=thin.versions,
        n_sessions=thin.n_sessions,
        required_behavior=thin.required_behavior,
    )


_JSON_BLOCK_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


class RealizationParseError(ValueError):
    pass


def _extract_json(raw: str) -> dict[str, Any]:
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        raise RealizationParseError("no JSON object found in LLM output")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise RealizationParseError(f"JSON parse error: {e}") from e


def parse_sessions(raw: str, expected_n: int) -> list[SessionSpec]:
    obj = _extract_json(raw)
    if "sessions" not in obj or not isinstance(obj["sessions"], list):
        raise RealizationParseError("missing or non-list 'sessions' field")
    sessions_json = obj["sessions"]
    if len(sessions_json) != expected_n:
        raise RealizationParseError(
            f"expected {expected_n} sessions, got {len(sessions_json)}"
        )

    out: list[SessionSpec] = []
    for i, s in enumerate(sessions_json):
        sid_expected = f"s{i + 1}"
        sid = s.get("session_id", "").strip()
        if sid != sid_expected:
            # Allow a soft renaming: if the LLM produced "S1" or "session-1"
            # we coerce to "sN".
            sid = sid_expected
        timestamp = s.get("timestamp")
        turns_raw = s.get("turns")
        if not isinstance(turns_raw, list) or not turns_raw:
            raise RealizationParseError(f"session {sid_expected}: turns missing or empty")
        turns: list[TurnSpec] = []
        for t in turns_raw:
            role = t.get("role")
            text = t.get("text", "").strip()
            if role not in ("user", "assistant"):
                raise RealizationParseError(
                    f"session {sid_expected}: invalid role {role!r}"
                )
            if not text:
                raise RealizationParseError(
                    f"session {sid_expected}: empty turn text"
                )
            turns.append(TurnSpec(role=role, text=text))
        out.append(SessionSpec(session_id=sid, timestamp=timestamp, turns=turns))
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass
class RealizationResult:
    seed_spec: SeedSpec | None
    sample: Sample | None
    raw_outputs: list[str]
    failure_reason: str | None = None
    attempts: int = 0


def _check_horizon_budget(sample: Sample) -> str | None:
    """Strict horizon-tier validation (per data_plan §9.2.1, audit P0).

    If the sample's metadata declares a horizon, the actual
    ``history_token_count`` must fall inside that horizon's budget
    band ``[min_tokens, max_tokens)`` from
    ``skeleton_realizer.HORIZON_BUDGETS``. Returns a description of
    the violation if any, else None. Samples without a declared
    horizon (compact pilot, pre-Phase 2 realized batches) pass.
    """
    # Local import to avoid a circular skeleton_realizer ↔ realization pull.
    from pipeline.construction.skeleton_realizer import HORIZON_BUDGETS  # noqa: WPS433

    horizon = getattr(sample.gold.metadata, "horizon", None)
    if horizon is None:
        return None
    budget = HORIZON_BUDGETS.get(horizon)
    if budget is None:
        return f"unknown horizon label {horizon!r}"
    n_tokens = sample.gold.metadata.history_token_count
    if n_tokens is None:
        return None
    if n_tokens < budget.min_tokens:
        return (
            f"horizon budget violation: declared={horizon!r}, "
            f"history_token_count={n_tokens} < min_tokens={budget.min_tokens}"
        )
    if n_tokens >= budget.max_tokens:
        return (
            f"horizon budget violation: declared={horizon!r}, "
            f"history_token_count={n_tokens} >= max_tokens={budget.max_tokens}"
        )
    return None


def _gauntlet_check(sample: Sample) -> str | None:
    """Return None if the sample passes; otherwise a description of the failure."""
    # Same-target rule check (only for supersession)
    st_report = check_sample(sample)
    if not st_report.passes:
        bad = [
            f"{a}-{b}: {r.reason}" for a, b, r in st_report.pair_results if not r.passes
        ]
        return f"same-target rule check failed: {bad}"
    # Leakage filter
    verdict = filter_sample(sample)
    if not verdict.accepted:
        return (
            f"leakage filter rejected: reasons={verdict.reasons}, "
            f"matched_tokens={verdict.matched_tokens}, "
            f"matched_relation_phrases={verdict.matched_relation_phrases}"
        )
    # Strict horizon-tier budget gate (audit P0). For Phase 2 samples
    # whose metadata declares a horizon, history_token_count must fall
    # inside the budget band declared by HORIZON_BUDGETS.
    horizon_err = _check_horizon_budget(sample)
    if horizon_err is not None:
        return horizon_err
    # Gold-vs-history consistency gate (2026-04-26 audit + post-audit
    # findings 2026-04-26 + 2026-04-26 v9 drift sweep). Block on the
    # high-confidence clusters:
    #   A — active-value tokens missing from history wholesale
    #   B — session_introduced points at a session that doesn't carry
    #       v2-distinguishing tokens
    #   C — drift sample lacks user-role agency
    #   E — active.value contains chunks unrealized in dialogue
    #       (over-specification, stricter than A)
    #   F — drift active session opens with observational speech act
    #       and no declarative phrase rescues it
    #   G — drift active session leaks explicit-change phrasing
    #       ("the old X", "now I just", "cutting X out entirely",
    #       "stick to Y only") that contradicts implicit form
    #   H — drift active session has v2-distinguishing chunk(s) absent
    #       from its USER turns (assistant-only or other-session
    #       mentions don't establish user agency)
    # Cluster D (narrowing-label vs replacement transition) stays
    # advisory because of false positives on chains with full
    # vocabulary turnover.
    from pipeline.construction.audit_gold_consistency import audit_sample
    findings = audit_sample(sample)
    # Cluster J is hard-fail when it returns a *non-advisory* finding
    # (i.e. survivors < 2). When detail.advisory is True the sample
    # passes ≥2 but has rule-violating items the caller should drop.
    # Note: cluster L (intermediate-version coverage) is intentionally
    # NOT in the blocking set here. It fires only on compact-horizon
    # non-drift, where the realizer-drops-a-version-turn bug lives —
    # but cluster L is paired-group destructive: blocking the compact
    # member would cascade-fail an otherwise-good triple's standard +
    # hard members. Instead, cluster L runs as a member-level advisory
    # and is enforced later in scripts/select_phase3_manifest.py
    # (degrade triple → doublet by dropping the offending compact).
    blocking = [
        f for f in findings
        if f.cluster in ("A", "B", "C", "E", "F", "G", "H")
        or (f.cluster == "J" and not f.detail.get("advisory"))
    ]
    if blocking:
        reasons = "; ".join(f"cluster {f.cluster}: {f.reason}" for f in blocking)
        return f"gold-consistency gate failed: {reasons}"
    return None


def _seed_spec_from(thin: ThinSpine, sessions: list[SessionSpec]) -> SeedSpec:
    return SeedSpec(
        sample_id=thin.sample_id,
        sample_type=thin.sample_type,
        target_type=thin.target_type,
        domain=thin.domain,
        target_description=thin.target_description,
        target_slot_id=thin.target_slot_id,
        topic=thin.topic,
        versions=list(thin.versions),
        sessions=sessions,
        current_query=thin.current_query,
        required_behavior=thin.required_behavior,
        invalid_behavior=list(thin.invalid_behavior),
        subtype=thin.subtype,
        signal_strength=thin.signal_strength,
        scoring=thin.scoring,
        violation_rule_types=list(thin.violation_rule_types),
        notes=thin.notes,
    )


def realize(
    thin: ThinSpine,
    llm: Callable[[str], str],
    *,
    max_retries: int = 3,
    on_attempt: Callable[[int, str | None], None] | None = None,
) -> RealizationResult:
    """Generate sessions for ``thin`` with up to ``max_retries`` attempts.

    Returns a ``RealizationResult`` with either a valid (seed_spec, sample)
    or a populated ``failure_reason``. Raw LLM outputs are kept for audit.
    """
    raw_outputs: list[str] = []
    last_failure: str | None = None
    base_prompt = render_realization_prompt(thin)

    for attempt in range(1, max_retries + 1):
        prompt = base_prompt
        if last_failure:
            prompt += (
                "\n\nPrevious attempt failed validation: "
                f"{last_failure}\nTry again with strict JSON only."
            )
        if on_attempt is not None:
            on_attempt(attempt, last_failure)

        raw = llm(prompt)
        raw_outputs.append(raw)

        try:
            sessions = parse_sessions(raw, expected_n=thin.n_sessions)
        except RealizationParseError as e:
            last_failure = f"parse error: {e}"
            continue

        spec = _seed_spec_from(thin, sessions)
        try:
            sample = materialize(spec)
        except Exception as e:  # noqa: BLE001
            last_failure = f"materialization failed: {type(e).__name__}: {e}"
            continue

        gauntlet_err = _gauntlet_check(sample)
        if gauntlet_err:
            last_failure = gauntlet_err
            continue

        return RealizationResult(
            seed_spec=spec,
            sample=sample,
            raw_outputs=raw_outputs,
            failure_reason=None,
            attempts=attempt,
        )

    return RealizationResult(
        seed_spec=None,
        sample=None,
        raw_outputs=raw_outputs,
        failure_reason=last_failure,
        attempts=max_retries,
    )


__all__ = [
    "RealizationParseError",
    "RealizationResult",
    "ThinSpine",
    "parse_sessions",
    "realize",
    "render_realization_prompt",
]
