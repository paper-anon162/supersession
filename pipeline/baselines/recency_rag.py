"""Custom Temporal-RAG baseline (data_plan §10.4).

A lightweight temporal-memory baseline: each session is encoded as a
single embedding via local BGE, stored with its ``valid_at`` timestamp.
Retrieval ranks by similarity score scaled by ``exp(-Δt / halflife)``,
favoring recent over old facts. Top-k retrieved sessions are injected
into the answer-generation backbone (Llama 3.1 8B).

This is intentionally simpler than Graphiti's bi-temporal knowledge
graph: no entity dedup, no LLM-driven invalidation, no graph traversal —
only timestamped vector retrieval with recency rerank. The architectural
ablation question this baseline answers:

  "Is *temporal metadata + recency rerank* enough to capture
   supersession, or do we need full bi-temporal graph reasoning
   (Graphiti)?"

If Custom Temporal-RAG performs near Graphiti, the paper's headline
becomes "expensive graph reasoning is unnecessary; recency-weighted
retrieval suffices." If Graphiti dominates, the headline is the
opposite. Either result is a meaningful architectural finding.

Cost profile vs Graphiti:
  - 0 LLM calls per sample on ingest (vs Graphiti's 25-45)
  - 0 LLM calls per sample on retrieval (vs Graphiti's ~5-10)
  - 1 LLM call per sample for answer generation (Llama 8B, same as all
    other baselines)
  - Embedding via local BGE (no Bedrock spend)
  - Phase 3 N=1000 estimated: <$1 total + ~30 min wall
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from pipeline.baselines.naive_rag import _Chunk, _chunk_per_session, _cosine_top_k, _get_embedder
from pipeline.schema import RunMetadata


# ---------------------------------------------------------------------------
# Recency-weighting helpers
# ---------------------------------------------------------------------------


def _parse_ts(ts: str | None) -> datetime:
    """Parse an ISO-format timestamp string. Falls back to epoch on
    None/invalid so missing-timestamp facts get effectively-zero weight
    in the recency rerank without crashing."""
    if not ts:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    try:
        # Strip trailing Z or +HH:MM and let fromisoformat parse;
        # accept both "2026-01-04T08:00:00Z" and "2026-01-04T08:00:00+00:00".
        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.fromtimestamp(0, tz=timezone.utc)


def _recency_weight(ts: datetime, ref_ts: datetime, halflife_days: float) -> float:
    """exp(-Δt/halflife) with halflife given in days. ``ref_ts`` is
    typically the latest session's timestamp (so the most-recent fact
    gets weight ~1.0 and older facts decay toward 0)."""
    if halflife_days <= 0:
        return 1.0
    delta = ref_ts - ts
    age_days = max(0.0, delta.total_seconds() / 86400.0)
    # exp(-ln2 * age / halflife) = 0.5^(age/halflife)
    return math.pow(0.5, age_days / halflife_days)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass
class RecencyRAGConfig:
    """Custom Temporal-RAG knobs.

    The pilot grid (data_plan §10.2 v1.3.7) varies ``top_k`` ∈ {5, 10, 20}
    and ``recency_halflife_days`` ∈ {7, 30, 90}. The winning config is
    locked before the main run.
    """

    top_k: int = 5
    # Recency-decay halflife in days. Older facts get weight 0.5 once
    # this many days have passed since the latest session. 30 days is
    # a reasonable default for our weekly-spaced multi-session samples.
    recency_halflife_days: float = 30.0
    embedding_model_id: str = "BAAI/bge-small-en-v1.5"


@dataclass
class RecencyRAGBaseline:
    """Vector RAG with timestamp metadata and recency-weighted retrieval.

    Conforms to the ``Baseline`` Protocol in
    ``pipeline.baselines.runner`` (``respond(public_sample) -> str``
    plus ``run_metadata``). Mirrors ``NaiveRAGBaseline`` shape; the
    only architectural difference is the recency-weighted scoring at
    retrieval time.
    """

    backbone: Any
    config: RecencyRAGConfig = field(default_factory=RecencyRAGConfig)
    name: str = "recency_rag"
    answer_backbone_provider: str = "bedrock"
    extra: dict[str, Any] = field(default_factory=dict)

    def respond(self, public_sample: dict[str, Any]) -> str:
        chunks = _chunk_per_session(public_sample["history"])
        if not chunks:
            return self._answer_with([], public_sample)

        embedder = _get_embedder(self.config.embedding_model_id)
        query = public_sample["current_query"]
        injection = public_sample.get("_intervention_injection")

        chunk_embs = embedder.encode(
            [c.text for c in chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        query_emb = embedder.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        # Compute raw similarity for all chunks.
        sims = chunk_embs @ query_emb  # both L2-normalized → dot product == cosine
        # Recency weight per chunk, anchored at the latest chunk's
        # timestamp (so the freshest fact has weight 1.0).
        timestamps = [_parse_ts(c.metadata.get("timestamp")) for c in chunks]
        ref_ts = max(timestamps)
        weights = np.array([
            _recency_weight(t, ref_ts, self.config.recency_halflife_days)
            for t in timestamps
        ])
        # Final score = similarity × recency_weight. Higher is better.
        scored = sims * weights
        k = min(self.config.top_k, len(scored))
        top_idx = list(np.argsort(-scored)[:k])
        retrieved = [chunks[i] for i in top_idx]
        return self._answer_with(retrieved, public_sample, injection=injection)

    def _answer_with(
        self,
        retrieved: list[_Chunk],
        public_sample: dict[str, Any],
        *,
        injection: str | None = None,
    ) -> str:
        if retrieved:
            retrieved_block = "\n\n".join(c.text for c in retrieved)
            prompt = (
                f"=== Retrieved memory (top-{self.config.top_k}, "
                f"recency-weighted halflife="
                f"{self.config.recency_halflife_days:.0f}d) ===\n"
                f"{retrieved_block}\n\n"
                f"=== Current request ===\n{public_sample['current_query']}\n"
            )
        else:
            prompt = f"=== Current request ===\n{public_sample['current_query']}\n"
        if injection:
            prompt = f"{prompt}\n=== Note ===\n{injection}\n"
        bb = self.backbone
        original = bb.system_prompt
        bb.system_prompt = RECENCY_RAG_SYSTEM
        try:
            return bb(prompt)
        finally:
            bb.system_prompt = original

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="local",
            answer_backbone=self.backbone.model_id,
            answer_backbone_provider=self.answer_backbone_provider,  # type: ignore[arg-type]
            embedding_model=self.config.embedding_model_id,
            embedding_provider="local",
            uses_full_history=False,
            uses_retrieved_memory=True,
            prompt_template_id=(
                f"recency_rag/topk{self.config.top_k}_halflife"
                f"{self.config.recency_halflife_days:.0f}d/v1"
            ),
            temperature=self.backbone.temperature,
            max_tokens=self.backbone.max_new_tokens,
        )


RECENCY_RAG_SYSTEM = (
    "You are a personal assistant. The retrieved memory is ranked by "
    "similarity to your current request and weighted by recency: more "
    "recent facts are favored over older ones. Treat the most recent "
    "retrieved fact as the user's current state of preference; older "
    "facts are historical context. Respond directly to the current "
    "request."
)


__all__ = ["RecencyRAGBaseline", "RecencyRAGConfig", "RECENCY_RAG_SYSTEM"]
