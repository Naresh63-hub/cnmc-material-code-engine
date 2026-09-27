# Tier 3 — Human Review Interface & API

## Objective (one line)
Build a simple screen where a reviewer sees uncertain matches (confidence < 85%) and
approves or rejects them, plus the API that records their decision.

## Why This Matters
This is what makes the system trustworthy instead of a black box — uncertain matches
never get silently auto-merged, a real person signs off. This tier is what you'll point
to when a judge asks "what stops a wrong merge?"

## Input
Match records from Tier 2 where `status == "needs_review"`, matching the schema in
`ARCHITECTURE.md`. For display, you'll need the two items' descriptions — either Tier 2
includes them in the match record, or you fetch them by `item_id` from Tier 1's output
(confirm which approach with Tier 2's owner before building).

## Output
A decision record per reviewed match, matching the schema in `ARCHITECTURE.md`:
```json
{
  "match_id": "same as Tier 2's match_id",
  "reviewer_decision": "approved | rejected",
  "reviewer_id": "string",
  "reviewed_at": "ISO timestamp",
  "notes": "optional string"
}
```
Sent via `POST /api/review-decision` to Tier 4.

## What You Need to Build

**Backend (FastAPI):**
1. `GET /api/pending-reviews` — returns list of matches needing review
2. `POST /api/review-decision` — accepts a decision, forwards to Tier 4's persistence layer

**Frontend (React):**
1. A list/queue view of pending matches
2. For each match: show both item descriptions side by side, the confidence score, and
   the score breakdown (text/specs/units) — so the reviewer understands *why* it matched,
   not just a bare number
3. Approve / Reject buttons that call the API
4. Some visual confirmation when a decision is submitted (so reviewers know it registered)

## Deliverables Checklist
- [ ] Working `GET /api/pending-reviews` endpoint
- [ ] Working `POST /api/review-decision` endpoint
- [ ] Frontend screen showing the review queue
- [ ] Approve/Reject buttons wired to the API
- [ ] Score breakdown visibly displayed per match (not just the final number)
- [ ] Short README on how to run frontend + backend locally

## Acceptance Criteria
- A reviewer can open the screen, see a real pending match (from Tier 2's test output),
  and approve/reject it, and that decision is correctly POSTed in the right format
- Works end-to-end even with placeholder/sample data before Tier 2 is fully done —
  don't block yourself waiting on live data, build against the schema first

## Tech Stack
`React` (frontend), `FastAPI` (backend)

## Things to Know
- You don't need real auth/login for the prototype — a simple reviewer_id field or
  dropdown is enough to demonstrate the concept.
- Keep the UI simple and clear over fancy — judges care that the review step visibly
  exists and works, not that it's beautifully designed.
- If Tier 2 isn't ready yet, build against a hand-written sample JSON file matching the
  schema so you're not blocked — swap in real data once it's available.
