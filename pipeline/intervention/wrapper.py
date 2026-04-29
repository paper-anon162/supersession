"""Minimal supersession-aware wrapper (protocol §12, data_plan §10.7).

Three components per protocol §12.2:

  - ``MinimalSupersessionWrapper``  : extract candidate updates → select active
                                      version → inject into base prompt.
  - ``AblatedWrapper``               : injects a generic memory summary
                                      *without* version invalidation. Used as
                                      contrast — protocol §12.4: "Wrapper ≈
                                      ablated wrapper" implies improvement is
                                      from generic context, not supersession.
  - ``OracleCurrentVersionInjector`` : *diagnostic only*. Uses gold to inject
                                      the active version directly. Provides
                                      the upper bound (protocol §11.1).

Hard input invariants (protocol §12.3):

    Allowed   : history, current_query, public sample fields
    Forbidden : _gold, target_versions, semantic_spine, violation_predicate,
                gold_target_type, supersession_subtype, active/outdated labels

The fair-baseline wrappers refuse to construct themselves around a sample if
the public payload contains forbidden fields. The oracle wrapper is the
*only* component permitted to consume gold — and it self-labels as
``architecture-plus-oracle`` so its results never get reported as a fair
baseline.

Phase 0 implements the orchestration layer with stub LLM-backed steps; Phase
1 wires in real prompts. The lock fields enumerated in protocol §12.5 are
encoded as ``InterventionConfig`` and serialized to ``intervention_lock_config.yaml``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from pipeline.io import GOLD_KEY
from pipeline.schema import RunMetadata, Sample

# Forbidden field names that must never reach the wrapper's input. These
# correspond to the gold-only fields enumerated in protocol §12.3 plus
# convenience labels.
_FORBIDDEN_KEYS = (
    GOLD_KEY,
    "target_versions",
    "semantic_spine",
    "violation_predicate",
    "gold_target_type",
    "supersession_subtype",
    "active_version",
    "outdated_version",
)


class InterventionGoldLeakageError(RuntimeError):
    """Raised when forbidden fields appear in the wrapper's input."""


def assert_no_gold(public_sample: dict[str, Any], context: str = "") -> None:
    leaked = [k for k in _FORBIDDEN_KEYS if k in public_sample]
    if leaked:
        raise InterventionGoldLeakageError(
            f"forbidden field(s) {leaked} present in wrapper input ({context})"
        )


# ---------------------------------------------------------------------------
# Lock-config (protocol §12.5)
# ---------------------------------------------------------------------------


@dataclass
class InterventionConfig:
    intervention_llm_backbone: str
    candidate_extraction_prompt_id: str
    active_version_selection_prompt_id: str
    injection_format: str
    ablation_prompt_id: str
    max_candidate_updates: int
    tie_breaking_rule: str
    uncertainty_handling: str
    retry_policy: str

    def to_yaml(self) -> str:
        return yaml.safe_dump(asdict(self), sort_keys=False)

    @classmethod
    def from_yaml(cls, text: str) -> "InterventionConfig":
        data = yaml.safe_load(text)
        return cls(**data)

    def write(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_yaml())


def default_phase0_config() -> InterventionConfig:
    """Phase 0 placeholder config. Phase 1 must replace these IDs with the
    real prompt IDs and lock the file before MVP execution.
    """
    return InterventionConfig(
        intervention_llm_backbone="phase0_stub",
        candidate_extraction_prompt_id="prompts/intervention/extract_candidates.v0.jinja",
        active_version_selection_prompt_id="prompts/intervention/select_active.v0.jinja",
        injection_format="The user's currently valid state on {topic} is: {value}.",
        ablation_prompt_id="prompts/intervention/ablation.v0.jinja",
        max_candidate_updates=8,
        tie_breaking_rule="prefer_most_recent_session",
        uncertainty_handling="abstain_with_no_injection",
        retry_policy="single_retry_on_parse_failure",
    )


# ---------------------------------------------------------------------------
# Step-level types
# ---------------------------------------------------------------------------


