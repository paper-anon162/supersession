"""Tiny helpers shared by CLI runner scripts (not part of the public API).

The point of this module is twofold:

1. Force line-buffered stdout regardless of whether the script's
   stdout is a TTY, a file, or a pipe (e.g. ``tee``). Without this,
   Python's default block-buffering hides progress for tens of minutes
   when a long-running script is piped through ``tee``.

2. Print an ETA banner at script start so a long run announces its
   expected duration up front. The banner takes a per-system rate
   estimate and a sample count.

Usage:

    from pipeline._runner_utils import enable_live_stdout, print_eta_banner

    def main():
        enable_live_stdout()
        print_eta_banner(
            label="Sonnet 4.6 long-context baseline",
            n_units=len(samples),
            seconds_per_unit=4.0,
            unit="sample",
        )
        ...
"""

from __future__ import annotations

import datetime as _dt
import os
import sys


def enable_live_stdout() -> None:
    """Force line-buffered stdout/stderr so progress prints stream live.

    Equivalent to running with ``python -u`` or ``PYTHONUNBUFFERED=1``
    but doesn't require the user to remember either.
    """
    # ``reconfigure`` was added in Python 3.7.
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        # Fall back to flushing manually — script-side `print(..., flush=True)`
        # remains an option.
        pass
    try:
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    # Belt-and-suspenders for environments that re-wrap stdout.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f}min"
    return f"{seconds/3600:.1f}hr"


def print_eta_banner(
    *,
    label: str,
    n_units: int,
    seconds_per_unit: float,
    unit: str = "unit",
) -> None:
    """Announce an estimated runtime at script start.

    Output is one or two lines, line-flushed. It also prints the
    expected wall-clock finish time so the user can decide whether to
    leave the process running.
    """
    total_seconds = max(0.0, n_units * seconds_per_unit)
    eta = _dt.datetime.now() + _dt.timedelta(seconds=total_seconds)
    rate = 1.0 / seconds_per_unit if seconds_per_unit > 0 else float("inf")
    print(
        f"[{label}] {n_units} {unit}s × ~{seconds_per_unit:.1f}s "
        f"= ~{_format_seconds(total_seconds)} "
        f"(rate ~{rate:.2f}/s, eta ~{eta.strftime('%H:%M')})",
        flush=True,
    )


def progress_bar(
    *,
    i: int,
    total: int,
    elapsed_seconds: float,
    label: str = "",
) -> str:
    """Return a one-line progress string with rate and remaining-time ETA.

    Use as ``print(progress_bar(...), flush=True)`` from inside loops
    that already have their own per-item output cadence.
    """
    if i == 0 or elapsed_seconds <= 0:
        return f"  [{i}/{total}] {label}".rstrip()
    rate = i / elapsed_seconds
    remaining = (total - i) / rate if rate > 0 else 0
    return (
        f"  [{i}/{total}] {label} elapsed={elapsed_seconds:.0f}s "
        f"rate={rate:.2f}/s eta={_format_seconds(remaining)}"
    ).rstrip()


__all__ = [
    "_format_seconds",
    "enable_live_stdout",
    "print_eta_banner",
    "progress_bar",
]
