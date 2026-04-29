"""Rule-based same-target incompatibility checker (protocol §6.2, data_plan §6.2).

Two version states are treated as competing versions of the same target only
if at least one of the five replacement rules fires:

    1. value_replacement     — same topic, mutually exclusive values
    2. polarity_reversal      — prefer/avoid (or allow/disallow) flip on the same value
    3. procedure_replacement  — workflow W1 violates a required step of W2
    4. boundary_replacement   — interpersonal/topic boundary flips
    5. stance_replacement     — incompatible interpretive frames on same question

Rule decisions are *primary* and schema- or rule-based. LLM judgement may be
used only as a secondary recall filter — kept out of this module deliberately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pipeline.schema import GoldTargetType, Sample, VersionState

RuleName = Literal[
    "value_replacement",
    "polarity_reversal",
    "procedure_replacement",
    "boundary_replacement",
    "stance_replacement",
]


_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _norm(value) -> str:
    if isinstance(value, str):
        s = value
    elif isinstance(value, list):
        s = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        # stable, content-bearing dump
        s = " ".join(f"{k}={v}" for k, v in sorted(value.items()))
    else:
        s = str(value)
    return _NORMALIZE_RE.sub(" ", s.lower()).strip()


def _values_distinct(v1: VersionState, v2: VersionState) -> bool:
    a, b = _norm(v1.value), _norm(v2.value)
    if not a or not b:
        return False
    return a != b


@dataclass
class IncompatibilityResult:
    same_target: bool
    triggered_rules: list[RuleName]
    reason: str

    @property
    def passes(self) -> bool:
        return self.same_target and bool(self.triggered_rules)


def _check_value_replacement(v1: VersionState, v2: VersionState) -> bool:
    """Both versions assert a value on the same topic, and the values differ."""
    if v1.topic != v2.topic:
        return False
    if v1.polarity != "prefer" or v2.polarity != "prefer":
        return False
    return _values_distinct(v1, v2)


def _check_polarity_reversal(v1: VersionState, v2: VersionState) -> bool:
    """Polarities flip across {prefer, avoid} on the same topic value."""
    if v1.topic != v2.topic:
        return False
    flipped = {v1.polarity, v2.polarity} == {"prefer", "avoid"}
    if not flipped:
        return False
    # If they reverse polarity on the same anchored value, that's a polarity
    # flip. If polarities flip but the values also differ, this is interpreted
    # as still a polarity reversal because the user is now disallowing what
    # they previously preferred (or vice versa).
    return True


def _check_procedure_replacement(
    v1: VersionState, v2: VersionState, target_type: GoldTargetType | None
) -> bool:
    if target_type != "procedural_constraint":
        return False
    if v1.topic != v2.topic:
        return False
    if v1.polarity != "constraint" or v2.polarity != "constraint":
        return False
    return _values_distinct(v1, v2)


def _check_boundary_replacement(
    v1: VersionState, v2: VersionState, target_type: GoldTargetType | None
) -> bool:
    if target_type != "interpersonal_boundary":
        return False
    if v1.topic != v2.topic:
        return False
    polarity_flip = {v1.polarity, v2.polarity} == {"prefer", "avoid"}
    constraint_flip = (
        {v1.polarity, v2.polarity} == {"constraint", "prefer"}
        and _values_distinct(v1, v2)
    )
    # 2026-04-26 (Phase 3): constraint→constraint narrowing (e.g.
    # "9–6 weekdays" → "9–6 weekdays except focus blocks") is a valid
    # boundary replacement. Mirrors procedure_replacement's logic for
    # procedural_constraint. Without this rule, narrow chains on
    # interpersonal_boundary with all-constraint polarities fail the
    # gauntlet's same-target check at realize time.
    constraint_narrowing = (
        v1.polarity == "constraint"
        and v2.polarity == "constraint"
        and _values_distinct(v1, v2)
    )
    return polarity_flip or constraint_flip or constraint_narrowing


def _check_stance_replacement(
    v1: VersionState, v2: VersionState, target_type: GoldTargetType | None
) -> bool:
    if target_type != "conceptual_stance":
        return False
    if v1.topic != v2.topic:
        return False
    # Mirror procedure_replacement / boundary_replacement: accept either
    # prefer+prefer (the canonical case for stance preferences) OR
    # constraint+constraint with distinct values (for conceptual stances
    # encoded as behavioral constraints, e.g. "post status as a long
    # written summary" → "post status as terse Slack bullets" where the
    # constraint shape carries the stance).
    if v1.polarity == "prefer" and v2.polarity == "prefer":
        return _values_distinct(v1, v2)
    if v1.polarity == "constraint" and v2.polarity == "constraint":
        return _values_distinct(v1, v2)
    return False


def check_pair(
    v1: VersionState,
    v2: VersionState,
    target_type: GoldTargetType | None = None,
) -> IncompatibilityResult:
    """Run all five rules; report which fire and whether the pair counts as
    same-target competing versions.
    """
    triggered: list[RuleName] = []

    if _check_value_replacement(v1, v2):
        triggered.append("value_replacement")
    if _check_polarity_reversal(v1, v2):
        triggered.append("polarity_reversal")
    if _check_procedure_replacement(v1, v2, target_type):
        triggered.append("procedure_replacement")
    if _check_boundary_replacement(v1, v2, target_type):
        triggered.append("boundary_replacement")
    if _check_stance_replacement(v1, v2, target_type):
        triggered.append("stance_replacement")

    same_target = bool(triggered)
    if not same_target:
        reason = (
            f"no incompatibility rule fired between {v1.version_id!r} and "
            f"{v2.version_id!r} (topic={v1.topic!r} vs {v2.topic!r}; "
            f"polarity={v1.polarity!r} vs {v2.polarity!r}; target_type={target_type!r})"
        )
    else:
        reason = (
            f"competing on rules={triggered}; topic={v1.topic!r}; "
            f"polarity={v1.polarity!r} vs {v2.polarity!r}; "
            f"value={_norm(v1.value)!r} vs {_norm(v2.value)!r}"
        )
    return IncompatibilityResult(
        same_target=same_target, triggered_rules=triggered, reason=reason
    )


@dataclass
class SampleIncompatibilityReport:
    sample_id: str
    pair_results: list[tuple[str, str, IncompatibilityResult]]
    passes: bool


def check_sample(sample: Sample) -> SampleIncompatibilityReport:
    """Validate competing versions on the sample's gold target.

    Pass condition (core supersession): every consecutive pair of versions on
    the gold spine's target_slot_id must satisfy at least one incompatibility
    rule. We also require that all versions in ``target_versions`` share the
    spine's topic anchor.
    """
    versions = sample.gold.target_versions
    target_type = sample.gold.gold_target_type
    pair_results: list[tuple[str, str, IncompatibilityResult]] = []

    if sample.sample_type != "supersession":
        return SampleIncompatibilityReport(
            sample_id=sample.sample_id, pair_results=[], passes=True
        )

    if len(versions) < 2:
        return SampleIncompatibilityReport(
            sample_id=sample.sample_id,
            pair_results=[],
            passes=False,
        )

    # Sort versions by introduction order.
    ordered = sorted(versions, key=lambda v: v.session_introduced)
    all_pass = True
    for v1, v2 in zip(ordered, ordered[1:]):
        result = check_pair(v1, v2, target_type=target_type)
        pair_results.append((v1.version_id, v2.version_id, result))
        if not result.passes:
            all_pass = False
    return SampleIncompatibilityReport(
        sample_id=sample.sample_id, pair_results=pair_results, passes=all_pass
    )


__all__ = [
    "IncompatibilityResult",
    "RuleName",
    "SampleIncompatibilityReport",
    "check_pair",
    "check_sample",
]
