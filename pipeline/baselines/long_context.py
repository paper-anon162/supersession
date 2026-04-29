"""Long-context baseline (protocol §11; data_plan §10.4).

Reads the entire history plus the current query and produces a response.
This is the baseline that tests whether the model can solve supersession
purely from full-history reading, with no retrieval or memory architecture.

For local execution we use ``HFTransformersBackbone`` (Qwen-7B FP16 by
default). For frontier closed long-context (Claude / GPT) the same shape
applies — swap the backbone factory.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pipeline.evaluation.local_backbone import HFTransformersBackbone
from pipeline.schema import RunMetadata

# Anything that is callable as ``backbone(prompt) -> str`` and exposes
# ``system_prompt``, ``model_id``, ``temperature``, ``max_new_tokens`` works
# here — both ``HFTransformersBackbone`` and ``BedrockBackbone`` satisfy
# this protocol.
LongContextBackboneLike = Any

LONG_CONTEXT_SYSTEM = (
    "You are a personal assistant helping the user with their request. "
    "Use the conversation history to understand what the user wants, "
    "including any preferences, constraints, or instructions they have "
    "given you in past sessions. Respond directly to the current request "
    "in a natural, helpful way. Do not list the history back to the user. "
    "Do not ask clarifying questions unless absolutely necessary."
)


def _format_history(history: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for s in history:
        ts = f" @ {s['timestamp']}" if s.get("timestamp") else ""
        blocks.append(f"[Session {s['session_id']}{ts}]")
        for t in s["turns"]:
            blocks.append(f"{t['role']}: {t['text']}")
        blocks.append("")
    return "\n".join(blocks)


def render_long_context_prompt(public_sample: dict[str, Any]) -> str:
    history = _format_history(public_sample["history"])
    return (
        f"=== Conversation history ===\n{history}\n"
        f"=== Current request ===\n{public_sample['current_query']}\n"
    )


@dataclass
class LongContextBaseline:
    """Long-context baseline backed by an HF transformers model."""

    backbone: LongContextBackboneLike
    name: str = "long_context_local"
    answer_backbone_provider: str = "local"
    memory_infra_location: str = "none"
    extra: dict[str, Any] = field(default_factory=dict)

    def respond(self, public_sample: dict[str, Any]) -> str:
        prompt = render_long_context_prompt(public_sample)
        # Augment if intervention injection has been added by a wrapper.
        injection = public_sample.get("_intervention_injection")
        if injection:
            prompt = f"{prompt}\n=== Note ===\n{injection}\n"
        # Apply the long-context system prompt at this layer; the backbone's
        # default system prompt is not used.
        bb = self.backbone
        original_system = bb.system_prompt
        bb.system_prompt = LONG_CONTEXT_SYSTEM
        try:
            return bb(prompt)
        finally:
            bb.system_prompt = original_system

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location=self.memory_infra_location,  # type: ignore[arg-type]
            answer_backbone=self.backbone.model_id,
            answer_backbone_provider=self.answer_backbone_provider,  # type: ignore[arg-type]
            embedding_model="none",
            embedding_provider="none",
            uses_full_history=True,
            uses_retrieved_memory=False,
            prompt_template_id="long_context/full_history/v1",
            temperature=self.backbone.temperature,
            max_tokens=self.backbone.max_new_tokens,
        )


__all__ = [
    "LONG_CONTEXT_SYSTEM",
    "LongContextBaseline",
    "render_long_context_prompt",
]
