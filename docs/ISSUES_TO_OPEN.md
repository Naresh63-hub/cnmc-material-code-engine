# Issues to Open (copy each block as one GitHub Issue)

Use the "Tier Task" template for each. Suggested milestones: `Tier 1`, `Tier 2`,
`Tier 3`, `Tier 4`, `Tier 5`, `Integration`.

---

### [Tier 1] File loader for multi-format CPSE catalogs
Input: raw CSV/Excel in `data/raw/`. Output: raw rows normalized into a common
internal format before cleaning. DoD: handles 2+ real file formats without code changes.

### [Tier 1] Description cleaner + abbreviation expansion
Input: raw description strings. Output: `clean_description` field per schema.

### [Tier 1] Spec + unit extractor
Input: clean descriptions. Output: `specs` object + `unit_of_measure` per schema.
DoD: sample output committed to `data/processed/`.

---

### [Tier 2] Embedding generation pipeline
Input: Tier 1 output. Output: vector embeddings per item, indexed in FAISS.

### [Tier 2] Candidate matching + weighted scoring
Input: embeddings + specs + units. Output: match records with confidence_score
per the 50/30/20 formula. DoD: threshold check (≥0.85 → auto_linked) implemented.

### [Tier 2] Sample match output for Tier 3/4 testing
DoD: a small (20-30 pair) sample match file committed so Tier 3/4 aren't blocked.

---

### [Tier 3] Review API — GET /api/pending-reviews
DoD: returns needs_review matches in correct schema.

### [Tier 3] Review API — POST /api/review-decision
DoD: accepts decision, correct schema, forwards to Tier 4.

### [Tier 3] Review queue frontend screen
DoD: shows side-by-side items, confidence + breakdown, approve/reject buttons working.

---

### [Tier 4] Database schema (cnmc_registry, code_mapping, audit_log)
DoD: schema documented in tier's README, migrations committed.

### [Tier 4] CNMC generation logic (auto-link + human-approved paths)
DoD: both paths tested, produce correct CNMC + mapping + audit entry.

### [Tier 4] GET /api/cnmc and GET /api/audit-log endpoints
DoD: both return correct data matching schema.

---

### [Tier 5] Summary stats section
DoD: pulls live counts from Tier 3/4 APIs.

### [Tier 5] Savings calculation panel (formula-based, not static)
DoD: visibly shows the calculation, matches PPT framing.

### [Tier 5] CNMC/duplicates browsable table + audit log view
DoD: real data, not hardcoded.

---

### [Integration] Wire Tier 1 → Tier 2 → Tier 3 → Tier 4 → Tier 5 end-to-end
DoD: a single real catalog file goes in, a CNMC comes out, visible on the dashboard.

### [Internals-prep] Pilot data extraction script (real public tender data)
DoD: real (not synthetic) sample dataset in `data/raw/`, sourced and documented —
see `scripts/` and the internals prep notes.
