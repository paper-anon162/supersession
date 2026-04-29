"""AWS Bedrock backbone for the LLM judge / response generation.

Mirrors the ``HFTransformersBackbone`` interface (callable: ``prompt -> str``)
so any code that consumes ``JudgeBackbone`` can swap to a frontier closed
model via Bedrock without further changes.

Uses the **Converse** API, which presents a unified message format across
providers (Anthropic, Meta, Mistral, DeepSeek, Qwen, ...). The model_id
should be a Bedrock inference-profile ID (e.g.
``us.anthropic.claude-opus-4-5-20251101-v1:0``).

Auth comes from the standard AWS credential chain. Set ``profile`` to use
a named profile; otherwise it defaults to the environment / default chain.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BedrockBackbone:
    """Bedrock Converse-API text backbone (callable as prompt -> str)."""

    model_id: str
    region: str = "us-east-1"
    profile: str | None = None
    max_new_tokens: int = 512
    temperature: float = 0.0
    name: str = ""
    system_prompt: str | None = None
    max_retries: int = 4
    initial_backoff: float = 2.0
    _client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name:
            # Make a clean filesystem-safe name out of the model id.
            self.name = self.model_id.replace("/", "__").replace(":", "_")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3

        session_kwargs = {}
        if self.profile:
            session_kwargs["profile_name"] = self.profile
        session = boto3.session.Session(**session_kwargs)
        self._client = session.client("bedrock-runtime", region_name=self.region)
        return self._client

    def __call__(self, prompt: str) -> str:
        client = self._get_client()
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": self.max_new_tokens,
                "temperature": self.temperature,
            },
        }
        if self.system_prompt:
            kwargs["system"] = [{"text": self.system_prompt}]

        backoff = self.initial_backoff
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = client.converse(**kwargs)
                blocks = resp.get("output", {}).get("message", {}).get("content", [])
                # Concatenate any text blocks (skips reasoning/thinking blocks).
                parts = [b.get("text", "") for b in blocks if "text" in b]
                return "".join(parts).strip()
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                # Throttled / transient → backoff and retry.
                if any(
                    tok in msg
                    for tok in (
                        "ThrottlingException",
                        "Throttling",
                        "TooManyRequests",
                        "ServiceUnavailable",
                        "ModelTimeoutException",
                        "InternalServerException",
                    )
                ):
                    last_err = e
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        if last_err is not None:
            raise last_err
        raise RuntimeError("BedrockBackbone: exhausted retries with no captured error")


__all__ = ["BedrockBackbone"]
