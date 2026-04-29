import numpy as np

from pipeline.stats import bootstrap_mean, paired_bootstrap_diff


def test_bootstrap_mean_recovers_value():
    rng = np.random.default_rng(42)
    values = np.ones(200) * 0.7
    result = bootstrap_mean(values, rng=rng, n_resamples=2000)
    assert abs(result.mean - 0.7) < 1e-9
    assert abs(result.ci_low - 0.7) < 1e-9
    assert abs(result.ci_high - 0.7) < 1e-9
    # CI = [0.7, 0.7] sits entirely above 0, so excludes_zero is True.
    assert result.excludes_zero()


def test_bootstrap_mean_ci_width_shrinks_with_n():
    rng = np.random.default_rng(0)
    small = bootstrap_mean(rng.binomial(1, 0.6, size=30), rng=rng, n_resamples=2000)
    rng2 = np.random.default_rng(0)
    large = bootstrap_mean(rng2.binomial(1, 0.6, size=600), rng=rng2, n_resamples=2000)
    assert large.ci_width < small.ci_width


def test_paired_bootstrap_excludes_zero_when_clear_diff():
    rng = np.random.default_rng(7)
    pairs = {
        f"s-{i}": (0.9, 0.5) for i in range(50)  # always +0.4
    }
    result = paired_bootstrap_diff(pairs, rng=rng, n_resamples=2000)
    assert abs(result.mean - 0.4) < 1e-9
    assert result.excludes_zero()


def test_paired_bootstrap_includes_zero_when_no_diff():
    rng = np.random.default_rng(7)
    pairs = {f"s-{i}": (0.5, 0.5) for i in range(50)}
    result = paired_bootstrap_diff(pairs, rng=rng, n_resamples=2000)
    assert result.mean == 0
    assert not result.excludes_zero()


def test_paired_bootstrap_skips_none():
    pairs = {
        "s-1": (0.7, 0.5),
        "s-2": (None, 0.5),
        "s-3": (0.7, None),
    }
    result = paired_bootstrap_diff(pairs, n_resamples=500)
    assert result.n == 1
