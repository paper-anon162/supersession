"""Tests for pipeline.construction.cleanup."""

import random

from pipeline.construction.cleanup import clean_dataset, clean_sample
from pipeline.construction.skeleton_loader import (
    DialogueCorpus,
    DialogueSession,
    DialogueTurn,
)


def _session(sid: str, turns: list[tuple[str, str]], ts: str = "2026-01-01T00:00:00"):
    return DialogueSession(
        session_id=sid,
        timestamp=ts,
        turns=[DialogueTurn(role=r, text=t) for r, t in turns],
        source="test",
    )


def _make_corpus(n_clean: int = 10) -> DialogueCorpus:
    sessions = [
        _session(f"clean-{i}", [
            ("user", f"Heads up, lunch is moved to {1 + i}pm tomorrow."),
            ("assistant", "Got it, I'll update the calendar."),
        ])
        for i in range(n_clean)
    ]
    return DialogueCorpus(name="test", sessions=sessions)


def _make_sample(sid: str, history: list[dict], *, event_positions: tuple[int, ...] = (2,)):
    """Build a sample whose event sessions are at ``event_positions``
    (1-indexed). The first position is must_honor; the rest are
    must_not_honor. Sessions outside event_positions are distractors and
    will be considered for cleanup.
    """
    must_honor = event_positions[0]
    must_not = list(event_positions[1:])
    return {
        "sample_id": sid,
        "sample_type": "supersession",
        "history": history,
        "current_query": "Help me draft a quick reply.",
        "_gold": {
            "violation_predicate": {
                "must_honor": {"session_introduced": must_honor},
                "must_not_honor": [{"session_introduced": p} for p in must_not],
            }
        },
    }


def test_clean_sample_replaces_dirty_distractor():
    history = [
        # s1: dirty distractor (will be replaced)
        {
            "session_id": "s1",
            "timestamp": "2026-01-01T00:00:00",
            "turns": [
                {"role": "user", "text": "Web search results: Brexit policy update."},
                {"role": "assistant", "text": "Acknowledged."},
            ],
        },
        # s2: event session (must NOT be touched even if it had artifacts)
        {
            "session_id": "s2",
            "timestamp": "2026-01-02T00:00:00",
            "turns": [
                {"role": "user", "text": "Going forward I want bullet-list summaries."},
                {"role": "assistant", "text": "Understood."},
            ],
        },
        # s3: clean distractor (no change)
        {
            "session_id": "s3",
            "timestamp": "2026-01-03T00:00:00",
            "turns": [
                {"role": "user", "text": "Reschedule tomorrow's lunch."},
                {"role": "assistant", "text": "Done."},
            ],
        },
    ]
    sample = _make_sample("p2-test-001", history, event_positions=(2,))
    pool = _make_corpus().sessions  # all clean
    cleaned, repls, skipped = clean_sample(
        sample, pool=pool, used_corpus_ids=set(), rng=random.Random(0),
    )
    assert len(repls) == 1
    assert repls[0].session_position == 1
    assert "raw_web_artifact" in repls[0].matched_categories
    # s2 (event) untouched
    assert cleaned["history"][1] == history[1]
    # s3 (clean distractor) untouched
    assert cleaned["history"][2] == history[2]
    # s1 swapped
    assert "Web search" not in cleaned["history"][0]["turns"][0]["text"]
    # session_id and timestamp preserved
    assert cleaned["history"][0]["session_id"] == "s1"
    assert cleaned["history"][0]["timestamp"] == "2026-01-01T00:00:00"


