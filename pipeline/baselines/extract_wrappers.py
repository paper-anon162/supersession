"""Temporal Wrapper baselines (B1, B2) for the supersession-aware pipeline.

Two extraction-style baselines that follow the same 5-step
``MinimalSupersessionWrapper`` template as ``sonnet_extract``, but
replace the LLM-driven ``ActiveVersionSelector`` with explicit
timestamp-based rules:

  - **B1 ``RecencyWrapperBaseline``** (system name
    ``recency_wrapper``): pick the candidate with the latest
    ``session_introduced`` regardless of which target slot it
    addresses. Naive "most-recent-wins" temporal handling.

  - **B2 ``ActiveStateWrapperBaseline``** (system name
    ``active_state_wrapper``): bind candidates to the same
    behaviorally contestable target (group by ``topic``, pick the
    topic most similar to ``current_query`` by BGE embedding), then
    return that topic's latest candidate. Supersession-aware temporal
    intervention.

Why two: B1 vs B2 isolates *target binding* as a single-variable
ablation. If B2 ≫ B1, supersession is not just recency — the agent
must reconstruct the *active state of the contested target*, not
merely the latest fact in time. Distractor sessions in our pool
provide the testbed that pulls these apart.

Both share extraction with ``sonnet_extract`` (same Sonnet 4.6
candidate extractor) so the baselines are directly comparable.

Conforms to ``pipeline.baselines.runner.Baseline`` Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pipeline.intervention.temporal_selectors import (
    recency_selector,
    target_bound_recency_selector,
)
from pipeline.intervention.wrapper import (
    CandidateExtractor,
    CandidateUpdate,
    InterventionConfig,
    MinimalSupersessionWrapper,
    WrapperTrace,
    assert_no_gold,
    default_phase0_config,
)
from pipeline.schema import RunMetadata


@dataclass
class _TemporalWrapperBase:
    """Common scaffold for B1/B2 — only the ``selector`` differs.

    Adapts ``MinimalSupersessionWrapper`` (which returns
    ``(response, trace)``) to the ``Baseline`` Protocol (returns just
    ``str``). The internal trace can be inspected via
    ``last_trace`` after each call (used for tests / debugging).
    """

    backbone: Any                           # for run_metadata
    extractor: CandidateExtractor
    responder: Callable[[dict[str, Any]], str]
    config: InterventionConfig = field(default_factory=default_phase0_config)
    name: str = "temporal_wrapper_base"
    answer_backbone_provider: str = "bedrock"
    extra: dict[str, Any] = field(default_factory=dict)

    last_trace: WrapperTrace | None = field(default=None, init=False, repr=False)

    def _selector(
        self,
        candidates: list[CandidateUpdate],
        public_sample: dict[str, Any],
    ) -> CandidateUpdate | None:
        raise NotImplementedError

    def respond(self, public_sample: dict[str, Any]) -> str:
        assert_no_gold(public_sample, context=self.name)
        wrapper = MinimalSupersessionWrapper(
            config=self.config,
            extractor=self.extractor,
            selector=self._selector,
            responder=self.responder,
            name=self.name,
        )
        response, trace = wrapper.respond(public_sample)
        self.last_trace = trace
        return response

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone=getattr(self.backbone, "model_id", "unknown"),
            answer_backbone_provider=self.answer_backbone_provider,  # type: ignore[arg-type]
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_provider="local",
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id=(
                f"{self.name}/extract_then_temporal_resolve/v1"
            ),
            temperature=getattr(self.backbone, "temperature", 0.0),
            max_tokens=getattr(self.backbone, "max_new_tokens", 0),
        )


@dataclass
class RecencyWrapperBaseline(_TemporalWrapperBase):
    """B1: pick the latest candidate, ignoring topic."""

    name: str = "recency_wrapper"

    def _selector(
        self,
        candidates: list[CandidateUpdate],
        public_sample: dict[str, Any],
    ) -> CandidateUpdate | None:
        return recency_selector(candidates, public_sample)


@dataclass
class ActiveStateWrapperBaseline(_TemporalWrapperBase):
    """B2: group by topic, pick query-relevant topic's latest candidate."""

    name: str = "active_state_wrapper"

    def _selector(
        self,
        candidates: list[CandidateUpdate],
        public_sample: dict[str, Any],
    ) -> CandidateUpdate | None:
        return target_bound_recency_selector(candidates, public_sample)


__all__ = [
    "RecencyWrapperBaseline",
    "ActiveStateWrapperBaseline",
]
