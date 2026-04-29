from pipeline.construction.same_target_checker import (
    check_pair,
    check_sample,
)
from pipeline.schema import VersionState
from pipeline.schema.fixtures import dummy_supersession_sample


def _v(
    *,
    vid: str,
    topic: str,
    value,
    polarity: str = "prefer",
    session: int = 1,
    status: str = "outdated",
) -> VersionState:
    return VersionState(
        version_id=vid,
        topic=topic,
        value=value,
        polarity=polarity,  # type: ignore[arg-type]
        session_introduced=session,
        status=status,  # type: ignore[arg-type]
    )


def test_value_replacement_fires():
    v1 = _v(vid="v1", topic="coffee", value="latte", session=1)
    v2 = _v(vid="v2", topic="coffee", value="black coffee", session=2)
    result = check_pair(v1, v2, target_type="object_preference")
    assert result.passes
    assert "value_replacement" in result.triggered_rules


def test_same_value_same_polarity_does_not_fire():
    v1 = _v(vid="v1", topic="coffee", value="latte", session=1)
    v2 = _v(vid="v2", topic="coffee", value="latte", session=2)
    result = check_pair(v1, v2, target_type="object_preference")
    assert not result.passes


def test_polarity_reversal_fires():
    v1 = _v(vid="v1", topic="meeting_topic", value="my-ex", polarity="avoid", session=1)
    v2 = _v(
        vid="v2", topic="meeting_topic", value="my-ex", polarity="prefer", session=3
    )
    result = check_pair(v1, v2, target_type="interpersonal_boundary")
    assert result.passes
    assert "polarity_reversal" in result.triggered_rules


def test_different_topic_never_fires():
    v1 = _v(vid="v1", topic="coffee", value="latte", session=1)
    v2 = _v(vid="v2", topic="tea", value="oolong", session=2)
    assert not check_pair(v1, v2, target_type="object_preference").passes


def test_procedure_replacement_requires_constraint_polarity():
    v1 = _v(vid="v1", topic="meeting_notes_format", value="paragraph",
            polarity="constraint", session=1)
    v2 = _v(vid="v2", topic="meeting_notes_format", value="bullet list",
            polarity="constraint", session=3)
    result = check_pair(v1, v2, target_type="procedural_constraint")
    assert result.passes
    assert "procedure_replacement" in result.triggered_rules


def test_stance_replacement():
    v1 = _v(vid="v1", topic="market_analysis", value="DCF framework", session=1)
    v2 = _v(vid="v2", topic="market_analysis", value="comps multiples", session=4)
    result = check_pair(v1, v2, target_type="conceptual_stance")
    assert result.passes
    assert "stance_replacement" in result.triggered_rules


def test_check_sample_passes_on_dummy():
    s = dummy_supersession_sample()
    report = check_sample(s)
    assert report.passes
    assert len(report.pair_results) == 1
    assert report.pair_results[0][2].triggered_rules == ["value_replacement"]