@dataclass
class CandidateUpdate:
    topic: str
    value: str
    polarity: str
    session_introduced: int
    rationale: str = ""


@dataclass
class WrapperTrace:
    sample_id: str
    candidates: list[CandidateUpdate]
    selected: CandidateUpdate | None
    abstained: bool
    injected_text: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Step interfaces (Phase 1+ plugs in real LLM calls)
# ---------------------------------------------------------------------------


class CandidateExtractor(Protocol):
    def __call__(self, public_sample: dict[str, Any]) -> list[CandidateUpdate]: ...


class ActiveVersionSelector(Protocol):
    def __call__(
        self, candidates: list[CandidateUpdate], public_sample: dict[str, Any]
    ) -> CandidateUpdate | None: ...


# ---------------------------------------------------------------------------
# Wrappers
# ---------------------------------------------------------------------------


@dataclass
class MinimalSupersessionWrapper:
    """Wraps a base ``responder`` callable.

    Pipeline: extract candidates → select active → inject into prompt → call
    responder. The base responder must accept a ``dict[str, Any]`` (public
    sample with optional ``_intervention_injection`` field).
    """

    config: InterventionConfig
    extractor: CandidateExtractor
    selector: ActiveVersionSelector
    responder: Callable[[dict[str, Any]], str]
    name: str = "minimal_supersession_wrapper"

    def respond(
        self, public_sample: dict[str, Any]
    ) -> tuple[str, WrapperTrace]:
        assert_no_gold(public_sample, context=self.name)
        candidates = self.extractor(public_sample)
        if len(candidates) > self.config.max_candidate_updates:
            candidates = candidates[: self.config.max_candidate_updates]

        selected: CandidateUpdate | None = None
        abstained = False
        injected_text = ""
        notes = ""

        if not candidates:
            abstained = True
            notes = "no candidates extracted"
        else:
            selected = self.selector(candidates, public_sample)
            if selected is None:
                abstained = True
                notes = "selector abstained (uncertainty)"
            else:
                injected_text = self.config.injection_format.format(
                    topic=selected.topic,
                    value=selected.value,
                )

        augmented = dict(public_sample)
        if injected_text:
            augmented["_intervention_injection"] = injected_text
        response = self.responder(augmented)

        trace = WrapperTrace(
            sample_id=public_sample["sample_id"],
            candidates=candidates,
            selected=selected,
            abstained=abstained,
            injected_text=injected_text,
            notes=notes,
        )
        return response, trace

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone=self.config.intervention_llm_backbone,
            answer_backbone_provider="local",
            embedding_model="none",
            embedding_provider="none",
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id=self.config.candidate_extraction_prompt_id,
            temperature=0.0,
            max_tokens=0,
        )


@dataclass
class AblatedWrapper:
    """Generic memory-summary injection without version invalidation.

    Per protocol §12.2 / §12.4: matches the wrapper's surface plumbing but
    does NOT identify or honor specific update relations. If the active
    wrapper does not beat this, the apparent improvement is just generic
    context injection.
    """

    config: InterventionConfig
    summary_fn: Callable[[dict[str, Any]], str]
    responder: Callable[[dict[str, Any]], str]
    name: str = "ablated_wrapper"

    def respond(
        self, public_sample: dict[str, Any]
    ) -> tuple[str, WrapperTrace]:
        assert_no_gold(public_sample, context=self.name)
        injected_text = self.summary_fn(public_sample)
        augmented = dict(public_sample)
        if injected_text:
            augmented["_intervention_injection"] = injected_text
        response = self.responder(augmented)
        trace = WrapperTrace(
            sample_id=public_sample["sample_id"],
            candidates=[],
            selected=None,
            abstained=False,
            injected_text=injected_text,
            notes="ablated: generic memory summary",
        )
        return response, trace


