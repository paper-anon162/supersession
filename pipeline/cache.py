"""Local-first cache layers for benchmark runs.

Design goals (per the cache spec accepted 2026-04-25):

  * Content-addressed: cache keys are SHA-256 hashes of the
    deterministic inputs to the operation (sample content, prompt,
    model id, decoding params). Same inputs → same key → same row.
  * Append-immediately, merge-later: each writer process appends
    JSONL records to its own ``shards/{run_id}.jsonl`` file. A
    separate ``merge_cache_shards.py`` step combines shards into
    ``merged.jsonl`` for read paths.
  * Crash-safe writes: each row is a single line terminated by a
    newline. Partial writes leave at most one malformed line; readers
    skip such lines.
  * Schema-versioned: every row carries ``cache_format_version`` so
    future format changes can be migrated explicitly.

Cache layers:

  1. Response cache    — ``data/cache/responses/``
  2. Wrapper-trace cache — ``data/cache/wrapper_traces/``  (P1)
  3. Verdict cache     — ``data/cache/verdicts/``
  4. Embedding cache   — ``data/cache/embeddings/``         (P2)

This module exposes the primitives every layer uses; per-layer
key composition lives in ``make_*_key`` helpers below.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

CACHE_FORMAT_VERSION = 1

REPO = Path(__file__).resolve().parents[1]
CACHE_ROOT = REPO / "data" / "cache"


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def short_hash(value: Any, *, length: int = 16) -> str:
    """Return a stable short hex digest of ``value``.

    ``value`` is JSON-serialised with sorted keys so dict ordering does
    not affect the digest. ``length`` characters of the SHA-256 hex
    digest are returned (default 16 = 64 bits, sufficient for cache
    keys at our scale).
    """
    if isinstance(value, str):
        payload = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray)):
        payload = bytes(value)
    else:
        payload = json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


# ---------------------------------------------------------------------------
# Cache-key composition
# ---------------------------------------------------------------------------


def public_content_hash(sample: Any) -> str:
    """Hash only the public fields of a Sample (history, current_query,
    sample_type). Use for response caches of public-facing systems
    (long_context, naive_rag, intervention wrappers, ablated, query_only)
    so gold-only metadata edits (e.g. ambiguity_class flags) do not
    invalidate their cached responses.
    """
    if hasattr(sample, "model_dump"):
        payload = sample.model_dump(by_alias=True)
    else:
        payload = sample
    keys = ("history", "current_query", "sample_type")
    minimal = {k: payload.get(k) for k in keys if k in payload}
    return short_hash(minimal, length=16)


def gold_content_hash(sample: Any) -> str:
    """Hash public fields plus ``_gold``. Use for response caches that
    actually depend on gold (oracle injection) and for verdict caches
    (judge prompt embeds gold). When gold changes, these must rebuild.
    """
    if hasattr(sample, "model_dump"):
        payload = sample.model_dump(by_alias=True)
    else:
        payload = sample
    keys = ("history", "current_query", "sample_type", "_gold")
    minimal = {k: payload.get(k) for k in keys if k in payload}
    return short_hash(minimal, length=16)


def sample_content_hash(sample: Any) -> str:
    """Backward-compatible alias = ``gold_content_hash``.

    Historical name. Most call sites should migrate to
    :func:`public_content_hash` (response caches of public systems) or
    :func:`gold_content_hash` (oracle response cache + all verdict
    caches). Keeping the alias avoids breaking external scripts; new
    code should import the explicit name.
    """
    return gold_content_hash(sample)


def history_hash(sample: Any) -> str:
    """Hash just the history (used by wrapper-trace and embedding caches)."""
    if hasattr(sample, "model_dump"):
        payload = sample.model_dump(by_alias=True)
    else:
        payload = sample
    return short_hash(payload.get("history", []), length=16)


_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _file_sha(path: Path) -> str:
    """SHA-256 of a file's content. Empty string on missing file."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def system_artifact_hash(system_name: str, **extras: Any) -> str:
    """Compute a content-addressed hash of the prompt + config artifacts
    that determine a system's rendered prompt.

    Replaces the brittle manual ``SYSTEM_VERSIONS["v1"]`` literal: any
    edit to a referenced prompt template, system prompt string, or
    listed config knob auto-invalidates the response cache for that
    system. Forgetting to bump a version sentinel can no longer
    silently reuse stale cache entries on a new prompt.

    ``extras`` lets callers thread in dynamic config that the system
    depends on (e.g. ``embedding_model_id`` for naive_rag,
    ``injection_format`` for intervention/oracle, sonnet extractor
    model id for the sonnet-extract diagnostic).
    """
    artifacts: dict[str, Any] = {"system": system_name}

    # Inline system-prompt strings (live in module-level constants).
    # We import lazily to avoid circular imports during cache module
    # bootstrap.
    if system_name in (
        "long_context_local",
        "long_context_sonnet46",
        "long_context_mistral",
    ):
        try:
            from pipeline.baselines.long_context import LONG_CONTEXT_SYSTEM
            artifacts["long_context_system"] = LONG_CONTEXT_SYSTEM
        except Exception:  # noqa: BLE001
            pass
    elif system_name == "naive_rag_local":
        try:
            from pipeline.baselines.naive_rag import NAIVE_RAG_SYSTEM
            artifacts["naive_rag_system"] = NAIVE_RAG_SYSTEM
        except Exception:  # noqa: BLE001
            artifacts["naive_rag_system_inline"] = "v1"

    # Prompt template files (`.jinja`).
    file_artifacts: dict[str, str] = {}
    if system_name == "intervention_wrapper":
        file_artifacts["extract"] = _file_sha(
            _PROMPTS_DIR / "intervention_extract.jinja"
        )
        file_artifacts["select"] = _file_sha(
            _PROMPTS_DIR / "intervention_select.jinja"
        )
    elif system_name in (
        "intervention_wrapper_drift_aware",
        "intervention_wrapper_drift_aware_sonnet_extract",
    ):
        file_artifacts["extract"] = _file_sha(
            _PROMPTS_DIR / "intervention_extract_drift_aware.jinja"
        )
        file_artifacts["select"] = _file_sha(
            _PROMPTS_DIR / "intervention_select.jinja"
        )
    if file_artifacts:
        artifacts["prompts"] = file_artifacts

    # Caller-supplied dynamic config.
    if extras:
        artifacts["extras"] = extras

    return short_hash(artifacts, length=16)


