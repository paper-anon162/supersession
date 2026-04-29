"""Gemini backbone via the Generative Language API REST endpoint.

Same callable contract as ``BedrockBackbone`` and ``OpenAIBackbone``
(``prompt -> str``) so any code consuming a long-context backbone can
swap in a Gemini model without other changes.

Auth: reads ``GEMINI_API_KEY`` from the environment. Either an AI Studio
API key (``AIza...``) or a Google Cloud API key for a project that has
the Generative Language API enabled. Set via:

    export GEMINI_API_KEY=AIza...

Model ids: pass any chat-capable id from
``GET /v1beta/models?key=$KEY`` (e.g. ``gemini-3.1-pro``,
``gemini-3.0-pro``, ``gemini-2.5-pro``). Strip the ``models/`` prefix
that the API returns.

Implementation note: uses ``urllib.request`` from the stdlib to avoid
adding a Google SDK dependency. The REST surface is small and stable.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class GeminiBackbone:
    """Generative Language API REST backbone (callable as prompt -> str)."""

    model_id: str
    max_new_tokens: int = 1024
    temperature: float = 0.0
    name: str = ""
    system_prompt: str | None = None
    # Gemini 3.x supports thinkingLevel: "low" / "medium" / "high".
    # We default to "medium" to match the cross-vendor default-reasoning
    # convention (parallel to OpenAI gpt-5.4 reasoning_effort="medium").
    # Pass None to let the API use its own default; pass a string
    # ("low"/"medium"/"high") to set explicitly. Older Gemini 2.5
    # models accept thinking_budget (token count) instead — set
    # thinking_level=None and use thinking_budget for those.
    thinking_level: str | None = "medium"
    thinking_budget: int | None = None
    # If True, sets responseMimeType="application/json" for guaranteed
    # JSON output. Use for wrapper extract / select calls.
    json_mode: bool = False
    # Gemini 3.x preview models have high-demand 503 spikes; bump retries
    # and timeout vs OpenAI defaults.
    max_retries: int = 8
    initial_backoff: float = 4.0
    request_timeout: float = 180.0
    api_key_env: str = "GEMINI_API_KEY"
    _key: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.model_id.replace("/", "__").replace(":", "_")

    def _get_key(self) -> str:
        if self._key:
            return self._key
        k = os.environ.get(self.api_key_env)
        if not k:
            raise RuntimeError(
                f"GeminiBackbone: ${self.api_key_env} is not set. "
                f"Export it before running, e.g. "
                f"`export {self.api_key_env}=AIza...`"
            )
        self._key = k
        return k

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]},
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_new_tokens,
            },
        }
        if self.system_prompt:
            body["systemInstruction"] = {
                "parts": [{"text": self.system_prompt}]
            }
        thinking_cfg: dict[str, Any] = {}
        if self.thinking_level is not None:
            thinking_cfg["thinkingLevel"] = self.thinking_level
        if self.thinking_budget is not None:
            thinking_cfg["thinkingBudget"] = self.thinking_budget
        if thinking_cfg:
            body["generationConfig"]["thinkingConfig"] = thinking_cfg
        if self.json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        return body

    def __call__(self, prompt: str) -> str:
        key = self._get_key()
        url = f"{API_BASE}/models/{self.model_id}:generateContent?key={key}"
        body = json.dumps(self._build_payload(prompt)).encode("utf-8")

        backoff = self.initial_backoff
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.request_timeout) as r:
                    payload = json.loads(r.read().decode("utf-8"))
                return self._extract_text(payload)
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", errors="replace")
                status = e.code
                # Fail fast on unrecoverable account errors; retry on
                # transient throttling and server errors.
                fatal = ("prepayment credits are depleted" in msg
                         or "API key not valid" in msg
                         or "API_KEY_INVALID" in msg
                         or "PERMISSION_DENIED" in msg
                         or "billing" in msg.lower())
                if fatal:
                    raise RuntimeError(f"HTTP {status} (fatal): {msg[:500]}")
                if status in (429, 500, 502, 503, 504):
                    last_err = RuntimeError(f"HTTP {status}: {msg[:200]}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RuntimeError(f"HTTP {status}: {msg[:500]}")
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                time.sleep(backoff)
                backoff *= 2
        if last_err is not None:
            raise last_err
        raise RuntimeError("GeminiBackbone: exhausted retries with no captured error")

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        cands = payload.get("candidates") or []
        if not cands:
            return ""
        parts = cands[0].get("content", {}).get("parts", []) or []
        out = []
        for p in parts:
            t = p.get("text")
            if t:
                out.append(t)
        return "".join(out).strip()


__all__ = ["GeminiBackbone"]
