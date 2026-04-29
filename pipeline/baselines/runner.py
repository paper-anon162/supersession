"""Baseline runner skeleton (protocol §11, data_plan §11).

Defines the ``Baseline`` protocol every system implements, and a runner that
iterates samples through ``load_for_system`` (public-only) and records the
response plus a ``RunMetadata`` payload.

The runner is the single point through which every system, memory architecture
and intervention sees a sample. By construction it never hands gold-only
fields downstream — that contract is enforced via ``load_for_system``.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from pipeline.io import GOLD_KEY, load_for_system
from pipeline.schema import RunMetadata, Sample


class Baseline(Protocol):
    """Anything that takes a public sample view and returns a response."""

    name: str

    def respond(self, public_sample: dict[str, Any]) -> str: ...

    def run_metadata(self, sample_id: str, run_id: str) -> RunMetadata: ...


@dataclass
class RunResult:
    sample_id: str
    system_name: str
    run_id: str
    response: str
    elapsed_seconds: float
    run_metadata: RunMetadata
    error: str | None = None


class GoldLeakageInRunner(RuntimeError):
    """Raised if a baseline's input ever contains a gold-only key."""


def _assert_public_only(public_sample: dict[str, Any], sample_id: str) -> None:
    if GOLD_KEY in public_sample:
        raise GoldLeakageInRunner(
            f"runner attempted to feed _gold to system for {sample_id}"
        )


def run_baseline(
    baseline: Baseline,
    samples: Iterable[Sample],
    *,
    max_samples: int | None = None,
) -> list[RunResult]:
    """Run a single baseline over a sequence of samples.

    Each sample is fed to ``baseline.respond`` strictly through
    ``load_for_system``. Errors are captured per-sample so a single failure
    does not abort the run.
    """
    results: list[RunResult] = []
    for i, sample in enumerate(samples):
        if max_samples is not None and i >= max_samples:
            break
        public = load_for_system(sample)
        _assert_public_only(public, sample.sample_id)
        run_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        response = ""
        error: str | None = None
        try:
            response = baseline.respond(public)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
        elapsed = time.perf_counter() - t0
        meta = baseline.run_metadata(sample.sample_id, run_id)
        results.append(
            RunResult(
                sample_id=sample.sample_id,
                system_name=baseline.name,
                run_id=run_id,
                response=response,
                elapsed_seconds=elapsed,
                run_metadata=meta,
                error=error,
            )
        )
    return results


def _register_known_baselines() -> dict[str, type]:
    """Return the registry of known baseline classes by short name.

    This is a lightweight discovery hook for runner scripts that want to
    instantiate a baseline by name (``"graphiti"``,
    ``"naive_rag_local"``, ...). New baselines should be added here so
    they're listable without the runner script having to know each
    module path. Each entry is a class implementing the ``Baseline``
    Protocol (callers still wire backbone / config kwargs themselves).
    """
    from pipeline.baselines.extract_wrappers import (
        ActiveStateWrapperBaseline,
        RecencyWrapperBaseline,
    )
    from pipeline.baselines.graphiti_adapter import GraphitiBaseline
    from pipeline.baselines.long_context import LongContextBaseline
    from pipeline.baselines.naive_rag import NaiveRAGBaseline
    from pipeline.baselines.recency_rag import RecencyRAGBaseline

    return {
        "graphiti": GraphitiBaseline,
        "long_context": LongContextBaseline,
        "naive_rag": NaiveRAGBaseline,
        "recency_rag": RecencyRAGBaseline,
        "recency_wrapper": RecencyWrapperBaseline,
        "active_state_wrapper": ActiveStateWrapperBaseline,
    }


KNOWN_BASELINES = _register_known_baselines


__all__ = [
    "KNOWN_BASELINES",
    "Baseline",
    "GoldLeakageInRunner",
    "RunResult",
    "run_baseline",
]
