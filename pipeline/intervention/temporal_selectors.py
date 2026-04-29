"""Temporal selectors for the supersession-aware wrapper pipeline.

Two non-LLM ``ActiveVersionSelector`` implementations that resolve the
active state from a list of timestamped ``CandidateUpdate`` objects via
explicit rules (no extra LLM call). They plug into
``MinimalSupersessionWrapper`` as a drop-in replacement for the
LLM-backed selector used by ``sonnet_extract``.

Two architectural points on the temporal-handling spectrum:

  - **B1 ``recency_selector``** — naive temporal: ignore topic, pick the
    candidate with the latest ``session_introduced``. Tests "is taking
    the most recent fact enough?"

  - **B2 ``target_bound_recency_selector``** — supersession-aware
    temporal: group candidates by ``topic``, pick the topic most
    similar to ``current_query``, return that topic's latest
    candidate. Tests "is recency + target-binding enough, even
    without graph reasoning?"

Both use ``session_introduced`` as the temporal proxy (later session
index ≈ later in story time, since sessions are ordered chronologically
in our pool). Neither calls an LLM, so they add no Bedrock cost beyond
the upstream extractor.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from pipeline.intervention.wrapper import CandidateUpdate, CandidateExtractor


# ---------------------------------------------------------------------------
# Caching wrapper around any base CandidateExtractor
# ---------------------------------------------------------------------------


class CachedExtractor:
    """Memoize candidate extraction by ``sample_id`` across selector
    variants. Letting B1 and B2 share the same extraction pass cuts
    Phase 3 N=1000 cost in half compared to running each baseline with
    its own extractor."""

    def __init__(self, base: CandidateExtractor):
        self.base = base
        self.cache: dict[str, list[CandidateUpdate]] = {}

    def __call__(self, public_sample: dict[str, Any]) -> list[CandidateUpdate]:
        sid = public_sample["sample_id"]
        if sid not in self.cache:
            self.cache[sid] = self.base(public_sample)
        return self.cache[sid]

    @property
    def name(self) -> str:
        return getattr(self.base, "name", "cached_extractor")


# ---------------------------------------------------------------------------
# B1 — Temporal Recency Selector
# ---------------------------------------------------------------------------


def recency_selector(
    candidates: list[CandidateUpdate], public_sample: dict[str, Any]
) -> CandidateUpdate | None:
    """B1: pick the candidate with the latest ``session_introduced``.

    No topic-binding, no LLM call. Returns the most-recent candidate
    regardless of which target slot it pertains to. Architectural test:
    is naive recency enough? (Without ``target binding``, this baseline
    will mis-resolve when the most-recent extracted candidate happens
    to be about a different target than the current_query, even though
    it's the latest fact in time.)
    """
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.session_introduced)


# ---------------------------------------------------------------------------
# B2 — Target-Bound Active-State Resolver
# ---------------------------------------------------------------------------


_EMBEDDER_CACHE: dict[str, Any] = {}


def _get_embedder(model_id: str = "BAAI/bge-small-en-v1.5") -> Any:
    """Local sentence-transformer for query↔topic similarity."""
    if model_id in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[model_id]
    from sentence_transformers import SentenceTransformer

    embedder = SentenceTransformer(model_id, device="cuda")
    _EMBEDDER_CACHE[model_id] = embedder
    return embedder


def _pick_query_topic(
    query: str, topics: list[str], embedder: Any
) -> str | None:
    """Return the topic most similar to the query by cosine-similarity
    of BGE embeddings. Topics are short strings (e.g.
    "morning_beverage", "tone_of_voice"); pre-normalize whitespace and
    underscores to give the embedder a chance at semantic match."""
    if not topics:
        return None
    pretty = [t.replace("_", " ") for t in topics]
    embs = embedder.encode(
        pretty + [query], normalize_embeddings=True, convert_to_numpy=True
    )
    topic_embs = embs[: len(topics)]
    query_emb = embs[-1]
    sims = topic_embs @ query_emb
    best = int(np.argmax(sims))
    return topics[best]


def target_bound_recency_selector(
    candidates: list[CandidateUpdate], public_sample: dict[str, Any]
) -> CandidateUpdate | None:
    """B2: group candidates by ``topic``, pick the topic that best
    matches ``current_query`` by embedding similarity, return that
    topic's latest-by-session candidate.

    Adds *target binding* on top of B1's recency. Tests whether
    explicit "this update is about target T" reasoning is needed for
    supersession, or whether the LLM can implicitly handle that
    (sonnet_extract path).
    """
    if not candidates:
        return None
    by_topic: dict[str, list[CandidateUpdate]] = {}
    for c in candidates:
        by_topic.setdefault(c.topic, []).append(c)
    if not by_topic:
        return None
    # Single-topic samples don't need similarity matching.
    if len(by_topic) == 1:
        candidates_in_topic = next(iter(by_topic.values()))
    else:
        embedder = _get_embedder()
        target_topic = _pick_query_topic(
            public_sample.get("current_query", ""),
            list(by_topic.keys()),
            embedder,
        )
        if target_topic is None:
            return None
        candidates_in_topic = by_topic[target_topic]
    return max(candidates_in_topic, key=lambda c: c.session_introduced)


__all__ = [
    "CachedExtractor",
    "recency_selector",
    "target_bound_recency_selector",
]
