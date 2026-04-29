"""Public / gold separation (data_plan §2.1, protocol §2.3, §5.2).

Three loaders:

- ``load_for_system``      : public-only view; what every tested system,
                             memory architecture, and intervention sees.
- ``load_for_judge``        : full view including `_gold`. Used by the LLM judge
                             and by gold-aware analysis.
- ``load_for_diagnostic``   : same as judge view; but the call site is
                             discriminated for audit logging.

The public view is constructed by *building a fresh dict from the public
fields*, never by popping `_gold` from a copy. This makes accidental leakage
impossible at the source.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pipeline.schema import Sample

# Behavioral-system inputs — what a baseline / memory system / wrapper sees.
# `recall_query` is deliberately EXCLUDED here: that field exists only for the
# dedicated recall-session diagnostic (data_plan §7) and would otherwise leak
# the active target through a "list all versions you recall" cue.
PUBLIC_FIELDS_BEHAVIOR = (
    "sample_id",
    "history",
    "current_query",
    "sample_type",
)

# Recall-session inputs — used only by `scripts/run_recall_query_session.py`
# and any other diagnostic that explicitly elicits version recall. Adds
# `recall_query` so the diagnostic loader can substitute it in for current_query.
PUBLIC_FIELDS_RECALL = PUBLIC_FIELDS_BEHAVIOR + ("recall_query",)

# Backwards-compatible alias used by older code paths and the validity gauntlet
# leakage filter, which scans the largest public surface.
PUBLIC_FIELDS = PUBLIC_FIELDS_RECALL

GOLD_KEY = "_gold"


class GoldLeakageError(RuntimeError):
    """Raised when gold-only content is detected in a system-bound payload."""


def _public_view(sample: Sample, fields: tuple[str, ...]) -> dict[str, Any]:
    raw = sample.model_dump(by_alias=True)
    out: dict[str, Any] = {}
    for f in fields:
        if f in raw:
            out[f] = raw[f]
    # Defense in depth: refuse to emit anything if `_gold` somehow shows up.
    if GOLD_KEY in out:
        raise GoldLeakageError(
            f"_gold present in public view for sample {sample.sample_id}"
        )
    return out


def load_for_system(sample: Sample) -> dict[str, Any]:
    """View handed to baselines, memory systems, and the intervention wrapper.

    Behavioral input only — does NOT include ``recall_query`` (per audit P0
    §"recall_query leaks into behavioral system input"). Use
    ``load_for_recall_session`` for the recall-only diagnostic.
    """
    return _public_view(sample, PUBLIC_FIELDS_BEHAVIOR)


def load_for_recall_session(sample: Sample) -> dict[str, Any]:
    """View for the dedicated recall-session diagnostic.

    Returns the behavioral view plus ``recall_query``. Recall sessions
    typically substitute ``recall_query`` into the ``current_query`` slot
    before passing the dict to a baseline.
    """
    return _public_view(sample, PUBLIC_FIELDS_RECALL)


def load_for_judge(sample: Sample) -> dict[str, Any]:
    """View for the LLM judge. Full sample including ``_gold``."""
    return sample.model_dump(by_alias=True)


def load_for_diagnostic(sample: Sample) -> dict[str, Any]:
    """View for diagnostic analysis (recall-only, oracle injection, etc.).

    Behaviorally equivalent to ``load_for_judge`` today, but the call site is
    distinct so audit logs can attribute oracle / recall reads separately from
    judge reads.
    """
    return sample.model_dump(by_alias=True)


# ---------------------------------------------------------------------------
# File-level loaders
# ---------------------------------------------------------------------------


def iter_samples_from_jsonl(path: str | Path) -> Iterator[Sample]:
    p = Path(path)
    with p.open() as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield Sample.model_validate_json(line)
            except Exception as e:  # pragma: no cover - exercised in tests
                raise ValueError(
                    f"failed to parse sample at {p}:{line_no}: {e}"
                ) from e


def write_samples_jsonl(samples: Iterable[Sample], path: str | Path) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w") as f:
        for s in samples:
            f.write(s.model_dump_json(by_alias=True) + "\n")
            n += 1
    return n


def write_public_jsonl(samples: Iterable[Sample], path: str | Path) -> int:
    """Write the public release file; emits only public fields per sample."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w") as f:
        for s in samples:
            f.write(json.dumps(_public_view(s, PUBLIC_FIELDS), ensure_ascii=False) + "\n")
            n += 1
    return n


def write_gold_jsonl(samples: Iterable[Sample], path: str | Path) -> int:
    """Write the companion gold file, aligned by ``sample_id``."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w") as f:
        for s in samples:
            entry = {
                "sample_id": s.sample_id,
                GOLD_KEY: s.gold.model_dump(),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            n += 1
    return n


__all__ = [
    "GOLD_KEY",
    "GoldLeakageError",
    "PUBLIC_FIELDS",
    "iter_samples_from_jsonl",
    "load_for_diagnostic",
    "load_for_judge",
    "load_for_system",
    "write_gold_jsonl",
    "write_public_jsonl",
    "write_samples_jsonl",
]
