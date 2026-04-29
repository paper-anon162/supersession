"""Topic-group balance tracking for Phase 3 (protocol §10.5).

Phase 3 replaces strict per-domain quotas with a coarse 4-bucket
topic balance. Existing samples carry a free-text ``domain`` field;
this module maps that to the 4 canonical topic groups and provides
helpers for runtime balance tracking during direct-manifest
construction.

Topic groups:

  - daily_preference:      food / travel / entertainment / shopping /
                           hobbies / home / pet care / lifestyle /
                           fitness
  - work_tooling:          software tools / work workflow / project
                           workflow / note-taking / productivity /
                           tech_workflow / work_communication
  - learning_routine:      learning / fitness routine / scheduling /
                           recurring habits / management cadence
  - communication_boundary: tone / discussion boundary / message
                           style / interpersonal phrasing

Constraints (per protocol §10.5):
  - no single topic_group accounts for >50% of any
    failure_pattern × horizon cell
  - drift samples not all sourced from work_tooling
  - hard horizon not concentrated in one topic_group
"""

from __future__ import annotations

import warnings
from collections import Counter, defaultdict
from typing import Iterable

from pipeline.schema import FailurePattern, Horizon, Sample, TopicGroup

# Track unknown domains we've already warned about so we warn once per domain
# per process — avoids flooding a 350-group realize run.
_WARNED_UNKNOWN_DOMAINS: set[str] = set()

# Mapping from free-text domain → coarse topic_group.
#
# Phase 2 samples don't carry a topic_group; we backfill from domain
# at audit / manifest time. Domains not in the table fall back to
# "daily_preference" (the catch-all bucket) and a warning is emitted.
_DOMAIN_TO_GROUP: dict[str, TopicGroup] = {
    # daily_preference
    "food": "daily_preference",
    "food_dining": "daily_preference",
    "travel": "daily_preference",
    "leisure": "daily_preference",
    "lifestyle": "daily_preference",
    "fitness": "daily_preference",
    "creative": "daily_preference",
    "shopping": "daily_preference",
    "hobbies": "daily_preference",
    "home": "daily_preference",
    "pet_care": "daily_preference",
    "family": "daily_preference",
    "health": "daily_preference",
    "finance": "daily_preference",
    "hobby": "daily_preference",
    "media": "daily_preference",
    "community": "daily_preference",
    "relationships": "daily_preference",
    "career": "work_tooling",
    # work_tooling
    "tech_workflow": "work_tooling",
    "work": "work_tooling",
    "work_workflow": "work_tooling",
    "work_style": "work_tooling",
    "productivity": "work_tooling",
    "business": "work_tooling",
    "writing": "work_tooling",
    "writing_style": "work_tooling",
    # learning_routine
    "learning": "learning_routine",
    "management": "learning_routine",
    # communication_boundary
    "work_communication": "communication_boundary",
}


def domain_to_topic_group(domain: str | None) -> TopicGroup:
    """Map a free-text domain to a TopicGroup. Falls back to
    ``daily_preference`` for unknown domains, with a one-time warning per
    domain so authoring typos surface instead of being silently absorbed."""
    if not domain:
        return "daily_preference"
    if domain not in _DOMAIN_TO_GROUP:
        if domain not in _WARNED_UNKNOWN_DOMAINS:
            _WARNED_UNKNOWN_DOMAINS.add(domain)
            warnings.warn(
                f"unknown domain {domain!r} mapped to 'daily_preference' "
                f"fallback; add it to _DOMAIN_TO_GROUP if intentional, fix "
                f"the typo otherwise (this warning fires once per domain)",
                stacklevel=2,
            )
        return "daily_preference"
    return _DOMAIN_TO_GROUP[domain]


def annotate_sample_topic_group(sample: Sample) -> None:
    """Populate ``sample.gold.metadata.topic_group`` from
    ``sample.gold.metadata.domain`` if not already set. In-place."""
    md = sample.gold.metadata
    if md.topic_group is None:
        md.topic_group = domain_to_topic_group(md.domain)


# ---------------------------------------------------------------------------
# Balance tracker (used by realize_phase3 driver)
# ---------------------------------------------------------------------------


class TopicBalanceTracker:
    """Live counter of accepted samples per (topic_group,
    failure_pattern, horizon) cell. Used by the Phase 3 driver to
    enforce §10.5 constraints when picking the next candidate to
    generate.

    Counts only samples added via ``record()``. Samples loaded from
    cache need to be replayed through this for the tracker to be
    accurate.
    """

    def __init__(self) -> None:
        self._counts: dict[
            tuple[TopicGroup, FailurePattern, Horizon], int
        ] = defaultdict(int)
        self._totals: Counter = Counter()

    def record(
        self,
        *,
        topic_group: TopicGroup,
        failure_pattern: FailurePattern,
        horizon: Horizon,
    ) -> None:
        self._counts[(topic_group, failure_pattern, horizon)] += 1
        self._totals[topic_group] += 1

    def cell_count(
        self,
        *,
        topic_group: TopicGroup,
        failure_pattern: FailurePattern,
        horizon: Horizon,
    ) -> int:
        return self._counts[(topic_group, failure_pattern, horizon)]

    def cell_share(
        self,
        *,
        topic_group: TopicGroup,
        failure_pattern: FailurePattern,
        horizon: Horizon,
    ) -> float:
        """Share of (failure_pattern × horizon) cell occupied by
        topic_group. Returns 0.0 when the cell is empty."""
        cell_total = sum(
            self._counts[(g, failure_pattern, horizon)]
            for g in ("daily_preference", "work_tooling", "learning_routine", "communication_boundary")
        )
        if cell_total == 0:
            return 0.0
        return self._counts[(topic_group, failure_pattern, horizon)] / cell_total

    def would_break_50pct_cell_cap(
        self,
        *,
        topic_group: TopicGroup,
        failure_pattern: FailurePattern,
        horizon: Horizon,
        cell_target_total: int,
    ) -> bool:
        """True if accepting one more sample for this cell would
        push topic_group over the 50% per-cell cap, given the
        cell's final target total."""
        if cell_target_total <= 0:
            return False
        new_count = self._counts[(topic_group, failure_pattern, horizon)] + 1
        return new_count / cell_target_total > 0.5

    def summary(self) -> dict:
        """Per-topic-group totals and per-cell breakdown for reporting."""
        return {
            "totals": dict(self._totals),
            "cells": {
                f"{g}|{p}|{h}": n
                for (g, p, h), n in self._counts.items()
                if n > 0
            },
        }

    def replay(self, samples: Iterable[Sample]) -> None:
        """Re-record from a batch of accepted samples (e.g. when
        loading from cache at startup)."""
        for s in samples:
            md = s.gold.metadata
            tg = md.topic_group or domain_to_topic_group(md.domain)
            fps = md.failure_patterns or []
            # Phase 3 always tags exactly one primary failure_pattern;
            # Phase 2 samples may have multiple — use the first.
            if not fps:
                continue
            primary = fps[0]
            horizon = md.horizon or "standard"
            self.record(
                topic_group=tg,
                failure_pattern=primary,
                horizon=horizon,
            )


__all__ = [
    "TopicBalanceTracker",
    "annotate_sample_topic_group",
    "domain_to_topic_group",
]
