"""Tests for the long-context, naive-RAG, and LLM-driven intervention modules.

The transformers / sentence-transformers paths are mocked so the tests do
not require GPU or model downloads.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from pipeline.baselines.long_context import (
    LONG_CONTEXT_SYSTEM,
    LongContextBaseline,
    render_long_context_prompt,
)
from pipeline.intervention.llm_steps import (
    make_llm_extractor,
    make_llm_selector,
)
from pipeline.io import load_for_system
from pipeline.schema.fixtures import dummy_supersession_sample


class _FakeBackbone:
    name = "fake"
    model_id = "fake/model"
    temperature = 0.0
    max_new_tokens = 100
    system_prompt = None

    def __init__(self, fixed: str = "fixed response"):
        self.fixed = fixed
        self.calls: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.fixed


def test_render_long_context_prompt_includes_history_and_query():
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    prompt = render_long_context_prompt(public)
    assert "=== Conversation history ===" in prompt
    assert "=== Current request ===" in prompt
    assert public["current_query"] in prompt
    # gold-only fields must not appear in the rendered long-context prompt
    assert "_gold" not in prompt
    assert "morning_beverage::v1" not in prompt


def test_long_context_baseline_runs_with_fake_backbone():
    bb = _FakeBackbone(fixed="black coffee for you, sir.")
    bl = LongContextBaseline(backbone=bb)
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    response = bl.respond(public)
    assert response == "black coffee for you, sir."
    # The system prompt should have been swapped during the call and restored
    assert bb.system_prompt is None
    # The prompt that the backbone saw should include the long-context system
    # context (the SUT temporarily set it).
    assert any("=== Conversation history ===" in p for p in bb.calls)


def test_long_context_baseline_includes_intervention_injection():
    bb = _FakeBackbone(fixed="ok")
    bl = LongContextBaseline(backbone=bb)
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    public["_intervention_injection"] = "Active state: black coffee."
    bl.respond(public)
    assert any("Active state: black coffee." in p for p in bb.calls)


def test_long_context_run_metadata_records_backbone():
    bb = _FakeBackbone()
    bl = LongContextBaseline(backbone=bb)
    meta = bl.run_metadata("s1", "run-1")
    assert meta.answer_backbone == "fake/model"
    assert meta.uses_full_history is True
    assert meta.uses_retrieved_memory is False


def test_llm_extractor_parses_candidates():
    fake = _FakeBackbone(
        fixed='{"candidates": ['
        '{"topic": "drink", "value": "black coffee", "polarity": "prefer", '
        '"session_introduced": 3, "rationale": "user announced switch"}, '
        '{"topic": "drink", "value": "oat-milk latte", "polarity": "prefer", '
        '"session_introduced": 1, "rationale": "earliest preference"}'
        "]}"
    )
    extract = make_llm_extractor(fake)
    public = load_for_system(dummy_supersession_sample())
    cands = extract(public)
    assert len(cands) == 2
    assert cands[0].value == "black coffee"
    assert cands[1].session_introduced == 1


def test_llm_extractor_returns_empty_on_parse_failure():
    fake = _FakeBackbone(fixed="not json at all")
    extract = make_llm_extractor(fake)
    public = load_for_system(dummy_supersession_sample())
    assert extract(public) == []


def test_llm_selector_picks_chosen_index():
    from pipeline.intervention.wrapper import CandidateUpdate

    cands = [
        CandidateUpdate(topic="drink", value="oat-milk latte", polarity="prefer",
                        session_introduced=1, rationale=""),
        CandidateUpdate(topic="drink", value="black coffee", polarity="prefer",
                        session_introduced=3, rationale=""),
    ]
    fake = _FakeBackbone(fixed='{"selected_index": 1, "rationale": "latest"}')
    select = make_llm_selector(fake)
    public = load_for_system(dummy_supersession_sample())
    selected = select(cands, public)
    assert selected is not None
    assert selected.value == "black coffee"


def test_llm_selector_returns_none_on_null():
    from pipeline.intervention.wrapper import CandidateUpdate

    cands = [
        CandidateUpdate(topic="drink", value="x", polarity="prefer",
                        session_introduced=1, rationale=""),
    ]
    fake = _FakeBackbone(fixed='{"selected_index": null, "rationale": "n/a"}')
    select = make_llm_selector(fake)
    public = load_for_system(dummy_supersession_sample())
    assert select(cands, public) is None


def test_llm_selector_returns_none_on_oob_index():
    from pipeline.intervention.wrapper import CandidateUpdate

    cands = [
        CandidateUpdate(topic="drink", value="x", polarity="prefer",
                        session_introduced=1, rationale=""),
    ]
    fake = _FakeBackbone(fixed='{"selected_index": 7, "rationale": "n/a"}')
    select = make_llm_selector(fake)
    public = load_for_system(dummy_supersession_sample())
    assert select(cands, public) is None
