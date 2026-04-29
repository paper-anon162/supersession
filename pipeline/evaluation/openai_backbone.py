"""OpenAI Chat Completions backbone with the same callable contract as
``BedrockBackbone`` (``prompt -> str``). Uses the official OpenAI Python SDK
so any code that consumes ``LongContextBackboneLike`` can swap in a GPT
model without other changes.

Auth: reads ``OPENAI_API_KEY`` from the environment. Set via
``export OPENAI_API_KEY=sk-...`` before running. Do not pass the key as a
constructor argument or store it in any tracked file.

Model ids: pass any chat-capable id from
``https://api.openai.com/v1/models`` (e.g. ``gpt-5.4``,
``gpt-5.4-2026-03-05``, ``gpt-5.5``).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenAIBackbone:
    """OpenAI Chat-Completions text backbone (callable as prompt -> str)."""

    model_id: str
    max_new_tokens: int = 512
    temperature: float = 0.0
    name: str = ""
    system_prompt: str | None = None
    # For GPT-5 family only. Default is OpenAI's vendor-recommended
    # user-facing config: "medium" reasoning_effort. This is the right
    # cross-vendor comparison anchor — Sonnet 4.6 / Mistral / Llama all run
    # at their respective vendor defaults (no extended-thinking enabled,
    # but with whatever uncontrolled internal reasoning each model does).
    # Forcing GPT-5 to "none" would handicap it below its own default
    # rather than match it to other backbones. For sensitivity analysis,
    # pass reasoning_effort="none" / "low" / "high" / "xhigh" via the
    # constructor.
    reasoning_effort: str = "medium"
    # If True, sets response_format={"type": "json_object"} for the
    # GPT-5 family. Use this for the extract / select wrapper steps
    # to guarantee strict JSON output (avoids prose-around-JSON parse
    # failures and avoids wasting completion tokens on prose).
    json_mode: bool = False
    max_retries: int = 5
    initial_backoff: float = 2.0
    request_timeout: float = 90.0
    api_key_env: str = "OPENAI_API_KEY"
    # Retry on empty content (GPT-5 reasoning tokens can exhaust
    # max_completion_tokens, returning "" with finish_reason="length").
    # Each retry doubles max_completion_tokens up to a cap.
    empty_retries: int = 1
    empty_retry_max_tokens: int = 16384
    _client: Any = field(default=None, init=False, repr=False)
    # Diagnostic state from the most recent call (for trace logging).
    last_finish_reason: str | None = field(default=None, init=False, repr=False)
    last_usage: dict | None = field(default=None, init=False, repr=False)
    last_resolved_model: str | None = field(default=None, init=False, repr=False)
    last_empty_retried: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.model_id.replace("/", "__").replace(":", "_")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        from openai import OpenAI

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(
                f"OpenAIBackbone: ${self.api_key_env} is not set. "
                f"Export it before running, e.g. "
                f"`export {self.api_key_env}=sk-...`"
            )
        self._client = OpenAI(api_key=api_key, timeout=self.request_timeout)
        return self._client

    def __call__(self, prompt: str) -> str:
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        # GPT-5 family uses `max_completion_tokens` (not `max_tokens`) and
        # only supports `temperature=1` (default). We set max_completion_tokens
        # and skip temperature for gpt-5.x; for older models we use the
        # legacy parameters.
        is_gpt5 = self.model_id.startswith("gpt-5")
        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
        }
        if is_gpt5:
            kwargs["max_completion_tokens"] = self.max_new_tokens
            # GPT-5 family rejects custom temperature; rely on default.
            kwargs["reasoning_effort"] = self.reasoning_effort
        else:
            kwargs["max_tokens"] = self.max_new_tokens
            kwargs["temperature"] = self.temperature
        if self.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Reset diagnostic state for this call.
        self.last_finish_reason = None
        self.last_usage = None
        self.last_resolved_model = None
        self.last_empty_retried = 0

        backoff = self.initial_backoff
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = client.chat.completions.create(**kwargs)
                if not resp.choices:
                    return ""
                choice = resp.choices[0]
                content = (choice.message.content or "").strip()
                # Capture diagnostic fields regardless of empty/non-empty.
                self.last_finish_reason = getattr(choice, "finish_reason", None)
                self.last_resolved_model = getattr(resp, "model", None)
                if getattr(resp, "usage", None) is not None:
                    try:
                        self.last_usage = resp.usage.model_dump()
                    except Exception:  # pragma: no cover
                        self.last_usage = dict(getattr(resp, "usage", {}) or {})

                # Retry-on-empty: GPT-5 reasoning models can return ""
                # when reasoning tokens exhaust max_completion_tokens.
                # finish_reason="length" is the typical signal.
                if (
                    is_gpt5
                    and not content
                    and self.last_empty_retried < self.empty_retries
                ):
                    self.last_empty_retried += 1
                    new_budget = min(
                        self.empty_retry_max_tokens,
                        kwargs.get("max_completion_tokens", self.max_new_tokens) * 2,
                    )
                    kwargs["max_completion_tokens"] = new_budget
                    continue  # retry within the same loop
                return content
            except Exception as e:  # noqa: BLE001
                msg = str(e).lower()
                # Retry on transient errors; fail fast on quota / auth / context.
                transient = any(t in msg for t in (
                    "rate limit", "429", "timeout", "timed out",
                    "service unavailable", "503", "502", "504",
                    "internal server error", "500", "connection",
                ))
                fatal = any(t in msg for t in (
                    "insufficient_quota", "invalid_api_key", "authentication",
                    "context_length_exceeded", "maximum context length",
                    "model_not_found",
                ))
                if fatal or not transient:
                    raise
                last_err = e
                time.sleep(backoff)
                backoff *= 2
        if last_err is not None:
            raise last_err
        raise RuntimeError("OpenAIBackbone: exhausted retries with no captured error")


__all__ = ["OpenAIBackbone"]