def test_event_session_with_artifact_is_flagged_not_modified():
    history = [
        {"session_id": "s1", "timestamp": "2026-01-01T00:00:00", "turns": [
            {"role": "user", "text": "ok"},
            {"role": "assistant", "text": "ok"},
        ]},
        # event session WITH a corporate-jargon hit — should be flagged but
        # not modified
        {"session_id": "s2", "timestamp": "2026-01-02T00:00:00", "turns": [
            {"role": "user", "text": "I want to manage Brexit risk going forward."},
            {"role": "assistant", "text": "Noted."},
        ]},
    ]
    sample = _make_sample("p2-evt-001", history, event_positions=(2,))
    pool = _make_corpus().sessions
    cleaned, repls, skipped = clean_sample(
        sample, pool=pool, used_corpus_ids=set(), rng=random.Random(0),
    )
    # s2 is unchanged
    assert cleaned["history"][1] == history[1]
    # but it's reported via the skipped channel as event-session-dirty
    assert any(s.session_position == 2 for s in skipped)


def test_clean_dataset_idempotent_on_clean_input():
    history = [
        {"session_id": "s1", "timestamp": "2026-01-01T00:00:00", "turns": [
            {"role": "user", "text": "Reschedule the standup to 10am."},
            {"role": "assistant", "text": "Done."},
        ]},
        {"session_id": "s2", "timestamp": "2026-01-02T00:00:00", "turns": [
            {"role": "user", "text": "From now on prefer bullet lists."},
            {"role": "assistant", "text": "Understood."},
        ]},
    ]
    sample = _make_sample("p2-clean-001", history, event_positions=(2,))
    cleaned, result = clean_dataset([sample], corpus=_make_corpus(), seed=0)
    assert result.n_samples == 1
    assert result.n_samples_changed == 0
    assert result.replacements == []
    assert cleaned[0] == sample


def test_shared_registry_prevents_cross_file_dup():
    """Regression: A and B cleaned in two clean_dataset calls with the
    same seed must not pick the same replacement when they share a
    used_corpus_ids registry. Without sharing, both calls deterministically
    pick the same first match.
    """
    import random as _random

    def _dirty():
        return _make_sample("xfile", [
            {
                "session_id": "s1",
                "timestamp": "2026-01-01T00:00:00",
                "turns": [{"role": "user", "text": "act as a typography style guide"}],
            },
            {
                "session_id": "s2",
                "timestamp": "2026-01-02T00:00:00",
                "turns": [
                    {"role": "user", "text": "Going forward I want bullet-list summaries."},
                    {"role": "assistant", "text": "Understood."},
                ],
            },
        ], event_positions=(2,))

    corpus = _make_corpus(n_clean=20)
    shared_used: set[str] = set()
    rng = _random.Random(0)

    _, result_a = clean_dataset(
        [_dirty()], corpus=corpus, used_corpus_ids=shared_used, rng=rng,
    )
    _, result_b = clean_dataset(
        [_dirty()], corpus=corpus, used_corpus_ids=shared_used, rng=rng,
    )
    assert len(result_a.replacements) == 1
    assert len(result_b.replacements) == 1
    assert (
        result_a.replacements[0].replaced_with_corpus_id
        != result_b.replacements[0].replaced_with_corpus_id
    ), "shared registry must prevent the same corpus session being used twice across files"


def test_used_registry_prevents_intra_batch_dup():
    # Two samples each with a dirty distractor; both should be replaced
    # but with different corpus sessions.
    def _dirty_history():
        return [{
            "session_id": "s1",
            "timestamp": "2026-01-01T00:00:00",
            "turns": [{"role": "user", "text": "act as a typography style guide"}],
        }, {
            "session_id": "s2",
            "timestamp": "2026-01-02T00:00:00",
            "turns": [
                {"role": "user", "text": "Going forward I want bullet-list summaries."},
                {"role": "assistant", "text": "Understood."},
            ],
        }]
    samples = [
        _make_sample("p2-a-001", _dirty_history(), event_positions=(2,)),
        _make_sample("p2-a-002", _dirty_history(), event_positions=(2,)),
    ]
    cleaned, result = clean_dataset(samples, corpus=_make_corpus(n_clean=20), seed=0)
    assert result.n_samples_changed == 2
    repl_ids = [r.replaced_with_corpus_id for r in result.replacements]
    assert len(repl_ids) == 2
    assert repl_ids[0] != repl_ids[1], "intra-batch replacements must differ"
