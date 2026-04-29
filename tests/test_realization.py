"""Tests for the LLM-assisted seed realization helper.

We mock the LLM by injecting a deterministic callable that produces a
canned JSON string. This keeps the test suite cheap and the realization
contract honest.
"""

import json

import pytest

from pipeline.construction.realization import (
    RealizationParseError,
    ThinSpine,
    parse_sessions,
    realize,
)
from pipeline.construction.seeds import VersionSpec


def _thin_strong_seed() -> ThinSpine:
    return ThinSpine(
        sample_id="real-test-001",
        sample_type="supersession",
        target_type="object_preference",
        domain="food_dining",
        target_description="user's standard morning beverage",
        target_slot_id="morning_beverage::v1",
        topic="morning_beverage",
        versions=[
            VersionSpec(value="oat-milk latte", polarity="prefer", session_introduced=1),
            VersionSpec(value="black coffee", polarity="prefer", session_introduced=3),
        ],
        current_query="Putting in tomorrow's drinks order — what should I list for me?",
        required_behavior="recommend a black-coffee-only order",
        invalid_behavior=["recommend an oat-milk latte"],
        n_sessions=3,
        subtype="strong",
    )


def _good_canned_output() -> str:
    return json.dumps(
        {
            "sessions": [
                {
                    "session_id": "s1",
                    "timestamp": "2026-01-01T08:00:00Z",
                    "turns": [
                        {"role": "user", "text": "Always grab an oat-milk latte before standup."},
                        {"role": "assistant", "text": "Noted."},
                    ],
                },
                {
                    "session_id": "s2",
                    "timestamp": "2026-01-15T09:00:00Z",
                    "turns": [
                        {"role": "user", "text": "Move Tuesday's 1:1 to Wednesday."},
                        {"role": "assistant", "text": "Done."},
                    ],
                },
                {
                    "session_id": "s3",
                    "timestamp": "2026-02-01T08:00:00Z",
                    "turns": [
                        {"role": "user", "text": "Cutting dairy entirely. Black coffee from now on."},
                        {"role": "assistant", "text": "Updated."},
                    ],
                },
            ]
        }
    )


def test_parse_sessions_happy_path():
    raw = _good_canned_output()
    sessions = parse_sessions(raw, expected_n=3)
    assert len(sessions) == 3
    assert sessions[0].session_id == "s1"
    assert sessions[2].turns[0].role == "user"


def test_parse_sessions_rejects_wrong_count():
    raw = _good_canned_output()
    with pytest.raises(RealizationParseError):
        parse_sessions(raw, expected_n=4)


def test_parse_sessions_rejects_missing_text():
    bad = json.dumps(
        {
            "sessions": [
                {
                    "session_id": "s1",
                    "turns": [{"role": "user", "text": ""}, {"role": "assistant", "text": "ok"}],
                },
            ]
        }
    )
    with pytest.raises(RealizationParseError):
        parse_sessions(bad, expected_n=1)


def test_realize_happy_path_via_canned_llm():
    canned = _good_canned_output()
    calls = {"n": 0}

    def llm(prompt: str) -> str:
        calls["n"] += 1
        return canned

    result = realize(_thin_strong_seed(), llm, max_retries=2)
    assert result.failure_reason is None
    assert result.seed_spec is not None
    assert result.sample is not None
    assert result.attempts == 1
    assert calls["n"] == 1


def test_realize_retries_on_parse_error():
    bad = "not JSON at all"
    canned = _good_canned_output()
    states = iter([bad, canned])

    def llm(prompt: str) -> str:
        return next(states)

    result = realize(_thin_strong_seed(), llm, max_retries=3)
    assert result.failure_reason is None
    assert result.attempts == 2


def test_realize_returns_failure_after_max_retries():
    def llm(prompt: str) -> str:
        return "not json"

    result = realize(_thin_strong_seed(), llm, max_retries=2)
    assert result.failure_reason is not None
    assert result.seed_spec is None
    assert result.sample is None
    assert result.attempts == 2
