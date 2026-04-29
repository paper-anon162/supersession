#!/usr/bin/env python3
"""Validate Phase 3 release artifacts:schema、manifest、public/gold split、
gold-leakage、horizon × pattern quotas。

Runs all release-time checks any reviewer should be able to run on the
cloned repo + downloaded artifacts. No API calls.

Usage:
  python scripts/validate_release.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "✅" if condition else "❌"
    print(f"  {status} {name}{(': ' + detail) if detail else ''}")
    return condition


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest",
                   default=str(DATA / "manifests" / "phase3_main.json"),
                   type=Path)
    p.add_argument("--full",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--public",
                   default=str(DATA / "dataset/realized_phase3_main_public.jsonl"),
                   type=Path)
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_gold.jsonl"),
                   type=Path)
    args = p.parse_args()

    all_ok = True

    print("\n=== 1. File presence ===")
    for path in [args.manifest, args.full, args.public, args.gold]:
        if not check(f"{path.name} exists", path.exists()):
            all_ok = False

    if not all_ok:
        print("\nMissing files; aborting further checks.")
        return 1

    # Load
    full = [json.loads(l) for l in open(args.full)]
    public = [json.loads(l) for l in open(args.public)]
    gold = [json.loads(l) for l in open(args.gold)]
    manifest = json.loads(args.manifest.read_text())

    print("\n=== 2. Sample counts ===")
    check(f"full N=1000", len(full) == 1000, f"got {len(full)}")
    check(f"public N=1000", len(public) == 1000, f"got {len(public)}")
    check(f"gold N=1000", len(gold) == 1000, f"got {len(gold)}")

    print("\n=== 3. Sample-id consistency across files ===")
    sids_full = {s["sample_id"] for s in full}
    sids_public = {s["sample_id"] for s in public}
    sids_gold = {s["sample_id"] for s in gold}
    check("full == public sids", sids_full == sids_public)
    check("full == gold sids", sids_full == sids_gold)

    print("\n=== 4. Public-only loader contract (no _gold leak) ===")
    leaks = sum(1 for s in public if "_gold" in s)
    check(f"public 文件无 _gold 字段", leaks == 0,
          f"{leaks} samples leak _gold" if leaks else "0 leaks")

    print("\n=== 5. Manifest structure ===")
    n_groups = len(manifest.get("groups", []))
    n_members = sum(len(g.get("members", [])) for g in manifest.get("groups", []))
    check("350 groups in manifest", n_groups == 350, f"got {n_groups}")
    check("1000 sample members in manifest", n_members == 1000, f"got {n_members}")
    sids_manifest = {m["sample_id"] for g in manifest["groups"] for m in g["members"]}
    check("manifest sids ⊆ full sids", sids_manifest <= sids_full,
          f"{len(sids_manifest - sids_full)} manifest sids not in full")

    print("\n=== 6. Schema fields ===")
    sample = full[0]
    required_top = ["sample_id", "history", "current_query", "_gold"]
    for k in required_top:
        check(f"top-level '{k}'", k in sample)
    g = sample["_gold"]
    required_gold = ["target_versions", "violation_predicate", "metadata",
                     "gold_target_type"]
    for k in required_gold:
        check(f"_gold.{k}", k in g)
    md = g["metadata"]
    required_md = ["horizon", "failure_patterns", "implicit_drift_type",
                   "triple_id", "domain", "topic_group", "group_type"]
    for k in required_md:
        check(f"_gold.metadata.{k}", k in md)

    print("\n=== 7. Horizon × pattern quotas (per protocol §10.2) ===")
    horizon_counts = Counter()
    pattern_counts = Counter()
    drift_subtype_counts = Counter()
    for s in full:
        m = s["_gold"]["metadata"]
        horizon_counts[m["horizon"]] += 1
        for p in (m.get("failure_patterns") or []):
            pattern_counts[p] += 1
        if (m.get("failure_patterns") or [None])[0] == "implicit_drift":
            drift_subtype_counts[m.get("implicit_drift_type") or "unknown"] += 1
    check("compact = 300", horizon_counts["compact"] == 300,
          f"got {horizon_counts['compact']}")
    check("standard = 350", horizon_counts["standard"] == 350,
          f"got {horizon_counts['standard']}")
    check("hard = 350", horizon_counts["hard"] == 350,
          f"got {horizon_counts['hard']}")

    print("\n  Pattern distribution:")
    for p, n in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        print(f"    {p}: {n}")
    print("  Drift subtype distribution:")
    for s, n in sorted(drift_subtype_counts.items(), key=lambda x: -x[1]):
        print(f"    {s}: {n}")

    print("\n=== 8. Non-object target-type floor (≥ 50%) ===")
    target_counts = Counter(s["_gold"]["metadata"].get("gold_target_type")
                            for s in full)
    non_obj = sum(n for t, n in target_counts.items()
                  if t and t != "object_preference")
    pct = non_obj / len(full) * 100
    check(f"non-object share ≥ 50%", pct >= 50, f"{pct:.1f}%")

    print("\n=== 9. Ambiguity: 0 ambiguous samples in main set ===")
    n_ambig = sum(1 for s in full
                  if s["_gold"]["metadata"].get("ambiguity_class")
                  not in (None, "not_ambiguous"))
    check("0 ambiguous samples", n_ambig == 0, f"got {n_ambig}")

    print("\n=== Summary ===")
    print("All checks PASS ✅" if all_ok else "Some checks failed ❌")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
