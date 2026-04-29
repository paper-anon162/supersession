"""Tests for pipeline.construction.naturalness."""

from pipeline.construction.naturalness import (
    build_target_tokens,
    is_distractor_natural,
    is_distractor_topic_orthogonal,
    scan_dataset,
    scan_sample,
    scan_text,
)


def _make_session(turns):
    return {"session_id": "s1", "turns": turns}


def _make_sample(sid: str, sessions, *, sample_type="supersession", horizon=None,
                 failure_patterns=None):
    return {
        "sample_id": sid,
        "sample_type": sample_type,
        "history": sessions,
        "current_query": "Help me draft a quick reply.",
        "_gold": {
            "metadata": {
                "horizon": horizon,
                "failure_patterns": failure_patterns or [],
            }
        },
    }


def test_scan_text_clean():
    assert scan_text("Could you write up the notes in our usual format?") == []


def test_scan_text_disclaimer():
    hits = scan_text("As an AI language model, I cannot recall previous conversations.")
    cats = {c for c, _ in hits}
    assert "ai_disclaimer" in cats


def test_scan_text_web_artifact():
    hits = scan_text("Web search results: here are the articles I found.")
    cats = {c for c, _ in hits}
    assert "raw_web_artifact" in cats


def test_scan_text_staged_qa_artifact():
    hits = scan_text("Part 5 (acknowledge and wait for the next part):")
    cats = {c for c, _ in hits}
    assert "staged_qa_artifact" in cats


def test_scan_text_roleplay_opener():
    hits = scan_text("Act as a typography style guide and rate my deck.")
    cats = {c for c, _ in hits}
    assert "roleplay_opener" in cats


def test_is_distractor_natural_filters_artifacts():
    dirty = _make_session([
        {"role": "user", "text": "Here is the final part: a long source dump..."},
        {"role": "assistant", "text": "Acknowledged."},
    ])
    clean = _make_session([
        {"role": "user", "text": "Heads up — Friday lunch is moved to 1pm."},
        {"role": "assistant", "text": "Got it, I'll update the calendar."},
    ])
    assert is_distractor_natural(clean) is True
    assert is_distractor_natural(dirty) is False


def test_scan_sample_per_sample_report():
    sessions = [
        _make_session([
            {"role": "user", "text": "Web search results: Brexit policy update."},
        ]),
        _make_session([
            {"role": "user", "text": "Schedule lunch with the Berlin team."},
        ]),
    ]
    issue = scan_sample(_make_sample("p2-test-001", sessions))
    assert not issue.clean
    cats = set(issue.categories)
    # both raw_web_artifact and corporate_jargon should fire
    assert "raw_web_artifact" in cats
    assert "corporate_jargon" in cats


def test_scan_dataset_aggregate():
    clean_sessions = [_make_session([
        {"role": "user", "text": "Reschedule the standup to 10am."},
    ])]
    dirty_sessions = [_make_session([
        {"role": "user", "text": "act as a typography style guide"},
    ])]
    samples = [
        _make_sample("ok-001", clean_sessions),
        _make_sample("ok-002", clean_sessions),
        _make_sample("dirty-001", dirty_sessions),
    ]
    report = scan_dataset(samples)
    assert report.n_samples == 3
    assert report.n_clean == 2
    assert report.n_dirty == 1
    assert report.rejected_by_category.get("roleplay_opener") == 1


def test_build_target_tokens_strips_stopwords():
    tokens = build_target_tokens(
        target_description="user's preferred morning beverage",
        target_slot_id="morning_beverage::v1",
        active_value="black coffee",
    )
    # stopwords like "the", "preferred", "morning" should NOT survive
    assert "the" not in tokens
    assert "preferred" not in tokens
    assert "morning" not in tokens
    # content tokens should
    assert "beverage" in tokens
    assert "coffee" in tokens
    assert "black" in tokens


def test_topic_orthogonal_rejects_target_overlap():
    # spine target is "morning beverage" with active value "oat-milk
    # latte". Gate is literal-token (not semantic) — a distractor that
    # mentions "latte" or "beverage" verbatim hits; one that uses
    # disjoint vocabulary like "coffee" does not.
    target_tokens = build_target_tokens(
        target_description="user's preferred morning beverage",
        active_value="oat-milk latte",
    )
    dirty = _make_session([
        {"role": "user", "text": "Got a latte with Priya before standup."},
    ])
    clean = _make_session([
        {"role": "user", "text": "Reschedule the demo to 3pm tomorrow."},
    ])
    assert is_distractor_topic_orthogonal(clean, target_tokens=target_tokens)
    assert not is_distractor_topic_orthogonal(dirty, target_tokens=target_tokens)


def test_topic_orthogonal_passes_when_target_empty():
    """Empty target token set means no constraint; always pass."""
    sess = _make_session([{"role": "user", "text": "anything goes here"}])
    assert is_distractor_topic_orthogonal(sess, target_tokens=set())


def test_topic_orthogonal_distinguishing_extra_added():
    """Caller-supplied tokens get included alongside auto-derived ones."""
    target_tokens = build_target_tokens(
        target_description="standup cadence",
        active_value="weekly",
        distinguishing_extra=["loomvideo"],
    )
    assert "loomvideo" in target_tokens
    sess = _make_session([
        {"role": "user", "text": "Did the loomvideo from Marcus go through?"},
    ])
    assert not is_distractor_topic_orthogonal(sess, target_tokens=target_tokens)


def test_scan_sample_pulls_metadata_from_gold():
    sessions = [_make_session([{"role": "user", "text": "ok"}])]
    sample = _make_sample(
        "p2-x-001", sessions,
        horizon="standard", failure_patterns=["implicit_drift"],
    )
    issue = scan_sample(sample)
    assert issue.horizon == "standard"
    assert issue.failure_patterns == ["implicit_drift"]
