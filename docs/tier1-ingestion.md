# Tier 1 — Data Ingestion & Preprocessing

## Objective (one line)
Take raw, messy material catalogs (Excel/CSV, different formats per CPSE) and turn them
into one clean, standardized dataset that Tier 2 can run matching on.

## Why This Matters
Every CPSE's catalog will look different — different column names, inconsistent
abbreviations ("SS" vs "Stainless Steel"), messy units. If this tier doesn't clean things
up properly, every downstream tier inherits the mess. This is the foundation.

## Input
- Raw catalog files, one per CPSE, placed in `data/raw/`
- Format: CSV or Excel (.xlsx)
- Columns will vary by source — expect: item code, description, unit, sometimes specs
  bundled into the description text itself (e.g. "Flange 150# RF SS316")

## Output (must match this exactly — see ARCHITECTURE.md for full schema)
A cleaned record per item:
```json
{
  "item_id": "ONGC-00123",
  "source_cpse": "ONGC",
  "raw_description": "FLG 150# RF SS316 6IN",
  "clean_description": "Flange 150# Raised Face Stainless Steel 316, 6 inch",
  "specs": {"size": "6IN", "material_grade": "SS316", "pressure_rating": "150#"},
  "unit_of_measure": "EA",
  "category_hint": "Piping"
}
```
Save as JSON Lines or a pandas DataFrame in `data/processed/`.

## What You Need to Build
1. **File loader** — reads CSV/Excel from `data/raw/`, handles varying column names
   (build a small mapping config so adding a new CPSE source later is just adding a
   config entry, not new code).
2. **Description cleaner** — expand common abbreviations (SS → Stainless Steel, EA →
   Each, etc.), normalize casing, strip extra whitespace/symbols.
3. **Spec extractor** — pull out size, material grade, pressure rating (or whatever
   specs are present) from the raw text into structured fields. Regex-based extraction
   is fine for the prototype, doesn't need to be perfect.
4. **Unit normalizer** — map unit variants to a standard set (e.g. "Nos", "EA", "PCS" all
   → "EA").
5. **item_id generator** — unique ID per item, prefixed by source CPSE.

## Deliverables Checklist
- [ ] Script/module that takes a raw file path and returns cleaned records
- [ ] Handles at least 2 different source file formats (so it's genuinely generalized,
      not hardcoded to one file)
- [ ] Output validated against the schema in `ARCHITECTURE.md`
- [ ] A short `README.md` in `src/ingestion/` explaining how to run it
- [ ] Sample output file committed to `data/processed/` for Tier 2 to test against early

## Acceptance Criteria (what "done" looks like)
- Running your script on a raw sample file produces valid JSON matching the schema
- No manual fixing needed after your script runs — output is directly usable by Tier 2
- Works on at least 2 differently-formatted input files without code changes (only
  config changes)

## Tech Stack
`pandas`, `openpyxl` (for .xlsx), Python's `re` module for extraction

## Things to Know
- Don't worry about perfect spec extraction — the prototype needs it working well
  enough on our pilot dataset, not production-grade for every possible material type.
- If a field can't be extracted, use `null`, don't guess or leave it blank/inconsistent.
- Talk to whoever owns Tier 2 before changing the output schema — they're building
  directly against it.
