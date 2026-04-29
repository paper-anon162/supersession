import json

import pytest

from pipeline.schema import Sample
from pipeline.schema.fixtures import dummy_supersession_sample


def test_dummy_sample_validates():
    s = dummy_supersession_sample()
    assert s.sample_type == "supersession"
    assert s.gold.metadata.competing_versions_count >= 2
    # Round-trip through JSON preserves the alias for `_gold`
    payload = json.loads(s.model_dump_json(by_alias=True))
    assert "_gold" in payload
    assert "gold" not in payload
    Sample.model_validate(payload)


def test_supersession_must_have_competing_versions():
    s = dummy_supersession_sample()
    raw = s.model_dump(by_alias=True)
    raw["_gold"]["metadata"]["competing_versions_count"] = 1
    with pytest.raises(Exception):
        Sample.model_validate(raw)


def test_recall_query_only_for_supersession():
    s = dummy_supersession_sample()
    raw = s.model_dump(by_alias=True)
    raw["sample_type"] = "carryover"
    with pytest.raises(Exception):
        Sample.model_validate(raw)


def test_reverted_probe_requires_reverted_subtype():
    s = dummy_supersession_sample()
    raw = s.model_dump(by_alias=True)
    raw["_gold"]["reverted_probe"] = {
        "query": "Are you back to oat-milk lattes now?",
        "expected_mention": "no",
    }
    # subtype is "strong" — adding a probe should fail
    with pytest.raises(Exception):
        Sample.model_validate(raw)


def test_extra_fields_rejected():
    s = dummy_supersession_sample()
    raw = s.model_dump(by_alias=True)
    raw["surprise_extra_field"] = "boom"
    with pytest.raises(Exception):
        Sample.model_validate(raw)
