"""Recall-query generator (data_plan §7, protocol §8.4).

Recall is *not* latest-version accuracy. It measures retention of historical
versions on the same target. The recall ground truth is therefore the union
of all versions in ``target_versions`` (active + outdated).

This module produces:

- ``recall_query_for(sample)`` — the standard recall prompt.
- ``recall_ground_truth(sample)`` — the gold list of normalized version values.
- ``score_recall(sample, response)`` — token-overlap recall hit rate against
  the ground truth list. Phase 0 implementation; Phase 1 may upgrade to a
  semantic-match scorer using embeddings.

Per protocol §8.4, recall queries are run in an *independent session* from
the behavioral query — that's a runner concern, not enforced here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.schema import Sample, VersionState

RECALL_TEMPLATE = (
    "In our past conversations, what did you learn about my {topic}? "
    "List all versions you recall."
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "at", "for", "with",
    "as", "is", "are", "was", "were", "be", "by", "from", "that", "this",
    "i", "you", "we", "my", "your", "our", "their",
}


def _content_tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _value_tokens(v: VersionState) -> set[str]:
    if isinstance(v.value, str):
        s = v.value
    elif isinstance(v.value, list):
        s = " ".join(str(x) for x in v.value)
    elif isinstance(v.value, dict):
        s = " ".join(str(x) for x in v.value.values())
    else:
        s = str(v.value)
    return _content_tokens(s)


def _spine_topic(sample: Sample) -> str:
    """Use the spine's target description as the topic surface form, falling
    back to the active version's ``topic`` field if the description is empty.
    """
    desc = sample.gold.semantic_spine.target_description.strip()
    if desc:
        return desc
    return sample.gold.violation_predicate.must_honor.topic


def recall_query_for(sample: Sample) -> str | None:
    """Return the recall query for a supersession sample, else None.

    Recall queries are only emitted for supersession samples (data_plan §3, §7).
    """
    if sample.sample_type != "supersession":
        return None
    return RECALL_TEMPLATE.format(topic=_spine_topic(sample))


def recall_ground_truth(sample: Sample) -> list[VersionState]:
    """Ground truth = all versions in history (active + outdated)."""
    if sample.sample_type != "supersession":
        return []
    return list(sample.gold.target_versions)


@dataclass
class RecallScore:
    sample_id: str
    n_versions: int
    n_recovered: int
    per_version: list[tuple[str, bool]]  # (version_id, recovered?)

    @property
    def hit_rate(self) -> float:
        if self.n_versions == 0:
            return 0.0
        return self.n_recovered / self.n_versions


def score_recall(
    sample: Sample, response: str, *, min_overlap: int = 1
) -> RecallScore:
    """Phase 0 token-overlap recall scorer.

    A version is counted as recovered if at least ``min_overlap`` of its
    content tokens appear in the response. This is a deliberately permissive
    bar appropriate for a Phase 0 dry run; Phase 1 should replace this with
    an embedding- or LLM-based semantic match.
    """
    response_tokens = _content_tokens(response)
    versions = recall_ground_truth(sample)
    per: list[tuple[str, bool]] = []
    n_recovered = 0
    for v in versions:
        v_tokens = _value_tokens(v)
        if not v_tokens:
            recovered = False
        else:
            recovered = len(v_tokens & response_tokens) >= min_overlap
        per.append((v.version_id, recovered))
        if recovered:
            n_recovered += 1
    return RecallScore(
        sample_id=sample.sample_id,
        n_versions=len(versions),
        n_recovered=n_recovered,
        per_version=per,
    )


def attach_recall_query(sample: Sample) -> Sample:
    """Return a copy of ``sample`` with ``recall_query`` populated.

    No-op for non-supersession samples.
    """
    if sample.sample_type != "supersession":
        return sample
    rq = recall_query_for(sample)
    return sample.model_copy(update={"recall_query": rq})


__all__ = [
    "RECALL_TEMPLATE",
    "RecallScore",
    "attach_recall_query",
    "recall_ground_truth",
    "recall_query_for",
    "score_recall",
]
