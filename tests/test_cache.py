"""Tests for pipeline.cache (P0 cache infrastructure)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.cache import (
    CACHE_FORMAT_VERSION,
    CacheConflictError,
    append_jsonl,
    gold_content_hash,
    iter_jsonl,
    load_cache_index,
    make_embedding_key,
    make_response_key,
    make_verdict_key,
    make_wrapper_trace_key,
    merge_shards,
    public_content_hash,
    sample_content_hash,
    short_hash,
    system_artifact_hash,
)


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_short_hash_is_deterministic_across_dict_orderings():
    a = short_hash({"a": 1, "b": [2, 3]})
    b = short_hash({"b": [2, 3], "a": 1})
    assert a == b


def test_short_hash_changes_when_value_changes():
    assert short_hash("hello") != short_hash("hello!")
    assert short_hash({"x": 1}) != short_hash({"x": 2})


def test_short_hash_length_param():
    assert len(short_hash("x", length=8)) == 8
    assert len(short_hash("x", length=24)) == 24


def test_short_hash_handles_bytes_str_dict_uniformly():
    # Different surface representations should be allowed; we just check
    # each one returns a stable hex string.
    for v in (b"abc", "abc", {"a": 1}, [1, 2, 3]):
        h = short_hash(v)
        assert isinstance(h, str)
        assert len(h) == 16


# ---------------------------------------------------------------------------
# Key composition
# ---------------------------------------------------------------------------


def _kwargs_response():
    return dict(
        sample_content_hash="s1",
        system_name="long_context_qwen",
        model_id="Qwen/Qwen2.5-7B-Instruct",
        rendered_prompt_hash="p1",
        max_new_tokens=300,
        temperature=0.0,
    )


def test_make_response_key_is_stable_and_field_sensitive():
    base = make_response_key(**_kwargs_response())
    assert base == make_response_key(**_kwargs_response())
    # Each field changes the key.
    for field, new in [
        ("sample_content_hash", "s2"),
        ("system_name", "different_sys"),
        ("model_id", "claude-sonnet-4-6"),
        ("rendered_prompt_hash", "p2"),
        ("max_new_tokens", 600),
        ("temperature", 0.7),
    ]:
        kw = _kwargs_response()
        kw[field] = new
        assert make_response_key(**kw) != base, f"{field} did not change key"


def test_make_response_key_temperature_normalized_int_vs_float():
    a = make_response_key(**{**_kwargs_response(), "temperature": 0})
    b = make_response_key(**{**_kwargs_response(), "temperature": 0.0})
    assert a == b


def test_make_wrapper_trace_key_is_distinct_from_response_key():
    rkey = make_response_key(**_kwargs_response())
    wkey = make_wrapper_trace_key(
        sample_content_hash="s1",
        system_name="intervention_wrapper",
        history_hash="h1",
        extractor_model_id="Qwen/Qwen2.5-7B-Instruct",
        extractor_prompt_hash="ep1",
        selector_version="v1",
    )
    assert rkey != wkey


def test_make_verdict_key_depends_on_response_key():
    a = make_verdict_key(
        sample_content_hash="s1",
        system_name="long_context_qwen",
        response_key="rk1",
        judge_model_id="us.anthropic.claude-opus-4-6-v1",
        judge_prompt_hash="jp1",
    )
    b = make_verdict_key(
        sample_content_hash="s1",
        system_name="long_context_qwen",
        response_key="rk2",  # different response → different verdict cache row
        judge_model_id="us.anthropic.claude-opus-4-6-v1",
        judge_prompt_hash="jp1",
    )
    assert a != b


def test_make_embedding_key_changes_with_chunker_version():
    a = make_embedding_key(
        sample_content_hash="s1", history_hash="h1",
        embedding_model="BAAI/bge-small-en-v1.5", chunker_version="v1",
    )
    b = make_embedding_key(
        sample_content_hash="s1", history_hash="h1",
        embedding_model="BAAI/bge-small-en-v1.5", chunker_version="v2",
    )
    assert a != b


def test_sample_content_hash_dict_input():
    payload = {
        "history": [{"session_id": "s1", "turns": []}],
        "current_query": "q",
        "sample_type": "supersession",
        "_gold": {"semantic_spine": {"target_slot_id": "x::v1"}},
    }
    h1 = sample_content_hash(payload)
    h2 = sample_content_hash({**payload, "history": []})
    assert h1 != h2


def test_public_hash_ignores_gold_metadata_edits():
    """public_content_hash must NOT change when _gold is edited (e.g.
    when scripts/mark_ambiguous.py adds an ambiguity_class flag).
    Only history / current_query / sample_type matter to public systems."""
    payload = {
        "history": [{"session_id": "s1", "turns": []}],
        "current_query": "q",
        "sample_type": "supersession",
        "_gold": {"metadata": {"horizon": "compact"}},
    }
    edited = {**payload, "_gold": {"metadata": {
        "horizon": "compact", "ambiguity_class": "ambiguous_active_evidence"
    }}}
    assert public_content_hash(payload) == public_content_hash(edited)


def test_gold_hash_changes_on_gold_edit():
    """gold_content_hash MUST change when _gold changes — used by oracle
    response cache and all verdict caches, which both depend on gold."""
    payload = {
        "history": [{"session_id": "s1", "turns": []}],
        "current_query": "q",
        "sample_type": "supersession",
        "_gold": {"metadata": {"horizon": "compact"}},
    }
    edited = {**payload, "_gold": {"metadata": {
        "horizon": "compact", "ambiguity_class": "ambiguous_active_evidence"
    }}}
    assert gold_content_hash(payload) != gold_content_hash(edited)


def test_public_and_gold_hashes_diverge_when_gold_present():
    payload = {
        "history": [{"session_id": "s1", "turns": []}],
        "current_query": "q",
        "sample_type": "supersession",
        "_gold": {"metadata": {"horizon": "compact"}},
    }
    assert public_content_hash(payload) != gold_content_hash(payload)


def test_system_artifact_hash_distinguishes_systems():
    """Each public-system name should produce a distinct artifact hash."""
    names = (
        "long_context_local",
        "naive_rag_local",
        "intervention_wrapper",
        "intervention_wrapper_drift_aware",
        "intervention_wrapper_drift_aware_sonnet_extract",
        "ablated_wrapper",
        "oracle_current_version",
        "query_only",
    )
    hashes = {n: system_artifact_hash(n) for n in names}
    assert len(set(hashes.values())) == len(names), (
        f"system_artifact_hash collisions across systems: {hashes}"
    )


def test_system_artifact_hash_propagates_extras():
    """Caller-threaded extras (top_k, embedding model, injection_format,
    etc.) must change the hash. Forgetting to bump version sentinels
    can no longer silently reuse stale cache on a config change."""
    a = system_artifact_hash("naive_rag_local",
                             embedding_model_id="BAAI/bge-small-en-v1.5", top_k=5)
    b = system_artifact_hash("naive_rag_local",
                             embedding_model_id="BAAI/bge-small-en-v1.5", top_k=10)
    c = system_artifact_hash("naive_rag_local",
                             embedding_model_id="BAAI/bge-large-en-v1.5", top_k=5)
    assert a != b
    assert a != c
    assert b != c


# ---------------------------------------------------------------------------
# JSONL append + index loading
# ---------------------------------------------------------------------------


def test_append_jsonl_writes_one_line_per_call(tmp_path):
    p = tmp_path / "shard.jsonl"
    append_jsonl(p, {"cache_key": "k1", "value": 1})
    append_jsonl(p, {"cache_key": "k2", "value": 2})
    rows = list(iter_jsonl(p))
    assert len(rows) == 2
    assert rows[0]["cache_key"] == "k1"
    assert rows[1]["value"] == 2


def test_iter_jsonl_skips_blank_and_malformed_lines(tmp_path):
    p = tmp_path / "shard.jsonl"
    p.write_text(
        '{"cache_key":"good1","v":1}\n'
        '\n'
        '{"cache_key":"good2","v":2}\n'
        '{"cache_key":"truncated"\n'  # malformed trailing line (crash)
    )
    rows = list(iter_jsonl(p))
    keys = [r["cache_key"] for r in rows]
    assert keys == ["good1", "good2"]


def test_load_cache_index_includes_merged_and_shards(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    # Old merged content
    (layer / "merged.jsonl").write_text('{"cache_key":"old","v":"merged"}\n')
    # Two shards from concurrent runs
    (layer / "shards" / "run-a.jsonl").write_text(
        '{"cache_key":"new1","v":"a"}\n'
    )
    (layer / "shards" / "run-b.jsonl").write_text(
        '{"cache_key":"new2","v":"b"}\n'
    )
    idx = load_cache_index(layer)
    assert "old" in idx
    assert "new1" in idx
    assert "new2" in idx
    assert len(idx) == 3


def test_load_cache_index_shard_overrides_merged_with_same_key(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "merged.jsonl").write_text('{"cache_key":"k","v":"old"}\n')
    (layer / "shards" / "later.jsonl").write_text('{"cache_key":"k","v":"new"}\n')
    idx = load_cache_index(layer)
    assert idx.get("k")["v"] == "new"


# ---------------------------------------------------------------------------
# Shard merging + conflict handling
# ---------------------------------------------------------------------------


def test_merge_shards_combines_shards_into_merged(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "shards" / "a.jsonl").write_text(
        '{"cache_key":"k1","v":1}\n'
        '{"cache_key":"k2","v":2}\n'
    )
    (layer / "shards" / "b.jsonl").write_text(
        '{"cache_key":"k3","v":3}\n'
    )
    summary = merge_shards(layer)
    assert summary["merged_rows"] == 3
    assert summary["conflicts_resolved"] == 0
    rows = list(iter_jsonl(layer / "merged.jsonl"))
    keys = sorted(r["cache_key"] for r in rows)
    assert keys == ["k1", "k2", "k3"]


def test_merge_shards_ignores_wallclock_fields_when_comparing(tmp_path):
    """Two shards with same payload but different elapsed_seconds should
    NOT be flagged as a conflict."""
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "shards" / "a.jsonl").write_text(
        '{"cache_key":"k","v":1,"elapsed_seconds":1.0}\n'
    )
    (layer / "shards" / "b.jsonl").write_text(
        '{"cache_key":"k","v":1,"elapsed_seconds":2.0}\n'
    )
    summary = merge_shards(layer, on_conflict="fail")
    assert summary["conflicts_resolved"] == 0


def test_merge_shards_fails_on_payload_conflict(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "shards" / "a.jsonl").write_text('{"cache_key":"k","v":1}\n')
    (layer / "shards" / "b.jsonl").write_text('{"cache_key":"k","v":2}\n')
    with pytest.raises(CacheConflictError):
        merge_shards(layer, on_conflict="fail")


def test_merge_shards_accept_first(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "shards" / "a.jsonl").write_text('{"cache_key":"k","v":"first"}\n')
    (layer / "shards" / "b.jsonl").write_text('{"cache_key":"k","v":"later"}\n')
    summary = merge_shards(layer, on_conflict="accept_first")
    assert summary["conflicts_resolved"] == 1
    rows = list(iter_jsonl(layer / "merged.jsonl"))
    assert len(rows) == 1
    assert rows[0]["v"] == "first"


def test_merge_shards_accept_latest(tmp_path):
    layer = tmp_path / "responses"
    (layer / "shards").mkdir(parents=True)
    (layer / "shards" / "a.jsonl").write_text('{"cache_key":"k","v":"first"}\n')
    (layer / "shards" / "b.jsonl").write_text('{"cache_key":"k","v":"later"}\n')
    summary = merge_shards(layer, on_conflict="accept_latest")
    assert summary["conflicts_resolved"] == 1
    rows = list(iter_jsonl(layer / "merged.jsonl"))
    assert len(rows) == 1
    assert rows[0]["v"] == "later"


def test_cache_format_version_constant_is_stable():
    assert CACHE_FORMAT_VERSION >= 1
