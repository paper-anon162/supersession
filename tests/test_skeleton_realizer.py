"""Tests for the skeleton-aware realizer.

Uses a deterministic stub LLM (no real API calls) and the LongMemEval
oracle skeleton (smallest variant) as the distractor source.
"""

from __future__ import annotations

import json

import pytest

from pipeline.construction.realization import RealizationParseError
from pipeline.construction.seeds import VersionSpec
from pipeline.construction.skeleton_loader import LONGMEMEVAL_ORACLE_PATH
from pipeline.construction.skeleton_realizer import (
    HORIZON_BUDGETS,
    SkeletonAwareSpine,
    parse_event_sessions,
    realize_with_skeleton,
)


def _stub_llm_factory(active_value: str, v1_value: str, v2_value: str | None = None):
    """Return a callable that emits valid event-session JSON for any prompt."""
    def _llm(prompt: str) -> str:
        events = [
            {
                "label": "v1",
                "turns": [
                    {"role": "user", "text": f"I prefer {v1_value} for these tasks."},
                    {"role": "assistant", "text": "Got it, I'll keep that in mind."},
                ],
            },
        ]
        if v2_value is not None:
            events.append({
                "label": "v2",
                "turns": [
                    {"role": "user", "text": f"Actually let's switch to {v2_value} going forward."},
                    {"role": "assistant", "text": "Updating my notes."},
                ],
            })
        events.append({
            "label": "active",
            "turns": [
                {"role": "user", "text": f"Reminder: I now use {active_value}."},
                {"role": "assistant", "text": "Noted."},
            ],
        })
        return json.dumps({"event_sessions": events})

    return _llm


def test_parse_event_sessions_accepts_valid_json():
    raw = json.dumps({
        "event_sessions": [
            {"label": "v1", "turns": [
                {"role": "user", "text": "hello"},
                {"role": "assistant", "text": "hi"},
            ]},
            {"label": "active", "turns": [
                {"role": "user", "text": "now active"},
                {"role": "assistant", "text": "ok"},
            ]},
        ]
    })
    out = parse_event_sessions(raw, expected_n=2)
    assert len(out) == 2
    assert out[0][0].text == "hello"
    assert out[1][1].text == "ok"


def test_parse_event_sessions_rejects_wrong_count():
    raw = json.dumps({"event_sessions": []})
    with pytest.raises(RealizationParseError):
        parse_event_sessions(raw, expected_n=2)


def test_parse_event_sessions_rejects_bad_role():
    raw = json.dumps({
        "event_sessions": [
            {"label": "v1", "turns": [
                {"role": "system", "text": "nope"},
            ]}
        ]
    })
    with pytest.raises(RealizationParseError):
        parse_event_sessions(raw, expected_n=1)


def test_horizon_budgets_are_sane():
    assert HORIZON_BUDGETS["compact"].max_tokens <= HORIZON_BUDGETS["standard"].min_tokens
    assert HORIZON_BUDGETS["standard"].max_tokens <= HORIZON_BUDGETS["hard"].min_tokens
    for tier in ("compact", "standard", "hard"):
        b = HORIZON_BUDGETS[tier]
        assert b.min_distractors <= b.max_distractors


@pytest.mark.skipif(
    not LONGMEMEVAL_ORACLE_PATH.exists(),
    reason="LongMemEval oracle skeleton not present",
)
def test_realize_with_skeleton_compact_no_distractors():
    """Compact tier with skeleton_variant=None should produce a sample with
    only event sessions (no distractor borrowing)."""
    spine = SkeletonAwareSpine(
        sample_id="test-compact-001",
        sample_type="supersession",
        target_type="object_preference",
        domain="testing",
        target_description="user's preferred coffee order",
        target_slot_id="coffee::v1",
        topic="coffee preferences",
        versions=[
            VersionSpec(value="black coffee", polarity="prefer", session_introduced=1),
            VersionSpec(value="oat milk latte", polarity="prefer", session_introduced=2),
        ],
        current_query="What should I order at the new cafe today?",
        required_behavior="Recommend an oat milk latte.",
        invalid_behavior=["Recommends black coffee"],
        n_sessions=2,
        subtype="strong",
        horizon="compact",
        skeleton_variant=None,
    )
    llm = _stub_llm_factory(
        active_value="oat milk latte", v1_value="black coffee"
    )
    result = realize_with_skeleton(spine, llm)
    assert result.failure_reason is None, result.failure_reason
    assert result.sample is not None
    assert len(result.sample.history) == 2  # only the 2 event sessions


@pytest.mark.skipif(
    not LONGMEMEVAL_ORACLE_PATH.exists(),
    reason="LongMemEval oracle skeleton not present",
)
def test_realize_with_skeleton_standard_with_distractors():
    """Standard tier should produce a sample whose history includes real
    LongMemEval distractor sessions plus 2 event sessions."""
    spine = SkeletonAwareSpine(
        sample_id="test-standard-001",
        sample_type="supersession",
        target_type="object_preference",
        domain="testing",
        target_description="user's preferred coffee order",
        target_slot_id="coffee::v1",
        topic="coffee preferences",
        versions=[
            VersionSpec(value="black coffee", polarity="prefer", session_introduced=1),
            VersionSpec(value="oat milk latte", polarity="prefer", session_introduced=2),
        ],
        current_query="What should I order at the new cafe today?",
        required_behavior="Recommend an oat milk latte.",
        invalid_behavior=["Recommends black coffee"],
        n_sessions=2,
        subtype="strong",
        horizon="standard",
        skeleton_variant="oracle",
        distractor_seed=42,
    )
    llm = _stub_llm_factory(
        active_value="oat milk latte", v1_value="black coffee"
    )
    result = realize_with_skeleton(spine, llm)
    assert result.failure_reason is None, result.failure_reason
    assert result.sample is not None
    n_sessions = len(result.sample.history)
    assert n_sessions >= 3 + 2, (
        f"standard tier should have ≥ 3 distractors + 2 events, got {n_sessions}"
    )
    # Both event values should appear somewhere in history
    full_history_text = " ".join(
        t.text for s in result.sample.history for t in s.turns
    )
    assert "oat milk latte" in full_history_text
    assert "black coffee" in full_history_text


