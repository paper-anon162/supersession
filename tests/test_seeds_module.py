"""Tests for the seed construction DSL."""

import pytest

from pipeline.construction import (
    SeedSpec,
    SessionSpec,
    TurnSpec,
    VersionSpec,
    materialize,
)
from pipeline.construction.same_target_checker import check_sample
from pipeline.io import GOLD_KEY, load_for_system


def _make_strong_seed():
    return SeedSpec(
        sample_id="test-strong-001",
        sample_type="supersession",
        target_type="object_preference",
        domain="food_dining",
        target_description="user's standard morning beverage order",
        target_slot_id="morning_beverage::v1",
        topic="morning_beverage",
        versions=[
            VersionSpec(value="oat-milk latte", polarity="prefer", session_introduced=1),
            VersionSpec(value="black coffee", polarity="prefer", session_introduced=3),
        ],
        sessions=[
            SessionSpec(
                session_id="s1",
                turns=[
                    TurnSpec(role="user", text="I usually grab an oat-milk latte before work."),
                    TurnSpec(role="assistant", text="Noted."),
                ],
            ),
            SessionSpec(
                session_id="s2",
                turns=[
                    TurnSpec(role="user", text="Quarterly review next week?"),
                    TurnSpec(role="assistant", text="Tuesday looks open."),
                ],
            ),
            SessionSpec(
                session_id="s3",
                turns=[
                    TurnSpec(
                        role="user",
                        text="Cut dairy entirely now — black coffee from here on out.",
                    ),
                    TurnSpec(role="assistant", text="Got it, switching that."),
                ],
            ),
        ],
        current_query="Putting in tomorrow's drinks order — what should I list for me?",
        required_behavior="recommend or prepare a black-coffee-only order",
        invalid_behavior=[
            "recommend an oat-milk latte",
            "include any dairy-based morning drink",
        ],
        subtype="strong",
    )


def test_materialize_strong_seed_passes_validation():
    spec = _make_strong_seed()
    sample = materialize(spec)
    assert sample.sample_type == "supersession"
    assert sample.gold.metadata.competing_versions_count == 2
    assert sample.recall_query is not None
    assert sample.gold.violation_predicate.must_honor.value == "black coffee"
    assert len(sample.gold.violation_predicate.must_not_honor) == 1
    assert sample.gold.violation_predicate.must_not_honor[0].value == "oat-milk latte"


def test_materialize_strong_seed_passes_same_target_check():
    sample = materialize(_make_strong_seed())
    report = check_sample(sample)
    assert report.passes
    assert "value_replacement" in report.pair_results[0][2].triggered_rules


def test_seeds_emit_recall_query_via_attach():
    sample = materialize(_make_strong_seed())
    assert sample.recall_query is not None
    assert "past conversations" in sample.recall_query


def test_seeds_pass_public_gold_separation():
    sample = materialize(_make_strong_seed())
    public = load_for_system(sample)
    assert GOLD_KEY not in public
    # spine token shouldn't be in public release
    import json

    blob = json.dumps(public)
    assert "morning_beverage::v1" not in blob
