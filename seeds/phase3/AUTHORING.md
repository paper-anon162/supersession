# Phase 3 spine authoring guide

This file documents how to author SkeletonAwareSpine + Phase3GroupSpec
entries that pass the cluster A–J gates and land in the canonical
Phase 3 manifest. Read this before adding new spines to a phase 3
batch under `seeds/phase3/`.

The protocol §10 spec is canonical; this guide is a translation into
operational rules that authors can apply directly.

---

## 1. Pick the failure_pattern + group_type

| failure_pattern | group_type | n versions | implicit_drift_type |
|---|---|---|---|
| `explicit_replacement` | `triple` | 2 | None |
| `narrowing` | `triple` | ≥3 (explicit transitions) | None |
| `multi_version` (simple) | `triple` | 2–3 | None |
| `multi_version` (complex 4+) | `doublet` (std+hard) | 4+ | None |
| `implicit_drift` (repeated_use) | `triple` | 2 | `repeated_use` |
| `implicit_drift` (abandonment) | `triple` | 2 | `abandonment` |
| `implicit_drift` (gradual_narrowing) | `triple` | 2 inferred-active (no explicit version transitions) | `gradual_narrowing` |

**The hardest distinction:** `narrowing` (pattern) vs
`gradual_narrowing` (drift type).

- `narrowing`: ≥3 versions, **explicitly announced** by the user
  ("New rule: only X", "Tightening: also no Y"). Authoring style
  matches Phase 2's `seeds/phase2/_batch_h_compact.py` narrow seeds.
- `gradual_narrowing`: 2 versions, **only inferred** from cumulative
  user behavior across sessions. No explicit replacement or
  narrowing announcement. The active state must be discoverable from
  ≥2 independent post-old-state evidence items.

If you're tempted to put a "the user gradually narrowed from X to Y
with explicit comments" sample, that's `narrowing` (pattern), not
`gradual_narrowing`.

---

## 2. Write the SkeletonAwareSpine

Required fields:

```python
SkeletonAwareSpine(
    sample_id="p3-{pattern_short}-{topic}-{nnn}",
    sample_type="supersession",
    target_type=...,            # one of object_preference / interpersonal_boundary / conceptual_stance / procedural_constraint
    domain=...,                 # free-text; will be mapped to topic_group automatically
    target_description=(
        "user's drifted/narrowed/explicit ... — short, slot-shaped"
    ),
    target_slot_id="<slot>::v1",
    topic="<short canonical topic>",
    versions=[
        VersionSpec(value="<v1 outdated value>",
                    polarity="prefer" or "constraint",
                    session_introduced=1),
        VersionSpec(value="<v2 active value>",
                    polarity=...,
                    session_introduced=2),
        # narrowing: add v3 (and v4 for 4+-version doublet multi_version)
    ],
    current_query="<short user-side query that requires picking v_active>",
    required_behavior="<single sentence describing the behavior an ideal model produces>",
    invalid_behavior=[
        "<bullet 1: a behavior that violates v_active or revives v_outdated>",
        "<bullet 2>",
        "<bullet 3>",
    ],
    n_sessions=5,                # placeholder; horizon-overridden by group orchestrator
    subtype="strong",            # strong / multi_step / reverted (multi_version only)
    horizon="standard",          # placeholder; group orchestrator overrides per horizon
    failure_patterns=["implicit_drift"],   # exactly one for the primary pattern
    triple_id="<group id, defaults to sample_id>",
)
```

The `sample_id` is a **stem**; the group orchestrator suffixes
`-compact` / `-standard` / `-hard` automatically. Don't include the
horizon in your authored sample_id.

### Active value format rules (cluster E avoidance)

The realizer splits the active value on `, ; — - and with plus` and
requires every **non-negation chunk** to surface in the realized
dialogue. Therefore:

- Keep the active value short and concrete. "Obsidian vault with
  daily-notes plugin and wiki-style backlinks" is fine (3 chunks,
  each surfaceable).
- Avoid over-stuffed values. "ESG-rated large-cap dividend-yielding
  consumer-staples equities only (market cap above $10B excluding
  utilities)" is too many chunks; either drop attributes or split
  the spine into multiple narrower spines.
- Avoid negation-only chunks. "no diagrams, no tables, no charts" is
  three negations; the cluster E gate skips them but you still need
  ≥1 positive chunk. Format as "text only — no diagrams, no tables,
  no charts" to give cluster E a positive anchor.

### implicit_drift active value rules (cluster G/H avoidance)

For `implicit_drift`, the realizer's active session **must not**
contain explicit-change phrasing in user turns:

- forbidden: "the old X", "now I just X", "I VERB now", "from now
  on", "I switched to", "cutting X out entirely", "stick to Y only"
- forbidden: any sentence that announces v_outdated as retired

Instead, evidence the active state by:

