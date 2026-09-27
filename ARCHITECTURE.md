# Architecture & Data Contracts

This document defines the **exact** data shape that passes between tiers. If you're building
a tier, your output MUST match the schema below so the next tier can consume it without
anyone needing to read your internal code.

---

## Tier 1 → Tier 2 Contract

**Tier 1 outputs** a cleaned, standardized record per material item:

```json
{
  "item_id": "string (unique, source-prefixed, e.g. ONGC-00123)",
  "source_cpse": "string (e.g. ONGC, SAIL, CoalIndia)",
  "raw_description": "string (original, unmodified)",
  "clean_description": "string (standardized casing, expanded abbreviations)",
  "specs": {
    "size": "string or null",
    "material_grade": "string or null",
    "pressure_rating": "string or null",
    "other_attrs": "object (key-value, flexible)"
  },
  "unit_of_measure": "string (standardized, e.g. EA, MTR, KG)",
  "category_hint": "string or null (raw category/group field if present in source)"
}
```

Output as a JSON Lines file or a pandas DataFrame saved to `data/processed/`.

---

## Tier 2 → Tier 3 / Tier 4 Contract

**Tier 2 outputs** a match record per candidate pair:

```json
{
  "match_id": "string (unique)",
  "item_a": "item_id from Tier 1 output",
  "item_b": "item_id from Tier 1 output",
  "confidence_score": "float 0-1",
  "score_breakdown": {
    "text_similarity": "float 0-1 (weight 0.5)",
    "spec_match": "float 0-1 (weight 0.3)",
    "unit_compatibility": "float 0-1 (weight 0.2)"
  },
  "status": "string — 'auto_linked' if confidence >= 0.85, else 'needs_review'"
}
```

- `confidence_score = 0.5*text_similarity + 0.3*spec_match + 0.2*unit_compatibility`
- Threshold for auto-link: **0.85** (keep consistent across all slides/docs — see note below)

---

## Tier 3 → Tier 4 Contract

**Tier 3 outputs** a decision record after human review:

```json
{
  "match_id": "string (same as Tier 2 match_id)",
  "reviewer_decision": "string — 'approved' | 'rejected'",
  "reviewer_id": "string",
  "reviewed_at": "ISO 8601 timestamp",
  "notes": "string or null"
}
```

Posted to Tier 4's API endpoint: `POST /api/review-decision`

---

## Tier 4 → Tier 5 Contract

**Tier 4 outputs** the final CNMC record, queryable by Tier 5:

```json
{
  "cnmc_code": "string (new common national code)",
  "canonical_description": "string",
  "mapped_source_codes": [
    {"cpse": "ONGC", "original_code": "X123"},
    {"cpse": "SAIL", "original_code": "Y456"}
  ],
  "confidence_at_merge": "float",
  "merge_type": "string — 'auto' | 'human_approved'",
  "created_at": "ISO 8601 timestamp",
  "audit_log_ref": "string (link/id to full audit entry)"
}
```

Exposed via `GET /api/cnmc` (list + filter) for the dashboard to consume.

---

## Key Design Constants (keep consistent everywhere — PPT, docs, code)

| Constant | Value | Used in |
|---|---|---|
| Auto-link confidence threshold | **85%** | Tier 2 scoring, PPT Slide 2 & 3 |
| Score weights | Text 50% / Specs 30% / Units 20% | Tier 2 scoring, PPT Slide 2 |
| Pilot scope | 2 CPSEs, ~50k SKUs | PPT Slide 5 |

> ⚠️ If you change any of these while building, flag it in the team chat immediately —
> these numbers are already in the PPT and must stay consistent across code and deck.

## Tech Stack Summary

| Tier | Stack |
|---|---|
| Tier 1 | pandas, openpyxl |
| Tier 2 | sentence-transformers, rapidfuzz, scikit-learn |
| Tier 3 | React, FastAPI |
| Tier 4 | PostgreSQL, FastAPI |
| Tier 5 | React, Chart.js |
