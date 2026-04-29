# `data/skeletons/` — long-conversation source corpora

SupersessionBench borrows multi-session dialogue **structure** (session
length, turn cadence, timestamp distributions, distractor / bridge
content) from two existing long-conversation benchmarks during dataset
re-realization (Appendix A.4). We never copy a foreign QA into a
SupersessionBench gold predicate.

These corpora are **not redistributed in this repository** to honor each
upstream project's license. Users who want to re-realize the dataset
from semantic spines (`scripts/realize_phase3.py`) must populate the
files below from the upstream releases.

## Required layout

```
data/skeletons/
├── locomo/
│   ├── locomo10.json              ~2.7 MB   10 conversations × ~35 sessions
│   └── msc_personas_all.json      ~3.0 MB   MSC persona pool (LoCoMo's seed)
└── longmemeval/
    ├── longmemeval_oracle.json     ~15 MB   evidence-only sessions
    └── longmemeval_s_cleaned.json ~265 MB   ~40 sessions × ~115 K tokens
```

The loaders in `pipeline/construction/skeleton_loader.py` read these
exact filenames; placing files at any other path will fail.

## How to fetch

### LoCoMo (CC BY-NC 4.0)

Upstream: https://github.com/snap-research/locomo

```bash
# Option A — clone the upstream repo and copy the JSON files
git clone https://github.com/snap-research/locomo external/locomo
cp external/locomo/data/locomo10.json data/skeletons/locomo/
cp external/locomo/data/msc_personas_all.json data/skeletons/locomo/
```

(The exact in-repo path may shift between LoCoMo releases; consult the
upstream README if `data/locomo10.json` does not exist.)

### LongMemEval (MIT)

Upstream: https://github.com/xiaowu0162/LongMemEval

The `_oracle` and `_s` variants are released as pre-built JSON files;
download according to the upstream instructions and place them at:

- `data/skeletons/longmemeval/longmemeval_oracle.json`
- `data/skeletons/longmemeval/longmemeval_s_cleaned.json`

The `_cleaned` suffix on `longmemeval_s` indicates the SupersessionBench
naming for the LongMemEval `_s` variant; if upstream distributes a file
named `longmemeval_s.json`, simply copy it to the expected
`longmemeval_s_cleaned.json` filename.

## Verifying

After placing the files, the unit tests under `tests/test_skeleton_loader.py`
confirm shape and parse correctness:

```bash
uv run pytest tests/test_skeleton_loader.py
```

If those 8 tests pass, the skeletons are wired correctly and
`scripts/realize_phase3.py` can re-realize the dataset from semantic
spines.

## License

LoCoMo content is **CC BY-NC 4.0** (NonCommercial);
LongMemEval content is **MIT**. The SupersessionBench dataset license
(CC BY-NC 4.0; see top-level `LICENSE-DATA`) is chosen to match the
most restrictive upstream source.
