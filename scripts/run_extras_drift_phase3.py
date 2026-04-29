#!/usr/bin/env python3
"""Phase 3 drift-only runner for the new vendor systems.

Adds 3 conditions to extend the architecture × backbone matrix from 2x2
to 2x4 on the drift focal cell (360 samples):

  --system structured_gpt54           -> GPT-5.4 extract+select+answer
  --system long_context_gemini31pro   -> Gemini 3.1 Pro direct long-context
  --system structured_gemini31pro     -> Gemini 3.1 Pro extract+select+answer

(long_context_gpt54 already runs separately on the full N=1000 set via
run_long_context_gpt54_phase3.py; its drift subset is reused for the
2x4 table without re-running.)

Auth: OPENAI_API_KEY for gpt54 systems, GEMINI_API_KEY for gemini31pro.

Output: data/responses/phase3_<system>_responses.jsonl (one JSON line per sample).

Usage:
  uv run python scripts/run_extras_drift_phase3.py --system structured_gpt54 --workers 6
  uv run python scripts/run_extras_drift_phase3.py --system long_context_gemini31pro --workers 6
  uv run python scripts/run_extras_drift_phase3.py --system structured_gemini31pro --workers 6
  uv run python scripts/run_extras_drift_phase3.py --system structured_gpt54 --limit 5  # smoke
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
from pipeline.evaluation.gemini_backbone import GeminiBackbone  # noqa: E402
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
DEFAULT_GOLD = DATA / "dataset/realized_phase3_main_full.jsonl"

SYSTEMS = {
    "long_context_gpt54": {
        "vendor": "openai",
        "model": "gpt-5.4",
        "kind": "direct",
    },
    "structured_gpt54": {
        "vendor": "openai",
        "model": "gpt-5.4",
        "kind": "structured",  # extract + select + answer
    },
    "long_context_gemini31pro": {
        "vendor": "gemini",
        "model": "gemini-3.1-pro-preview",
        "kind": "direct",
        "thinking_level": "medium",
    },
    "structured_gemini31pro": {
        "vendor": "gemini",
        "model": "gemini-3.1-pro-preview",
        "kind": "structured",
        "thinking_level": "medium",
    },
    "long_context_gemini25pro": {
        "vendor": "gemini",
        "model": "gemini-2.5-pro",
        "kind": "direct",
        # 2.5-pro doesn't support thinkingLevel; use vendor default
        "thinking_level": None,
    },
    "structured_gemini25pro": {
        "vendor": "gemini",
        "model": "gemini-2.5-pro",
        "kind": "structured",
        "thinking_level": None,
    },
}


def load_manifest_sids(manifest_path: Path) -> list[str]:
    m = json.loads(manifest_path.read_text())
    out = []
    for g in m["groups"]:
        for mem in g["members"]:
            out.append(mem["sample_id"])
    return out


def load_drift_sids(gold_path: Path) -> set[str]:
    out: set[str] = set()
    with open(gold_path) as f:
        for line in f:
            r = json.loads(line)
            md = r.get("_gold", {}).get("metadata", {}) or {}
            if (md.get("failure_patterns") or [None])[0] == "implicit_drift":
                out.add(r["sample_id"])
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


def make_backbone(vendor: str, model: str, max_tokens: int,
                   *, json_mode: bool = False,
                   reasoning_effort: str = "medium",
                   thinking_level: str | None = "medium") -> object:
    if vendor == "openai":
        return OpenAIBackbone(
            model_id=model,
            max_new_tokens=max_tokens,
            temperature=0.0,
            reasoning_effort=reasoning_effort,
            json_mode=json_mode,
        )
    if vendor == "gemini":
        return GeminiBackbone(
            model_id=model,
            max_new_tokens=max_tokens,
            temperature=0.0,
            thinking_level=thinking_level,
            json_mode=json_mode,
        )
    raise ValueError(f"unknown vendor: {vendor}")


def respond_direct(sample: dict, vendor: str, model: str,
                   max_tokens: int, system_name: str,
                   *, reasoning_override: str | None = None,
                   thinking_override: str | None = "DEFAULT") -> str:
    tl = "medium" if thinking_override == "DEFAULT" else thinking_override
    bb = make_backbone(vendor, model, max_tokens,
                        reasoning_effort=reasoning_override or "medium",
                        thinking_level=tl)
    base = LongContextBaseline(
        backbone=bb, name=system_name,
        answer_backbone_provider=("openai" if vendor == "openai" else "google"),
    )
    return base.respond(sample)


def respond_structured(sample: dict, vendor: str, model: str,
                       max_tokens: int, system_name: str,
                       *, reasoning_override: str | None = None,
                       thinking_override: str | None = "DEFAULT") -> str:
    re_eff = reasoning_override or "medium"
    tl = "medium" if thinking_override == "DEFAULT" else thinking_override
    bb_struct = make_backbone(vendor, model, max_tokens,
                                json_mode=True, reasoning_effort=re_eff,
                                thinking_level=tl)
    bb_plain = make_backbone(vendor, model, max_tokens,
                              json_mode=False, reasoning_effort=re_eff,
                              thinking_level=tl)

    extractor = make_drift_aware_llm_extractor(bb_struct, max_candidates=8)
    selector = make_llm_selector(bb_struct)

    def responder(public_sample):
        return LongContextBaseline(
            backbone=bb_plain, name=f"_{system_name}_inner_responder",
        ).respond(public_sample)

    wrapper = MinimalSupersessionWrapper(
        config=default_phase0_config(),
        extractor=extractor,
        selector=selector,
        responder=responder,
        name=system_name,
    )
    response, _trace = wrapper.respond(sample)
    return response


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--system", required=True, choices=list(SYSTEMS.keys()))
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST), type=Path)
    p.add_argument("--public", default=str(DEFAULT_PUBLIC), type=Path)
    p.add_argument("--gold", default=str(DEFAULT_GOLD), type=Path)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=4096,
                   help="Per-call completion-token budget. Default 4096 "
                        "matches the long-context runner. GPT-5 reasoning "
                        "tokens count against this; 2048 is too tight for "
                        "long histories and produces silent empty outputs.")
    p.add_argument("--reasoning-effort", default=None,
                   choices=["none", "low", "medium", "high", "xhigh"],
                   help="Override the OpenAI reasoning_effort. Default "
                        "None lets make_backbone use the vendor default "
                        "(medium for gpt-5.x).")
    p.add_argument("--filter-sids-file", type=Path, default=None,
                   help="Path to a newline-separated list of sample_ids "
                        "to restrict the run to (intersected with the "
                        "drift filter).")
    p.add_argument("--out-suffix", default="",
                   help="If set, output is "
                        "responses/phase3_<system><out_suffix>_responses.jsonl "
                        "instead of the default name. Use to keep "
                        "alternate runs (e.g. reasoning=high) separate.")
    args = p.parse_args()

    spec = SYSTEMS[args.system]
    out_path = DATA / f"responses/phase3_{args.system}{args.out_suffix}_responses.jsonl"

    if spec["vendor"] == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2
    if spec["vendor"] == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        return 2

    all_sids = load_manifest_sids(args.manifest)
    drift_sids = load_drift_sids(args.gold)
    sids = [s for s in all_sids if s in drift_sids]
    if args.filter_sids_file:
        wanted = set(args.filter_sids_file.read_text().split())
        sids = [s for s in sids if s in wanted]
        print(f"--filter-sids-file: restricted to {len(sids)} target sids")
    if args.limit:
        sids = sids[: args.limit]
    print(f"Drift-only filter: {len(sids)} sample_ids "
          f"(of {len(all_sids)} manifest, {len(drift_sids)} drift in gold)")

    samples_map = load_public_samples(args.public, set(sids))
    samples = [samples_map[sid] for sid in sids if sid in samples_map]
    done = load_done(out_path)
    samples = [s for s in samples if s["sample_id"] not in done]
    print(f"Resume: {len(done)} cached. Running {len(samples)} fresh through "
          f"{args.system} ({spec['vendor']} / {spec['model']} / {spec['kind']}) "
          f"at workers={args.workers}...")
    if not samples:
        return 0

    t0 = time.perf_counter()
    out_lock = threading.Lock()
    n_ok = 0
    n_err = 0
    n_done = 0

    spec_thinking = spec.get("thinking_level", "DEFAULT")
    def run_one(idx_sample):
        idx, sample = idx_sample
        sid = sample["sample_id"]
        ts = time.perf_counter()
        try:
            if spec["kind"] == "direct":
                resp = respond_direct(sample, spec["vendor"], spec["model"],
                                       args.max_tokens, args.system,
                                       reasoning_override=args.reasoning_effort,
                                       thinking_override=spec_thinking)
            else:
                resp = respond_structured(sample, spec["vendor"], spec["model"],
                                           args.max_tokens, args.system,
                                           reasoning_override=args.reasoning_effort,
                                           thinking_override=spec_thinking)
            return idx, sid, resp, None, time.perf_counter() - ts
        except Exception as e:  # noqa: BLE001
            return idx, sid, None, f"{type(e).__name__}: {e}", time.perf_counter() - ts

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
                    "system_name": args.system,
                    "response": resp,
                    "elapsed_s": round(elapsed, 2),
                }
                with open(out_path, "a") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                if n_done % 20 == 0 or n_done == len(samples):
                    rate = n_done / max(0.001, time.perf_counter() - t0)
                    eta = (len(samples) - n_done) / max(0.001, rate)
                    print(f"  [{n_done}/{len(samples)}] "
                          f"ok={n_ok} err={n_err} rate={rate:.2f}/s eta={eta:.0f}s")

    wall = time.perf_counter() - t0
    print(f"\nDone. {n_ok} ok / {n_err} err in {wall:.1f}s")
    print(f"Output: {out_path}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
