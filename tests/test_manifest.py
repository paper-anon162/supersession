"""Tests for pipeline.manifest."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.manifest import (
    Manifest,
    ManifestGroup,
    ManifestMember,
    load_manifest,
    manifest_pool_diff,
    select_by_manifest,
    write_manifest,
)


def _example_manifest() -> Manifest:
    return Manifest(
        name="phase2_v5_main",
        version="1",
        selection_rule="stratified + matched_triples_where_feasible",
        groups=[
            ManifestGroup(
                triple_id="drift-comm",
                members=[
                    ManifestMember(sample_id="drift-comm-compact", horizon="compact"),
                    ManifestMember(sample_id="drift-comm-standard", horizon="standard"),
                    ManifestMember(sample_id="drift-comm-hard", horizon="hard"),
                ],
            ),
            ManifestGroup(
                triple_id="multi-deploy",
                members=[
                    ManifestMember(sample_id="multi-deploy-standard", horizon="standard"),
                    ManifestMember(sample_id="multi-deploy-hard", horizon="hard"),
                ],
            ),
        ],
    )


def test_manifest_basic_properties():
    m = _example_manifest()
    assert m.n_groups == 2
    assert m.n_samples == 5
    assert m.all_sample_ids() == {
        "drift-comm-compact", "drift-comm-standard", "drift-comm-hard",
        "multi-deploy-standard", "multi-deploy-hard",
    }


def test_manifest_group_completeness():
    m = _example_manifest()
    assert m.groups[0].is_complete_triple
    assert not m.groups[0].is_doublet
    assert not m.groups[1].is_complete_triple
    assert m.groups[1].is_doublet


def test_manifest_extra_field_rejected():
    """Pydantic extra=forbid catches typos."""
    with pytest.raises(ValidationError):
        Manifest.model_validate({
            "name": "x", "version": "1", "selection_rule": "y",
            "groupz": [],   # typo
        })


def test_manifest_round_trip(tmp_path: Path):
    m = _example_manifest()
    p = tmp_path / "manifest.json"
    write_manifest(m, p)
    loaded = load_manifest(p)
    assert loaded == m


def test_select_by_manifest_filters_pool():
    pool = [
        {"sample_id": "drift-comm-compact"},
        {"sample_id": "drift-comm-standard"},
        {"sample_id": "drift-comm-hard"},
        {"sample_id": "drift-comm-extra"},          # in pool, not in manifest
        {"sample_id": "multi-deploy-standard"},
        {"sample_id": "multi-deploy-hard"},
        {"sample_id": "different-spine-001"},       # reserve
    ]
    selected = select_by_manifest(pool, _example_manifest())
    ids = [s["sample_id"] for s in selected]
    # Manifest order is preserved (group, then member)
    assert ids == [
        "drift-comm-compact", "drift-comm-standard", "drift-comm-hard",
        "multi-deploy-standard", "multi-deploy-hard",
    ]


def test_select_by_manifest_skips_missing_silently():
    """If the pool is missing a manifest entry, select_by_manifest
    drops it (caller uses manifest_pool_diff to audit)."""
    pool = [{"sample_id": "drift-comm-standard"}]
    selected = select_by_manifest(pool, _example_manifest())
    assert [s["sample_id"] for s in selected] == ["drift-comm-standard"]


def test_manifest_pool_diff():
    pool = [
        {"sample_id": "drift-comm-compact"},
        {"sample_id": "drift-comm-standard"},
        {"sample_id": "extra-001"},                 # reserve
        {"sample_id": "extra-002"},                 # reserve
    ]
    diff = manifest_pool_diff(pool, _example_manifest())
    assert "drift-comm-hard" in diff["missing_in_pool"]
    assert "multi-deploy-standard" in diff["missing_in_pool"]
    assert "extra-001" in diff["extra_in_pool"]
    assert "extra-002" in diff["extra_in_pool"]
