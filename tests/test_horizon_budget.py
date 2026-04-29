"""Tests for the strict horizon-tier budget gate (audit P0).

Two layers:

1. Unit: ``pipeline.construction.realization._check_horizon_budget`` and
   ``pipeline.construction.realization._gauntlet_check`` correctly
   accept in-band samples and reject out-of-band ones.
2. Integration (gated on data-file presence): every realized Phase 2
   sample's ``_gold.metadata.history_token_count`` falls inside the
   declared horizon's budget band, and the recorded count matches a
   recomputed-from-history count to within rounding tolerance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.construction.realization import (
    _check_horizon_budget,
    _gauntlet_check,
)
from pipeline.construction.skeleton_realizer import HORIZON_BUDGETS
from pipeline.schema.fixtures import dummy_supersession_sample

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
PHASE2_FILES = (
    DATA / "realized_phase2_a_full.jsonl",
    DATA / "realized_phase2_b_full.jsonl",
)
_TOK = re.compile(r"\w+|[^\w\s]")


# ---------------------------------------------------------------------------
# Unit: _check_horizon_budget
# ---------------------------------------------------------------------------


def _set_horizon(sample, horizon, history_token_count):
    """Return a copy of `sample` with metadata.horizon and
    metadata.history_token_count updated."""
    return sample.model_copy(
        update={
            "gold": sample.gold.model_copy(
                update={
                    "metadata": sample.gold.metadata.model_copy(
                        update={
                            "horizon": horizon,
                            "history_token_count": history_token_count,
                        }
                    )
                }
            )
        }
    )


def test_no_horizon_passes():
    s = dummy_supersession_sample()
    # dummy fixture has no horizon set
    assert _check_horizon_budget(s) is None


def test_compact_in_band_passes():
    s = _set_horizon(dummy_supersession_sample(), "compact", 1500)
    assert _check_horizon_budget(s) is None


def test_standard_in_band_passes():
    s = _set_horizon(dummy_supersession_sample(), "standard", 5000)
    assert _check_horizon_budget(s) is None


def test_hard_in_band_passes():
    s = _set_horizon(dummy_supersession_sample(), "hard", 15000)
    assert _check_horizon_budget(s) is None


def test_below_min_rejected():
    # Standard min is 3000; 2500 is below.
    s = _set_horizon(dummy_supersession_sample(), "standard", 2500)
    err = _check_horizon_budget(s)
    assert err is not None
    assert "min_tokens" in err
    assert "history_token_count=2500" in err


def test_at_max_rejected():
    # Bounds are inclusive on min, exclusive on max — so a sample at
    # exactly max_tokens must be rejected (it belongs to the next tier).
    std_max = HORIZON_BUDGETS["standard"].max_tokens
    s = _set_horizon(dummy_supersession_sample(), "standard", std_max)
    err = _check_horizon_budget(s)
    assert err is not None
    assert "max_tokens" in err


def test_above_hard_max_rejected():
    hard_max = HORIZON_BUDGETS["hard"].max_tokens
    s = _set_horizon(dummy_supersession_sample(), "hard", hard_max + 5000)
    err = _check_horizon_budget(s)
    assert err is not None
    assert ">= max_tokens" in err


def test_unknown_horizon_label_rejected():
    s = _set_horizon(dummy_supersession_sample(), "extreme", 50000)
    err = _check_horizon_budget(s)
    assert err is not None
    assert "unknown horizon" in err


def test_gauntlet_includes_horizon_check():
    """A sample that would otherwise pass should be rejected by the
    gauntlet if its horizon budget is violated."""
    s = _set_horizon(dummy_supersession_sample(), "standard", 100)  # way too small
    err = _gauntlet_check(s)
    assert err is not None
    assert "horizon budget" in err


def test_horizon_budget_thresholds_are_contiguous():
    """The std max and hard min must be equal — no gap, no overlap.
    A sample at exactly that boundary is ``hard`` (max is exclusive on
    std, inclusive on hard)."""
    assert (
        HORIZON_BUDGETS["standard"].max_tokens == HORIZON_BUDGETS["hard"].min_tokens
    ), "std/hard budget bounds must be contiguous"
    assert (
        HORIZON_BUDGETS["compact"].max_tokens == HORIZON_BUDGETS["standard"].min_tokens
    ), "compact/std budget bounds must be contiguous"


# ---------------------------------------------------------------------------
# Integration: realized phase 2 data
# ---------------------------------------------------------------------------


def _approx_tokens(history) -> int:
    return sum(
        len(_TOK.findall(t.get("text", "") or ""))
        for sess in history
        for t in sess.get("turns") or []
    )


def _data_present() -> bool:
    return all(p.exists() for p in PHASE2_FILES)


@pytest.mark.skipif(not _data_present(), reason="phase 2 data files not present")
def test_phase2_samples_within_declared_horizon():
    """Every realized Phase 2 sample's history_token_count must lie
    inside its declared horizon's budget band."""
    bad: list[str] = []
    for path in PHASE2_FILES:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                s = json.loads(line)
                meta = s["_gold"]["metadata"]
                horizon = meta.get("horizon")
                if horizon is None:
                    continue
                budget = HORIZON_BUDGETS[horizon]
                n = meta.get("history_token_count")
                if n is None:
                    bad.append(f"{s['sample_id']}: missing history_token_count")
                    continue
                if not (budget.min_tokens <= n < budget.max_tokens):
                    bad.append(
                        f"{s['sample_id']}: declared={horizon} tokens={n} "
                        f"band=[{budget.min_tokens},{budget.max_tokens})"
                    )
    assert not bad, "\n  " + "\n  ".join(bad)


@pytest.mark.skipif(not _data_present(), reason="phase 2 data files not present")
def test_phase2_ambiguity_marking_consistent():
    """Samples flagged ambiguity_class=ambiguous_active_evidence must
    have a non-empty ambiguity_reason. Codex audit P0 fix.
    """
    from pipeline.schema import Sample

    bad: list[str] = []
    for path in PHASE2_FILES:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            # Pydantic-validate (catches schema-level ambiguity_class
            # values outside the AmbiguityClass Literal).
            Sample.model_validate(d)
            meta = d["_gold"]["metadata"]
            ac = meta.get("ambiguity_class")
            if ac and ac != "not_ambiguous" and not meta.get("ambiguity_reason"):
                bad.append(
                    f"{d['sample_id']}: ambiguity_class={ac!r} but "
                    "ambiguity_reason is empty"
                )
    assert not bad, "\n  " + "\n  ".join(bad)


@pytest.mark.skipif(not _data_present(), reason="phase 2 data files not present")
def test_phase2_history_token_count_matches_history():
    """Recorded history_token_count must agree with a fresh count from
    `history` to within ±5% (tokenizer drift) — large divergence means
    cleanup or repair didn't refresh metadata."""
    bad: list[str] = []
    for path in PHASE2_FILES:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                s = json.loads(line)
                meta = s["_gold"]["metadata"]
                recorded = meta.get("history_token_count")
                actual = _approx_tokens(s.get("history") or [])
                if recorded is None:
                    continue  # already covered by the band test
                if abs(recorded - actual) > max(50, 0.05 * actual):
                    bad.append(
                        f"{s['sample_id']}: recorded={recorded} actual={actual} "
                        f"(diff={recorded - actual})"
                    )
    assert not bad, "\n  " + "\n  ".join(bad)
