import pytest

from pipeline.intervention import (
    AblatedWrapper,
    InterventionConfig,
    InterventionGoldLeakageError,
    MinimalSupersessionWrapper,
    OracleCurrentVersionInjector,
    assert_no_gold,
    default_phase0_config,
    stub_extract_candidates,
    stub_select_active,
    stub_summary,
)
from pipeline.io import GOLD_KEY, load_for_system
from pipeline.schema.fixtures import dummy_supersession_sample


def _responder_uses_injection(public_sample):
    inj = public_sample.get("_intervention_injection", "")
    return f"INJECTED:{inj}|RESPONSE:black coffee."


def test_assert_no_gold_blocks_forbidden_keys():
    public = load_for_system(dummy_supersession_sample())
    with pytest.raises(InterventionGoldLeakageError):
        assert_no_gold({**public, GOLD_KEY: {"x": 1}}, context="test")
    with pytest.raises(InterventionGoldLeakageError):
        assert_no_gold({**public, "target_versions": []}, context="test")
    with pytest.raises(InterventionGoldLeakageError):
        assert_no_gold({**public, "semantic_spine": {}}, context="test")
    # Plain public view passes
    assert_no_gold(public, context="test")


def test_minimal_wrapper_extracts_and_injects():
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    wrapper = MinimalSupersessionWrapper(
        config=default_phase0_config(),
        extractor=stub_extract_candidates,
        selector=stub_select_active,
        responder=_responder_uses_injection,
    )
    response, trace = wrapper.respond(public)
    assert "INJECTED:" in response
    assert trace.candidates  # the dummy fixture has "I've cut dairy"
    assert not trace.abstained
    assert trace.selected is not None


def test_minimal_wrapper_abstains_with_no_candidates():
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    # Strip the user turns that signal updates
    public = dict(public)
    public["history"] = []
    wrapper = MinimalSupersessionWrapper(
        config=default_phase0_config(),
        extractor=stub_extract_candidates,
        selector=stub_select_active,
        responder=_responder_uses_injection,
    )
    response, trace = wrapper.respond(public)
    assert trace.abstained
    assert trace.injected_text == ""


def test_minimal_wrapper_refuses_gold_in_input():
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    bad = {**public, GOLD_KEY: {"sneaky": True}}
    wrapper = MinimalSupersessionWrapper(
        config=default_phase0_config(),
        extractor=stub_extract_candidates,
        selector=stub_select_active,
        responder=_responder_uses_injection,
    )
    with pytest.raises(InterventionGoldLeakageError):
        wrapper.respond(bad)


def test_ablated_wrapper_does_not_select_versions():
    sample = dummy_supersession_sample()
    public = load_for_system(sample)
    wrapper = AblatedWrapper(
        config=default_phase0_config(),
        summary_fn=stub_summary,
        responder=_responder_uses_injection,
    )
    response, trace = wrapper.respond(public)
    assert trace.selected is None
    assert trace.candidates == []
    assert trace.injected_text  # generic summary present


def test_oracle_injects_gold_active_version():
    sample = dummy_supersession_sample()
    oracle = OracleCurrentVersionInjector(responder=_responder_uses_injection)
    response, trace = oracle.respond(sample)
    assert "black coffee" in trace.injected_text
    assert oracle.is_diagnostic is True
    meta = oracle.run_metadata(sample.sample_id, "run-1")
    assert meta.system_name == "oracle_current_version"
    assert meta.answer_backbone == "oracle_diagnostic"


def test_intervention_config_yaml_roundtrip(tmp_path):
    cfg = default_phase0_config()
    p = tmp_path / "lock.yaml"
    cfg.write(p)
    text = p.read_text()
    cfg2 = InterventionConfig.from_yaml(text)
    assert cfg == cfg2
