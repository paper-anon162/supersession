"""Trivial baselines used to exercise the pipeline end-to-end without an LLM.

These exist only to validate the runner / judge / scoring chain. They are not
real systems and must not appear in any benchmark result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.schema import RunMetadata


@dataclass
class CannedResponseBaseline:
    """Returns a fixed string for every sample. Useful as a low-bar reference
    in the judge dry-run."""

    response_text: str
    name: str = "canned_dummy"

    def respond(self, public_sample: dict[str, Any]) -> str:
        return self.response_text

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone="canned",
            answer_backbone_provider="local",
            embedding_model="none",
            embedding_provider="none",
            vector_store=None,
            graph_store=None,
            uses_full_history=False,
            uses_retrieved_memory=False,
            prompt_template_id="dummy/canned/v1",
            temperature=0.0,
            max_tokens=0,
        )


@dataclass
class LastUserTurnEchoBaseline:
    """Echoes the user's last turn — a deliberately weak retention baseline."""

    name: str = "last_user_turn_echo"

    def respond(self, public_sample: dict[str, Any]) -> str:
        history = public_sample["history"]
        for session in reversed(history):
            for turn in reversed(session["turns"]):
                if turn["role"] == "user":
                    return turn["text"]
        return ""

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone="echo",
            answer_backbone_provider="local",
            embedding_model="none",
            embedding_provider="none",
            vector_store=None,
            graph_store=None,
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id="dummy/echo/v1",
            temperature=0.0,
            max_tokens=0,
        )


@dataclass
class CallableBaseline:
    """Adapter that turns any ``(public_sample) -> str`` callable into a
    Baseline. Useful in tests."""

    fn: Any
    name: str = "callable_baseline"
    metadata_template: dict[str, Any] = field(default_factory=dict)

    def respond(self, public_sample: dict[str, Any]) -> str:
        return self.fn(public_sample)

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        defaults = dict(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="none",
            answer_backbone="callable",
            answer_backbone_provider="local",
            embedding_model="none",
            embedding_provider="none",
            vector_store=None,
            graph_store=None,
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id="callable/v1",
            temperature=0.0,
            max_tokens=0,
        )
        defaults.update(self.metadata_template)
        return RunMetadata(**defaults)


__all__ = [
    "CallableBaseline",
    "CannedResponseBaseline",
    "LastUserTurnEchoBaseline",
]
