# Tier 4 — Persistence, Mapping & Audit

## Objective (one line)
Take approved matches (auto-linked or human-approved) and generate the Common National
Material Code (CNMC), store the mapping back to original CPSE codes, and log everything
for the audit trail.

## Why This Matters
This is the "glue" tier — it's what turns a matching algorithm into an actual governed
system. The audit trail is one of the strongest points in our Feasibility slide
("full traceability, no black-box merging"), so this tier needs to genuinely work, not
just look like it does.

## Input
- Auto-linked matches directly from Tier 2 (`status == "auto_linked"`)
- Human-approved decisions from Tier 3 (`POST /api/review-decision` with
  `reviewer_decision == "approved"`)
- Both need to end up going through the same CNMC-generation logic

## Output
CNMC record, matching the schema in `ARCHITECTURE.md`:
```json
{
  "cnmc_code": "CNMC-000045",
  "canonical_description": "Flange 150# Raised Face Stainless Steel 316, 6 inch",
  "mapped_source_codes": [
    {"cpse": "ONGC", "original_code": "X123"},
    {"cpse": "SAIL", "original_code": "Y456"}
  ],
  "confidence_at_merge": 0.91,
  "merge_type": "auto",
  "created_at": "2026-09-01T10:00:00Z",
  "audit_log_ref": "AUDIT-000045"
}
```
Exposed via `GET /api/cnmc` for Tier 5 to consume.

## What You Need to Build

**Database schema (PostgreSQL):**
- `cnmc_registry` table: cnmc_code, canonical_description, confidence_at_merge,
  merge_type, created_at
- `code_mapping` table: cnmc_code (FK), source_cpse, original_code
- `audit_log` table: entry_id, cnmc_code (FK), action, actor (system or reviewer_id),
  timestamp, details

**API endpoints (FastAPI):**
1. Internal function/endpoint that receives an approved/auto-linked match and creates
   the CNMC + mapping + audit entry
2. `GET /api/cnmc` — list all CNMCs, with filter support (by CPSE, by date range)
3. `GET /api/audit-log` — full audit history, for transparency

## Deliverables Checklist
- [ ] Database schema created and documented
- [ ] Logic to generate a new CNMC code (simple incrementing/prefixed scheme is fine)
- [ ] Handles both auto-linked and human-approved paths into the same CNMC logic
- [ ] Every CNMC creation writes a corresponding audit log entry
- [ ] `GET /api/cnmc` and `GET /api/audit-log` working and returning correct data
- [ ] Short README documenting the schema and endpoints

## Acceptance Criteria
- Feeding in a sample auto-linked match AND a sample human-approved decision both
  correctly produce a CNMC record with proper mapping and an audit entry
- Nothing gets merged without a corresponding audit log entry, no exceptions
- Original CPSE codes are never overwritten or lost, only mapped

## Tech Stack
`PostgreSQL`, `FastAPI`

## Things to Know
- This is the tier judges will probe hardest on the "governance" claims in our deck —
  make sure the audit trail is genuinely functional, not just a UI mockup.
- Coordinate closely with whoever owns Tier 3 on the exact `POST /api/review-decision`
  contract before building — that's your primary input alongside Tier 2's auto-links.
