#!/usr/bin/env python3
"""Phase 3 runner for the three extraction-wrapper baselines.

Runs `sonnet_extract`, `recency_wrapper`, and `active_state_wrapper`
on the Phase 3 manifest, sharing a **single** Sonnet 4.6 candidate
extraction per sample across all three wrappers. Architecturally:

  - Same extractor (Sonnet 4.6 + drift-aware prompt) for all three.
  - Different selectors:
      * `sonnet_extract`        — LLM-based active-version selector (Sonnet)
      * `recency_wrapper`       — pick latest by session_introduced
      * `active_state_wrapper`  — group by topic, pick query-relevant
                                  topic's latest candidate

Per-sample LLM accounting (with shared extraction):
  - 1 Sonnet extract call (cached, shared across the 3 wrappers)
  - 1 Sonnet select call (only for sonnet_extract)
  - 3 Llama 8B answer calls (one per wrapper)
  - 0 extra Bedrock calls for B1/B2 selectors (rule-based + local BGE)

Total per sample: 2 Sonnet + 3 Llama = 5 LLM calls. Phase 3 N=1000
wall ~1.5–2 hr at workers=2; cost ~$50-80 (mostly Sonnet extraction).

Cost-share is the point: running all three wrappers separately would
cost 3× more Sonnet extraction. The single-process design holds the
extractor backbone constant across baselines, which is also the
fairness contract per protocol §10.5.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.baselines.extract_wrappers import (  # noqa: E402
    ActiveStateWrapperBaseline,
    RecencyWrapperBaseline,
)
from pipeline.evaluation.bedrock_backbone import BedrockBackbone  # noqa: E402
from pipeline.intervention.temporal_selectors import CachedExtractor  # noqa: E402
from pipeline.intervention.wrapper import (  # noqa: E402
    MinimalSupersessionWrapper,
    default_phase0_config,
)
from pipeline.intervention.llm_steps import (  # noqa: E402
    make_drift_aware_llm_extractor,
    make_llm_selector,
)

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"

OUT_FILES = {
    "sonnet_extract": DATA / "responses/phase3_sonnet_extract_responses.jsonl",
    "recency_wrapper": DATA / "responses/phase3_recency_wrapper_responses.jsonl",
    "active_state_wrapper": DATA / "responses/phase3_active_state_wrapper_responses.jsonl",
}


def load_manifest_sids(manifest_path: Path) -> list[str]:
    m = json.loads(manifest_path.read_text())
    out = []
    for g in m["groups"]:
        for mem in g["members"]:
            out.append(mem["sample_id"])
    return out


def load_public_samples(path: Path, sids: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            sid = d.get("sample_id")
            if sid in sids and sid not in out:
                out[sid] = d
    return out


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    with open(path) as f:
        for line in f:
            try:
                out.add(json.loads(line)["sample_id"])
            except Exception:
                pass
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST), type=Path)
    p.add_argument("--public", default=str(DEFAULT_PUBLIC), type=Path)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--profile", default="ahe-long")
    p.add_argument("--sonnet-model", default="us.anthropic.claude-sonnet-4-6")
    p.add_argument("--llama-model", default="us.meta.llama3-1-8b-instruct-v1:0")
    p.add_argument(
        "--baselines",
        nargs="+",
        default=["sonnet_extract", "recency_wrapper", "active_state_wrapper"],
        choices=["sonnet_extract", "recency_wrapper", "active_state_wrapper"],
    )
    args = p.parse_args()

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    missing = [sid for sid in sids if sid not in samples_map]
    if missing:
        print(
            f"WARN: {len(missing)} manifest sids missing from public file; "
            f"first 3: {missing[:3]}"
        )
    print(f"Loaded {len(samples)} samples")

    # Resume per baseline.
    done_per_baseline = {b: load_done(OUT_FILES[b]) for b in args.baselines}
    pending_baselines = [b for b in args.baselines]
    n_skipped = sum(len(done_per_baseline[b]) for b in pending_baselines)
    print(f"Resume: {n_skipped} cached responses across {len(pending_baselines)} baselines")

    # If a sample is fully done across all selected baselines, skip it.
    def fully_done(sid: str) -> bool:
        return all(sid in done_per_baseline[b] for b in pending_baselines)

    samples = [s for s in samples if not fully_done(s["sample_id"])]
    print(f"Running {len(samples)} fresh samples through {pending_baselines}...")
    t0 = time.perf_counter()

    # Shared extractor + selector singletons (reused per worker via
    # per-sample fresh backbones inside run_one). The extractor is
    # wrapped in CachedExtractor so the 3 wrappers share its output
    # within one sample call.
    config = default_phase0_config()

    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        # Per-sample fresh backbones (boto3 connection-pool isolation —
        # same fix that unblocked Graphiti batch runs).
        sonnet_bb = BedrockBackbone(
            model_id=args.sonnet_model, profile=args.profile,
            max_new_tokens=600, temperature=0.0,
        )
        llama_bb = BedrockBackbone(
            model_id=args.llama_model, profile=args.profile,
            max_new_tokens=1024, temperature=0.0,
        )
        # Build extractor + cache it (cache is per-call here since each
        # run_one creates its own CachedExtractor; the share happens
        # across the 3 wrappers within this single function call).
        base_extractor = make_drift_aware_llm_extractor(sonnet_bb, max_candidates=8)
        cached_extractor = CachedExtractor(base_extractor)
        # Shared LLM selector for sonnet_extract. Local (no LLM)
        # selectors come from the wrapper instances themselves.
        sonnet_selector = make_llm_selector(sonnet_bb)

        def llama_responder(public_sample):
            from pipeline.baselines.long_context import LongContextBaseline
            return LongContextBaseline(
                backbone=llama_bb, name="long_context_llama8b"
            ).respond(public_sample)

        # sonnet_extract — uses the existing wrapper directly.
        wrappers = {}
        if "sonnet_extract" in pending_baselines:
            wrappers["sonnet_extract"] = MinimalSupersessionWrapper(
                config=config, extractor=cached_extractor,
                selector=sonnet_selector, responder=llama_responder,
                name="sonnet_extract",
            )
        if "recency_wrapper" in pending_baselines:
            wrappers["recency_wrapper"] = RecencyWrapperBaseline(
                backbone=llama_bb, extractor=cached_extractor,
                responder=llama_responder, config=config,
            )
        if "active_state_wrapper" in pending_baselines:
            wrappers["active_state_wrapper"] = ActiveStateWrapperBaseline(
                backbone=llama_bb, extractor=cached_extractor,
                responder=llama_responder, config=config,
            )

        results: dict[str, tuple[str | None, str | None, float]] = {}
        for name, w in wrappers.items():
            if sid in done_per_baseline[name]:
                continue  # already done for this baseline; skip
            ts = time.perf_counter()
            try:
                if name == "sonnet_extract":
                    resp, _trace = w.respond(sample)
                else:
                    resp = w.respond(sample)
                elapsed = time.perf_counter() - ts
                results[name] = (resp, None, elapsed)
            except Exception as e:  # noqa: BLE001
                elapsed = time.perf_counter() - ts
                results[name] = (None, f"{type(e).__name__}: {e}", elapsed)
        return idx, sample, results

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, (i, s)): i for i, s in enumerate(samples)}
        for fut in as_completed(futs):
            idx, sample, results = fut.result()
            sid = sample["sample_id"]
            with out_lock:
                for name, (resp, err, elapsed) in results.items():
                    if err:
                        n_err += 1
                        print(
                            f"  ✗ [{idx+1}/{len(samples)}] {name:<22} "
                            f"{sid:<40} {elapsed:.1f}s FAIL: {err[:120]}",
                            flush=True,
                        )
                    else:
                        n_ok += 1
                        rec = {
                            "sample_id": sid,
                            "system_name": name,
                            "response": resp,
                            "elapsed_s": round(elapsed, 2),
                        }
                        with open(OUT_FILES[name], "a") as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        done_per_baseline[name].add(sid)
                        print(
                            f"  ✓ [{idx+1}/{len(samples)}] {name:<22} "
                            f"{sid:<40} {elapsed:.1f}s",
                            flush=True,
                        )

    wall = time.perf_counter() - t0
    print(f"\nDone in {wall:.1f}s — {n_ok} ✓ / {n_err} ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
