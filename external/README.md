# External skeleton sources

This directory holds checkouts of the two upstream long-conversation
corpora that SupersessionBench borrows distractor sessions from
(see Appendix A.4 of the paper):

- **LongMemEval** (MIT license) — default skeleton source (~89% of samples)
  Get it at: https://github.com/xiaowu0162/LongMemEval

- **LoCoMo** (CC BY-NC 4.0) — alternative skeleton source
  Get it at: https://github.com/snap-research/locomo

These are required if you want to **re-realize** the dataset from semantic
spines via `scripts/realize_phase3.py`. They are NOT required for any
result-verification path (paper-table recompute, judge re-scoring, etc.),
because every released sample already contains its baked-in distractor text.

The upstream content is not redistributed in this repo to preserve each
project's license terms. The supplementary archive includes a snapshot
matching what we used.
