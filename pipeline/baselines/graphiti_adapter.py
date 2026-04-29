"""Graphiti memory-architecture baseline (data_plan §10.2; protocol §11).

Per the 2026-04-27 baseline pivot (protocol v1.3.7), Graphiti is the
**sole** memory-architecture baseline in the main study. Graphiti is the
open-source temporal knowledge graph engine that powers Zep Cloud
(Rasmussen et al. 2025, arxiv:2501.13956); the Zep Community Edition
wrapper was officially deprecated upstream (code moved to legacy/) so we
go straight to the underlying engine.

Architecture being tested: bi-temporal edges (``valid_at`` / ``invalid_at``)
in a knowledge graph. The internal extractor LLM identifies supersession
events from the conversation and writes ``invalid_at`` timestamps on the
fact edges they replace. Retrieval can filter to "currently valid" facts.
The benchmark's ``implicit_drift`` failure pattern is the case where this
should struggle most (no explicit supersession signal); ``explicit_replacement``
is the case where it should excel.

This module is **code-complete but unrun against real Bedrock**.
Required runtime dependencies:

  1. A running FalkorDB instance (default: ``redis://localhost:6379``).
     Bring up via ``scripts/graphiti_infra.sh up`` (which uses
     ``docker/docker-compose.graphiti.yml``). Neo4j is also wired
     conditionally.
  2. ``graphiti-core[falkordb]`` installed (pinned via ``uv add``;
     locks ``falkordb==1.6.0``, ``redis==7.4.0``).
  3. The shared answer-generation backbone (Llama 3.1 8B Bedrock, locked)
     wired through ``BedrockBackbone``.
  4. AWS credentials (env / ``~/.aws/credentials`` / IMDS) with access
     to **Sonnet 4.6** + **Titan-Embed v2** in ``us-east-1`` (or override
     via ``BedrockLLMClient(region=..., profile=...)``). Sonnet 4.6 is
     used as Graphiti's internal extractor LLM (NOT the answer backbone)
     so the head-to-head against ``sonnet_extract`` isolates the
     architectural effect from extractor-strength differences (data_plan
     §10.2 v1.3.7 rationale).

Per-sample lifecycle (current plan, subject to user lock)
---------------------------------------------------------

Each evaluation sample is treated as an **isolated user namespace**:

  1. ``ingest(sample)`` — create a fresh Graphiti ``group_id`` (the
     namespace/tenant primitive); push each Session as a sequence of
     ``add_episode`` calls so Graphiti's extractor builds the temporal
     knowledge graph. Use the Session's ``timestamp`` as the episode
     ``reference_time`` so ``valid_at`` / ``invalid_at`` edges anchor to
     story time, not ingest wall-clock time.
  2. ``retrieve(sample)`` — query the temporal graph with
     ``sample.current_query`` via ``client.search`` (or the typed search
     API); return top-k facts/edges.
  3. ``answer(sample)`` — feed retrieved memory + the current query to
     the shared answer backbone (``BedrockBackbone``).
  4. After the sample is scored, **delete the group** (or wipe its edges)
     to prevent state leakage across samples.

Why fresh-per-sample, not shared:
  - Each Sample carries its own self-contained ``history`` and gold
    semantic spine. Sharing a Graphiti namespace across samples would
    mix versions across unrelated topics and contaminate retrieval.
  - The benchmark's fairness contract requires every system to see
    *exactly* the conversation history in ``sample.history`` and nothing
    else — no warm cache from prior samples.

The trade-off: per-sample fresh ingest pays the extractor LLM cost
N times (= manifest size). At 1064 Phase-3 samples × (avg ~8 sessions ×
~6 turns) this is ~50k extractor calls. Cost-control levers:
(a) one ``add_episode`` per session (default) instead of per turn;
(b) consider parallelizing ingest across samples with a worker pool;
(c) the Phase-2 N=135 smoke test bounds initial cost.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pipeline.schema import RunMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class GraphitiConfig:
    """Graphiti service + retrieval configuration.

    The 2×3 grid (data_plan §10.2) — top-k ∈ {5, 10, 20} × temporal
    invalidation ∈ {on, off} — is selected by varying ``top_k`` and
    ``temporal_invalidation`` across pilot runs. The winning config is
    locked before the main run and may not be retuned afterwards.
    """

    # Graph backend connection. FalkorDB ships with a docker image and a
    # smaller footprint than Neo4j; both are supported by Graphiti.
    graph_backend: str = "falkordb"        # "falkordb" | "neo4j"
    graph_uri: str = "redis://localhost:6379"  # FalkorDB; Neo4j uses bolt://
    graph_user: str | None = None             # Neo4j only
    graph_password: str | None = None         # Neo4j only

    # Retrieval knobs (data_plan §10.2 grid)
    top_k: int = 10
    temporal_invalidation: bool = True      # if False, retrieve all facts
                                            # without filtering by valid_at /
                                            # invalid_at edge state

    # Extractor backbone — Graphiti's internal "build the knowledge graph"
    # LLM. Locked to **Sonnet 4.6** (NOT the answer-gen backbone) so the
    # head-to-head against ``sonnet_extract`` isolates the architectural
    # effect from extractor-strength differences (data_plan §10.2 v1.3.7
    # rationale: Graphiti vs sonnet_extract is the cleanest "same frontier
    # extractor, different storage architecture" comparison; using a
    # weaker extractor here would conflate extractor capability with
    # graph-architecture quality). Answer-gen still goes through
    # Llama 8B per the shared-backbone rule (§10.5).
    extractor_model_id: str = "us.anthropic.claude-sonnet-4-6"  # Bedrock inference profile id (verified 2026-04-27)
    extractor_provider: str = "bedrock"     # "bedrock" | "openai" | "anthropic"

    # Embedding model used by Graphiti for similarity search.
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_provider: str = "bedrock"

    # Ingest granularity
    one_session_per_episode: bool = True    # True = one add_episode call
                                            # per Session; False = one per
                                            # turn (more granular extractor
                                            # signal, ~6× more LLM calls)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@dataclass
class GraphitiBaseline:
    """Graphiti temporal-memory baseline; mirrors ``NaiveRAGBaseline`` shape.

    Conforms to the ``Baseline`` Protocol in
    ``pipeline.baselines.runner`` (``respond(public_sample) -> str`` plus
    ``run_metadata``). Pre-/post-respond hooks (``ingest`` / ``retrieve`` /
    ``answer``) are exposed publicly to make the per-sample lifecycle
    inspectable — useful for debugging Graphiti state and for the
    ``__main__`` smoke test below.

    The shared answer backbone (``BedrockBackbone`` for Llama 3.1 8B)
    is injected as ``backbone`` so this adapter does not duplicate
    Bedrock plumbing — same convention as the long-context and
    naive-rag baselines.
    """

    backbone: Any                                  # BedrockBackbone-like
    config: GraphitiConfig = field(default_factory=GraphitiConfig)
    name: str = "graphiti_local_top10_inv_on"
    answer_backbone_provider: str = "bedrock"
    extra: dict[str, Any] = field(default_factory=dict)

    # Lazy Graphiti client; instantiated on first ingest() call.
    _client: Any = field(default=None, init=False, repr=False)

    # ----- public lifecycle -------------------------------------------------

    def ingest(self, public_sample: dict[str, Any]) -> dict[str, Any]:
        """Push the sample's history into a fresh Graphiti group_id.

        Returns the ingest payload (same shape as
        ``_build_ingest_payload``) so callers can inspect what was sent.
        Sessions are ingested in chronological order — the extractor's
        bi-temporal logic depends on this for ``invalid_at`` to fire on
        superseded edges.
        """
        client = self._get_client()
        payload = self._build_ingest_payload(public_sample)
        asyncio.run(self._ingest_async(client, payload))
        return payload

    async def _ingest_async(self, client: Any, payload: dict[str, Any]) -> None:
        from graphiti_core.nodes import EpisodeType

        group_id: str = payload["group_id"]
        sessions: list[dict[str, Any]] = payload["sessions"]
        # Chronological order: the input list is already authored that
        # way, but make it explicit so a future refactor of the public
        # sample shape doesn't silently shuffle ingest order.
        sessions = sorted(
            sessions,
            key=lambda s: s.get("reference_time") or "",
        )

        for session in sessions:
            ref_time = _parse_reference_time(session.get("reference_time"))
            if self.config.one_session_per_episode:
                await client.add_episode(
                    name=session["episode_name"],
                    episode_body=session["episode_body"] or "",
                    source_description="ssbench session transcript",
                    reference_time=ref_time,
                    source=EpisodeType.message,
                    group_id=group_id,
                )
            else:
                # Per-turn mode: one add_episode per message. Re-use the
                # session-level reference_time for every turn (we don't
                # carry per-turn timestamps in the public sample).
                turns = session["turn_messages"] or []
                for i, turn in enumerate(turns):
                    body = f"{turn['role']}: {turn['content']}"
                    await client.add_episode(
                        name=f"{session['episode_name']}--t{i:03d}",
                        episode_body=body,
                        source_description="ssbench turn",
                        reference_time=ref_time,
                        source=EpisodeType.message,
                        group_id=group_id,
                    )

    def retrieve(self, public_sample: dict[str, Any]) -> list[dict[str, Any]]:
        """Query Graphiti's temporal graph for facts/edges relevant to
        ``current_query``. Returns the retrieved chunks for ``answer()``.
        """
        client = self._get_client()
        sample_id = public_sample["sample_id"]
        group_id = self._group_id_for(sample_id)
        query = public_sample["current_query"]
        return asyncio.run(self._retrieve_async(client, query, group_id))

    async def _retrieve_async_raw(
        self, client: Any, query: str, group_id: str
    ) -> list[dict[str, Any]]:
        """Search without the invalidation filter — returns every retrieved
        edge with full bi-temporal annotations preserved. Callers decide
        whether to filter (see ``_retrieve_async`` and ``respond_both``).
        """
        edges = await client.search(
            query=query,
            group_ids=[group_id],
            num_results=self.config.top_k,
        )

        chunks: list[dict[str, Any]] = []
        for e in edges:
            valid_at = getattr(e, "valid_at", None)
            invalid_at = getattr(e, "invalid_at", None)
            chunk = {
                "fact": getattr(e, "fact", ""),
                "name": getattr(e, "name", ""),
                "valid_at": valid_at.isoformat() if valid_at else None,
                "invalid_at": invalid_at.isoformat() if invalid_at else None,
                "uuid": getattr(e, "uuid", None),
                "is_currently_valid": invalid_at is None,
            }
            chunks.append(chunk)
        return chunks

    async def _retrieve_async(
        self, client: Any, query: str, group_id: str
    ) -> list[dict[str, Any]]:
        chunks = await self._retrieve_async_raw(client, query, group_id)
        # Ablation: when temporal_invalidation is OFF we surface edges
        # regardless of invalid_at; when ON we filter out superseded
        # edges so the answer LLM never sees them. This reproduces the
        # data_plan §10.2 grid (top-k × inv ∈ {on, off}).
        if self.config.temporal_invalidation:
            chunks = [c for c in chunks if c["is_currently_valid"]]
        return chunks

    def answer(
        self,
        public_sample: dict[str, Any],
        retrieved: list[dict[str, Any]],
        *,
        injection: str | None = None,
    ) -> str:
        """Feed retrieved memory + current query to the shared answer
        backbone. Identical prompt template to ``naive_rag`` so the only
        causal difference is the retrieval mechanism (data_plan §10.5).
        """
        if retrieved:
            retrieved_block = "\n\n".join(self._format_chunk(c) for c in retrieved)
            prompt = (
                f"=== Retrieved memory (top-{self.config.top_k}, "
                f"temporal_invalidation={self.config.temporal_invalidation}) ===\n"
                f"{retrieved_block}\n\n"
                f"=== Current request ===\n{public_sample['current_query']}\n"
            )
        else:
            prompt = f"=== Current request ===\n{public_sample['current_query']}\n"
        if injection:
            prompt = f"{prompt}\n=== Note ===\n{injection}\n"

        bb = self.backbone
        original = bb.system_prompt
        bb.system_prompt = GRAPHITI_SYSTEM
        try:
            return bb(prompt)
        finally:
            bb.system_prompt = original

    # ----- Baseline Protocol ----------------------------------------------

    def respond(self, public_sample: dict[str, Any]) -> str:
        """Full per-sample lifecycle. Order: ingest → retrieve → answer →
        teardown. The Graphiti client + FalkorDB async driver hold
        connections bound to the asyncio loop where they were created;
        once `asyncio.run` returns, that loop is closed and any retained
        client breaks. We therefore build a *fresh* client per sample
        inside the orchestration and discard it afterwards.
        """
        injection = public_sample.get("_intervention_injection")
        sample_id = public_sample["sample_id"]
        group_id = self._group_id_for(sample_id)
        payload = self._build_ingest_payload(public_sample)
        query = public_sample["current_query"]

        async def _orchestrate() -> list[dict[str, Any]]:
            client = self._build_fresh_client()
            try:
                await self._ingest_async(client, payload)
                return await self._retrieve_async(client, query, group_id)
            finally:
                try:
                    await self._teardown_async(client, group_id)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "graphiti teardown failed for %s: %s", group_id, e
                    )

        retrieved = asyncio.run(_orchestrate())
        return self.answer(public_sample, retrieved, injection=injection)

    def respond_both(self, public_sample: dict[str, Any]) -> tuple[str, str]:
        """Single ingest+retrieve, two answers — for the inv=ON vs inv=OFF
        ablation that tests Graphiti's bi-temporal invalidation claim
        (data_plan §10.2). Cost: 1 ingest + 1 retrieve + 2 answer calls.

        Returns ``(response_inv_on, response_inv_off)``:
          - ``inv_on``  filters out superseded edges (main config)
          - ``inv_off`` keeps every retrieved edge regardless of
            invalid_at (responder sees raw bi-temporal annotations and
            must reason over time itself)
        """
        injection = public_sample.get("_intervention_injection")
        sample_id = public_sample["sample_id"]
        group_id = self._group_id_for(sample_id)
        payload = self._build_ingest_payload(public_sample)
        query = public_sample["current_query"]

        async def _orchestrate() -> list[dict[str, Any]]:
            client = self._build_fresh_client()
            try:
                await self._ingest_async(client, payload)
                return await self._retrieve_async_raw(client, query, group_id)
            finally:
                try:
                    await self._teardown_async(client, group_id)
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "graphiti teardown failed for %s: %s", group_id, e
                    )

        raw_chunks = asyncio.run(_orchestrate())
        chunks_on = [c for c in raw_chunks if c["is_currently_valid"]]
        resp_on = self.answer(public_sample, chunks_on, injection=injection)
        resp_off = self.answer(public_sample, raw_chunks, injection=injection)
        return resp_on, resp_off

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata:
        return RunMetadata(
            system_name=self.name,
            run_id=run_id,
            sample_id=sample_id,
            memory_infra_location="local",  # FalkorDB / Neo4j local docker
            answer_backbone=self.backbone.model_id,
            answer_backbone_provider=self.answer_backbone_provider,  # type: ignore[arg-type]
            embedding_model=self.config.embedding_model_id,
            embedding_provider=self.config.embedding_provider,  # type: ignore[arg-type]
            vector_store="graphiti",          # Graphiti embeds against the graph backend
            graph_store=self.config.graph_backend,  # falkordb | neo4j
            uses_full_history=False,
            uses_retrieved_memory=True,
            prompt_template_id=(
                f"graphiti/topk{self.config.top_k}_inv-"
                f"{'on' if self.config.temporal_invalidation else 'off'}/v1"
            ),
            temperature=self.backbone.temperature,
            max_tokens=self.backbone.max_new_tokens,
        )

    # ----- internals -------------------------------------------------------

    def _get_client(self) -> Any:
        # Backward-compat shim: prefer ``_build_fresh_client`` from inside
        # ``respond`` so each sample gets a connection bound to its own
        # event loop. This lazy cache survives only for off-loop ingest /
        # retrieve / answer callers (e.g. tests poking individual hooks).
        if self._client is not None:
            return self._client
        self._client = self._build_fresh_client()
        return self._client

    def _build_fresh_client(self) -> Any:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client.config import LLMConfig
        from pipeline.baselines.graphiti_bedrock_llm import (
            BedrockEmbeddingClient,
            BedrockEmbeddingConfig,
            BedrockLLMClient,
        )

        # ---- graph driver -------------------------------------------------
        if self.config.graph_backend == "falkordb":
            from graphiti_core.driver.falkordb_driver import FalkorDriver

            host, port = _parse_falkor_uri(self.config.graph_uri)
            driver = FalkorDriver(host=host, port=port)
        elif self.config.graph_backend == "neo4j":
            from graphiti_core.driver.neo4j_driver import Neo4jDriver

            driver = Neo4jDriver(
                uri=self.config.graph_uri,
                user=self.config.graph_user or "neo4j",
                password=self.config.graph_password or "",
            )
        else:  # pragma: no cover — config-time error
            raise ValueError(
                f"Unsupported graph_backend: {self.config.graph_backend}"
            )

        # ---- LLM client (Sonnet 4.6 on Bedrock — D2) ---------------------
        if self.config.extractor_provider != "bedrock":
            # TODO: verify against real SDK on first real run — only
            # Bedrock is wired up here. Other providers would need their
            # own Graphiti LLMClient subclass.
            raise NotImplementedError(
                f"extractor_provider={self.config.extractor_provider} not wired"
            )
        llm_config = LLMConfig(
            model=self.config.extractor_model_id,
            temperature=0.0,
        )
        llm_client = BedrockLLMClient(config=llm_config)

        # ---- embedder (Titan v2 on Bedrock) ------------------------------
        if self.config.embedding_provider != "bedrock":
            raise NotImplementedError(
                f"embedding_provider={self.config.embedding_provider} not wired"
            )
        embedder = BedrockEmbeddingClient(
            config=BedrockEmbeddingConfig(
                embedding_model=self.config.embedding_model_id,
            )
        )

        # cross_encoder defaults to OpenAIRerankerClient — and Graphiti
        # 0.28.2 instantiates it eagerly at __init__ time even when the
        # default search recipe (EDGE_HYBRID_SEARCH_RRF) doesn't invoke
        # rank(). We have no OpenAI key, so plug in a no-op subclass to
        # bypass the eager instantiation. If a future search path ever
        # calls rank(), it returns the input passages with score 1.0 in
        # original order (a sane no-op).
        from graphiti_core.cross_encoder.client import CrossEncoderClient

        class _NoOpCrossEncoder(CrossEncoderClient):
            async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
                return [(p, 1.0) for p in passages]

        return Graphiti(
            graph_driver=driver,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=_NoOpCrossEncoder(),
        )

    def _group_id_for(self, sample_id: str) -> str:
        # Sample IDs use hyphens (e.g. "p3-smoke-drift-noteapp-001-compact")
        # but FalkorDB's RediSearch fulltext indexer treats hyphens as
        # token separators, causing "Syntax error" on group_id-filtered
        # queries. Replace hyphens with underscores for Graphiti's
        # group_id; the sample-id mapping is still 1-1.
        return f"ssbench_{sample_id.replace('-', '_')}"

    def _build_ingest_payload(
        self, public_sample: dict[str, Any]
    ) -> dict[str, Any]:
        """Build the JSON payload that would be sent to Graphiti, without
        actually sending it. Used by the smoke test below.

        Each Session becomes one Graphiti episode (or one episode per
        turn if ``one_session_per_episode`` is False); ``timestamp``
        (story time) is preserved as ``reference_time`` so the temporal
        graph anchors valid_at edges to the conversation timeline rather
        than wall-clock ingest time.
        """
        sessions_payload = []
        for s in public_sample["history"]:
            messages = [
                {
                    "role": t["role"],            # "user" / "assistant"
                    "content": t["text"],
                }
                for t in s["turns"]
            ]
            # Episode body: concatenated session text when ingesting per
            # session; per-message dict list when ingesting per turn.
            session_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in messages
            )
            sessions_payload.append(
                {
                    "episode_name": (
                        f"{self._group_id_for(public_sample['sample_id'])}"
                        f"--{s['session_id']}"
                    ),
                    "reference_time": s.get("timestamp"),
                    "episode_body": (
                        session_text
                        if self.config.one_session_per_episode
                        else None  # turn-by-turn mode handled in ingest()
                    ),
                    "turn_messages": (
                        None
                        if self.config.one_session_per_episode
                        else messages
                    ),
                }
            )
        return {
            "group_id": self._group_id_for(public_sample["sample_id"]),
            "sessions": sessions_payload,
            "ingest_mode": (
                "one_session_per_episode"
                if self.config.one_session_per_episode
                else "one_message_per_episode"
            ),
        }

    def _format_chunk(self, chunk: dict[str, Any]) -> str:
        # Render a fact in a way the answer LLM can reason about.
        # When temporal_invalidation=on (the default), every chunk is
        # currently-valid so the [valid_at ...] / [invalidated ...]
        # annotation is for the model's benefit when it sees stale facts
        # under the OFF ablation.
        fact = chunk.get("fact", "") or ""
        valid_at = chunk.get("valid_at")
        invalid_at = chunk.get("invalid_at")
        annotations: list[str] = []
        if valid_at:
            annotations.append(f"valid_at={valid_at}")
        if invalid_at:
            annotations.append(f"invalidated_at={invalid_at}")
        elif valid_at:
            annotations.append("currently_valid=true")
        if annotations:
            return f"- {fact}  [{', '.join(annotations)}]"
        return f"- {fact}"

    def _teardown(self, public_sample: dict[str, Any]) -> None:
        """Delete the per-sample Graphiti group_id. Per-sample isolation
        is a hard fairness invariant — see module docstring.

        Implementation: graphiti_core 0.28.x does not expose a typed
        ``delete_group()`` helper, but the FalkorDB driver clones into
        a per-group_id database (see ``Graphiti.add_episode`` — when
        ``group_id != driver._database`` it calls ``driver.clone(database=
        group_id)``). We DROP that database via the FalkorDB driver's
        client. For Neo4j the equivalent is a Cypher
        ``MATCH (n {group_id:$g}) DETACH DELETE n`` — done as a
        fallback. Errors are logged but not raised: the runner already
        captures per-sample errors, and a stale group_id is at worst a
        garbage-collection issue, not a correctness one.
        """
        if self._client is None:
            return
        sample_id = public_sample["sample_id"]
        group_id = self._group_id_for(sample_id)
        try:
            asyncio.run(self._teardown_async(self._client, group_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "graphiti teardown for group_id=%s failed: %s", group_id, exc
            )

    async def _teardown_async(self, client: Any, group_id: str) -> None:
        # FalkorDB path: delete the per-group_id graph DB outright.
        if self.config.graph_backend == "falkordb":
            falkor_client = getattr(client.driver, "client", None)
            if falkor_client is not None:
                # falkordb.asyncio.FalkorDB: select_graph(name).delete()
                try:
                    graph = falkor_client.select_graph(group_id)
                    delete_coro = graph.delete()
                    if asyncio.iscoroutine(delete_coro):
                        await delete_coro
                    return
                except Exception:  # noqa: BLE001
                    pass  # fall through to Cypher delete

        # Generic Cypher fallback (works on both backends but slower).
        # TODO: verify against real SDK on first real run — node label
        # / property names below assume Graphiti's default schema
        # (``group_id`` property on every node + edge); if upstream
        # ever renames these, this will silently no-op.
        try:
            await client.driver.execute_query(
                "MATCH (n {group_id: $gid}) DETACH DELETE n",
                gid=group_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Cypher teardown for group_id=%s failed: %s", group_id, exc
            )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _parse_falkor_uri(uri: str) -> tuple[str, int]:
    """Best-effort parser for ``redis://host:port`` (the locked default).

    FalkorDriver takes ``host`` + ``port`` as separate kwargs, not a
    full URI; this lets us keep the URI form in ``GraphitiConfig`` for
    parity with Neo4j configs.
    """
    s = uri
    for prefix in ("redis://", "rediss://", "falkordb://"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    # Strip any path component
    s = s.split("/", 1)[0]
    if ":" in s:
        host, port_s = s.rsplit(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            port = 6379
    else:
        host = s
        port = 6379
    return host or "localhost", port


def _parse_reference_time(ts: Any) -> datetime:
    """Coerce a Session ``timestamp`` field into a tz-aware ``datetime``.

    Public samples use ISO-8601 strings (``"2024-03-12T10:00:00"`` or with
    ``Z``). Graphiti's ``add_episode`` requires a ``datetime``. If the
    timestamp is missing we fall back to wall-clock UTC; the protocol
    docs flag that as "story time preferred", but no-timestamp samples
    are tolerated rather than raising.
    """
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str) and ts:
        s = ts.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return datetime.now(tz=timezone.utc)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


GRAPHITI_SYSTEM = (
    "You are a personal assistant. The retrieved memory below is sourced "
    "from a temporal knowledge graph that tracks when facts about the "
    "user became valid and when they were superseded. Treat facts marked "
    "as currently valid as authoritative; treat facts marked as invalid "
    "or outdated as historical context only. Respond directly to the "
    "current request."
)


__all__ = ["GraphitiBaseline", "GraphitiConfig", "GRAPHITI_SYSTEM"]


# ---------------------------------------------------------------------------
# Smoke test (no Graphiti call) — ``python -m pipeline.baselines.graphiti_adapter``
# ---------------------------------------------------------------------------


def _smoke_main() -> None:
    """Load one sample from the Phase-3 manifest and print the planned
    ingest payload. Does NOT call Graphiti. Lets the user sanity-check
    the group_id / episode shape before any service is wired up.
    """
    manifest_path = os.environ.get(
        "SSBENCH_PHASE3_FULL",
        "/root/projects/supersession/data/dataset/realized_phase3_full.jsonl",
    )
    if not os.path.exists(manifest_path):
        print(f"[graphiti_adapter smoke] manifest not found at {manifest_path}")
        return

    with open(manifest_path, encoding="utf-8") as fh:
        first = json.loads(fh.readline())

    # Strip gold (smoke test must not see _gold; mirror runner contract).
    public = {k: v for k, v in first.items() if k != "_gold"}

    # Build a GraphitiBaseline with a *dummy* backbone — we only call the
    # offline payload builder, not respond() / ingest().
    class _NoBackbone:
        model_id = "smoke-test-noop"
        temperature = 0.0
        max_new_tokens = 0
        system_prompt = None

    baseline = GraphitiBaseline(
        backbone=_NoBackbone(),
        config=GraphitiConfig(top_k=10, temporal_invalidation=True),
    )
    payload = baseline._build_ingest_payload(public)

    print(f"[graphiti_adapter smoke] sample_id = {public['sample_id']}")
    print(f"[graphiti_adapter smoke] sessions  = {len(payload['sessions'])}")
    print(
        f"[graphiti_adapter smoke] total turns = "
        f"{sum(len((s['episode_body'] or '').splitlines()) or len(s['turn_messages'] or []) for s in payload['sessions'])}"
    )
    print(f"[graphiti_adapter smoke] group_id = {payload['group_id']}")
    print(f"[graphiti_adapter smoke] mode     = {payload['ingest_mode']}")
    print("[graphiti_adapter smoke] payload preview (first session):")
    preview = dict(payload)
    preview["sessions"] = payload["sessions"][:1]
    print(json.dumps(preview, indent=2, ensure_ascii=False, default=str)[:2000])


if __name__ == "__main__":
    _smoke_main()
