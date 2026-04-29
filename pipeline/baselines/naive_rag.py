"""Naive RAG baseline (protocol §11; data_plan §10.4).

Chunks the per-sample history (one chunk per session by default), embeds
each chunk and the current query using a local sentence-transformer, picks
the top-k chunks by cosine similarity, and feeds the retrieved chunks plus
the query to the answer-generation backbone.

This is the retrieval lower-bound — it has no temporal awareness, no
version tracking, no graph structure. It is *deliberately* simple: the
benchmark's premise is that pure retrieval cannot solve supersession, and
this baseline is the canonical illustration of that.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pipeline.evaluation.local_backbone import HFTransformersBackbone
from pipeline.schema import RunMetadata


@dataclass
class _Chunk:
    text: str
    metadata: dict[str, Any]


def _chunk_per_session(history: list[dict[str, Any]]) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    for s in history:
        ts = s.get("timestamp")
        body = "\n".join(f"{t['role']}: {t['text']}" for t in s["turns"])
        head = f"[Session {s['session_id']}{(' @ ' + ts) if ts else ''}]"
        text = f"{head}\n{body}"
        chunks.append(
            _Chunk(text=text, metadata={"session_id": s["session_id"], "timestamp": ts})
        )
    return chunks


# Cache the embedder across calls so we don't reload weights per sample.
_EMBEDDER_CACHE: dict[str, Any] = {}


def _get_embedder(model_id: str):
    if model_id in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[model_id]
    from sentence_transformers import SentenceTransformer

    embedder = SentenceTransformer(model_id, device="cuda")
    _EMBEDDER_CACHE[model_id] = embedder
    return embedder


def _cosine_top_k(q: np.ndarray, M: np.ndarray, k: int) -> list[int]:
    # Both rows already L2-normalized by sentence-transformers when
    # ``normalize_embeddings=True``.
    sims = M @ q
    k = min(k, len(sims))
    return list(np.argsort(-sims)[:k])


@dataclass
class NaiveRAGBaseline:
    """Top-k embedding-retrieval RAG with a shared answer backbone."""

    backbone: HFTransformersBackbone
    embedding_model_id: str = "BAAI/bge-small-en-v1.5"
    top_k: int = 5
    name: str = "naive_rag_local"
    answer_backbone_provider: str = "local"
    extra: dict[str, Any] = field(default_factory=dict)

    def respond(self, public_sample: dict[str, Any]) -> str:
        chunks = _chunk_per_session(public_sample["history"])
        if not chunks:
            return self._answer_with([], public_sample)

        embedder = _get_embedder(self.embedding_model_id)
        query = public_sample["current_query"]
        injection = public_sample.get("_intervention_injection")

        chunk_embs = embedder.encode(
            [c.text for c in chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # Sentence-transformers convention for bge: prefix queries with
        # "Represent this sentence for searching relevant passages:" — we use
        # the simpler approach of just embedding the raw query, which works
        # fine for our short queries.
        query_emb = embedder.encode(
            [query], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        top_idx = _cosine_top_k(query_emb, chunk_embs, self.top_k)
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
                f"=== Retrieved memory (top-{self.top_k}) ===\n{retrieved_block}\n\n"
                f"=== Current request ===\n{public_sample['current_query']}\n"
            )
        else:
            prompt = f"=== Current request ===\n{public_sample['current_query']}\n"
        if injection:
            prompt = f"{prompt}\n=== Note ===\n{injection}\n"
        bb = self.backbone
        original = bb.system_prompt
        bb.system_prompt = NAIVE_RAG_SYSTEM
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
            embedding_model=self.embedding_model_id,
            embedding_provider="local",
            uses_full_history=False,
            uses_retrieved_memory=True,
            prompt_template_id="naive_rag/per_session_topk/v1",
            temperature=self.backbone.temperature,
            max_tokens=self.backbone.max_new_tokens,
        )


NAIVE_RAG_SYSTEM = (
    "You are a personal assistant. Use the retrieved memory to "
    "understand the user's preferences and constraints. Respond "
    "directly to the current request."
)


__all__ = ["NaiveRAGBaseline", "NAIVE_RAG_SYSTEM"]
