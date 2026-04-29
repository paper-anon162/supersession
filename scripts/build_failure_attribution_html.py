#!/usr/bin/env python3
"""Build the Failure-Attribution annotation HTML.

Per outline §5.4. Goal: classify *failed* (judge VF=0) responses into
mechanism categories — to support §5.3 / §6 mechanism narrative with
quantitative attribution rather than purely qualitative claims.

  Inputs to annotator:    history + current_query + model response
                          + gold current valid state + gold outdated state(s)
  Hidden from annotator:  judge verdict, failure_pattern label,
                          system identity (system name)
  Task:                   "Why did this response fail?" — 3-class
                          force-choice (A. Target-binding /
                          B. Current-state-resolution / C. Mixed).

Sample stratification (PAIR-level, vf=0 only):

  N = 150 failed sample-response pairs (pattern only)
  implicit_drift:        90    (focal cell)
  explicit_replacement:  20
  multi_version:         20
  narrowing:             20

  Within each pattern: uniform random from the failed (vf=0) Phase 3
  N=1000 pool, fixed random seed for reproducibility. No subtype
  stratification.

System pool: 6 systems spanning the VF range (long_context_sonnet46 /
llama8b + naive_rag + sonnet_extract + graphiti + structured_sonnet);
within each pattern, system assignment is uniform random with soft
balancing.

Generates ONE self-contained HTML file (single annotator-id input at
top). Annotator types in their ID, labels all 150 pairs in-browser.
LocalStorage namespaced by annotator_id. Force-choice A/B/C.

CSV download: pair_id, annotator_id, label.

Roles:
  - 2 primary annotators (A, B) → pairwise κ on 3 classes
  - 1 arbiter (C) → resolves A-B disagreements
  - All 3 use the same HTML; merge script handles role assignment.

Usage:
  python scripts/build_failure_attribution_html.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"

PATTERN_QUOTAS = {
    "implicit_drift":        90,
    "explicit_replacement":  20,
    "multi_version":         20,
    "narrowing":             20,
}
TOTAL_PAIRS = sum(PATTERN_QUOTAS.values())  # = 150

SYSTEMS_FOR_POOL = [
    "long_context_sonnet46",
    "long_context_llama8b",
    "naive_rag",
    "sonnet_extract",
    "graphiti",
    "structured_sonnet",
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path) if l.strip()]


def select_failed_pairs(
    samples: list[dict],
    responses_by_system: dict[str, dict[str, dict]],
    failed_pairs_by_sys: dict[str, set[str]],
    rng: random.Random,
) -> list[tuple[str, str]]:
    """Pair-level stratified sampling restricted to vf=0 (failed) pairs.

    Pattern-only stratification — no subtype stratification within drift.
    Within each pattern, iterate sample IDs in shuffled order; for each
    sid, pick the system with the lowest current count whose response
    is a *failed* one.
    """
    md_by_sid: dict[str, str] = {}
    for s in samples:
        md = s.get("_gold", {}).get("metadata", {}) or {}
        fps = md.get("failure_patterns") or []
        md_by_sid[s["sample_id"]] = fps[0] if fps else "unknown"

    by_pattern: dict[str, list[str]] = defaultdict(list)
    for sid, pat in md_by_sid.items():
        by_pattern[pat].append(sid)

    selected: list[tuple[str, str]] = []
    system_count: dict[str, int] = defaultdict(int)

    for pat, q in PATTERN_QUOTAS.items():
        sids = list(by_pattern.get(pat, []))
        if not sids:
            print(f"WARN: empty pattern {pat}, quota {q}")
            continue
        rng.shuffle(sids)
        picks_this = 0
        used_sids: set[str] = set()
        for sid in sids:
            if picks_this >= q:
                break
            if sid in used_sids:
                continue
            sorted_systems = sorted(SYSTEMS_FOR_POOL,
                                    key=lambda s: system_count[s])
            placed = False
            for sys_name in sorted_systems:
                if sid not in responses_by_system.get(sys_name, {}):
                    continue
                if sid not in failed_pairs_by_sys.get(sys_name, set()):
                    continue
                selected.append((sid, sys_name))
                used_sids.add(sid)
                system_count[sys_name] += 1
                picks_this += 1
                placed = True
                break
            if not placed:
                continue
        if picks_this < q:
            print(f"WARN: pattern {pat} under-filled: {picks_this}/{q}")
    return selected


def build_pool(
    selected: list[tuple[str, str]],
    samples_by_sid: dict[str, dict],
    responses_by_system: dict[str, dict[str, dict]],
    verdicts: list[dict],
) -> list[dict]:
    pool: list[dict] = []
    verdict_idx: dict[tuple[str, str], dict] = {}
    for v in verdicts:
        verdict_idx[(v["sample_id"], v["system_name"])] = v

    for sid, sys_name in selected:
        full = samples_by_sid[sid]
        resp = responses_by_system[sys_name].get(sid)
        if resp is None:
            continue
        verdict = verdict_idx.get((sid, sys_name))
        md = full.get("_gold", {}).get("metadata", {}) or {}
        pool.append({
            "pair_id": f"{sid}::{sys_name}",
            "sample_id": sid,
            "system_name": sys_name,
            "_visible_to_annotator": {
                "history_text": _render_history(full),
                "current_query": full.get("current_query", ""),
                "model_response": resp.get("response", ""),
                "gold_current_state": _gold_active(full),
                "gold_outdated_states": _gold_outdated(full),
            },
            "_hidden": {
                "llm_judge_vf": verdict.get("vf") if verdict else None,
                "llm_judge_rationale": (
                    verdict.get("rationale") if verdict else None),
                "stratification": {
                    "pattern": (md.get("failure_patterns") or ["unknown"])[0],
                    "drift_sub": md.get("implicit_drift_type"),
                    "horizon": md.get("horizon"),
                    "target_type": md.get("gold_target_type"),
                },
            },
        })
    return pool


def _gold_active(sample: dict) -> dict:
    gold = sample.get("_gold") or {}
    pred = gold.get("violation_predicate") or {}
    active = pred.get("must_honor") or {}
    return {
        "topic": active.get("topic", ""),
        "value": active.get("value", ""),
    }


def _gold_outdated(sample: dict) -> list[dict]:
    gold = sample.get("_gold") or {}
    pred = gold.get("violation_predicate") or {}
    must_avoid = pred.get("must_not_honor") or pred.get("must_avoid") or []
    out = []
    if isinstance(must_avoid, list):
        for entry in must_avoid:
            if isinstance(entry, dict):
                out.append({
                    "topic": entry.get("topic", ""),
                    "value": entry.get("value", ""),
                })
    return out


def _render_history(sample: dict) -> str:
    sessions = sample.get("history") or sample.get("sessions") or []
    parts: list[str] = []
    for sess in sessions:
        ref_t = sess.get("reference_time", "") or sess.get("timestamp", "")
        name = sess.get("episode_name") or sess.get("session_id") or ""
        parts.append(f"--- {name} ({ref_t}) ---")
        body = sess.get("episode_body")
        if body:
            parts.append(body)
            continue
        for turn in sess.get("turns") or sess.get("turn_messages") or []:
            role = turn.get("role", "user")
            content = turn.get("text") or turn.get("content") or ""
            parts.append(f"[{role}] {content}")
    return "\n\n".join(parts)


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>SupersessionBench — Failure Attribution Annotation</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif;
         max-width: 1100px; margin: 20px auto; padding: 0 20px;
         color: #222; line-height: 1.5; }}
  h1 {{ font-size: 22px; }}
  .annotator-id-input {{ background: #ffffd0; padding: 8px 14px;
                        border-radius: 4px; display: inline-block;
                        font-weight: 700; font-size: 16px; }}
  .annotator-id-input input {{ font-size: 16px; padding: 4px 8px;
                              border: 1px solid #999; border-radius: 3px;
                              width: 80px; text-transform: lowercase; }}
  .progress {{ position: sticky; top: 0; background: #fff;
              padding: 8px 0; border-bottom: 2px solid #ddd;
              z-index: 100; }}
  .pair {{ border: 1px solid #ccc; border-radius: 6px;
          padding: 16px; margin: 24px 0;
          background: #fafafa; }}
  .pair h2 {{ font-size: 16px; margin: 0 0 10px;
              color: #555; font-weight: 600; }}
  .gold-current {{ background: #d8f5d8; border-left: 4px solid #2a8a2a;
                  padding: 8px 12px; margin: 8px 0; border-radius: 3px; }}
  .gold-outdated {{ background: #fdd8d8; border-left: 4px solid #b22;
                   padding: 8px 12px; margin: 8px 0; border-radius: 3px; }}
  .response {{ background: #fff; border: 1px solid #999;
              padding: 10px 14px; margin: 8px 0; white-space: pre-wrap;
              font-family: ui-monospace, monospace; font-size: 13px; }}
  details summary {{ cursor: pointer; color: #36c; font-weight: 600;
                    padding: 4px 0; }}
  details > div {{ background: #eee; padding: 10px;
                  white-space: pre-wrap;
                  font-family: ui-monospace, monospace; font-size: 12px;
                  max-height: 400px; overflow-y: auto;
                  border-radius: 3px; }}
  .label-radio label {{ display: block; margin: 6px 0;
                       cursor: pointer; padding: 8px 12px;
                       border: 1px solid #aaa; border-radius: 4px;
                       background: #fff; }}
  .label-radio input:checked + span {{ font-weight: 700; color: #36c; }}
  .label-radio label:has(input:checked) {{ background: #e8f0ff;
                                           border-color: #36c; }}
  .saved {{ color: #2a8a2a; font-size: 12px; margin-left: 12px; }}
  .download-bar {{ position: fixed; bottom: 20px; right: 20px;
                  background: #fff; padding: 12px 16px;
                  border: 2px solid #36c; border-radius: 6px;
                  box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
  .download-bar button {{ font-size: 14px; padding: 8px 16px;
                         background: #36c; color: #fff; border: none;
                         border-radius: 4px; cursor: pointer;
                         font-weight: 700; }}
  .download-bar button:disabled {{ background: #aaa; cursor: not-allowed; }}
  .class-desc {{ font-size: 12px; color: #555; font-weight: 400;
                margin-left: 4px; }}
</style>
</head>
<body>

<h1>SupersessionBench — Failure Attribution Annotation</h1>
<div class="annotator-id-input">
  Your annotator ID:
  <input type="text" id="annotatorIdInput" maxlength="20"
         placeholder="e.g. a / b / arbiter" oninput="onAnnotatorIdChange()">
  <span style="font-size: 13px; font-weight: 400; margin-left: 8px;">
    (use a single letter for primary annotators, "arbiter" for the third)
  </span>
</div>
<p>
  Pairs: 150 (all pre-filtered to known failures)
  · Estimated time: ~10 hours
  · Force-choice 3-class: A / B / C
</p>

<div class="progress">
  Progress: <span id="progress">0 / 150</span>
  · <span id="saveStatus" class="saved"></span>
</div>

<details open>
<summary><b>Instructions</b> (read before starting)</summary>
<div>
Every response shown below was scored as a FAILURE. Your job is to
classify *why* it failed, by comparing the model response against the
gold current state and gold outdated state(s).

Pick exactly ONE of three classes:

  A. Target-binding failure
     - The response shows the model did NOT bind the update to the
       correct target. Examples: completely ignores the user's update
       (acts as if no update happened); answers about a different
       topic; honors an update but applies it to the wrong slot.

  B. Current-state-resolution failure
     - The response shows the model identified the update topic
       correctly, but acted on the OUTDATED version, OR mixed current
       and outdated versions. The target was located; the precedence
       was wrong.

  C. Mixed
     - Both binding and precedence look broken, OR the response is
       too sparse / ambiguous to attribute uniquely (e.g., refusal,
       generic non-answer that fails on both fronts).

Decision rule of thumb:
  - Did the response touch the right *topic* at all? If NO → A.
  - If YES, did it follow the OUTDATED value or mix versions? → B.
  - Both broken / cannot tell from response → C.

You will NOT see:
  - the failure-pattern category (drift / explicit / multi / narrow)
  - which system produced the response
  - the LLM judge's rationale

Auto-saves to your browser. To submit, click "Download CSV"
at the bottom and email back the file.
</div>
</details>

{PAIRS_HTML}

<div class="download-bar">
  <span id="dlSummary">0 / 150 labelled</span>
  &nbsp;<button id="dlBtn" onclick="downloadCSV()" disabled>Download CSV</button>
</div>

<script>
const PAIR_IDS = {PAIR_IDS_JSON};
let ANNOTATOR_ID = "";
let STORAGE_KEY = null;

function refreshStorageKey() {{
  STORAGE_KEY = ANNOTATOR_ID
    ? "ssbench_failure_attribution_" + ANNOTATOR_ID : null;
}}

function loadState() {{
  if (!STORAGE_KEY) return {{}};
  try {{
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
  }} catch (e) {{ return {{}}; }}
}}
function saveState(state) {{
  if (!STORAGE_KEY) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  document.getElementById("saveStatus").textContent =
    "saved at " + new Date().toLocaleTimeString();
}}
function refreshProgress() {{
  const state = loadState();
  const n = PAIR_IDS.filter(id => state[id] && state[id].label).length;
  document.getElementById("progress").textContent =
    n + " / " + PAIR_IDS.length;
  document.getElementById("dlSummary").textContent =
    n + " / " + PAIR_IDS.length + " labelled";
  document.getElementById("dlBtn").disabled =
    (n === 0 || !ANNOTATOR_ID);
}}

function onAnnotatorIdChange() {{
  ANNOTATOR_ID = document.getElementById("annotatorIdInput").value
    .trim().toLowerCase();
  refreshStorageKey();
  for (const id of PAIR_IDS) {{
    document.querySelectorAll(`input[name="label_${{id}}"]`).forEach(
      r => r.checked = false);
  }}
  if (STORAGE_KEY) {{
    const state = loadState();
    for (const [id, e] of Object.entries(state)) {{
      if (e.label) {{
        const radio = document.querySelector(
          `input[name="label_${{id}}"][value="${{e.label}}"]`);
        if (radio) radio.checked = true;
      }}
    }}
  }}
  refreshProgress();
}}

function onChange(pairId) {{
  if (!ANNOTATOR_ID) {{
    alert("Please enter your annotator ID at the top first.");
    return;
  }}
  const state = loadState();
  const labelEl = document.querySelector(
    `input[name="label_${{pairId}}"]:checked`);
  state[pairId] = {{
    label: labelEl ? labelEl.value : null,
    timestamp: new Date().toISOString(),
  }};
  saveState(state);
  refreshProgress();
}}

function downloadCSV() {{
  if (!ANNOTATOR_ID) return;
  const state = loadState();
  const rows = [["pair_id", "annotator_id", "label"]];
  for (const id of PAIR_IDS) {{
    const e = state[id] || {{}};
    rows.push([id, ANNOTATOR_ID, e.label || ""]);
  }}
  const csv = rows.map(r =>
    r.map(c => `"${{String(c).replace(/"/g, '""')}}"`).join(",")
  ).join("\\n");
  const blob = new Blob([csv], {{type: "text/csv"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "failure_attribution_" + ANNOTATOR_ID + ".csv";
  a.click();
  URL.revokeObjectURL(url);
}}

window.addEventListener("DOMContentLoaded", () => {{ refreshProgress(); }});
</script>

</body>
</html>
"""


