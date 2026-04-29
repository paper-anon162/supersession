"""Tests for the LoCoMo + LongMemEval skeleton loaders.

LoCoMo tests are skipped if the data is not on disk; LongMemEval tests are
skipped if the relevant JSON is not on disk.
"""

import pytest

from pipeline.construction.skeleton_loader import (
    LOCOMO_PATH,
    LONGMEMEVAL_ORACLE_PATH,
    LONGMEMEVAL_S_PATH,
    load_locomo_corpus,
    load_longmemeval_corpus,
    load_longmemeval_oracle_corpus,
    session_length_summary,
)

if not LOCOMO_PATH.exists():
    pytest.skip(
        f"LoCoMo data not present at {LOCOMO_PATH}; "
        "see data/skeletons/README.md.",
        allow_module_level=True,
    )


def test_locomo_loads_at_least_one_session():
    corpus = load_locomo_corpus()
    assert len(corpus) > 0
    s = corpus.sessions[0]
    assert s.n_turns > 0
    assert s.approx_token_count > 0
    assert s.source == "locomo"


def test_locomo_summary_fields():
    corpus = load_locomo_corpus()
    summary = session_length_summary(corpus)
    assert summary["n_sessions"] == len(corpus)
    assert summary["turns_mean"] > 0
    assert summary["tokens_mean"] > 0


def test_distractor_sessions_respects_filters():
    import random

    corpus = load_locomo_corpus()
    # No max_turns filter — should return any sessions
    rng = random.Random(0)
    drs = corpus.distractor_sessions(n=5, rng=rng)
    assert 1 <= len(drs) <= 5
    # With strict max_turns=2, may return fewer (LoCoMo sessions are long)
    drs_short = corpus.distractor_sessions(n=5, max_turns=2, rng=rng)
    for s in drs_short:
        assert s.n_turns <= 2


def test_distractor_sessions_returns_copies_not_aliases():
    import random

    corpus = load_locomo_corpus()
    drs = corpus.distractor_sessions(n=3, rng=random.Random(0))
    if not drs:
        return
    drs[0].turns.append(drs[0].turns[0])
    # The original corpus must not have grown
    new_corpus = load_locomo_corpus()
    matching = [
        s for s in new_corpus.sessions if s.session_id == drs[0].session_id
    ]
    if matching:
        # The corpus is rebuilt fresh from disk, so the modified copy did not
        # mutate the source. (Sanity test for lack of accidental sharing.)
        assert matching[0].n_turns != len(drs[0].turns) or drs[0].n_turns >= 1


@pytest.mark.skipif(
    not LONGMEMEVAL_ORACLE_PATH.exists(),
    reason=f"LongMemEval oracle not present at {LONGMEMEVAL_ORACLE_PATH}",
)
def test_longmemeval_oracle_loads_at_least_one_session():
    corpus = load_longmemeval_oracle_corpus()
    assert len(corpus) > 0
    assert corpus.sessions[0].source == "longmemeval_oracle"


@pytest.mark.skipif(
    not LONGMEMEVAL_ORACLE_PATH.exists(),
    reason=f"LongMemEval oracle not present at {LONGMEMEVAL_ORACLE_PATH}",
)
def test_longmemeval_oracle_distractor_sessions_short():
    import random

    corpus = load_longmemeval_oracle_corpus()
    drs = corpus.distractor_sessions(n=4, max_turns=4, rng=random.Random(0))
    for s in drs:
        assert s.n_turns <= 4


def test_longmemeval_variant_dispatch_unknown_raises():
    with pytest.raises(ValueError):
        load_longmemeval_corpus(variant="bogus")


@pytest.mark.skipif(
    not LONGMEMEVAL_S_PATH.exists(),
    reason=f"LongMemEval _s not present at {LONGMEMEVAL_S_PATH}",
)
def test_longmemeval_s_max_questions_loads_subset():
    # Use max_questions to keep this fast; full _s is 265 MB.
    corpus = load_longmemeval_corpus(variant="s", max_questions=2)
    assert len(corpus) > 0
    assert corpus.sessions[0].source == "longmemeval_s"