def make_response_key(
    *,
    sample_content_hash: str,
    system_name: str,
    model_id: str,
    rendered_prompt_hash: str,
    max_new_tokens: int,
    temperature: float,
) -> str:
    """Cache key for one (sample, system) → response generation."""
    return short_hash(
        {
            "kind": "response",
            "sample": sample_content_hash,
            "system": system_name,
            "model": model_id,
            "prompt": rendered_prompt_hash,
            "max_new_tokens": max_new_tokens,
            "temperature": float(temperature),
        },
        length=24,
    )


def make_wrapper_trace_key(
    *,
    sample_content_hash: str,
    system_name: str,
    history_hash: str,
    extractor_model_id: str,
    extractor_prompt_hash: str,
    selector_version: str,
) -> str:
    """Cache key for the wrapper's extract-and-select intermediate."""
    return short_hash(
        {
            "kind": "wrapper_trace",
            "sample": sample_content_hash,
            "system": system_name,
            "history": history_hash,
            "extractor_model": extractor_model_id,
            "extractor_prompt": extractor_prompt_hash,
            "selector_version": selector_version,
        },
        length=24,
    )


def make_verdict_key(
    *,
    sample_content_hash: str,
    system_name: str,
    response_key: str,
    judge_model_id: str,
    judge_prompt_hash: str,
) -> str:
    """Cache key for one judge verdict on a (sample, system, response)."""
    return short_hash(
        {
            "kind": "verdict",
            "sample": sample_content_hash,
            "system": system_name,
            "response_key": response_key,
            "judge_model": judge_model_id,
            "judge_prompt": judge_prompt_hash,
        },
        length=24,
    )


