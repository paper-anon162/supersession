"""Verifies that gold-only fields can never reach systems via load_for_system.

This is a critical safety test: the entire benchmark's validity rests on
public/gold separation. If this test ever fails, the run is invalid (per
protocol §2.3, §6).
"""

import json
from pathlib import Path

from pipeline.io import (
    GOLD_KEY,
    iter_samples_from_jsonl,
    load_for_diagnostic,
    load_for_judge,
    load_for_system,
    write_gold_jsonl,
    write_public_jsonl,
    write_samples_jsonl,
)
from pipeline.schema.fixtures import dummy_supersession_sample


# Sentinel substrings that should *only* appear in gold.
_GOLD_ONLY_TOKENS = (
    "morning_beverage::v1",  # target_slot_id
    "object_preference",  # gold_target_type
    "must_include_active_value",  # rule_type
    "required_behavior",  # spine field
    "violation_predicate",  # gold field
    "semantic_spine",  # gold field
    "supersession_subtype",  # gold metadata field
    "competing_versions_count",  # gold metadata field
)


def _flatten_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten_strings(k)
            yield from _flatten_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten_strings(v)


def _serialized(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def test_load_for_system_strips_gold():
    s = dummy_supersession_sample()
    public = load_for_system(s)
    assert GOLD_KEY not in public
    set_keys = set(public.keys())
    assert "_gold" not in set_keys
    blob = _serialized(public)
    for token in _GOLD_ONLY_TOKENS:
        assert token not in blob, f"gold token {token!r} leaked into public view"


def test_load_for_system_preserves_public_fields():
    s = dummy_supersession_sample()
    public = load_for_system(s)
    assert public["sample_id"] == s.sample_id
    assert public["sample_type"] == "supersession"
    assert public["current_query"] == s.current_query
    assert "recall_query" not in public  # audit P0: behavior input must not see recall_query
    assert isinstance(public["history"], list)
    assert len(public["history"]) == len(s.history)


def test_load_for_judge_includes_gold():
    s = dummy_supersession_sample()
    judge_view = load_for_judge(s)
    assert GOLD_KEY in judge_view
    assert judge_view[GOLD_KEY]["semantic_spine"]["target_slot_id"]


def test_load_for_diagnostic_includes_gold():
    s = dummy_supersession_sample()
    diag = load_for_diagnostic(s)
    assert GOLD_KEY in diag


def test_public_view_is_independent_copy():
    s = dummy_supersession_sample()
    public = load_for_system(s)
    public["history"].append({"session_id": "tampered", "turns": []})
    s2 = dummy_supersession_sample()
    assert len(s2.history) == 3  # unchanged


def test_jsonl_roundtrip_and_release_split(tmp_path: Path):
    samples = [dummy_supersession_sample(f"demo-{i:03d}") for i in range(3)]
    full = tmp_path / "all.jsonl"
    public = tmp_path / "public.jsonl"
    gold = tmp_path / "gold.jsonl"

    n_full = write_samples_jsonl(samples, full)
    n_pub = write_public_jsonl(samples, public)
    n_gold = write_gold_jsonl(samples, gold)
    assert n_full == n_pub == n_gold == 3

    # Round-trip the full file
    loaded = list(iter_samples_from_jsonl(full))
    assert len(loaded) == 3
    assert loaded[0].gold.metadata.gold_target_type == "object_preference"

    # Public file must not contain any gold tokens
    pub_blob = public.read_text()
    for token in _GOLD_ONLY_TOKENS:
        assert token not in pub_blob, f"gold token {token!r} leaked into release"

    # Gold file is keyed by sample_id and only contains _gold
    with gold.open() as f:
        for line in f:
            row = json.loads(line)
            assert set(row.keys()) == {"sample_id", "_gold"}


def test_load_for_system_excludes_recall_query():
    """Audit P0 §1: behavioral system input must not include recall_query."""
    sample = dummy_supersession_sample('test-recall-leak-001')
    behavior_view = load_for_system(sample)
    assert 'recall_query' not in behavior_view, (
        'recall_query leaked into behavioral system input'
    )
    assert 'history' in behavior_view
    assert 'current_query' in behavior_view


def test_load_for_recall_session_includes_recall_query():
    """Audit P0 §1: dedicated recall loader must expose recall_query."""
    from pipeline.io import load_for_recall_session
    sample = dummy_supersession_sample('test-recall-include-001')
    recall_view = load_for_recall_session(sample)
    assert 'recall_query' in recall_view
    assert recall_view['recall_query']  # non-empty

