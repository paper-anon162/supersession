#!/usr/bin/env python3
"""Phase 3 ablation: sonnet_extract pipeline with Sonnet 4.6 answer.

Tests the backbone confound: ``sonnet_extract`` (Sonnet extract+select +
**Llama 8B** answer) vs ``structured_sonnet`` (Sonnet extract
+select + **Sonnet 4.6** answer). Together with ``long_context_sonnet46``
(Sonnet direct, no extract) and ``long_context_llama8b`` (Llama direct,
no extract) this completes the 2×2:

                     | extract+select       | direct (no extract)
    -----------------+----------------------+-------------------------
    Sonnet answer    | sonnet_extract_      | long_context_sonnet46
                     | sonnet_respond (NEW) |
    Llama 8B answer  | sonnet_extract       | long_context_llama8b

Cost estimate (N=1000, workers=1):
  - Sonnet extract+select: ~$0 (response cache hits — already cached
    from Stage 3 ``run_wrappers_phase3.py`` run)
  - Sonnet 4.6 answer × 1000: ~$30
  - Wall: ~1.5-2 hr at workers=1 (TPM-friendly co-existence with
    Stage 4 graphiti, which uses Sonnet 4.6 internally)
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
DEFAULT_OUT = DATA / "responses/phase3_structured_sonnet_responses.jsonl"

# system_name written to responses; matches the conventional name for
# this ablation (Sonnet 4.6 throughout extract+select+answer, contrasting
# the "raw context" long_context_sonnet46 with this "structured" path).
SYSTEM_NAME = "structured_sonnet"


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
    p.add_argument("--workers", type=int, default=6,
                   help="Sonnet 4.6 TPM-limited; workers=6 safe when "
                        "no other Sonnet-heavy job is running concurrently.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--profile", default="ahe-long")
    p.add_argument("--sonnet-model", default="us.anthropic.claude-sonnet-4-6")
    args = p.parse_args()

    sids = load_manifest_sids(args.manifest)
    if args.limit:
        sids = sids[: args.limit]
    print(f"Phase 3 manifest: {len(sids)} sample_ids")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    print(f"Loaded {len(samples)} samples")

    done = load_done(args.out)
    if done:
        print(f"Resume: skipping {len(done)} already in {args.out.name}")
        samples = [s for s in samples if s["sample_id"] not in done]
    print(f"Running {len(samples)} fresh samples through "
          f"structured_sonnet...")
    t0 = time.perf_counter()

    config = default_phase0_config()
    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0

    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        # Per-sample fresh backbone (boto3 connection-pool isolation).
        sonnet_bb = BedrockBackbone(
            model_id=args.sonnet_model, profile=args.profile,
            max_new_tokens=1024, temperature=0.0,
        )
        # Same extractor + selector as run_wrappers_phase3 sonnet_extract,
        # so response cache from Stage 3 hits and we pay 0 for these steps
        # if cache is content-addressed by (model, prompt, params).
        base_extractor = make_drift_aware_llm_extractor(sonnet_bb, max_candidates=8)
        cached_extractor = CachedExtractor(base_extractor)
        sonnet_selector = make_llm_selector(sonnet_bb)

        def sonnet_responder(public_sample):
            return LongContextBaseline(
                backbone=sonnet_bb, name="long_context_sonnet46"
            ).respond(public_sample)

        wrapper = MinimalSupersessionWrapper(
            config=config,
            extractor=cached_extractor,
            selector=sonnet_selector,
            responder=sonnet_responder,
            name="structured_sonnet",
        )

        ts = time.perf_counter()
        try:
            resp, _trace = wrapper.respond(sample)
            return idx, sample, resp, None, time.perf_counter() - ts
        except Exception as e:  # noqa: BLE001
            return idx, sample, None, f"{type(e).__name__}: {e}", time.perf_counter() - ts

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(run_one, (i, s)): i for i, s in enumerate(samples)}
        for fut in as_completed(futs):
            idx, sample, resp, err, elapsed = fut.result()
            sid = sample["sample_id"]
            with out_lock:
                if err:
                    n_err += 1
                    print(
                        f"  ✗ [{idx+1}/{len(samples)}] {sid:<45} "
                        f"{elapsed:.1f}s FAIL: {err[:160]}",
                        flush=True,
                    )
                else:
                    n_ok += 1
                    rec = {
                        "sample_id": sid,
                        "system_name": SYSTEM_NAME,
                        "response": resp,
                        "elapsed_s": round(elapsed, 2),
                    }
                    with open(args.out, "a") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(
                        f"  ✓ [{idx+1}/{len(samples)}] {sid:<45} {elapsed:.1f}s",
                        flush=True,
                    )

    wall = time.perf_counter() - t0
    print(f"\nDone in {wall:.1f}s — {n_ok} ✓ / {n_err} ✗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