def make_embedding_key(
    *,
    sample_content_hash: str,
    history_hash: str,
    embedding_model: str,
    chunker_version: str,
) -> str:
    """Cache key for the per-sample retrieval embedding bundle."""
    return short_hash(
        {
            "kind": "embedding",
            "sample": sample_content_hash,
            "history": history_hash,
            "embedding_model": embedding_model,
            "chunker_version": chunker_version,
        },
        length=24,
    )


# ---------------------------------------------------------------------------
# JSONL append + load
# ---------------------------------------------------------------------------


def append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    """Append a single JSONL row, ensuring crash-safe semantics.

    Uses a single ``write`` call followed by ``flush`` and ``fsync`` so
    a crash mid-line yields at most one malformed trailing line.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    data = line.encode("utf-8")
    fd = os.open(p, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Iterate JSONL rows from ``path``. Skips blank or malformed lines."""
    p = Path(path)
    if not p.exists():
        return
    with p.open() as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Crash-safety: skip the at-most-one malformed trailing line.
                continue


# ---------------------------------------------------------------------------
# Cache index loading + shard merge
# ---------------------------------------------------------------------------


@dataclass
class CacheIndex:
    """In-memory index: cache_key → row payload, loaded once per run.

    Reads ``merged.jsonl`` (the canonical merge output) plus all
    ``shards/*.jsonl`` files so a freshly-written shard row is visible
    without a merge pass. On duplicate keys with same payload, last
    writer wins (cheap O(1) overwrite). Conflicts (same key, different
    payload) are surfaced as :class:`CacheConflictError` only by
    ``merge_shards``.
    """

    layer_dir: Path
    rows: dict[str, dict[str, Any]]

    def get(self, cache_key: str) -> dict[str, Any] | None:
        return self.rows.get(cache_key)

    def __contains__(self, cache_key: str) -> bool:
        return cache_key in self.rows

    def __len__(self) -> int:
        return len(self.rows)


def load_cache_index(layer_dir: str | Path) -> CacheIndex:
    """Load ``merged.jsonl`` ∪ ``shards/*.jsonl`` for one cache layer."""
    layer = Path(layer_dir)
    rows: dict[str, dict[str, Any]] = {}
    merged = layer / "merged.jsonl"
    if merged.exists():
        for r in iter_jsonl(merged):
            key = r.get("cache_key")
            if key:
                rows[key] = r
    shard_dir = layer / "shards"
    if shard_dir.exists():
        for shard in sorted(shard_dir.glob("*.jsonl")):
            for r in iter_jsonl(shard):
                key = r.get("cache_key")
                if key:
                    rows[key] = r
    return CacheIndex(layer_dir=layer, rows=rows)


def shard_path(layer_dir: str | Path, run_id: str | None = None) -> Path:
    """Return the path of the shard JSONL this process should append to.

    ``run_id`` defaults to ``${BENCH_RUN_ID}`` env var, or
    ``"pid{pid}-{epoch_ms}"`` otherwise. One shard per run/process so
    parallel writers don't contend on the same file.
    """
    layer = Path(layer_dir)
    if run_id is None:
        run_id = os.environ.get("BENCH_RUN_ID")
    if not run_id:
        run_id = f"pid{os.getpid()}-{int(time.time() * 1000)}"
    return layer / "shards" / f"{run_id}.jsonl"


# ---------------------------------------------------------------------------
# Conflict detection (used by merge_cache_shards)
# ---------------------------------------------------------------------------


