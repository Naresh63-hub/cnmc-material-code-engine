import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..persistence.database import SessionLocal
from ..persistence.service import process_match


router = APIRouter(prefix="/api", tags=["Tier 3 Review"])


class ReviewDecisionRequest(BaseModel):
    match_id: str
    reviewer_decision: str | None = None
    decision: str | None = None
    reviewer_id: str = "procurement_officer_01"
    reviewed_at: datetime | None = None
    notes: str = ""


review_decisions = {}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TIER1_FILE = PROJECT_ROOT / "processed_catalog.jsonl"
TIER2_FILE = PROJECT_ROOT / "tier2_match_output.json"


@router.get("/pending-reviews")
def get_pending_reviews(status: str | None = None):
    """Return matches needing human review or safety blocked for audit, enriched with item specifications and CNMC mappings."""
    catalog = load_tier1_catalog()
    matches = load_tier2_matches()

    db = SessionLocal()
    reviewed_pairs = set()
    item_to_cnmc = {}
    cnmc_all_mappings = {}
    try:
        from ..persistence.models import CodeMapping
        mappings = db.query(CodeMapping).all()
        for m in mappings:
            item_to_cnmc[m.original_code] = m.cnmc_code
            cnmc_all_mappings.setdefault(m.cnmc_code, []).append({
                "cpse": m.source_cpse,
                "code": m.original_code
            })
        cnmc_groups = {}
        for m in mappings:
            cnmc_groups.setdefault(m.cnmc_code, []).append(m.original_code)
        for codes in cnmc_groups.values():
            if len(codes) >= 2:
                for i in range(len(codes)):
                    for j in range(i + 1, len(codes)):
                        reviewed_pairs.add((codes[i], codes[j]))
                        reviewed_pairs.add((codes[j], codes[i]))
    except Exception:
        pass
    finally:
        db.close()

    pending = []
    for match in matches:
        m_id = match.get("match_id")
        m_status = match.get("status")

        if m_id in review_decisions:
            dec = (review_decisions[m_id].get("reviewer_decision") or review_decisions[m_id].get("decision") or "").lower()
            if dec == "approved":
                m_status = "human_approved"
            elif dec == "rejected":
                m_status = "human_rejected"
        elif (match.get("item_a"), match.get("item_b")) in reviewed_pairs:
            m_status = "human_approved"

        if status and status != "all":
            if status == "needs_review" and m_status != "needs_review":
                continue
            elif status == "safety_blocked" and m_status != "safety_gate_blocked":
                continue
            elif status not in ("needs_review", "safety_blocked") and m_status != status:
                continue

        item_a = catalog.get(match["item_a"], {})
        item_b = catalog.get(match["item_b"], {})

        enriched = dict(match)
        enriched["status"] = m_status
        enriched["item_a_detail"] = item_a
        enriched["item_b_detail"] = item_b

        existing_cnmc = item_to_cnmc.get(match["item_a"]) or item_to_cnmc.get(match["item_b"])
        if existing_cnmc:
            enriched["existing_cnmc"] = existing_cnmc
            enriched["existing_cnmc_mappings"] = cnmc_all_mappings.get(existing_cnmc, [])
        else:
            enriched["existing_cnmc"] = None
            enriched["existing_cnmc_mappings"] = []

        pending.append(enriched)

    return pending


@router.post("/batch-approve")
def batch_approve_reviews(
    min_confidence: float = 0.70,
    reviewer_id: str = "senior_procurement_lead"
):
    """
    1-Click Bulk Approval: Approves all pending high-confidence candidate matches
    (e.g. confidence >= 70%) and mints CNMC records in one go.
    """
    pending = get_pending_reviews()
    approved_count = 0
    minted_codes = []

    for match in pending:
        if match.get("confidence_score", 0) >= min_confidence:
            m_id = match.get("match_id")
            decision_req = ReviewDecisionRequest(
                match_id=m_id,
                reviewer_decision="approved",
                reviewer_id=reviewer_id,
                reviewed_at=datetime.utcnow(),
                notes=f"Batch approved (Confidence {match.get('confidence_score')})"
            )
            try:
                res = submit_review_decision(decision_req)
                if res.get("cnmc_code"):
                    minted_codes.append(res["cnmc_code"])
                approved_count += 1
            except Exception:
                continue

    return {
        "status": "success",
        "message": f"Successfully batch-approved {approved_count} candidate pairs.",
        "approved_count": approved_count,
        "minted_cnmc_codes": minted_codes,
    }


def load_tier1_catalog():
    """Load Tier 1 standardized catalog."""
    if not TIER1_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="Tier 1 output file not found.",
        )

    catalog = {}

    with TIER1_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)
            catalog[item["item_id"]] = item

    return catalog


