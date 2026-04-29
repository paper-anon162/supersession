"""Bedrock-backed LLM + embedding clients for Graphiti.

Graphiti's `LLMClient` and `EmbedderClient` ABCs are async; both speak
to a single async-friendly transport. Graphiti ships first-class clients
for OpenAI, Anthropic-direct, Gemini, Groq and Voyage — but **not**
Bedrock. This module fills that gap.

Both classes wrap `boto3` (sync) inside an `asyncio.to_thread` call so
they slot into Graphiti's async pipeline without blocking the event loop.

Locked decisions (data_plan §10.2 v1.3.7):
  - Extractor LLM: ``anthropic.claude-sonnet-4-6`` on Bedrock (D2)
  - Embedding model: ``amazon.titan-embed-text-v2:0`` (1024-dim default)

Region / profile defaults match `pipeline/evaluation/bedrock_backbone.py`
(``us-east-1``; AWS standard credential chain). Set ``BEDROCK_PROFILE``
or pass ``profile`` explicitly to use a named profile (e.g. ``ahe-long``).

Notes on the Anthropic Messages-on-Bedrock API surface
------------------------------------------------------

Bedrock-runtime's ``invoke_model`` accepts the same JSON body the
Anthropic Messages API takes (with ``anthropic_version`` set to
``bedrock-2023-05-31``). We use ``invoke_model`` here rather than
``converse`` because Graphiti's extraction pipeline asks the LLM to emit
a JSON object inside a ``tool_use`` block (mirroring
``llm_client/anthropic_client.py``). The Converse API does support tools
but with a different schema; staying on the raw Messages JSON keeps the
shape we return identical to what Graphiti's Anthropic client produces,
which means downstream parsing (tool args → dict → pydantic) "just
works".

# TODO: verify against real SDK on first real run — Bedrock
# inference-profile IDs for Anthropic Sonnet 4.6 are typically
# ``us.anthropic.claude-sonnet-4-6-v1:0`` (region-prefixed). The
# locked id ``anthropic.claude-sonnet-4-6`` (no prefix, no version
# suffix) follows the data_plan exactly; if Bedrock rejects that,
# the user will need to substitute the inference-profile id their
# account is provisioned for. See bedrock_backbone for the working
# profile + model-id pairs in use elsewhere in this project.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import typing
from collections.abc import Iterable
from typing import Any

from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
from graphiti_core.llm_client.errors import RateLimitError, RefusalError
from graphiti_core.prompts.models import Message
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# Default Bedrock anchor — D2 in the task spec. Region prefix may need
# to be added for cross-region inference profiles; the user can override
# via ``BedrockLLMClient(model_id=...)`` or env.
DEFAULT_BEDROCK_LLM_MODEL = "us.anthropic.claude-sonnet-4-6"  # inference profile id (verified 2026-04-27)
DEFAULT_BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_BEDROCK_REGION = "us-east-1"
ANTHROPIC_BEDROCK_VERSION = "bedrock-2023-05-31"


# ---------------------------------------------------------------------------
# Shared boto3 client factory (kept private; one client per (region, profile))
# ---------------------------------------------------------------------------


_BOTO_CACHE: dict[tuple[str, str | None], Any] = {}


def _get_bedrock_runtime(region: str, profile: str | None) -> Any:
    key = (region, profile)
    if key in _BOTO_CACHE:
        return _BOTO_CACHE[key]
    import boto3

    session_kwargs: dict[str, Any] = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.session.Session(**session_kwargs)
    client = session.client("bedrock-runtime", region_name=region)
    _BOTO_CACHE[key] = client
    return client


def _is_throttle_error(exc: Exception) -> bool:
    msg = str(exc)
    return any(
        tok in msg
        for tok in (
            "ThrottlingException",
            "Throttling",
            "TooManyRequests",
            "ServiceUnavailable",
            "ModelTimeoutException",
            "InternalServerException",
        )
    )


# ---------------------------------------------------------------------------
# BedrockLLMClient — for Graphiti's internal extractor (Sonnet 4.6, D2)
# ---------------------------------------------------------------------------


class BedrockLLMClient(LLMClient):
    """Graphiti ``LLMClient`` backed by Bedrock's Anthropic Messages API.

    Mirrors the structural-output protocol of ``AnthropicClient``:

      * Always uses a tool-use call. If a ``response_model`` is supplied,
        the tool's schema is the model's JSON schema; otherwise a generic
        ``{type: object}`` tool is used.
      * Returns ``dict[str, Any]`` (the parsed tool args). Graphiti's
        ``generate_response`` then validates against ``response_model``.

    Auth: standard AWS chain (env vars, ``~/.aws/credentials``, IMDS, ...).
    Pass ``profile`` for a named profile.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        cache: bool = False,
        *,
        region: str = DEFAULT_BEDROCK_REGION,
        profile: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_retries: int = 4,
        initial_backoff: float = 2.0,
    ) -> None:
        if config is None:
            config = LLMConfig()
        if config.model is None:
            config.model = DEFAULT_BEDROCK_LLM_MODEL
        if config.max_tokens is None or config.max_tokens == DEFAULT_MAX_TOKENS:
            config.max_tokens = max_tokens
        # Graphiti's LLMConfig defaults temperature=1; Bedrock-Anthropic
        # accepts that, but for an extractor we want determinism. Force
        # 0 unless the caller explicitly set something else.
        # (DEFAULT_TEMPERATURE in graphiti_core/llm_client/config.py is 1.)
        if config.temperature == 1:
            config.temperature = 0.0

        super().__init__(config, cache)
        self.region = region
        self.profile = profile or os.getenv("BEDROCK_PROFILE")
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        # Pre-warm the boto3 client so first call doesn't pay the
        # ~100-200ms session-init tax during a hot ingest loop.
        self._client = _get_bedrock_runtime(self.region, self.profile)

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _build_tool_block(
        response_model: type[BaseModel] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if response_model is not None:
            schema = response_model.model_json_schema()
            tool_name = response_model.__name__
            description = schema.get(
                "description", f"Extract {tool_name} information"
            )
        else:
            tool_name = "generic_json_output"
            description = "Output data in JSON format"
            schema = {
                "type": "object",
                "additionalProperties": True,
                "description": "Any JSON object containing the requested information",
            }
        tool = {
            "name": tool_name,
            "description": description,
            "input_schema": schema,
        }
        tool_choice = {"type": "tool", "name": tool_name}
        return [tool], tool_choice

    @staticmethod
    def _extract_json_from_text(text: str) -> dict[str, Any]:
        # Same fallback as graphiti_core.llm_client.anthropic_client.
        try:
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(text[json_start:json_end])
            raise ValueError(f"Could not extract JSON from model response: {text}")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(
                f"Could not extract JSON from model response: {text}"
            ) from e

    def _build_request_body(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        # First message is system per Graphiti's convention; the rest are
        # user/assistant. (See AnthropicClient._generate_response.)
        system_message = messages[0]
        user_messages = [
            {"role": m.role, "content": m.content} for m in messages[1:]
        ]
        tools, tool_choice = self._build_tool_block(response_model)
        return {
            "anthropic_version": ANTHROPIC_BEDROCK_VERSION,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "system": system_message.content,
            "messages": user_messages,
            "tools": tools,
            "tool_choice": tool_choice,
        }

    def _invoke_sync(self, body: dict[str, Any]) -> dict[str, Any]:
        # Synchronous Bedrock call wrapped in retries; runs inside
        # asyncio.to_thread so the event loop stays responsive.
        backoff = self.initial_backoff
        last_err: Exception | None = None
        for _ in range(self.max_retries):
            try:
                resp = self._client.invoke_model(
                    modelId=self.model,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                payload = resp.get("body")
                if hasattr(payload, "read"):
                    raw = payload.read()
                else:
                    raw = payload
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "refused to respond" in msg.lower():
                    raise RefusalError(msg) from e
                if _is_throttle_error(e):
                    last_err = e
                    import time as _time

                    _time.sleep(backoff)
                    backoff *= 2
                    continue
                # Hard failure (auth, validation, etc.) — bubble up.
                raise
        if last_err is not None:
            # Convert sustained throttle into Graphiti's RateLimitError so
            # the upstream tenacity retry decorator stops retrying.
            raise RateLimitError(
                f"Bedrock throttled after {self.max_retries} attempts: {last_err}"
            ) from last_err
        raise RuntimeError("BedrockLLMClient: exhausted retries with no captured error")

    @staticmethod
    def _parse_response(result: dict[str, Any]) -> dict[str, Any]:
        # Bedrock-Anthropic Messages response shape:
        #   {"id": ..., "type": "message", "role": "assistant",
        #    "content": [{"type": "tool_use", "name": ..., "input": {...}},
        #                {"type": "text", "text": "..."}],
        #    "stop_reason": ..., "usage": {...}}
        content_blocks: list[dict[str, Any]] = result.get("content", []) or []
        for block in content_blocks:
            if block.get("type") == "tool_use":
                tool_input = block.get("input", {})
                if isinstance(tool_input, dict):
                    return tool_input
                # Some providers stringify; tolerate both.
                return json.loads(str(tool_input))
        # Fallback: no tool_use, try to mine JSON out of a text block.
        for block in content_blocks:
            if block.get("type") == "text":
                return BedrockLLMClient._extract_json_from_text(
                    block.get("text", "")
                )
        raise ValueError(
            f"Could not extract structured data from Bedrock response: {result}"
        )

    # ---- LLMClient ABC --------------------------------------------------

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        # Graphiti's base `generate_response` already strips invalid
        # unicode and appends the multilingual instruction; we just need
        # to ship the messages.
        resolved_max = max_tokens or self.max_tokens or DEFAULT_MAX_TOKENS
        body = self._build_request_body(messages, response_model, resolved_max)
        try:
            result = await asyncio.to_thread(self._invoke_sync, body)
        except (RateLimitError, RefusalError):
            raise
        try:
            parsed = self._parse_response(result)
        except (ValueError, ValidationError) as e:
            logger.error(
                "BedrockLLMClient: %s",
                self._get_failed_generation_log(messages, json.dumps(result)[:1000]),
            )
            raise e
        return parsed


# ---------------------------------------------------------------------------
# BedrockEmbeddingClient — Titan v2 by default
# ---------------------------------------------------------------------------


class BedrockEmbeddingConfig(EmbedderConfig):
    embedding_model: str = Field(default=DEFAULT_BEDROCK_EMBEDDING_MODEL)
    region: str = Field(default=DEFAULT_BEDROCK_REGION)
    profile: str | None = Field(default=None)
    normalize: bool = Field(default=True)


class BedrockEmbeddingClient(EmbedderClient):
    """Graphiti embedder backed by Bedrock Titan-Embed-Text v2.

    Titan v2 returns 1024-dim float vectors by default (configurable to
    256 / 512 via ``dimensions`` request param; Graphiti's
    ``EmbedderConfig.embedding_dim`` default is 1024 so we stay there).
    Single-input invoke is sync; we wrap each call in ``asyncio.to_thread``.
    Batch is implemented as a serial loop because Titan invoke_model is
    one-input-per-call (the Bedrock batch-inference API is async-job-based
    and out of scope for the per-sample ingest loop).
    """

    def __init__(self, config: BedrockEmbeddingConfig | None = None) -> None:
        if config is None:
            config = BedrockEmbeddingConfig()
        self.config = config
        self.region = config.region
        self.profile = config.profile or os.getenv("BEDROCK_PROFILE")
        self._client = _get_bedrock_runtime(self.region, self.profile)

    def _embed_one_sync(self, text: str) -> list[float]:
        body = {"inputText": text}
        # Titan v2 supports `dimensions` and `normalize`; default is 1024
        # and True. Force them explicitly so behavior is reproducible.
        body["dimensions"] = self.config.embedding_dim
        body["normalize"] = self.config.normalize

        backoff = 2.0
        last_err: Exception | None = None
        for _ in range(4):
            try:
                resp = self._client.invoke_model(
                    modelId=self.config.embedding_model,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                payload = resp.get("body")
                raw = payload.read() if hasattr(payload, "read") else payload
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                parsed = json.loads(raw)
                return parsed["embedding"]
            except Exception as e:  # noqa: BLE001
                if _is_throttle_error(e):
                    last_err = e
                    import time as _time

                    _time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        raise RuntimeError(
            f"BedrockEmbeddingClient: exhausted retries: {last_err}"
        )

    async def create(
        self,
        input_data: str
        | list[str]
        | Iterable[int]
        | Iterable[Iterable[int]],
    ) -> list[float]:
        # Graphiti's contract is "single embedding back". For list input
        # the OpenAI client returns the *first* row truncated to
        # ``embedding_dim``; we mirror that.
        if isinstance(input_data, str):
            text = input_data
        elif isinstance(input_data, list) and input_data and isinstance(
            input_data[0], str
        ):
            text = typing.cast(list[str], input_data)[0]
        else:
            # Token-id forms aren't supported by Titan; coerce to string.
            text = str(list(input_data) if not isinstance(input_data, str) else input_data)

        emb = await asyncio.to_thread(self._embed_one_sync, text)
        return emb[: self.config.embedding_dim]

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        # Serial fallback. For the per-sample ingest sizes we expect
        # (a few dozen edge facts), this is fine; if it ever becomes
        # the bottleneck, swap in `asyncio.gather` with a semaphore.
        out: list[list[float]] = []
        for s in input_data_list:
            emb = await asyncio.to_thread(self._embed_one_sync, s)
            out.append(emb[: self.config.embedding_dim])
        return out


__all__ = [
    "BedrockEmbeddingClient",
    "BedrockEmbeddingConfig",
    "BedrockLLMClient",
    "DEFAULT_BEDROCK_EMBEDDING_MODEL",
    "DEFAULT_BEDROCK_LLM_MODEL",
    "DEFAULT_BEDROCK_REGION",
]
