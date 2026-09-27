# Tier 5 — Dashboard & Analytics

## Objective (one line)
Build the visual screen that shows duplicates found, potential savings, and pending
reviews — this is the main thing judges will actually watch during the demo.

## Why This Matters
This is the "face" of the whole project. All the matching logic and governance work
in Tiers 1-4 only matters if it's visible and legible in under 30 seconds on screen.

## Input
- `GET /api/cnmc` from Tier 4 — list of generated codes and their mappings
- `GET /api/pending-reviews` from Tier 3 — matches still awaiting review
- `GET /api/audit-log` from Tier 4 — for a transparency/history view

## What You Need to Build

**Key screens/sections:**
1. **Summary stats** — total duplicates found, total CNMCs generated, number of CPSEs
   covered, pending review count
2. **Savings estimate panel** — using the formula from the PPT: `duplicate % × avg PO
   value × bulk discount %` — display it as a calculation, not a bare final number, so
   it's clear where it comes from (matches how we're presenting it to judges)
3. **Duplicate detection table/list** — browsable view of CNMCs with their mapped
   source codes
4. **Pending review counter/link** — shows how many matches are waiting on Tier 3
5. **Audit trail view** (simple table is fine) — for the governance/transparency story

## Deliverables Checklist
- [ ] Summary stats section pulling live data from the APIs
- [ ] Savings calculation panel showing the formula, not just a final number
- [ ] Browsable CNMC/duplicates table
- [ ] Pending review count/link
- [ ] Basic audit log view
- [ ] Clean enough visually to be the centerpiece of the live demo

## Acceptance Criteria
- Loads real data from Tier 4/Tier 3's APIs (not hardcoded mock data) by the time of
  final demo — mock data is fine for early development, but must be swapped out
- Savings figure is clearly shown as calculated from real pilot inputs, not a static
  claimed number — this matches the "no pre-claimed savings" line in our PPT, so the
  dashboard needs to actually back that up

## Tech Stack
`React`, `Chart.js`

## Things to Know
- This is what gets shown on screen during the live pitch — prioritize clarity and a
  clean look over cramming in every possible metric.
- Start building against mock/sample data early so you're not blocked waiting on
  Tiers 3/4 — swap in real API calls once they're ready.
