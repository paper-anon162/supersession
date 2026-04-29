"""Phase manifest — canonical sample-set selector (protocol §9.2.2).

A *manifest* is a git-tracked JSON file that lists which samples in
the pool (`data/pool/*.jsonl`, gitignored) are part of the current
phase's main evaluation set. The manifest is the single source of
truth for downstream evaluation; runners read sample IDs from the
manifest, not from raw pool files.

Why manifests:

- Realization is allowed to over-generate (e.g. produce 50
  implicit_drift samples when the §9.2.2 share asks for ~25). The
  manifest picks the canonical subset and leaves the rest as
  reserve.
- Audit / human review may flag a main-set sample as ambiguous after
  the fact. The manifest can then *swap* in a reserve sample of the
  same horizon × pattern signature without re-realizing data. The
  swap history is git-blame-able.
- Multiple manifests (main / ablation / cross-check) over the same
  pool support different analyses without duplicating data.

Layout::

    data/pool/                       # gitignored
        batch_A_full.jsonl
        batch_B_full.jsonl
        ...
    data/manifests/                  # git tracked
        phase2_v5_main.json
        phase2_v5_main_history.md

A manifest groups members by ``triple_id`` so the matched-triples
design (protocol §9.2.2) survives downstream — aggregators can run
paired bootstrap by triple.

The Pydantic schema is intentionally permissive on selection_rule
(string), so the file format stays simple while semantic checks live
in ``scripts/validate_manifest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from pydantic import BaseModel, ConfigDict, Field

from pipeline.schema.sample import Horizon


class ManifestMember(BaseModel):
    """One sample reference inside a manifest."""

    model_config = ConfigDict(extra="forbid")

    sample_id: str
    horizon: Horizon | None = None
    sample_content_hash: str | None = None  # set when manifest is built; lets
                                            # downstream verify the pool sample
                                            # hasn't drifted out from under us


class ManifestGroup(BaseModel):
    """A matched-triples (or doublet) group; members share a triple_id.

    Singletons are also represented as groups of one (with triple_id =
    sample_id) so all manifest selection logic operates uniformly on
    groups.
    """

    model_config = ConfigDict(extra="forbid")

    triple_id: str
    members: list[ManifestMember] = Field(default_factory=list)

    @property
    def horizons(self) -> set[Horizon]:
        return {m.horizon for m in self.members if m.horizon is not None}

    @property
    def is_complete_triple(self) -> bool:
        return self.horizons == {"compact", "standard", "hard"}

    @property
    def is_doublet(self) -> bool:
        return self.horizons in ({"standard", "hard"}, {"compact", "standard"}, {"compact", "hard"})


class Manifest(BaseModel):
    """A versioned sample-selection manifest for one phase / set."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    selection_rule: str
    notes: str | None = None
    groups: list[ManifestGroup] = Field(default_factory=list)

    @property
    def n_groups(self) -> int:
        return len(self.groups)

    @property
    def n_samples(self) -> int:
        return sum(len(g.members) for g in self.groups)

    def all_sample_ids(self) -> set[str]:
        return {m.sample_id for g in self.groups for m in g.members}

    def iter_members(self) -> Iterator[tuple[ManifestGroup, ManifestMember]]:
        for g in self.groups:
            for m in g.members:
                yield g, m


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_manifest(path: str | Path) -> Manifest:
    p = Path(path)
    return Manifest.model_validate_json(p.read_text())


def write_manifest(manifest: Manifest, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(manifest.model_dump_json(indent=2) + "\n")


# ---------------------------------------------------------------------------
# Selection / filtering
# ---------------------------------------------------------------------------


def select_by_manifest(samples: Iterable, manifest: Manifest) -> list:
    """Return the subset of ``samples`` whose sample_id is in ``manifest``.

    Order follows the manifest (group order, then member order). Samples
    in the iterable but not in the manifest are dropped. Manifest
    entries with no matching pool sample are silently skipped — call
    ``manifest_pool_diff`` for an audit report.
    """
    by_id: dict = {}
    for s in samples:
        sid = getattr(s, "sample_id", None) or s["sample_id"]
        by_id[sid] = s
    out = []
    for _, m in manifest.iter_members():
        if m.sample_id in by_id:
            out.append(by_id[m.sample_id])
    return out


def manifest_pool_diff(samples: Iterable, manifest: Manifest) -> dict[str, list[str]]:
    """Return ``{"missing_in_pool": [...], "extra_in_pool": [...]}``.

    - ``missing_in_pool``: sample_ids the manifest references that the
      pool doesn't contain.
    - ``extra_in_pool``: sample_ids in the pool but not in the manifest
      (i.e. reserve samples available for swap-in).
    """
    pool_ids = set()
    for s in samples:
        sid = getattr(s, "sample_id", None) or s["sample_id"]
        pool_ids.add(sid)
    manifest_ids = manifest.all_sample_ids()
    return {
        "missing_in_pool": sorted(manifest_ids - pool_ids),
        "extra_in_pool": sorted(pool_ids - manifest_ids),
    }


__all__ = [
    "Manifest",
    "ManifestGroup",
    "ManifestMember",
    "load_manifest",
    "manifest_pool_diff",
    "select_by_manifest",
    "write_manifest",
]
