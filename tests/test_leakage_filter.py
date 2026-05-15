import pytest

from pipeline.construction.leakage_filter import (
    check_degeneracy,
    check_lexical_leakage,
    check_semantic_leakage,
    check_update_relation_leakage,
    filter_sample,
    filter_samples,
)
from pipeline.schema.fixtures import dummy_supersession_sample


def _with_query(query: str):
    s = dummy_supersession_sample()
    return s.model_copy(update={"current_query": query})


def test_dummy_sample_passes_filter():
    s = dummy_supersession_sample()
    v = filter_sample(s)
    assert v.accepted, v.reasons


def test_lexical_leakage_detected():
    # "black coffee" is the active value
    s = _with_query("Should I order a black coffee for the meeting?")
    leaks, tokens = check_lexical_leakage(s)
    assert leaks
    assert "black" in tokens
    assert "coffee" in tokens
    assert not filter_sample(s).accepted


def test_update_relation_leakage_detected():
    s = _with_query("As I told you before, what should I order tomorrow?")
    leaks, phrases = check_update_relation_leakage(s)
    assert leaks
    assert phrases
    assert not filter_sample(s).accepted


def test_switched_to_phrase_blocked():
    s = _with_query("Now that I switched to a new beverage, what's my order?")
    assert not filter_sample(s).accepted


def test_semantic_leakage_stem_collapse():
    # The dummy fixture's active value is "black coffee" and current_query
    # is a behavioral task that doesn't mention coffee — should not flag.
    s = dummy_supersession_sample()
    leaks, stems = check_semantic_leakage(s)
    assert not leaks
    assert stems == []
    # A plural / inflected form that lexical layer misses but stem-collapse
    # catches: value tokens "black", "coffee" stem to themselves; query
    # mentions "coffees" which stems to "coffee".
    s2 = _with_query("Should I order coffees for the all-hands?")
    leaks2, stems2 = check_semantic_leakage(s2)
    assert leaks2
    assert "coffee" in stems2


def test_semantic_leakage_does_not_double_count_lexical():
    # Direct lexical overlap should be reported by lexical filter, not by
    # the semantic-leakage layer.
    s = _with_query("Should I order a black coffee?")
    leaks_sem, stems = check_semantic_leakage(s)
    assert not leaks_sem
    assert stems == []


def test_degeneracy_recall_shaped_query_blocked():
    s = _with_query("What's my preference for morning drinks again?")
    degen, phrases = check_degeneracy(s)
    assert degen
    assert phrases
    assert not filter_sample(s).accepted


def test_degeneracy_remind_me_blocked():
    s = _with_query("Remind me what my usual order is.")
    assert check_degeneracy(s)[0]
    assert not filter_sample(s).accepted


def test_degeneracy_does_not_flag_natural_behavioral_queries():
    # All real Phase 2 current_queries (sample) should pass degeneracy.
    naturals = [
        "Putting in tomorrow's drinks order for the team. What should I get?",
        "Could you write up the notes in our usual format?",
        "Help me pick a thoughtful thank-you gift for the team.",
        "Marcus just hit a snag on the auth refactor. How should he loop me in?",
        "Calendar block at noon Wednesday for lunch — what should I plan?",
    ]
    for q in naturals:
        s = _with_query(q)
        assert not check_degeneracy(s)[0], f"false-positive degeneracy: {q!r}"


def test_semantic_leakage_skips_topic_shared_stems():
    """Same distinguishing-token semantics as lexical, but on stems."""
    s = dummy_supersession_sample()
    s.gold.violation_predicate.must_not_honor[0].value = "weak coffees with oat milk"
    leaks, stems = check_semantic_leakage(
        s.model_copy(update={"current_query": "Should I order coffees for the meeting?"})
    )
    assert not leaks, f"shared stem 'coffee' incorrectly flagged: {stems}"


def test_filter_samples_aggregates():
    samples = [
        dummy_supersession_sample("ok-001"),
        _with_query("Should I order a black coffee?"),  # lexical leak
        _with_query("As I previously said, place my order"),  # relation leak
    ]
    samples[0] = samples[0].model_copy(update={"sample_id": "ok-001"})
    report = filter_samples(samples)
    assert report.total == 3
    assert report.accepted == 1
    assert report.rejected == 2
    assert report.rejected_by_reason["active_value_lexical_leakage"] == 1
    assert report.rejected_by_reason["update_relation_leakage"] == 1
