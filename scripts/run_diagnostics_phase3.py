#!/usr/bin/env python3
"""Phase 3 N=1000 runner for the diagnostic systems.

Runs:
  - ``query_only``               — Llama 8B answers ``current_query`` with NO
                                   history context. Lower-bound on baseline
                                   ability to "guess" without memory.
  - ``oracle_current_version``   — Reads gold, injects the active-version
                                   value as a hint, then Llama 8B answers
                                   with full history + injection. Upper-bound
                                   diagnostic; **NOT a fair baseline**.

Each writes to its own responses file. Resume support per baseline.

Notes:
  - ``oracle_current_version`` consumes ``_gold`` (read from
    ``data/dataset/realized_phase3_main_full.jsonl`` which contains gold). All other
    baselines read from the public file (``..._public.jsonl``) which strips
    gold.
  - ``recall_only`` is a separate evaluation track (different query format)
    and is NOT covered by this script — run ``run_recall_phase3.py`` if /
    when that diagnostic is added.
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
from pipeline.evaluation.bedrock_backbone import BedrockBackbone  # noqa: E402

DATA = REPO / "data"
DEFAULT_MANIFEST = DATA / "manifests" / "phase3_main.json"
DEFAULT_PUBLIC = DATA / "dataset/realized_phase3_main_public.jsonl"
DEFAULT_FULL = DATA / "dataset/realized_phase3_main_full.jsonl"

OUT_FILES = {
    "query_only": DATA / "responses/phase3_query_only_responses.jsonl",
    "oracle_current_version": DATA / "responses/phase3_oracle_current_version_responses.jsonl",
}


QUERY_ONLY_SYSTEM = (
    "You are a personal assistant. You have NO prior context about the user. "
    "Answer the request below as best you can without making assumptions about "
    "the user's preferences."
)

ORACLE_SYSTEM = (
    "You are a personal assistant. The note below states the user's currently "
    "valid preference on the topic of the request. Treat it as authoritative "
    "and answer accordingly."
)


def load_manifest_sids(manifest_path: Path) -> list[str]:
    m = json.loads(manifest_path.read_text())
    out = []
    for g in m["groups"]:
        for mem in g["members"]:
            out.append(mem["sample_id"])
    return out


def load_jsonl_by_id(path: Path, sids: set[str]) -> dict[str, dict]:
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


def run_query_only(public_sample: dict, backbone: BedrockBackbone) -> str:
    """No history; just ask the query directly."""
    prompt = f"=== Current request ===\n{public_sample['current_query']}\n"
    original_system = backbone.system_prompt
    backbone.system_prompt = QUERY_ONLY_SYSTEM
    try:
        return backbone(prompt)
    finally:
        backbone.system_prompt = original_system


def run_oracle(full_sample: dict, backbone: BedrockBackbone) -> str:
    """Inject gold active value + run with full history (long-context style)."""
    gold = full_sample.get("_gold") or {}
    pred = gold.get("violation_predicate") or {}
    active = pred.get("must_honor") or {}
    topic = active.get("topic", "")
    value = active.get("value", "")
    injected = (
        f"The user's currently valid state on {topic!r} is: {value!r}."
    )
    # Build a public view + injection, route through long_context responder.
    public = {k: v for k, v in full_sample.items() if k != "_gold"}
    public["_intervention_injection"] = injected
    base = LongContextBaseline(backbone=backbone, name="oracle_current_version")
    return base.respond(public)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST), type=Path)
    p.add_argument("--public", default=str(DEFAULT_PUBLIC), type=Path)
    p.add_argument("--full", default=str(DEFAULT_FULL), type=Path)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--profile", default="ahe-long")
    p.add_argument(
        "--baselines",
        nargs="+",
        default=list(OUT_FILES.keys()),
        choices=list(OUT_FILES.keys()),
    )
    args = p.parse_args()

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    # Load public for query_only; full (with gold) for oracle.
    needs_public = "query_only" in args.baselines
    needs_full = "oracle_current_version" in args.baselines

    public_map: dict[str, dict] = {}
    full_map: dict[str, dict] = {}
    if needs_public:
        public_map = load_jsonl_by_id(args.public, set(sids))
        print(f"Loaded {len(public_map)} public samples")
    if needs_full:
        full_map = load_jsonl_by_id(args.full, set(sids))
        print(f"Loaded {len(full_map)} full samples (incl. gold)")

    done_per = {b: load_done(OUT_FILES[b]) for b in args.baselines}
    print(f"Resume: skipping "
          f"{sum(len(done_per[b]) for b in args.baselines)} cached responses")

    work_sids = []
    for sid in sids:
        if any(sid not in done_per[b] for b in args.baselines):
            work_sids.append(sid)
    print(f"Running {len(work_sids)} fresh sample-ids through {args.baselines}...")
    t0 = time.perf_counter()

    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0

    def run_one(idx_sid):
        idx, sid = idx_sid
        # Per-sample fresh backbone (consistency with other Phase 3 runners).
        backbone = BedrockBackbone(
            model_id="us.meta.llama3-1-8b-instruct-v1:0",
            profile=args.profile, max_new_tokens=512, temperature=0.0,
        )
        results: dict[str, tuple[str | None, str | None, float]] = {}
        for name in args.baselines:
            if sid in done_per[name]:
                continue
            ts = time.perf_counter()
            try:
                if name == "query_only":
                    if sid not in public_map:
                        raise KeyError(f"no public sample for {sid}")
                    resp = run_query_only(public_map[sid], backbone)
                elif name == "oracle_current_version":
                    if sid not in full_map:
                        raise KeyError(f"no full sample for {sid}")
                    resp = run_oracle(full_map[sid], backbone)
                else:
                    raise ValueError(f"unknown diagnostic: {name}")
                results[name] = (resp, None, time.perf_counter() - ts)
            except Exception as e:  # noqa: BLE001
                results[name] = (None, f"{type(e).__name__}: {e}",
                                 time.perf_counter() - ts)
        return idx, sid, results

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, (i, sid)): i for i, sid in enumerate(work_sids)}
        for fut in as_completed(futs):
            idx, sid, results = fut.result()
            with out_lock:
                for name, (resp, err, elapsed) in results.items():
                    if err:
                        n_err += 1
                        print(
                            f"  ✗ [{idx+1}/{len(work_sids)}] {name:<25} "
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
                            f"  ✓ [{idx+1}/{len(work_sids)}] {name:<25} "
                            f"{sid:<45} {elapsed:.1f}s",
                            flush=True,
                        )

    wall = time.perf_counter() - t0
    print(f"\nDone in {wall:.1f}s — {n_ok} ✓ / {n_err} ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
