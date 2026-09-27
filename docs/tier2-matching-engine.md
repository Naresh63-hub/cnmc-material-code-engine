# Tier 2 — Matching & Scoring Engine (Core — Owned by [Your Name])

## Objective (one line)
Compare items across CPSE catalogs and produce a confidence-scored match for every
plausible pair, using meaning-based similarity, not just spelling.

## Why This Stays With Me
This is the technical heart of the project — the part judges will drill into most, and
the part every other tier depends on. Keeping it centralized avoids integration risk on
the piece that's hardest to safely hand off mid-build.

## Input
Cleaned records from Tier 1 (`data/processed/`), matching the schema in `ARCHITECTURE.md`.

## Output
Match records per candidate pair, matching the schema in `ARCHITECTURE.md`:
- `confidence_score` = weighted combination of text similarity (50%), spec match (30%),
  unit compatibility (20%)
- `status`: `auto_linked` if score ≥ 0.85, else `needs_review`

## Approach
1. Generate semantic embeddings for `clean_description` using `sentence-transformers`
2. Candidate generation: don't compare every item to every other item (too slow at
   scale) — use approximate nearest-neighbor search (FAISS) to shortlist likely matches
   first, then score those candidates in detail
3. Score each candidate pair on the three signals, combine with fixed weights
4. Output match records for Tier 3/4 to consume

## Tech Stack
`sentence-transformers`, `FAISS`, `rapidfuzz` (as a secondary/fallback signal), `scikit-learn`

## What Other Tiers Need From This
- Tier 3 needs `match_id`, both item descriptions (for display), and `confidence_score`
  + `score_breakdown` (so the reviewer can see *why* it matched)
- Tier 4 needs the full match record to build the CNMC mapping

## Status
This tier's build tracked separately — see the GitHub issue for progress, not delegated
to another team member.