- **repeated_use**: user describes themselves doing the new state
  ("the matcha I whisked", "my Wednesday evening grocery run", "the
  daily-notes entry I made")
- **abandonment**: user references the old state only as inactive
  ("the laptop I keep in the living room now, not the bedroom",
  "the Friday window we no longer hold")
- **gradual_narrowing**: user expresses cumulative constraints
  ("salads have been better without dairy lately... I noticed
  gluten too... mostly leafy greens these days")

The cluster G regex catches the most common explicit-change
phrasings. If the realizer fails 5 retries, the spine is rejected.
Rewrite the `target_description` to be more behaviorally grounded if
this happens repeatedly.

---

## 3. Wrap in Phase3GroupSpec

```python
Phase3GroupSpec(
    spine=<SkeletonAwareSpine above>,
    group_type="triple" or "doublet",
    horizons=["compact", "standard", "hard"]  # triple
       or ["standard", "hard"],               # doublet
    implicit_drift_type=<ImplicitDriftType or None>,
    spine_source="hand",  # or "llm-generated" when an LLM authored
                          # the spine; tracked in cache for audit
)
```

---

## 4. Self-checklist before committing a new spine

1. **Pattern + drift_type alignment**
   - Is `failure_patterns` exactly one of the 4 canonical patterns?
   - If `implicit_drift`, is `implicit_drift_type` set on the
     Phase3GroupSpec (not on the spine itself)?
   - If `narrowing` (pattern), do you have ≥3 explicit version
     transitions in the dialogue plan?
   - If `gradual_narrowing` (drift_type), can a reader infer the
     active state from ≥2 independent post-old-state evidence items
     **without** any explicit narrowing announcement?

2. **target_slot_id consistency**
   - All versions sit on the same target slot.
   - The current_query forces a behavioral choice between v_outdated
     and v_active on this slot.
   - The query does not name v_active or v_outdated by content
     (cluster A/leakage check fires otherwise).

3. **Active value chunkability (cluster E)**
   - Split your active value on `, ; — and with plus`.
   - Each non-negation chunk is a single concrete attribute that
     can plausibly surface in user dialogue.
   - At least one chunk is non-negation.

4. **Implicit drift form (cluster G/H, J)**
   - The `target_description` is behavior-grounded, not preference-
     stated.
   - The `required_behavior` and `invalid_behavior` describe what
     the model should produce, not what the user announced.
   - For drift, the `current_query` is tangential to the drift
     event itself (e.g. asks about logistics around the new state,
     not "what's my current preference").

5. **Topic balance**
   - Pick a domain that maps to the topic_group you want (see
     `pipeline/construction/topic_groups.py:_DOMAIN_TO_GROUP`).
   - Don't put all your drift spines in `work_tooling`; rotate
     across the 4 topic groups.
   - Sensitive topics (medical, identity, intimate, political,
     addiction, legal trouble, trauma) are off-limits as core
     supersession targets per §10.5.

6. **invalid_behavior triple**
   - 3+ bullets, each describing a distinct way the model could
     wrongly honor v_outdated or fail to honor v_active.
   - First bullet typically: "follow the v_outdated value verbatim".
   - Second bullet: "mix v_outdated and v_active".
   - Third+: pattern-specific (e.g. "pick a different alternative
     not in the version chain").

---

## 5. Common authoring failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Cluster A fires (≥50% active stems missing in history) | active value has fancy words the user never says | Use plainer active-value vocabulary, or extend the dialogue plan to surface the fancy words |
| Cluster E fires (chunk has zero history overlap) | one of the active value's connector-split chunks is over-specified | Drop the over-specified chunk, or move it to a parenthetical |
| Cluster G fires (explicit-leakage in drift active session) | realizer produced "the old X" / "now I just" / etc. | Tighten target_description to be behaviorally-grounded; retry; if still failing, the active value may be too easy to express explicitly |
| Cluster H fires (drift v2-distinguishing chunk absent from user turns) | realizer assistant turn names v_active but user turn doesn't | Make the active value more user-natural; or add a sentence to invalid_behavior nudging the user to say it |
| Cluster J fires (active_evidence <2 valid items) | extractor couldn't find 2 verbatim spans in post-outdated sessions that match drift_type | The realized dialogue is too thin for evidence extraction; rewrite the spine to plant 2-3 evidence anchors in the active session and ≥1 follow-up |
| Splice error: "cannot fit N events in M sessions" | compact + few distractors + ≥2 events with default gap rules | Already auto-relaxes per §10.1 P2.0 fix; if still failing, the spine genuinely can't fit compact and should be a doublet |

---

## 6. Smoke test before scaling a batch

Once you've authored 3–5 new spines in a batch module, run:

```bash
AWS_PROFILE=ahe-long uv run python scripts/realize_phase3.py \\
    --batch <your_batch_name> --workers 4 --limit 5
```

Confirm acceptance rate ≥80% on the smoke; if it's below, the
authoring needs rework before scaling. Cluster J failures most
commonly stem from too-thin dialogue plans; cluster A/E failures
from over-specified gold values.