def load_tier2_matches():
    """Load the actual Tier 2 match output."""
    if not TIER2_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="Tier 2 output file not found.",
        )

    with TIER2_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_match(match_id: str):
    """Find a Tier 2 match using its match_id."""
    matches = load_tier2_matches()

    for match in matches:
        if match.get("match_id") == match_id:
            return match

    return None


def enrich_match(match: dict):
    """
    Add Tier 1 information required by Tier 4.

    The first item's standardized description is used as the
    canonical description for the approved merge.
    """
    catalog = load_tier1_catalog()

    item_a = catalog.get(match["item_a"])
    item_b = catalog.get(match["item_b"])

    if not item_a:
        raise HTTPException(
            status_code=404,
            detail=f"Tier 1 item not found: {match['item_a']}",
        )

    if not item_b:
        raise HTTPException(
            status_code=404,
            detail=f"Tier 1 item not found: {match['item_b']}",
        )

    enriched_match = dict(match)

    enriched_match["source_cpse_a"] = item_a["source_cpse"]
    enriched_match["source_cpse_b"] = item_b["source_cpse"]

    enriched_match["canonical_description"] = item_a["clean_description"]

    enriched_match["description_a"] = item_a["clean_description"]
    enriched_match["description_b"] = item_b["clean_description"]

    enriched_match["specs_a"] = item_a.get("specs", {})
    enriched_match["specs_b"] = item_b.get("specs", {})

    enriched_match["unit_a"] = item_a.get("unit_of_measure")
    enriched_match["unit_b"] = item_b.get("unit_of_measure")

    return enriched_match


@router.post("/review-decision")
def submit_review_decision(decision: ReviewDecisionRequest):

    dec_val = (decision.reviewer_decision or decision.decision or "").lower().strip()
    if dec_val not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="reviewer_decision must be 'approved' or 'rejected'",
        )
    decision.reviewer_decision = dec_val
    if not decision.reviewed_at:
        decision.reviewed_at = datetime.utcnow()

    match = find_match(decision.match_id)

    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"Tier 2 match not found: {decision.match_id}",
        )

    if decision.reviewer_decision == "approved" and match.get("status") == "safety_gate_blocked":
        raise HTTPException(
            status_code=400,
            detail=f"Safety gate blocked match cannot be approved: {match.get('block_reason', 'Critical engineering conflict')}",
        )

    review_decisions[decision.match_id] = decision.model_dump(
        mode="json"
    )

    # Rejected matches do not create CNMC records but are logged in AuditLog for AI training dataset
    if decision.reviewer_decision == "rejected":
        db = SessionLocal()
        try:
            from ..persistence.models import AuditLog
            audit_entry = AuditLog(
                cnmc_code=None,
                action="human_rejected",
                actor=decision.reviewer_id,
                details={
                    "match_id": decision.match_id,
                    "item_a": match.get("item_a"),
                    "item_b": match.get("item_b"),
                    "source_cpse_a": match.get("source_cpse_a"),
                    "source_cpse_b": match.get("source_cpse_b"),
                    "confidence_score": match.get("confidence_score"),
                    "notes": decision.notes,
                    "decision": "rejected",
                },
                timestamp=decision.reviewed_at,
            )
            db.add(audit_entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return {
            "status": "review_recorded",
            "match_id": decision.match_id,
            "reviewer_decision": "rejected",
            "reviewer_id": decision.reviewer_id,
            "reviewed_at": decision.reviewed_at,
            "notes": decision.notes,
            "cnmc_code": None,
            "message": "Match rejected and recorded in AuditLog for model evaluation. No CNMC was created.",
        }

    # Enrich Tier 2 data with Tier 1 information.
    enriched_match = enrich_match(match)

    # Convert Tier 3 approval into a Tier 4 human-approved merge.
    enriched_match["status"] = "human_approved"

    db = SessionLocal()

    try:
        result = process_match(
            db,
            enriched_match,
            actor=decision.reviewer_id,
        )

        return {
            "status": "review_recorded",
            "match_id": decision.match_id,
            "reviewer_decision": "approved",
            "reviewer_id": decision.reviewer_id,
            "reviewed_at": decision.reviewed_at,
            "notes": decision.notes,
            "cnmc_code": result["cnmc_code"],
            "canonical_description": enriched_match[
                "canonical_description"
            ],
            "merge_type": result["merge_type"],
            "confidence_score": result["confidence_score"],
            "message": (
                "Tier 3 approval successfully created "
                "Tier 4 CNMC record."
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Tier 4 persistence failed: {exc}",
        ) from exc

    finally:
        db.close()