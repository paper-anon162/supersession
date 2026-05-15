# SupersessionBench

A behavioral-supersession benchmark for long-term LLM agents: 1,000
multi-session samples evaluating whether systems honor the user's *current*
state instead of acting on outdated state from earlier in the conversation
history.

This repository contains the **code, scripts, dataset, cached responses,
and judge verdicts** for SupersessionBench --- everything needed to
reproduce the paper's headline numbers without any API calls. Two
auxiliary artefact categories live outside the repository (see
[§ Supplementary materials](#supplementary-materials)): the raw
per-annotator data underlying the human-validation pools ships in a
separate supplementary archive, and the upstream skeleton corpora
(LongMemEval / LoCoMo) used during optional dataset re-realization are
fetched by the user from their upstream sources.

For background on what behavioral supersession is and why it matters, see the
SupersessionBench paper (Track on Evaluations and Datasets, NeurIPS 2026).

---

## Quickstart

```bash
# 1. Install pinned dependencies (Python 3.12+). Either path works.
#    (a) uv (fast, deterministic; install via `pip install uv`).
uv sync
#    (b) pip + requirements.txt (compatibility path).
# pip install -r requirements.txt

# 2. Verify integrity of the release.
python scripts/validate_release.py

# 3. Reproduce every paper-table CSV (no API calls, runs in seconds).
python scripts/build_paper_data.py

# 4. Reproduce every figure (no API calls).
python scripts/build_paper_figures.py
```

If `validate_release.py` reports `All checks PASS`, the release is intact and
every script below will produce paper-identical numbers.

---

## What ships in the repository

`data/` already holds everything needed to reproduce the paper:

- `data/dataset/realized_phase3_main_{public,gold,full}.jsonl` — 1{,}000-sample release
  in three views (system-facing public; judge-only gold; full audit view).
- `data/responses/phase3_<system>_responses.jsonl` — cached responses for the 11
  evaluated systems plus 2 diagnostics.
- `data/verdicts/phase3_xsystem_opus_verdicts.jsonl` (+ vendor-extension shards) —
  Opus 4.6 judge verdicts.
- `data/verdicts/phase3_xjudge_mistral_*.jsonl` — Mistral Large 3 cross-judge.
- `data/manifests/phase3_main.json` — 350 matched groups used for paired
  bootstrap.
- `data/paper/` — 24 standalone CSVs backing every paper table and figure,
  plus an `index.md` mapping paper artefact -> CSV.

### Croissant metadata and per-file schemas

`croissant.json` (repo root) is the Croissant 1.0 dataset descriptor required
by the NeurIPS 2026 Evaluations & Datasets track. It declares every released
file with its sha256 hash, raw GitHub URL, and per-field schema, plus the
full Responsible-AI metadata block (data collection, limitations, biases,
intended use, social impact, etc.). Reviewers pointing automated pipelines
at the dataset should consume `croissant.json`.

Per-record fields at a glance (see `croissant.json` for canonical schemas):

| File | Key fields |
|---|---|
| `realized_phase3_main_public.jsonl` | `sample_id`, `history`, `current_query`, `sample_type`, `recall_query` |
| `realized_phase3_main_gold.jsonl` | `sample_id`, `_gold` (target versions, active state, outdated states, violation predicate, semantic spine, target type, supersession pattern, horizon, domain, construction metadata) |
| `manifests/phase3_main.json` | `name`, `version`, `selection_rule`, `groups` (350 matched groups of 2--3 sample IDs sharing one semantic spine across horizons) |
| `phase3_<system>_responses.jsonl` | `sample_id`, `system_name`, `response`, `elapsed_s` |
| `phase3_xsystem_opus_verdicts.jsonl` (+ shards) | `sample_id`, `system_name`, `vf` (binary), `raw_vf`, `ambiguity_class`, `confidence`, `rationale`, `recall` |

The public/gold split is enforced at load time: `pipeline/io.py:load_for_system()`
returns the public-only view, and any `_gold` access by a system-under-test
raises `GoldLeakageInRunner`. Judges and analysis scripts use the gold view
explicitly. License: dataset CC BY-NC 4.0; code MIT (see `LICENSE-DATA` /
`LICENSE-CODE`).

## Supplementary materials

Most artefacts ship in this repository. Two categories live elsewhere:

- **Skeleton corpora** (`data/skeletons/locomo/`,
  `data/skeletons/longmemeval/`) are not redistributed; they come from
  the upstream LongMemEval (MIT) and LoCoMo (CC BY-NC 4.0) projects.
  Users who want the optional re-realization path populate these
  themselves --- see `data/skeletons/README.md` for the expected layout
  and download links. The paper-number verification recipes do **not**
  need them.
- The three annotation pools (judge_validation N=150 / solvability
  N=270 / naturalness N=40) live in the supplementary archive (uploaded
  to the NeurIPS submission portal during review; the camera-ready
  version will mirror the archive at a permanent host such as Zenodo /
  Hugging Face Datasets). Each pool ships the merged adjudicated
  report, the HTML annotation interface (instructions inline), and the
  full written consent form; per-annotator raw CSVs are retained by the
  authors and available on request to keep the small annotator pool
  private. Aggregate statistics are emitted from `build_paper_data.py`
  using pre-computed values, so paper-headline annotation numbers
  reproduce without the raw data.
- The sampled-but-unannotated `failure_attribution_pool/` (150 pairs +
  HTML annotation interface) is shipped alongside as scaffolding for
  future researchers wishing to extend with a quantitative attribution
  pass; the paper itself makes no quantitative claim from it (see
  Appendix~I).

Unpack the supplementary archive at the repository root so that
`data/{judge_validation,solvability,naturalness,failure_attribution}_pool/`
resolves. Skeleton corpora are not in the archive --- see
`data/skeletons/README.md` for how to populate them from upstream.

---

## Reproduction recipes

### Low-cost path (recommended for reviewers; no API access required)

| Script | Output |
|---|---|
| `scripts/validate_release.py` | 9-section release-integrity check |
| `scripts/build_paper_data.py` | regenerate every main-text paper-table CSV (the 4 vendor-extension appendix CSVs ship as static artifacts) |
| `scripts/build_paper_figures.py` | regenerate every paper figure (PDF) |
| `scripts/recompute_main_table.py` | overall and per-pattern VF table |
| `scripts/recompute_paired_ci.py` | paired-bootstrap 95% CIs |
| `scripts/recompute_per_system_tables.py --by horizon` | per-system × horizon slice |
| `scripts/recompute_recall_gap.py` | recall--VF gap by system |
| `scripts/recompute_horizon_paired.py` | within-system horizon-transition CIs |
| `scripts/recompute_xjudge_mistral.py` | Opus / Mistral cross-judge agreement |

All recompute scripts read from cached verdicts; none calls a model API.

### Full rerun (optional; costly)

To re-generate model responses from scratch, run the per-stage runners
(requires API credentials for AWS Bedrock and, for the vendor-extension
matrix, Google + OpenAI):

```bash
# Stage 1 - long-context × 3 + naive_rag + recency_rag (~1 hr)
AWS_PROFILE=<profile> uv run python scripts/run_simple_baselines_phase3.py

# Stage 2 - diagnostic conditions (~25 min)
AWS_PROFILE=<profile> uv run python scripts/run_diagnostics_phase3.py

# Stage 3 - 3 wrappers sharing extract+select cache (~1.5 hr)
AWS_PROFILE=<profile> uv run python scripts/run_wrappers_phase3.py

# Stage 4 - graphiti + graphiti_inv_off (~12 hr)
AWS_PROFILE=<profile> uv run python scripts/run_graphiti_phase3.py

# Stage 5 - structured_sonnet ablation (~30 min)
AWS_PROFILE=<profile> uv run python scripts/run_sonnet_respond_ablation_phase3.py

# Vendor extension (drift focal cell only)
uv run python scripts/run_long_context_gemini_phase3.py
uv run python scripts/run_long_context_gpt54_phase3.py
uv run python scripts/run_extras_drift_phase3.py

# Score every cached response with Opus 4.6 judge (~2 hr)
AWS_PROFILE=<profile> uv run python scripts/score_responses.py \
    --responses data/responses/phase3_<system>_responses.jsonl \
    --out      data/verdicts/phase3_xsystem_opus_verdicts.jsonl
```

Total Bedrock cost for a full rerun is approximately
\$1{,}500--\$2{,}500 USD (the Opus judge accounts for the majority).
Vendor-extension systems (Gemini 2.5 Pro, GPT-5.4) run on Google / OpenAI
APIs and incur small additional non-Bedrock costs.

### Re-realize the dataset from semantic spines (optional; data-construction)

Re-realizing the 1{,}000 samples from the hand-authored semantic spines
(`seeds/phase3/_batch_*.py`) requires the upstream skeleton corpora
(LongMemEval, LoCoMo) — populate `data/skeletons/` from upstream per
`data/skeletons/README.md`. The end-to-end loop is:

```bash
# 1. Realize a batch of spines into multi-session histories
#    (~30s per sample on Bedrock Sonnet 4.6).
AWS_PROFILE=<profile> uv run python scripts/realize_phase3.py --batch <name>

# 2. Build the locked manifest from the realized pool
#    (deterministic; rule-locked; no API calls).
uv run python scripts/select_phase3_manifest.py
```

Step 1 writes to `data/pool/phase3_groups.jsonl` and
`data/dataset/realized_phase3_*.jsonl`; step 2 reads the pool and emits
`data/manifests/phase3_main.json` plus
`reports/phase3/selection_report.json`. The default released manifest
already represents this selection on the released pool; running step 2
on a freshly re-realized pool produces a new locked selection.

---

## Repository layout

```
pipeline/             benchmark engine: judge, baselines, retrieval, evaluation
scripts/              reproduction + recompute + per-stage runners
seeds/                hand-authored Phase 3 semantic spines (36 batches)
prompts/              judge prompt + extraction / selection prompts
docker/               Graphiti + FalkorDB compose for the temporal-graph baseline
tests/                pytest regression suite
reports/phase3/       selection report (Appendix J)
data/                 released artefacts (dataset, responses, verdicts, manifests, backing CSVs)
external/             upstream skeleton sources; populated by user (optional)
```

---

## License

| Component | License |
|---|---|
| Code (this repository) | MIT --- see `LICENSE-CODE` |
| Dataset (supplementary archive) | CC BY-NC 4.0 --- see `LICENSE-DATA` |

The dataset adopts CC BY-NC 4.0 to match the most restrictive upstream
skeleton source (LoCoMo). LongMemEval is MIT-licensed; either upstream may
be redistributed under CC BY-NC 4.0 within this dataset's scope. Per-sample
provenance JSON preserves the original attribution.

---

## Citation

```bibtex
@inproceedings{supersessionbench,
  title     = {Updated, Not Just Remembered: Behavioral Supersession in Long-Term LLM Agents},
  author    = {Anonymous},
  booktitle = {The 40th Conference on Neural Information Processing Systems (NeurIPS), Track on Evaluations and Datasets},
  year      = {2026}
}
```

(Author block redacted for double-blind review; updated for camera-ready.)
