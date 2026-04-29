#!/usr/bin/env python3
"""Phase 3 N=1000 runner for the Graphiti baseline.

Same per-sample-fresh-backbone pattern as ``run_graphiti_phase2.py`` —
each sample gets a fresh ``BedrockBackbone`` (Llama 8B answer) and
fresh ``GraphitiBaseline`` instance, isolating boto3 connection-pool
state across samples. ``SEMAPHORE_LIMIT=1`` is required to stay below
Sonnet 4.6 RPM ceiling for sustained operation.

Cost / wall (Phase 3 N=1000):
  - workers=1, SEMAPHORE_LIMIT=1: ~30 hr wall (stable, recommended default)
  - workers=1, SEMAPHORE_LIMIT=2: ~15 hr wall (test on 10-sample mini first)
  - estimated $300-500 in Bedrock Sonnet 4.6 extractor + Llama 8B answer

Resume support: re-running the script picks up where it stopped, skipping
sample_ids already in the responses file.
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

from pipeline.baselines.graphiti_adapter import GraphitiBaseline, GraphitiConfig  # noqa: E402
from pipeline.evaluation.bedrock_backbone import BedrockBackbone  # noqa: E402

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"
DEFAULT_RESPONSES_ON = DATA / "responses/phase3_graphiti_responses.jsonl"
DEFAULT_RESPONSES_OFF = DATA / "responses/phase3_graphiti_inv_off_responses.jsonl"


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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST), type=Path)
    p.add_argument("--public", default=str(DEFAULT_PUBLIC), type=Path)
    p.add_argument("--responses-on", default=str(DEFAULT_RESPONSES_ON), type=Path,
                   help="Output for inv=ON (main). Default phase3_graphiti_responses.jsonl")
    p.add_argument("--responses-off", default=str(DEFAULT_RESPONSES_OFF), type=Path,
                   help="Output for inv=OFF ablation. Default phase3_graphiti_inv_off_responses.jsonl")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--limit", type=int, default=None,
                   help="Run only first N manifest samples (debugging).")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--profile", default="ahe-long")
    args = p.parse_args()

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    missing = [sid for sid in sids if sid not in samples_map]
    if missing:
        print(f"WARN: {len(missing)} manifest sids missing from public file; "
              f"first 3: {missing[:3]}")
    print(f"Loaded {len(samples)} samples")

    config = GraphitiConfig(top_k=args.top_k, temporal_invalidation=True)

    # Resume support: a sample is "fully done" only if BOTH outputs already
    # have it. The ablation runs on the same ingest so partial completion
    # for one but not the other shouldn't happen except after a crash mid-
    # write — re-running just rebuilds whichever side is missing.
    def _load_done(path: Path) -> set[str]:
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

    done_on = _load_done(args.responses_on)
    done_off = _load_done(args.responses_off)
    fully_done = done_on & done_off
    if done_on or done_off:
        print(f"Resume: {len(done_on)} in inv_on, {len(done_off)} in inv_off "
              f"({len(fully_done)} fully done)")
        samples = [s for s in samples if s["sample_id"] not in fully_done]

    print(f"Running {len(samples)} fresh samples through Graphiti (inv_on + inv_off)...")
    t0 = time.perf_counter()

    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        ts = time.perf_counter()
        try:
            answer_bb = BedrockBackbone(
                model_id="us.meta.llama3-1-8b-instruct-v1:0",
                profile=args.profile, max_new_tokens=1024, temperature=0.0,
            )
            baseline = GraphitiBaseline(backbone=answer_bb, config=config)
            resp_on, resp_off = baseline.respond_both(sample)
            return idx, sample, (resp_on, resp_off), None, time.perf_counter() - ts
        except Exception as e:  # noqa: BLE001
            return idx, sample, None, f"{type(e).__name__}: {e}", time.perf_counter() - ts

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, (i, s)): i for i, s in enumerate(samples)}
        for fut in as_completed(futs):
            idx, sample, responses, err, elapsed = fut.result()
            with out_lock:
                if err:
                    n_err += 1
                    print(
                        f"  ✗ [{idx+1}/{len(samples)}] {sample['sample_id']}  "
                        f"FAIL ({elapsed:.1f}s): {err[:160]}",
                        flush=True,
                    )
                else:
                    n_ok += 1
                    resp_on, resp_off = responses
                    sid = sample["sample_id"]
                    if sid not in done_on:
                        rec = {
                            "sample_id": sid,
                            "system_name": "graphiti",
                            "response": resp_on,
                            "elapsed_s": round(elapsed, 2),
                        }
                        with open(args.responses_on, "a") as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        done_on.add(sid)
                    if sid not in done_off:
                        rec = {
                            "sample_id": sid,
                            "system_name": "graphiti_inv_off",
                            "response": resp_off,
                            "elapsed_s": round(elapsed, 2),
                        }
                        with open(args.responses_off, "a") as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        done_off.add(sid)
                    print(
                        f"  ✓ [{idx+1}/{len(samples)}] {sid:<45}  "
                        f"{elapsed:.1f}s",
                        flush=True,
                    )

    wall = time.perf_counter() - t0
    print(f"\nDone in {wall:.1f}s — {n_ok} ✓ / {n_err} ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
