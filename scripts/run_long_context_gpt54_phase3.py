#!/usr/bin/env python3
"""Phase 3 N=1000 runner for long_context_gpt54 (OpenAI GPT-5.4).

Adds a frontier-OpenAI long-context baseline to the existing 11-system
lineup. Mirrors the long-context contract: full history + current query
→ direct answer, no retrieval, no extraction wrapper.

Auth: reads OPENAI_API_KEY from the environment. Set via:
  export OPENAI_API_KEY=sk-...

Output: data/responses/phase3_long_context_gpt54_responses.jsonl
        (one JSON line per sample, schema matches the other phase3
         response files: sample_id, system_name, response, elapsed_s)

Resume support: skips sample_ids already cached.

Cost estimate (Phase 3 N=1000):
  - Input ~8M tokens × $1.25/1M  ≈ $10
  - Output 1000 × ~512 tokens × $10/1M ≈ $5
  Total ~$15-20

Usage:
  uv run python scripts/run_long_context_gpt54_phase3.py --workers 6
  uv run python scripts/run_long_context_gpt54_phase3.py --limit 5  # smoke
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
from pipeline.evaluation.openai_backbone import OpenAIBackbone  # noqa: E402

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"
DEFAULT_OUT = DATA / "responses/phase3_long_context_gpt54_responses.jsonl"
SYSTEM_NAME = "long_context_gpt54"


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
    p.add_argument("--model", default="gpt-5.4",
                   help="OpenAI model id (default: gpt-5.4)")
    p.add_argument("--max-tokens", type=int, default=4096,
                   help="max_completion_tokens. For gpt-5 with "
                        "reasoning_effort=medium, reasoning tokens count "
                        "against this; 4096 leaves room for ~2k reasoning "
                        "+ ~2k visible response.")
    p.add_argument("--reasoning-effort", default="medium",
                   choices=["none", "low", "medium", "high", "xhigh"],
                   help="GPT-5 reasoning_effort. Default 'medium' matches "
                        "OpenAI's vendor user-facing default.")
    args = p.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in environment.", file=sys.stderr)
        print("Set it with: export OPENAI_API_KEY=sk-...", file=sys.stderr)
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
        print("Nothing to do.")
        return 0

    t0 = time.perf_counter()
    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0
    n_done_so_far = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        # Fresh backbone per sample to isolate connection state
        bb = OpenAIBackbone(
            model_id=args.model,
            max_new_tokens=args.max_tokens,
            temperature=0.0,
            reasoning_effort=args.reasoning_effort,
        )
        ts = time.perf_counter()
        try:
            base = LongContextBaseline(backbone=bb, name=SYSTEM_NAME,
                                        answer_backbone_provider="openai")
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
                n_done_so_far += 1
                if err:
                    n_err += 1
                    print(f"  [{n_done_so_far}/{len(samples)}] ERR {sid}: {err[:140]}")
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
                if n_done_so_far % 25 == 0 or n_done_so_far == len(samples):
                    rate = n_done_so_far / max(0.001, time.perf_counter() - t0)
                    eta = (len(samples) - n_done_so_far) / max(0.001, rate)
                    print(f"  [{n_done_so_far}/{len(samples)}] "
                          f"ok={n_ok} err={n_err} rate={rate:.2f}/s eta={eta:.0f}s")

    wall = time.perf_counter() - t0
    print(f"\nDone. {n_ok} ok / {n_err} err in {wall:.1f}s")
    print(f"Output: {args.out}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
