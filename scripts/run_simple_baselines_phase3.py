#!/usr/bin/env python3
"""Phase 3 N=1000 runner for the simple (non-wrapper) baselines.

Runs in one process to share state efficiently:
  - long_context_sonnet46  (Bedrock Sonnet 4.6 reads full history)
  - long_context_llama8b   (Bedrock Llama 3.1 8B reads full history)
  - long_context_mistral   (Bedrock Mistral Large reads full history)
  - naive_rag              (BGE embedding + Llama 8B answer)
  - recency_rag            (BGE + timestamp recency rerank + Llama 8B answer)

Each baseline writes to its own ``phase3_<name>_responses.jsonl``.
Resume support: skips sample_ids already cached per-baseline.

Each sample triggers ~5 LLM calls (1 per baseline). With workers=4 the
concurrent Bedrock load is well within Sonnet 4.6 RPM ceiling.

Cost / wall (Phase 3 N=1000, all 5 baselines):
  - long_context_sonnet46:   ~$30, ~30 min wall
  - long_context_llama8b:    ~$2, ~30 min wall
  - long_context_mistral:    ~$23, ~30 min wall
  - naive_rag (Llama 8B):    ~$0.30, ~30 min wall
  - recency_rag (Llama 8B):  ~$0.30, ~30 min wall

Total ~$55, ~30-60 min wall at workers=4.
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

from pipeline.baselines.long_context import LongContextBaseline  # noqa: E402
from pipeline.baselines.naive_rag import NaiveRAGBaseline  # noqa: E402
from pipeline.baselines.recency_rag import RecencyRAGBaseline, RecencyRAGConfig  # noqa: E402
from pipeline.evaluation.bedrock_backbone import BedrockBackbone  # noqa: E402

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"

OUT_FILES = {
    "long_context_sonnet46": DATA / "responses/phase3_long_context_sonnet46_responses.jsonl",
    "long_context_llama8b":  DATA / "responses/phase3_long_context_llama8b_responses.jsonl",
    "long_context_mistral":  DATA / "responses/phase3_long_context_mistral_responses.jsonl",
    "naive_rag":             DATA / "responses/phase3_naive_rag_responses.jsonl",
    "recency_rag":           DATA / "responses/phase3_recency_rag_responses.jsonl",
}

MODEL_IDS = {
    "long_context_sonnet46": "us.anthropic.claude-sonnet-4-6",
    "long_context_llama8b":  "us.meta.llama3-1-8b-instruct-v1:0",
    "long_context_mistral":  "mistral.mistral-large-3-675b-instruct",
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
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--profile", default="ahe-long")
    p.add_argument(
        "--baselines",
        nargs="+",
        default=list(OUT_FILES.keys()),
        choices=list(OUT_FILES.keys()),
    )
    p.add_argument("--top-k", type=int, default=5,
                   help="top-k for naive_rag and recency_rag.")
    p.add_argument("--recency-halflife-days", type=float, default=30.0,
                   help="halflife for recency_rag's time decay.")
    args = p.parse_args()

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    missing = [sid for sid in sids if sid not in samples_map]
    if missing:
        print(f"WARN: {len(missing)} manifest sids missing; first 3: {missing[:3]}")
    print(f"Loaded {len(samples)} samples")

    done_per = {b: load_done(OUT_FILES[b]) for b in args.baselines}
    n_skipped = sum(len(done_per[b]) for b in args.baselines)
    print(f"Resume: {n_skipped} cached responses across {len(args.baselines)} baselines")

    def fully_done(sid: str) -> bool:
        return all(sid in done_per[b] for b in args.baselines)

    samples = [s for s in samples if not fully_done(s["sample_id"])]
    print(f"Running {len(samples)} fresh samples through {args.baselines}...")
    t0 = time.perf_counter()

    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        # Per-sample fresh backbones — shared boto3 connection-pool
        # bug applies to all baselines, not just Graphiti.
        backbones = {
            name: BedrockBackbone(
                model_id=MODEL_IDS[name],
                profile=args.profile, max_new_tokens=1024, temperature=0.0,
            )
            for name in args.baselines if name in MODEL_IDS
        }
        # Llama 8B for naive_rag / recency_rag (both Llama-answer).
        llama_bb = BedrockBackbone(
            model_id="us.meta.llama3-1-8b-instruct-v1:0",
            profile=args.profile, max_new_tokens=1024, temperature=0.0,
        )

        results: dict[str, tuple[str | None, str | None, float]] = {}
        for name in args.baselines:
            if sid in done_per[name]:
                continue
            ts = time.perf_counter()
            try:
                if name.startswith("long_context_"):
                    base = LongContextBaseline(backbone=backbones[name], name=name)
                elif name == "naive_rag":
                    base = NaiveRAGBaseline(backbone=llama_bb, top_k=args.top_k)
                elif name == "recency_rag":
                    base = RecencyRAGBaseline(
                        backbone=llama_bb,
                        config=RecencyRAGConfig(
                            top_k=args.top_k,
                            recency_halflife_days=args.recency_halflife_days,
                        ),
                    )
                else:
                    raise ValueError(f"unknown baseline: {name}")
                resp = base.respond(sample)
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
                            f"  ✗ [{idx+1}/{len(samples)}] {name:<28} "
                            f"{sid:<45} {elapsed:.1f}s FAIL: {err[:120]}",
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
                        done_per[name].add(sid)
                        print(
                            f"  ✓ [{idx+1}/{len(samples)}] {name:<28} "
                            f"{sid:<45} {elapsed:.1f}s",
                            flush=True,
                        )

    wall = time.perf_counter() - t0
    print(f"\nDone in {wall:.1f}s — {n_ok} ✓ / {n_err} ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
