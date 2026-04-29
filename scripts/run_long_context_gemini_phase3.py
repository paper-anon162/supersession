#!/usr/bin/env python3
"""Phase 3 N=1000 runner for long_context_gemini31pro (Google Gemini 3.1 Pro).

Mirrors run_long_context_gpt54_phase3.py but uses GeminiBackbone via the
Generative Language API REST endpoint. Same long-context contract: full
history + current query → direct answer, no retrieval.

Auth: reads GEMINI_API_KEY from the environment.
  export GEMINI_API_KEY=AIza...   # AI Studio
  export GEMINI_API_KEY=AQ...     # Google Cloud project key

Output: data/responses/phase3_long_context_gemini31pro_responses.jsonl

Cost estimate (Phase 3 N=1000, gemini-3.1-pro):
  - Input ~5K tokens × 1000 ≈ 5M tokens
  - Output ~512 tokens × 1000 ≈ 0.5M tokens
  - Pricing varies by tier; expect ~$10-30 total

Usage:
  uv run python scripts/run_long_context_gemini_phase3.py --workers 6
  uv run python scripts/run_long_context_gemini_phase3.py --limit 5  # smoke
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.baselines.long_context import LongContextBaseline  # noqa: E402
from pipeline.evaluation.gemini_backbone import GeminiBackbone  # noqa: E402

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"
DEFAULT_OUT = DATA / "responses/phase3_long_context_gemini31pro_responses.jsonl"
SYSTEM_NAME = "long_context_gemini31pro"


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
    p.add_argument("--out", default=str(DEFAULT_OUT), type=Path)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--model", default="gemini-3.1-pro",
                   help="Gemini model id (default: gemini-3.1-pro)")
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--thinking-budget", type=int, default=None,
                   help="Optional thinking_budget (Gemini 2.5+). Default "
                        "None lets the vendor user-facing default apply, "
                        "matching how Sonnet 4.6 / GPT-5.4 are configured.")
    args = p.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in environment.", file=sys.stderr)
        return 2

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    print(f"Loaded {len(samples)} samples")

    done = load_done(args.out)
    print(f"Resume: {len(done)} cached responses already in {args.out.name}")

    samples = [s for s in samples if s["sample_id"] not in done]
    print(f"Running {len(samples)} fresh samples through {SYSTEM_NAME} "
          f"(model={args.model}) at workers={args.workers}...")
    if not samples:
        return 0

    t0 = time.perf_counter()
    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0
    n_done = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        bb = GeminiBackbone(
            model_id=args.model,
            max_new_tokens=args.max_tokens,
            temperature=0.0,
            thinking_budget=args.thinking_budget,
        )
        ts = time.perf_counter()
        try:
            base = LongContextBaseline(backbone=bb, name=SYSTEM_NAME,
                                        answer_backbone_provider="google")
            resp = base.respond(sample)
            elapsed = time.perf_counter() - ts
            return idx, sid, resp, None, elapsed
        except Exception as e:  # noqa: BLE001
            elapsed = time.perf_counter() - ts
            return idx, sid, None, f"{type(e).__name__}: {e}", elapsed

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, (i, s)): i for i, s in enumerate(samples)}
        for fut in as_completed(futs):
            idx, sid, resp, err, elapsed = fut.result()
            with out_lock:
                n_done += 1
                if err:
                    n_err += 1
                    print(f"  [{n_done}/{len(samples)}] ERR {sid}: {err[:140]}")
                    continue
                n_ok += 1
                row = {
                    "sample_id": sid,
                    "system_name": SYSTEM_NAME,
                    "response": resp,
                    "elapsed_s": round(elapsed, 2),
                }
                with open(args.out, "a") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                if n_done % 25 == 0 or n_done == len(samples):
                    rate = n_done / max(0.001, time.perf_counter() - t0)
                    eta = (len(samples) - n_done) / max(0.001, rate)
                    print(f"  [{n_done}/{len(samples)}] "
                          f"ok={n_ok} err={n_err} rate={rate:.2f}/s eta={eta:.0f}s")

    wall = time.perf_counter() - t0
    print(f"\nDone. {n_ok} ok / {n_err} err in {wall:.1f}s")
    print(f"Output: {args.out}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
