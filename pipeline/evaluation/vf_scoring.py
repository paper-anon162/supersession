"""Version Fidelity scoring (protocol §8.1-§8.3, §14.4).

Three responsibilities:

1. ``apply_default_scoring`` — translate a single ``JudgeVerdict`` into a
   final binary VF, applying the protocol §8.2 ambiguous-response rule
   (default: ambiguous → VF=0). Sensitivity variants (exclude / 0.5) are also
   exposed.

2. ``majority_vote_vf`` — collapse multiple stochastic runs into a single
   sample-level VF via majority vote (protocol §14.4).

3. ``rule_based_shadow_score`` — a deterministic, no-LLM scorer that applies
   the gold ``ViolationPredicate`` rules directly. Used as a sanity baseline
   in tests and as a tie-breaker indicator in pilot validation; NOT the
   primary judge.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Literal

from pipeline.evaluation.judge import JudgeVerdict
from pipeline.schema import Sample, ViolationPredicate

ScoringMode = Literal["default", "exclude_ambiguous", "ambiguous_half"]


# ---------------------------------------------------------------------------
# Single-verdict scoring
# ---------------------------------------------------------------------------


@dataclass
class FinalScore:
    sample_id: str
    vf: float | None  # None means "exclude from this analysis"
    raw_vf: int
    ambiguity_class: str
    confidence: str
    mode: ScoringMode


def apply_default_scoring(
    verdict: JudgeVerdict, mode: ScoringMode = "default"
) -> FinalScore:
    """Translate a judge verdict into the final scored value.

    Default rule: ambiguous responses → VF=0 (protocol §8.2).
    Sensitivity modes are appendix-only.
    """
    is_ambiguous = verdict.ambiguity_class != "not_ambiguous"

    if mode == "default":
        vf: float | None = 0 if is_ambiguous else float(verdict.vf)
    elif mode == "exclude_ambiguous":
        vf = None if is_ambiguous else float(verdict.vf)
    elif mode == "ambiguous_half":
        vf = 0.5 if is_ambiguous else float(verdict.vf)
    else:  # pragma: no cover
        raise ValueError(f"unknown scoring mode {mode!r}")

    return FinalScore(
        sample_id=verdict.sample_id,
        vf=vf,
        raw_vf=verdict.vf,
        ambiguity_class=verdict.ambiguity_class,
        confidence=verdict.confidence,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# Stochastic majority vote (protocol §14.4)
# ---------------------------------------------------------------------------


@dataclass
class StochasticAggregate:
    sample_id: str
    n_runs: int
    final_vf: float | None
    run_level_vfs: list[float | None]
    unstable: bool


def majority_vote_vf(
    verdicts_per_run: Iterable[JudgeVerdict], *, mode: ScoringMode = "default"
) -> StochasticAggregate:
    """Aggregate ``k`` runs of the same sample into majority-vote VF."""
    finals = [apply_default_scoring(v, mode=mode) for v in verdicts_per_run]
    if not finals:
        raise ValueError("no verdicts provided")
    sample_id = finals[0].sample_id
    if any(f.sample_id != sample_id for f in finals):
        raise ValueError("verdicts span multiple sample_ids")
    raw_vfs = [f.vf for f in finals]
    counts = Counter(raw_vfs)
    most_common, top_count = counts.most_common(1)[0]
    second = counts.most_common(2)[1][1] if len(counts) > 1 else 0
    unstable = top_count == second  # tie
    return StochasticAggregate(
        sample_id=sample_id,
        n_runs=len(finals),
        final_vf=most_common,
        run_level_vfs=raw_vfs,
        unstable=unstable,
    )


# ---------------------------------------------------------------------------
# Rule-based shadow scorer (no-LLM, deterministic)
# ---------------------------------------------------------------------------


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "at", "for", "with",
    "as", "is", "are", "was", "were", "be", "by", "from",
}


def _content_words(text: str) -> set[str]:
    return {
        t
        for t in _TOKEN_RE.findall(text.lower())
        if t not in _STOPWORDS and len(t) >= 3
    }


def _value_words(value) -> set[str]:
    if isinstance(value, str):
        s = value
    elif isinstance(value, list):
        s = " ".join(str(v) for v in value)
    elif isinstance(value, dict):
        s = " ".join(str(v) for v in value.values())
    else:
        s = str(value)
    return _content_words(s)


@dataclass
class ShadowScore:
    sample_id: str
    vf: int
    rule_outcomes: dict[str, bool]
    notes: str


def rule_based_shadow_score(sample: Sample, response: str) -> ShadowScore:
    """Apply the gold ``ViolationPredicate`` rules deterministically.

    This is *not* the official judge. It is used in tests to verify that
    obvious cases produce expected scores, and as a sanity flag during pilot
    when LLM-judge calls disagree with the deterministic rules.

    Vocabulary overlap handling: when the active and outdated values share
    tokens (e.g. both contain "voice" or "exploratory"), the overlapping
    tokens are dropped from the outdated-vocabulary set. Otherwise the
    must_not_include_outdated rule would falsely fire on responses that
    legitimately honor the active value.
    """
    predicate: ViolationPredicate = sample.gold.violation_predicate
    active_words = _value_words(predicate.must_honor.value)
    raw_outdated_words: set[str] = set()
    for v in predicate.must_not_honor:
        raw_outdated_words |= _value_words(v.value)
    # Drop tokens that also appear in the active vocabulary; only the *unique*
    # outdated tokens are diagnostic of an outdated-version match.
    outdated_words = raw_outdated_words - active_words
    response_words = _content_words(response)

    rule_outcomes: dict[str, bool] = {}
    for rule in predicate.violation_rules:
        if rule.rule_type == "must_include_active_value":
            rule_outcomes[rule.rule_type] = bool(active_words & response_words)
        elif rule.rule_type == "must_not_include_outdated_value":
            rule_outcomes[rule.rule_type] = not (outdated_words & response_words)
        elif rule.rule_type == "must_not_mix":
            rule_outcomes[rule.rule_type] = not (
                bool(active_words & response_words)
                and bool(outdated_words & response_words)
            )
        elif rule.rule_type == "must_address_target_slot":
            # Permissive: response touches either active or outdated value's
            # vocabulary, or contains spine content tokens.
            spine_words = _content_words(
                sample.gold.semantic_spine.target_description
            )
            rule_outcomes[rule.rule_type] = bool(
                response_words & (active_words | outdated_words | spine_words)
            )
        elif rule.rule_type == "must_not_avoid_required_choice":
            # Approximated: response must mention the active vocabulary.
            rule_outcomes[rule.rule_type] = bool(active_words & response_words)
        else:  # pragma: no cover
            rule_outcomes[rule.rule_type] = True

    vf = 1 if all(rule_outcomes.values()) else 0
    notes = ", ".join(
        f"{k}={v}" for k, v in rule_outcomes.items()
    )
    return ShadowScore(
        sample_id=sample.sample_id, vf=vf, rule_outcomes=rule_outcomes, notes=notes
    )


# ---------------------------------------------------------------------------
# Aggregate over many samples
# ---------------------------------------------------------------------------


def aggregate_vf(scores: Iterable[FinalScore]) -> dict[str, float | int]:
    """Mean VF + counts. Excludes ``vf is None`` from the mean numerator."""
    included = [s for s in scores if s.vf is not None]
    n = len(included)
    n_total = len(list(scores)) if False else None  # avoid double-iteration
    mean = sum(s.vf for s in included) / n if n else 0.0
    return {
        "n": n,
        "n_total": n_total or n,
        "mean_vf": mean,
    }


__all__ = [
    "FinalScore",
    "ScoringMode",
    "ShadowScore",
    "StochasticAggregate",
    "aggregate_vf",
    "apply_default_scoring",
    "majority_vote_vf",
    "rule_based_shadow_score",
]
