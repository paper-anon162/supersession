"""Score the responses produced by run_benchmark.py.

Reads ``data/benchmark_v1_responses.jsonl`` and judges each
(system, sample, response) tuple with the local LLM, then writes
``data/benchmark_v1_verdicts.jsonl``.

Decoupled from run_benchmark.py so the model is loaded ONCE (avoiding the
double-load that pushes the answer + judge weights past 24 GB and forces
CPU offload).
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pipeline.construction import (
    load_all_seeds,
    materialize_all,
    score_recall,
)
import datetime as _dt

from pipeline._runner_utils import enable_live_stdout, print_eta_banner
from pipeline.cache import (
    CACHE_FORMAT_VERSION,
    append_jsonl,
    load_cache_index,
    make_response_key,
    make_verdict_key,
    gold_content_hash,
    shard_path,
    short_hash,
)
from pipeline.evaluation import apply_default_scoring, judge_sample
from pipeline.evaluation.bedrock_backbone import BedrockBackbone
from pipeline.evaluation.judge import render_judge_prompt
from pipeline.evaluation.local_backbone import HFTransformersBackbone
from pipeline.io import iter_samples_from_jsonl
from pipeline.schema import Sample

JUDGE_PROMPT_VERSION = "v1"  # bump when prompts/judge_vf.jinja changes

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
VERDICT_CACHE_DIR = DATA / "cache" / "verdicts"


_REALIZED_BATCH_FILES = (
    "realized_v1_full.jsonl",
    "realized_v2_full.jsonl",
    "realized_v3_full.jsonl",
    "realized_phase2_a_full.jsonl",
    "realized_phase2_b_full.jsonl",
    "realized_phase2_c_full.jsonl",
    "realized_phase2_d_full.jsonl",
    "realized_phase2_e_full.jsonl",
    "realized_phase2_g_full.jsonl",
    "realized_phase2_i_full.jsonl",
    "realized_phase2_j_full.jsonl",
    "realized_phase2_drift_v3_full.jsonl",
    "dataset/realized_phase3_main_full.jsonl",
)


def _load_pilot() -> dict[str, Sample]:
    samples = materialize_all(load_all_seeds())
    for batch_file in _REALIZED_BATCH_FILES:
        realized = DATA / batch_file
        if realized.exists():
            seen = {s.sample_id for s in samples}
            for s in iter_samples_from_jsonl(realized):
                if s.sample_id not in seen:
                    samples.append(s)
                    seen.add(s.sample_id)
    return {s.sample_id: s for s in samples}


def main() -> int:
    enable_live_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend",
        choices=["hf", "bedrock"],
        default="bedrock",
        help="bedrock (default) = AWS Bedrock Converse; "
             "hf = local HuggingFace transformers (e.g. for the legacy "
             "Qwen 2.5 7B cross-judge from Phase 1)",
    )
    parser.add_argument(
        "--model", default="us.anthropic.claude-opus-4-6-v1",
        help="Judge model id. Defaults to Bedrock Opus 4.6 (primary). "
             "Use mistral.mistral-large-3-675b-instruct for the Mistral "
             "cross-judge, or pass --backend hf with a HF model id for "
             "a local cross-judge.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=300)
    parser.add_argument(
        "--workers", type=int, default=0,
        help="Concurrent worker threads. Default 8 for backend=bedrock, "
             "1 for backend=hf.",
    )
    parser.add_argument("--bedrock-profile", default=None)
    parser.add_argument("--bedrock-region", default="us-east-1")
    parser.add_argument(
        "--responses",
        default=str(DATA / "benchmark_v1_responses.jsonl"),
    )
    parser.add_argument(
        "--out",
        default=str(DATA / "benchmark_v1_verdicts.jsonl"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="If set, only judge the first N rows (smoke-test mode).",
    )
    parser.add_argument(
        "--filter-system",
        default=None,
        help="If set, only judge responses whose system_name matches this value.",
    )
    parser.add_argument(
        "--filter-sample-ids",
        default=None,
        help="If set, comma-separated sample IDs; only judge responses on these samples.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="If set, append to --out (and de-duplicate by (sample_id, system_name)) "
        "instead of overwriting. Use this when scoring only a new system.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the verdict cache (force re-judging).",
    )
    args = parser.parse_args()

    sample_by_id = _load_pilot()
    responses_path = Path(args.responses)
    if not responses_path.exists():
        print(f"ERROR: responses file not found: {responses_path}")
        return 2

    rows = []
    with responses_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if args.filter_system is not None:
        before = len(rows)
        rows = [r for r in rows if r.get("system_name") == args.filter_system]
        print(f"filter-system {args.filter_system!r}: {before} → {len(rows)} rows")
    if args.filter_sample_ids:
        target_ids = {s.strip() for s in args.filter_sample_ids.split(",") if s.strip()}
        before = len(rows)
        rows = [r for r in rows if r.get("sample_id") in target_ids]
        print(f"filter-sample-ids ({len(target_ids)}): {before} → {len(rows)} rows")
    if args.limit is not None:
        rows = rows[: args.limit]
    print(f"loaded {len(rows)} responses to judge (backend={args.backend}, model={args.model})")

    if args.backend == "bedrock":
        backbone = BedrockBackbone(
            model_id=args.model,
            region=args.bedrock_region,
            profile=args.bedrock_profile,
            max_new_tokens=args.max_new_tokens,
            temperature=0.0,
        )
    else:
        backbone = HFTransformersBackbone(
            model_id=args.model, max_new_tokens=args.max_new_tokens, temperature=0.0
        )

    cache_idx = load_cache_index(VERDICT_CACHE_DIR)
    cache_shard = shard_path(VERDICT_CACHE_DIR)
    print(f"Verdict cache: {len(cache_idx)} rows; appending to {cache_shard.relative_to(REPO)}")
    # Empirical timing for the judge step:
    #   * Bedrock Opus 4.6 / Sonnet 4.6: ~3s/verdict
    #   * Local Qwen-7B / Mistral-7B: ~6-8s/verdict (depends on history length)
    sec_per = 3.0 if args.backend == "bedrock" else 7.0
    # Cache-hit miss-mix is unknown up front; print pessimistic ETA assuming
    # worst case (all miss). Cache hits will accelerate the wall clock.
    print_eta_banner(
        label=f"score_responses ({args.backend}/{args.model})",
        n_units=len(rows),
        seconds_per_unit=sec_per,
        unit="verdict",
    )

    verdicts: list[dict] = []
    n_hits = 0
    t0 = time.perf_counter()

    n_workers = args.workers if args.workers > 0 else (8 if args.backend == "bedrock" else 1)
    print(f"workers={n_workers} (backend={args.backend})")
    cache_lock = threading.Lock()
    state_lock = threading.Lock()

    def _judge_one(r):
        sample = sample_by_id.get(r["sample_id"])
        if sample is None:
            return ("skip", r["sample_id"], None)
        sch = gold_content_hash(sample)
        response_key = short_hash(r["response"], length=24)
        verdict_key = make_verdict_key(
            sample_content_hash=sch,
            system_name=r["system_name"],
            response_key=response_key,
            judge_model_id=args.model,
            judge_prompt_hash=JUDGE_PROMPT_VERSION,
        )
        cached = None if args.no_cache else cache_idx.get(verdict_key)
        if cached is not None:
            return ("hit", sample, {
                "sample_id": sample.sample_id,
                "system_name": r["system_name"],
                "vf": cached["vf"],
                "raw_vf": cached.get("raw_vf"),
                "ambiguity_class": cached["ambiguity_class"],
                "confidence": cached["confidence"],
                "rationale": cached.get("rationale", ""),
                "recall": cached.get("recall"),
            })
        try:
            verdict = judge_sample(sample, r["response"], backbone)
        except Exception as e:  # noqa: BLE001
            return ("err", r["sample_id"], str(e))
        final = apply_default_scoring(verdict)
        if sample.sample_type == "supersession":
            recall_hit = score_recall(sample, r["response"]).hit_rate
        else:
            recall_hit = None
        payload = {
            "sample_id": sample.sample_id,
            "system_name": r["system_name"],
            "vf": final.vf,
            "raw_vf": verdict.vf,
            "ambiguity_class": verdict.ambiguity_class,
            "confidence": verdict.confidence,
            "rationale": verdict.rationale,
            "recall": recall_hit,
        }
        cache_row = {
            "cache_format_version": CACHE_FORMAT_VERSION,
            "cache_key": verdict_key,
            "sample_content_hash": sch,
            "response_key": response_key,
            "judge_model_id": args.model,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            **payload,
            "_written_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }
        with cache_lock:
            append_jsonl(cache_shard, cache_row)
            cache_idx.rows[verdict_key] = cache_row
        return ("miss", sample, payload)

    if n_workers <= 1:
        results_iter = (_judge_one(r) for r in rows)
    else:
        pool = ThreadPoolExecutor(max_workers=n_workers)
        futures = [pool.submit(_judge_one, r) for r in rows]
        results_iter = (f.result() for f in as_completed(futures))

    n_done = 0
    for tag, sample_or_id, payload in results_iter:
        n_done += 1
        if tag == "skip":
            print(f"  [{n_done}/{len(rows)}] unknown sample_id {sample_or_id!r}; skipping")
            continue
        if tag == "err":
            print(f"  [{n_done}/{len(rows)}] judge error on {sample_or_id}: {payload}")
            continue
        with state_lock:
            verdicts.append(payload)
            if tag == "hit":
                n_hits += 1
        if n_done % 5 == 0 or n_done == len(rows):
            elapsed = time.perf_counter() - t0
            rate = n_done / elapsed if elapsed > 0 else 0
            eta = (len(rows) - n_done) / rate if rate > 0 else 0
            hit_pct = n_hits / n_done * 100 if n_done else 0
            print(
                f"  [{n_done}/{len(rows)}] elapsed={elapsed:.0f}s rate={rate:.2f}/s "
                f"eta={eta:.0f}s  cache_hit={hit_pct:.0f}%",
                flush=True,
            )
    if n_workers > 1:
        pool.shutdown(wait=False)

    print(f"\n{len(verdicts)} verdicts produced (cache hits: {n_hits}/{len(rows)})")

    out_path = Path(args.out)
    if args.append and out_path.exists():
        new_keys = {(v["sample_id"], v["system_name"]) for v in verdicts}
        existing = []
        with out_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if (obj["sample_id"], obj["system_name"]) in new_keys:
                    continue  # replaced by the new verdict
                existing.append(obj)
        combined = existing + verdicts
        out_path.write_text("\n".join(json.dumps(v) for v in combined) + "\n")
        print(f"\nappended {len(verdicts)} verdicts to {out_path} "
              f"(total {len(combined)}) in {time.perf_counter() - t0:.1f}s")
    else:
        out_path.write_text("\n".join(json.dumps(v) for v in verdicts) + "\n")
        print(f"\nwrote {len(verdicts)} verdicts to {out_path} "
              f"in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
