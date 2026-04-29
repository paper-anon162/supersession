import json

import pytest

from pipeline.evaluation.judge import (
    HeuristicJudgeBackbone,
    JudgeParseError,
    judge_sample,
    parse_verdict,
    render_judge_prompt,
)
from pipeline.schema.fixtures import dummy_supersession_sample


def test_render_prompt_includes_history_and_gold():
    s = dummy_supersession_sample()
    prompt = render_judge_prompt(s, "I'll order a black coffee.")
    assert "=== Conversation history ===" in prompt
    assert "=== Current query ===" in prompt
    assert "=== Model response ===" in prompt
    assert "I'll order a black coffee." in prompt
    assert "Active version value:" in prompt
    assert "black coffee" in prompt
    assert "oat-milk latte" in prompt


def test_heuristic_backbone_active_only_yields_vf_1():
    s = dummy_supersession_sample()
    backbone = HeuristicJudgeBackbone()
    verdict = judge_sample(s, "I'll grab a black coffee for the morning.", backbone)
    assert verdict.vf == 1
    assert verdict.ambiguity_class == "not_ambiguous"


def test_heuristic_backbone_outdated_only_yields_vf_0():
    s = dummy_supersession_sample()
    backbone = HeuristicJudgeBackbone()
    verdict = judge_sample(s, "Putting down an oat-milk latte for you.", backbone)
    assert verdict.vf == 0


def test_heuristic_backbone_mixed_yields_vf_0_mixed():
    s = dummy_supersession_sample()
    backbone = HeuristicJudgeBackbone()
    verdict = judge_sample(
        s,
        "Either an oat-milk latte or a black coffee — your call.",
        backbone,
    )
    assert verdict.vf == 0
    assert verdict.ambiguity_class == "mixed"


def test_heuristic_backbone_avoidance_yields_target_avoidance():
    s = dummy_supersession_sample()
    backbone = HeuristicJudgeBackbone()
    verdict = judge_sample(s, "Sounds like a productive morning ahead.", backbone)
    assert verdict.vf == 0
    assert verdict.ambiguity_class == "target_avoidance"


def test_parse_verdict_extracts_json_from_prose():
    raw = (
        "Here's my analysis. The model honored the active version.\n\n"
        '{"vf": 1, "confidence": "high", "ambiguity_class": "not_ambiguous", '
        '"rationale": "ok"}\n\nDone.'
    )
    v = parse_verdict("s1", "mock_backbone", raw)
    assert v.vf == 1


def test_parse_verdict_rejects_invalid_confidence():
    raw = json.dumps(
        {
            "vf": 1,
            "confidence": "bogus",
            "ambiguity_class": "not_ambiguous",
            "rationale": "x",
        }
    )
    with pytest.raises(JudgeParseError):
        parse_verdict("s1", "mock", raw)


def test_parse_verdict_rejects_invalid_vf():
    raw = json.dumps(
        {
            "vf": 2,
            "confidence": "high",
            "ambiguity_class": "not_ambiguous",
            "rationale": "x",
        }
    )
    with pytest.raises(JudgeParseError):
        parse_verdict("s1", "mock", raw)
