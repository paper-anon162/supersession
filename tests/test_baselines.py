import pytest

from pipeline.baselines import (
    CannedResponseBaseline,
    LastUserTurnEchoBaseline,
    run_baseline,
)
from pipeline.baselines.runner import GoldLeakageInRunner
from pipeline.io import GOLD_KEY, load_for_system
from pipeline.schema.fixtures import dummy_supersession_sample


def test_canned_baseline_runs_end_to_end():
    samples = [dummy_supersession_sample(f"s-{i}") for i in range(3)]
    baseline = CannedResponseBaseline(response_text="black coffee")
    results = run_baseline(baseline, samples)
    assert len(results) == 3
    assert all(r.response == "black coffee" for r in results)
    assert all(r.error is None for r in results)
    assert results[0].run_metadata.system_name == "canned_dummy"


def test_echo_baseline_returns_last_user_turn():
    sample = dummy_supersession_sample()
    baseline = LastUserTurnEchoBaseline()
    [result] = run_baseline(baseline, [sample])
    assert result.response.startswith("Actually I've cut dairy")


def test_runner_refuses_gold_leakage_in_input():
    """If a developer ever rebuilds the pipeline so that load_for_system
    returns _gold, the runner must refuse rather than feed it to a system."""
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    assert GOLD_KEY not in public

    # Simulate a (broken) public view that smuggled gold back in.
    from pipeline.baselines.runner import _assert_public_only

    public_bad = dict(public)
    public_bad[GOLD_KEY] = {"sneaky": True}
    with pytest.raises(GoldLeakageInRunner):
        _assert_public_only(public_bad, sample.sample_id)


def test_runner_captures_per_sample_errors():
    class BoomBaseline:
        name = "boom"

        def respond(self, public_sample):
            raise RuntimeError("kaboom")

        def run_metadata(self, sample_id, run_id):
            from pipeline.schema import RunMetadata
            return RunMetadata(
                system_name=self.name,
                run_id=run_id,
                sample_id=sample_id,
                memory_infra_location="none",
                answer_backbone="boom",
                answer_backbone_provider="local",
                embedding_model="none",
                embedding_provider="none",
                uses_full_history=False,
                uses_retrieved_memory=False,
                prompt_template_id="boom/v1",
                temperature=0.0,
                max_tokens=0,
            )

    samples = [dummy_supersession_sample("s-1")]
    [result] = run_baseline(BoomBaseline(), samples)
    assert result.error is not None
    assert "kaboom" in result.error
