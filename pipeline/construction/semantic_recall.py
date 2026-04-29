"""Semantic recall scoring (data_plan §7).

Replaces the Phase 0 token-overlap recall scorer with a sentence-transformer
cosine-similarity match. A version is "recovered" if any of its surface
forms (the literal value plus a few simple paraphrase prompts) has cosine
similarity to the response above the configured threshold.

This is more permissive than token overlap when the response uses
synonymous phrasing, and stricter when the response coincidentally
overlaps stop-content tokens with the value but does not actually mention
the value's meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pipeline.construction.recall_query_gen import recall_ground_truth
from pipeline.schema import Sample, VersionState

# Cache the embedder.
_EMBEDDER_CACHE: dict[str, object] = {}


def _get_embedder(model_id: str = "BAAI/bge-small-en-v1.5"):
    if model_id in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[model_id]
    from sentence_transformers import SentenceTransformer
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedder = SentenceTransformer(model_id, device=device)
    _EMBEDDER_CACHE[model_id] = embedder
    return embedder


def _value_surface_forms(v: VersionState) -> list[str]:
    """Surface forms used to test whether the response 'recalls' the version.

    We deliberately do NOT include the topic name on its own — that would
    make a response which only repeats the topic (e.g. an echo of the query)
    score as recall=1. We want the *value* to be recalled.
    """
    val = v.value
    if isinstance(val, list):
        s = ", ".join(str(x) for x in val)
    elif isinstance(val, dict):
        s = ", ".join(f"{k}={v}" for k, v in val.items())
    else:
        s = str(val)
    s = s.strip()
    if not s:
        return []
    forms = [s]
    if v.polarity == "avoid":
        forms.append(f"avoid {s}")
    elif v.polarity == "constraint":
        forms.append(f"a {s} constraint")
    return forms


@dataclass
class SemanticRecallScore:
    sample_id: str
    n_versions: int
    n_recovered: int
    per_version: list[tuple[str, float, bool]]
    threshold: float

    @property
    def hit_rate(self) -> float:
        if self.n_versions == 0:
            return 0.0
        return self.n_recovered / self.n_versions


def score_recall_semantic(
    sample: Sample,
    response: str,
    *,
    threshold: float = 0.65,
    embedder_id: str = "BAAI/bge-small-en-v1.5",
) -> SemanticRecallScore:
    """Cosine-similarity recall scorer.

    A version is recovered if at least one of its surface forms has cosine
    similarity ≥ ``threshold`` with the response.
    """
    versions = recall_ground_truth(sample)
    if not versions:
        return SemanticRecallScore(
            sample_id=sample.sample_id,
            n_versions=0,
            n_recovered=0,
            per_version=[],
            threshold=threshold,
        )
    import numpy as np

    embedder = _get_embedder(embedder_id)
    response_emb = embedder.encode(
        [response], normalize_embeddings=True, convert_to_numpy=True
    )[0]

    per: list[tuple[str, float, bool]] = []
    n_recovered = 0
    for v in versions:
        forms = _value_surface_forms(v)
        form_embs = embedder.encode(
            forms, normalize_embeddings=True, convert_to_numpy=True
        )
        sims = form_embs @ response_emb
        best = float(np.max(sims))
        recovered = best >= threshold
        per.append((v.version_id, best, recovered))
        if recovered:
            n_recovered += 1
    return SemanticRecallScore(
        sample_id=sample.sample_id,
        n_versions=len(versions),
        n_recovered=n_recovered,
        per_version=per,
        threshold=threshold,
    )


__all__ = ["SemanticRecallScore", "score_recall_semantic"]