def render_pair_card(pair: dict) -> str:
    v = pair["_visible_to_annotator"]
    pid = pair["pair_id"]
    gold_current = v["gold_current_state"]
    gold_outdated = v["gold_outdated_states"]

    outdated_html = ""
    if gold_outdated:
        items = "".join(
            f"<li><b>{escape(g['topic'])}</b>: {escape(g['value'])}</li>"
            for g in gold_outdated
        )
        outdated_html = (
            f'<div class="gold-outdated"><b>Gold OUTDATED state(s):</b>'
            f'<ul>{items}</ul></div>'
        )

    current_html = (
        f'<div class="gold-current">'
        f'<b>Gold CURRENT valid state:</b> '
        f'<code>{escape(gold_current.get("topic",""))}</code> = '
        f'<code>{escape(gold_current.get("value",""))}</code>'
        f'</div>'
    )

    return f"""
<div class="pair" data-pair-id="{escape(pid)}">
  <h2>Pair: {escape(pid)}</h2>
  <details>
    <summary>Conversation history (click to expand)</summary>
    <div>{escape(v.get('history_text', ''))}</div>
  </details>
  <p><b>Current request:</b><br>
     <i>{escape(v.get('current_query', ''))}</i></p>
  {current_html}
  {outdated_html}
  <p><b>Model response (this is a known FAILURE):</b></p>
  <div class="response">{escape(v.get('model_response', ''))}</div>

  <p><b>Why did this response fail?</b></p>
  <div class="label-radio">
    <label><input type="radio" name="label_{escape(pid)}" value="A"
                  onchange="onChange('{escape(pid)}')">
           <span>A. Target-binding failure</span>
           <span class="class-desc">— wrong target / ignored update</span></label>
    <label><input type="radio" name="label_{escape(pid)}" value="B"
                  onchange="onChange('{escape(pid)}')">
           <span>B. Current-state-resolution failure</span>
           <span class="class-desc">— right target, followed outdated version</span></label>
    <label><input type="radio" name="label_{escape(pid)}" value="C"
                  onchange="onChange('{escape(pid)}')">
           <span>C. Mixed</span>
           <span class="class-desc">— both broken, or cannot uniquely attribute</span></label>
  </div>
</div>
""".strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verdicts",
                   default=str(DATA / "verdicts/phase3_xsystem_opus_verdicts.jsonl"),
                   type=Path)
    p.add_argument("--gold",
                   default=str(DATA / "dataset/realized_phase3_main_full.jsonl"),
                   type=Path)
    p.add_argument("--responses-dir", default=str(DATA / "responses"), type=Path)
    p.add_argument("--out-dir",
                   default=str(DATA / "failure_attribution_pool"),
                   type=Path)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    verdicts = load_jsonl(args.verdicts)
    print(f"Loaded {len(verdicts)} verdicts")

    failed_pairs_by_sys: dict[str, set[str]] = defaultdict(set)
    for v in verdicts:
        if v.get("vf") in (0, 0.0):
            failed_pairs_by_sys[v["system_name"]].add(v["sample_id"])
    for sys_name in SYSTEMS_FOR_POOL:
        n_fail = len(failed_pairs_by_sys.get(sys_name, set()))
        print(f"  {sys_name}: {n_fail} failed (vf=0) responses available")

    samples = load_jsonl(args.gold)
    samples_by_sid = {s["sample_id"]: s for s in samples}
    print(f"Loaded {len(samples)} gold samples")

    responses_by_system: dict[str, dict[str, dict]] = {}
    for sys_name in SYSTEMS_FOR_POOL:
        path = args.responses_dir / f"phase3_{sys_name}_responses.jsonl"
        if not path.exists():
            responses_by_system[sys_name] = {}
            continue
        recs = load_jsonl(path)
        responses_by_system[sys_name] = {r["sample_id"]: r for r in recs}
        print(f"  {sys_name}: {len(recs)} responses")

    rng = random.Random(args.seed)
    selected = select_failed_pairs(samples, responses_by_system,
                                    failed_pairs_by_sys, rng)
    print(f"Selected {len(selected)} pairs (target {TOTAL_PAIRS})")

    pool = build_pool(selected, samples_by_sid, responses_by_system, verdicts)
    print(f"Pool: {len(pool)} pairs")

    master_path = args.out_dir / "master_pool.jsonl"
    with open(master_path, "w") as f:
        for pair in pool:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    print(f"Wrote {master_path}")

    pair_ids_json = json.dumps([p["pair_id"] for p in pool])
    cards_html = "\n".join(render_pair_card(p) for p in pool)
    html = HTML_TEMPLATE.format(
        PAIRS_HTML=cards_html,
        PAIR_IDS_JSON=pair_ids_json,
    )
    out_html = args.out_dir / "failure_attribution_annotation.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote {out_html}")

    # Sampling report.
    report_path = args.out_dir / "sampling_report.md"
    pat_counts: dict[str, int] = defaultdict(int)
    sub_counts: dict[str, int] = defaultdict(int)
    horizon_counts: dict[str, int] = defaultdict(int)
    sys_counts: dict[str, int] = defaultdict(int)
    for pair in pool:
        st = pair["_hidden"]["stratification"]
        pat_counts[st["pattern"]] += 1
        if st["pattern"] == "implicit_drift":
            sub_counts[st["drift_sub"] or "unknown"] += 1
        horizon_counts[st["horizon"] or "unknown"] += 1
        sys_counts[pair["system_name"]] += 1

    report = "# N=150 Failure Attribution sampling report\n\n"
    report += f"Pairs: {len(pool)} (target 150, vf=0 only)\n\n"
    report += "## Pattern (target: drift 90 / explicit 20 / multi 20 / narrow 20)\n\n"
    for p_, n in sorted(pat_counts.items()):
        report += f"- {p_}: {n}\n"
    report += "\n## Drift sub-pattern (post-hoc, no quota)\n\n"
    for sub, n in sorted(sub_counts.items()):
        report += f"- {sub}: {n}\n"
    report += "\n## Horizon (post-hoc, no quota)\n\n"
    for h, n in sorted(horizon_counts.items()):
        report += f"- {h}: {n}\n"
    report += "\n## System (soft target ~25 each)\n\n"
    for s, n in sorted(sys_counts.items()):
        report += f"- {s}: {n}\n"
    report_path.write_text(report)
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