@pytest.mark.skipif(
    not LONGMEMEVAL_ORACLE_PATH.exists(),
    reason="LongMemEval oracle skeleton not present",
)
def test_realize_with_skeleton_implicit_drift_flag():
    """implicit_drift in failure_patterns should be reflected in the prompt
    (we just assert the spine field plumbs through; LLM-side behavior is
    out of scope for this test)."""
    spine = SkeletonAwareSpine(
        sample_id="test-drift-001",
        sample_type="supersession",
        target_type="conceptual_stance",
        domain="testing",
        target_description="user's note-taking style",
        target_slot_id="notes::v1",
        topic="notes",
        versions=[
            VersionSpec(value="paper notebook", polarity="prefer", session_introduced=1),
            VersionSpec(value="digital app", polarity="prefer", session_introduced=2),
        ],
        current_query="Help me capture today's meeting outcomes.",
        required_behavior="Suggest digital app capture.",
        invalid_behavior=["Suggests paper notebook"],
        n_sessions=2,
        subtype="strong",
        horizon="compact",
        skeleton_variant=None,
        failure_patterns=["implicit_drift"],
    )
    assert spine.is_implicit_drift is True
    assert spine.is_narrowing is False


def test_realize_with_skeleton_retries_on_parse_error():
    """If the LLM returns garbage twice then valid JSON on the third try,
    realize_with_skeleton should succeed with attempts=3."""
    valid = json.dumps({
        "event_sessions": [
            {"label": "v1", "turns": [
                {"role": "user", "text": "I prefer black coffee for these tasks."},
                {"role": "assistant", "text": "Got it."},
            ]},
            {"label": "active", "turns": [
                {"role": "user", "text": "I now use oat milk latte."},
                {"role": "assistant", "text": "Noted."},
            ]},
        ]
    })
    call_count = {"n": 0}

    def flaky_llm(prompt: str) -> str:
        call_count["n"] += 1
        if call_count["n"] < 3:
            return "no JSON here, sorry"
        return valid

    spine = SkeletonAwareSpine(
        sample_id="test-retry-001",
        sample_type="supersession",
        target_type="object_preference",
        domain="testing",
        target_description="coffee preference",
        target_slot_id="coffee::v1",
        topic="coffee",
        versions=[
            VersionSpec(value="black coffee", polarity="prefer", session_introduced=1),
            VersionSpec(value="oat milk latte", polarity="prefer", session_introduced=2),
        ],
        current_query="What should I order today?",
        required_behavior="Recommend an oat milk latte.",
        invalid_behavior=["Recommends black coffee"],
        n_sessions=2,
        subtype="strong",
        horizon="compact",
        skeleton_variant=None,
    )
    result = realize_with_skeleton(spine, flaky_llm, max_retries=4)
    assert result.failure_reason is None, result.failure_reason
    assert result.attempts == 3


def test_choose_event_positions_keeps_active_off_last_session():
    """Audit P0 §2: active update must not be the last session before query."""
    import random
    from pipeline.construction.skeleton_realizer import _choose_event_positions
    rng = random.Random(0)
    # 2-version drift, 8 sessions
    pos = _choose_event_positions(8, 2, rng)
    assert pos[-1] <= 8 - 2, f"active session {pos[-1]} not ≥2 before end (n=8)"
    # 3-version chain, 14 sessions
    pos = _choose_event_positions(14, 3, rng)
    assert pos[-1] <= 14 - 2, f"active session {pos[-1]} not ≥2 before end (n=14)"
    # Strictly increasing
    assert all(pos[i] < pos[i + 1] for i in range(len(pos) - 1))


def test_choose_event_positions_non_adjacent():
    """v1 and v2 (and v3 if present) must be in different sessions."""
    import random
    from pipeline.construction.skeleton_realizer import _choose_event_positions
    rng = random.Random(0)
    # Only test configurations where the min span fits.
    cases = [(8, 2), (10, 3), (14, 3), (14, 4), (15, 4)]
    for n_total, n_events in cases:
        pos = _choose_event_positions(n_total, n_events, rng)
        for i in range(1, len(pos)):
            assert pos[i] - pos[i - 1] >= 2, (
                f"adjacent events at n_total={n_total}, "
                f"n_events={n_events}: {pos}"
            )


def test_choose_event_positions_raises_when_over_constrained():
    import random
    import pytest
    from pipeline.construction.skeleton_realizer import _choose_event_positions
    # 5 events in 8 sessions can't fit gap-of-2 + active-to-query gap of 2:
    # active_max=6, first_min=1, span_needed=8 > 5.
    with pytest.raises(ValueError):
        _choose_event_positions(8, 5, random.Random(0))
