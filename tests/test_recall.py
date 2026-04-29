from pipeline.construction.recall_query_gen import (
    attach_recall_query,
    recall_ground_truth,
    recall_query_for,
    score_recall,
)
from pipeline.schema.fixtures import dummy_supersession_sample


def test_recall_query_emitted_for_supersession():
    s = dummy_supersession_sample()
    q = recall_query_for(s)
    assert q is not None
    assert "past conversations" in q
    assert "morning beverage" in q.lower()


def test_recall_query_skipped_for_non_supersession():
    s = dummy_supersession_sample()
    raw = s.model_dump(by_alias=True)
    raw["sample_type"] = "stress"
    raw["recall_query"] = None
    raw["_gold"]["metadata"]["competing_versions_count"] = 0
    from pipeline.schema import Sample
    other = Sample.model_validate(raw)
    assert recall_query_for(other) is None


def test_ground_truth_includes_active_and_outdated():
    s = dummy_supersession_sample()
    gt = recall_ground_truth(s)
    statuses = {v.status for v in gt}
    assert statuses == {"active", "outdated"}


def test_score_recall_full_hit():
    s = dummy_supersession_sample()
    response = (
        "You first told me you like an oat-milk latte. "
        "Later you said you switched to black coffee."
    )
    score = score_recall(s, response)
    assert score.n_versions == 2
    assert score.n_recovered == 2
    assert score.hit_rate == 1.0


def test_score_recall_partial_hit():
    s = dummy_supersession_sample()
    response = "You like black coffee."
    score = score_recall(s, response)
    assert score.n_recovered == 1  # only active recovered
    assert 0 < score.hit_rate < 1


def test_attach_recall_query_round_trip():
    s = dummy_supersession_sample()
    s2 = attach_recall_query(s)
    assert s2.recall_query is not None
    assert s2.sample_id == s.sample_id
