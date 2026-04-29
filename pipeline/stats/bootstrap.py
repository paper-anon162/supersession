"""Bootstrap CI utilities (protocol §14.1, data_plan §10.1).

Two primitives:

  - ``bootstrap_mean``        : single-sample mean + CI.
  - ``paired_bootstrap_diff`` : paired difference (e.g. Recall − VF) using
                                ``sample_id`` as the resampling unit.

Defaults match the protocol: 10,000 resamples, 95% CI, sample-level
resampling unit. For deterministic test runs, supply ``rng`` (a seeded
``numpy.random.Generator``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_N_RESAMPLES = 10_000
DEFAULT_CI = 0.95


@dataclass
class BootstrapResult:
    mean: float
    ci_low: float
    ci_high: float
    n: int
    n_resamples: int

    @property
    def ci_width(self) -> float:
        return self.ci_high - self.ci_low

    def excludes_zero(self) -> bool:
        return self.ci_low > 0 or self.ci_high < 0


def bootstrap_mean(
    values: list[float] | np.ndarray,
    *,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    ci: float = DEFAULT_CI,
    rng: np.random.Generator | None = None,
) -> BootstrapResult:
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n == 0:
        return BootstrapResult(
            mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            n=0, n_resamples=n_resamples,
        )
    rng = rng or np.random.default_rng()
    idx = rng.integers(0, n, size=(n_resamples, n))
    resampled_means = arr[idx].mean(axis=1)
    alpha = (1 - ci) / 2
    lo, hi = np.quantile(resampled_means, [alpha, 1 - alpha])
    return BootstrapResult(
        mean=float(arr.mean()),
        ci_low=float(lo),
        ci_high=float(hi),
        n=n,
        n_resamples=n_resamples,
    )


def paired_bootstrap_diff(
    pairs: dict[str, tuple[float | None, float | None]],
    *,
    n_resamples: int = DEFAULT_N_RESAMPLES,
    ci: float = DEFAULT_CI,
    rng: np.random.Generator | None = None,
) -> BootstrapResult:
    """Bootstrap the mean of (x - y) where (x, y) are paired by ``sample_id``.

    ``pairs`` is keyed by sample_id and maps to ``(x, y)``. Pairs with either
    value None are dropped. Resampling is at the sample_id level (paired).
    """
    diffs: list[float] = []
    for x, y in pairs.values():
        if x is None or y is None:
            continue
        diffs.append(float(x) - float(y))
    arr = np.asarray(diffs, dtype=float)
    n = len(arr)
    if n == 0:
        return BootstrapResult(
            mean=float("nan"), ci_low=float("nan"), ci_high=float("nan"),
            n=0, n_resamples=n_resamples,
        )
    rng = rng or np.random.default_rng()
    idx = rng.integers(0, n, size=(n_resamples, n))
    resampled = arr[idx].mean(axis=1)
    alpha = (1 - ci) / 2
    lo, hi = np.quantile(resampled, [alpha, 1 - alpha])
    return BootstrapResult(
        mean=float(arr.mean()),
        ci_low=float(lo),
        ci_high=float(hi),
        n=n,
        n_resamples=n_resamples,
    )


__all__ = [
    "BootstrapResult",
    "DEFAULT_CI",
    "DEFAULT_N_RESAMPLES",
    "bootstrap_mean",
    "paired_bootstrap_diff",
]