@dataclass
class OracleCurrentVersionInjector:
    """Diagnostic-only: injects the gold active version directly.

    Per protocol §11.1, oracle is an upper-bound diagnostic. It must NOT be
    reported as a fair baseline. The label ``architecture-plus-oracle`` is
    embedded in ``run_metadata`` so downstream reporting can refuse to mix it
    into the main table.
    """

    responder: Callable[[dict[str, Any]], str]
    name: str = "oracle_current_version"
    is_diagnostic: bool = True

    def respond(self, sample: Sample) -> tuple[str, WrapperTrace]:
        # Oracle needs the gold view — that's the entire point. We do not
        # use ``load_for_system`` here.
        from pipeline.io import load_for_diagnostic

        full = load_for_diagnostic(sample)
        active = full[GOLD_KEY]["violation_predicate"]["must_honor"]
        topic = active["topic"]
        value = active["value"]
        injected_text = (
            f"The user's currently valid state on {topic} is: {value}."
        )

        # The responder still receives a public-only view augmented with the
        # oracle injection. It does not see ``_gold`` directly.
        from pipeline.io import load_for_system

        public = load_for_system(sample)
        augmented = dict(public)
        augmented["_intervention_injection"] = injected_text
        response = self.responder(augmented)

        trace = WrapperTrace(
            sample_id=sample.sample_id,
            candidates=[],
            selected=CandidateUpdate(
                topic=topic,
                value=str(value),
                polarity=active["polarity"],
                session_introduced=active["session_introduced"],
                rationale="oracle: gold active version",
            ),
            abstained=False,
            injected_text=injected_text,
            notes="oracle diagnostic; not a fair baseline",
        )
        return response, trace

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone="oracle_diagnostic",
            answer_backbone_provider="local",
            embedding_model="none",
            embedding_provider="none",
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id="oracle/diagnostic/v1",
            temperature=0.0,
            max_tokens=0,
        )


# ---------------------------------------------------------------------------
# Phase 0 stub steps (deterministic; no LLM)
# ---------------------------------------------------------------------------


def stub_extract_candidates(
    public_sample: dict[str, Any],
) -> list[CandidateUpdate]:
    """Naive Phase 0 extractor: scan user turns for "I'll switch to / I now /
    I prefer / changed to" markers and emit candidates. Strictly placeholder.
    """
    candidates: list[CandidateUpdate] = []
    for session in public_sample["history"]:
        for turn in session["turns"]:
            if turn["role"] != "user":
                continue
            text = turn["text"].strip()
            lower = text.lower()
            for marker in (
                " switched to ",
                " switched from ",
                " changed to ",
                " moved to ",
                " I now ",
                " I prefer ",
                " from now on ",
                " back to ",
                "i've cut",
                "i have cut",
            ):
                if marker in f" {lower} ":
                    candidates.append(
                        CandidateUpdate(
                            topic="user_state_update",
                            value=text,
                            polarity="prefer",
                            session_introduced=int(
                                session["session_id"].lstrip("s") or 0
                            )
                            if session["session_id"].startswith("s")
                            else 0,
                            rationale=f"matched marker {marker.strip()!r}",
                        )
                    )
                    break
    return candidates


def stub_select_active(
    candidates: list[CandidateUpdate], public_sample: dict[str, Any]
) -> CandidateUpdate | None:
    """Phase 0 selector: pick the latest candidate by session order."""
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.session_introduced)


def stub_summary(public_sample: dict[str, Any]) -> str:
    """Ablated summary: concatenate first user turn of each session."""
    snippets: list[str] = []
    for session in public_sample["history"]:
        for turn in session["turns"]:
            if turn["role"] == "user":
                snippets.append(turn["text"])
                break
    return " | ".join(snippets[:3])


__all__ = [
    "AblatedWrapper",
    "CandidateExtractor",
    "CandidateUpdate",
    "InterventionConfig",
    "InterventionGoldLeakageError",
    "MinimalSupersessionWrapper",
    "OracleCurrentVersionInjector",
    "WrapperTrace",
    "assert_no_gold",
    "default_phase0_config",
    "stub_extract_candidates",
    "stub_select_active",
    "stub_summary",
]