class CacheConflictError(RuntimeError):
    """Raised when two shards report different payloads for the same key."""

    def __init__(self, cache_key: str, a: dict, b: dict, source_a: str, source_b: str):
        self.cache_key = cache_key
        self.a = a
        self.b = b
        self.source_a = source_a
        self.source_b = source_b
        super().__init__(
            f"cache conflict on key {cache_key!r}: "
            f"{source_a} vs {source_b} disagree on payload"
        )


_CONFLICT_IGNORE_FIELDS = {
    # Wall-clock fields naturally vary; they don't define cache equivalence.
    "elapsed_seconds",
    "elapsed",
    "wall_clock_ms",
    "written_at",
    "_run_id",
}


def _payload_for_compare(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in _CONFLICT_IGNORE_FIELDS}


def merge_shards(
    layer_dir: str | Path,
    *,
    on_conflict: str = "fail",
) -> dict[str, Any]:
    """Merge ``shards/*.jsonl`` + ``merged.jsonl`` → fresh ``merged.jsonl``.

    Parameters
    ----------
    layer_dir
        Cache layer directory (e.g. ``data/cache/responses``).
    on_conflict
        ``"fail"`` (default), ``"accept_first"``, or ``"accept_latest"``.
        Conflict = same ``cache_key`` reported in two shards with
        non-equivalent payloads (per ``_payload_for_compare``).

    Returns
    -------
    Summary dict: ``{"merged_rows": N, "conflicts_resolved": M, ...}``.
    """
    if on_conflict not in ("fail", "accept_first", "accept_latest"):
        raise ValueError(f"bad on_conflict {on_conflict!r}")
    layer = Path(layer_dir)
    rows: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    n_seen = 0
    n_conflicts = 0

    sources_in_order: list[Path] = []
    merged_path = layer / "merged.jsonl"
    if merged_path.exists():
        sources_in_order.append(merged_path)
    shard_dir = layer / "shards"
    if shard_dir.exists():
        sources_in_order.extend(sorted(shard_dir.glob("*.jsonl")))

    for src in sources_in_order:
        src_label = str(src.relative_to(layer))
        for r in iter_jsonl(src):
            key = r.get("cache_key")
            if not key:
                continue
            n_seen += 1
            existing = rows.get(key)
            if existing is None:
                rows[key] = r
                sources[key] = src_label
                continue
            if _payload_for_compare(existing) == _payload_for_compare(r):
                # Same content, just refresh source bookkeeping.
                if on_conflict == "accept_latest":
                    rows[key] = r
                    sources[key] = src_label
                continue
            # Real conflict.
            n_conflicts += 1
            if on_conflict == "fail":
                raise CacheConflictError(key, existing, r, sources[key], src_label)
            if on_conflict == "accept_latest":
                rows[key] = r
                sources[key] = src_label
            # accept_first: leave existing in place.

    # Atomic-ish rewrite: write to .tmp then rename.
    out_tmp = layer / "merged.jsonl.tmp"
    out_tmp.parent.mkdir(parents=True, exist_ok=True)
    with out_tmp.open("w") as f:
        for key in sorted(rows.keys()):
            f.write(json.dumps(rows[key], ensure_ascii=False, separators=(",", ":")) + "\n")
    out_tmp.replace(merged_path)

    return {
        "merged_rows": len(rows),
        "conflicts_resolved": n_conflicts,
        "rows_seen": n_seen,
        "sources": [str(p.relative_to(layer)) for p in sources_in_order],
        "merged_path": str(merged_path),
    }


__all__ = [
    "CACHE_FORMAT_VERSION",
    "CACHE_ROOT",
    "CacheConflictError",
    "CacheIndex",
    "append_jsonl",
    "history_hash",
    "iter_jsonl",
    "load_cache_index",
    "make_embedding_key",
    "make_response_key",
    "make_verdict_key",
    "make_wrapper_trace_key",
    "merge_shards",
    "sample_content_hash",
    "shard_path",
    "short_hash",
]
