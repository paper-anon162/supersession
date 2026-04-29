from pipeline.evaluation import (
    HeuristicJudgeBackbone,
    JudgeVerdict,
    apply_default_scoring,
    judge_sample,
    majority_vote_vf,
    rule_based_shadow_score,
)
from pipeline.schema.fixtures import dummy_supersession_sample


def _verdict(vf: int, ambiguity: str = "not_ambiguous", confidence: str = "high"):
    return JudgeVerdict(
        sample_id="s1",
        backbone="mock",
        vf=vf,
        confidence=confidence,  # type: ignore[arg-type]
        ambiguity_class=ambiguity,  # type: ignore[arg-type]
        rationale="x",
        raw_output="{}",
    )


def test_default_scoring_clear_pass():
    fs = apply_default_scoring(_verdict(1))
    assert fs.vf == 1


def test_default_scoring_ambiguous_zeros():
    fs = apply_default_scoring(_verdict(1, ambiguity="vague"))
    assert fs.vf == 0


def test_exclude_ambiguous_returns_none():
    fs = apply_default_scoring(_verdict(1, ambiguity="refusal"), mode="exclude_ambiguous")
    assert fs.vf is None


def test_ambiguous_half_returns_half():
    fs = apply_default_scoring(_verdict(1, ambiguity="mixed"), mode="ambiguous_half")
    assert fs.vf == 0.5


def test_majority_vote_picks_majority():
    runs = [_verdict(1), _verdict(0), _verdict(1)]
    agg = majority_vote_vf(runs)
    assert agg.final_vf == 1
    assert not agg.unstable


def test_majority_vote_marks_tie_unstable():
    runs = [_verdict(1), _verdict(0)]
    agg = majority_vote_vf(runs)
    assert agg.unstable


def test_shadow_score_active_only_pass():
    s = dummy_supersession_sample()
    score = rule_based_shadow_score(s, "I'll order a black coffee.")
    assert score.vf == 1


def test_shadow_score_outdated_only_fails():
    s = dummy_supersession_sample()
    score = rule_based_shadow_score(s, "An oat-milk latte for you.")
    assert score.vf == 0


def test_shadow_score_mixing_fails():
    s = dummy_supersession_sample()
    score = rule_based_shadow_score(
        s, "Either an oat-milk latte or black coffee."
    )
    assert score.vf == 0


def test_judge_to_scoring_pipeline_default():
    s = dummy_supersession_sample()
    backbone = HeuristicJudgeBackbone()
    verdict = judge_sample(s, "I'll grab a black coffee.", backbone)
    final = apply_default_scoring(verdict)
    assert final.vf == 1
