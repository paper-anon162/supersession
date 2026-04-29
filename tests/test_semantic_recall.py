"""Tests for the semantic-recall scorer.

Mocks the embedder so the test suite does not require sentence-transformers
to actually load a model.
"""

from unittest.mock import MagicMock, patch

import numpy as np

from pipeline.construction.semantic_recall import (
    _value_surface_forms,
    score_recall_semantic,
)
from pipeline.schema.fixtures import dummy_supersession_sample


def test_surface_forms_skip_empty_topic_only():
    from pipeline.schema import VersionState

    v = VersionState(
        version_id="v1",
        topic="morning_beverage",
        value="black coffee",
        polarity="prefer",
        session_introduced=1,
        status="active",
    )
    forms = _value_surface_forms(v)
    assert "black coffee" in forms
    # We deliberately skip the topic-only form to avoid recall=1 on bare echoes
    assert "morning beverage" not in forms


def test_surface_forms_polarity_avoid():
    from pipeline.schema import VersionState

    v = VersionState(
        version_id="v1",
        topic="t",
        value="raw fish",
        polarity="avoid",
        session_introduced=1,
        status="active",
    )
    forms = _value_surface_forms(v)
    assert "avoid raw fish" in forms


def test_score_recall_semantic_recovers_via_high_cosine():
    s = dummy_supersession_sample()

    fake = MagicMock()
    state = {"first_call": True}

    def encode(texts, **_):
        # First call: response
        if state["first_call"]:
            state["first_call"] = False
            return np.array([[1.0, 0.0]])
        # Subsequent: surface forms. Match if the value text contains
        # "black"/"coffee".
        text = texts[0].lower()
        if "black" in text or "coffee" in text:
            return np.array([[1.0, 0.0]] * len(texts))
        return np.array([[0.0, 1.0]] * len(texts))

    fake.encode = encode
    with patch(
        "pipeline.construction.semantic_recall._get_embedder", return_value=fake
    ):
        score = score_recall_semantic(
            s, "I'll grab a black coffee.", threshold=0.65
        )
    assert score.n_versions == 2
    assert score.n_recovered == 1
    assert any(rec for _, _, rec in score.per_version)


def test_score_recall_semantic_threshold_zero_recovers_all():
    s = dummy_supersession_sample()
    fake = MagicMock()

    def encode(texts, **_):
        return np.ones((len(texts), 2)) / np.sqrt(2)

    fake.encode = encode
    with patch(
        "pipeline.construction.semantic_recall._get_embedder", return_value=fake
    ):
        score = score_recall_semantic(s, "anything", threshold=0.0)
    assert score.n_recovered == score.n_versions  # everything passes


def test_score_recall_semantic_threshold_one_recovers_none():
    s = dummy_supersession_sample()
    fake = MagicMock()
    state = {"first_call": True}

    def encode(texts, **_):
        if state["first_call"]:
            state["first_call"] = False
            return np.array([[1.0, 0.0]])
        # Orthogonal vectors → cosine similarity 0
        return np.array([[0.0, 1.0]] * len(texts))

    fake.encode = encode
    with patch(
        "pipeline.construction.semantic_recall._get_embedder", return_value=fake
    ):
        score = score_recall_semantic(s, "anything", threshold=0.99)
    assert score.n_recovered == 0
