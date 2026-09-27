from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import AuditLog, CNMCRegistry, CodeMapping


def _next_cnmc_code(db: Session) -> str:
    """
    Generate the next CNMC code.

    Uses the highest existing numeric CNMC suffix and increments it.
    The operation is performed inside the same database transaction
    as the CNMC creation.
    """
    result = db.execute(
        select(CNMCRegistry.cnmc_code)
        .where(CNMCRegistry.cnmc_code.like("CNMC-%"))
        .order_by(CNMCRegistry.cnmc_code.desc())
        .limit(1)
    ).scalar_one_or_none()

    if result is None:
        next_number = 1
    else:
        try:
            next_number = int(result.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_number = 1

    return f"CNMC-{next_number:06d}"


def _get_required_value(data: dict[str, Any], key: str) -> Any:
    value = data.get(key)

    if value is None or value == "":
        raise ValueError(f"Required field missing: {key}")

    return value


def _create_cnmc_record(
    db: Session,
    match: dict[str, Any],
    merge_type: str,
    actor: str,
) -> CNMCRegistry:
    """
    Create one CNMC registry entry, its source mappings,
    and the corresponding audit record.
    """

    canonical_description = _get_required_value(
        match,
        "canonical_description",
    )

    confidence = float(
        _get_required_value(
            match,
            "confidence_score",
        )
    )

    item_a = _get_required_value(match, "item_a")
    item_b = _get_required_value(match, "item_b")

    source_cpse_a = match.get("source_cpse_a")
    source_cpse_b = match.get("source_cpse_b")

    if not source_cpse_a or not source_cpse_b:
        raise ValueError(
            "source_cpse_a and source_cpse_b are required "
            "to preserve original CPSE mappings"
        )

    # Multi-CPSE Clustering: Check if either item is already mapped to a CNMC
    existing_a = db.query(CodeMapping).filter_by(
        source_cpse=source_cpse_a,
        original_code=item_a,
    ).first()

    existing_b = db.query(CodeMapping).filter_by(
        source_cpse=source_cpse_b,
        original_code=item_b,
    ).first()

    if existing_a and existing_b:
        # Both already mapped to CNMC codes
        cnmc = db.query(CNMCRegistry).filter_by(
            cnmc_code=existing_a.cnmc_code
        ).first()
        return cnmc

    if existing_a and not existing_b:
        # Item A is already mapped; link Item B into existing CNMC
        cnmc_code = existing_a.cnmc_code
        cnmc = db.query(CNMCRegistry).filter_by(cnmc_code=cnmc_code).first()
        mapping_b = CodeMapping(
            cnmc_code=cnmc_code,
            source_cpse=source_cpse_b,
            original_code=item_b,
        )
        db.add(mapping_b)
    elif existing_b and not existing_a:
        # Item B is already mapped; link Item A into existing CNMC
        cnmc_code = existing_b.cnmc_code
        cnmc = db.query(CNMCRegistry).filter_by(cnmc_code=cnmc_code).first()
        mapping_a = CodeMapping(
            cnmc_code=cnmc_code,
            source_cpse=source_cpse_a,
            original_code=item_a,
        )
        db.add(mapping_a)
    else:
        # New cluster: Mint fresh CNMC
        cnmc_code = _next_cnmc_code(db)
        cnmc = CNMCRegistry(
            cnmc_code=cnmc_code,
            canonical_description=canonical_description,
            confidence_at_merge=confidence,
            merge_type=merge_type,
            created_at=datetime.utcnow(),
        )
        db.add(cnmc)
        db.flush()

        mapping_a = CodeMapping(
            cnmc_code=cnmc_code,
            source_cpse=source_cpse_a,
            original_code=item_a,
        )
        mapping_b = CodeMapping(
            cnmc_code=cnmc_code,
            source_cpse=source_cpse_b,
            original_code=item_b,
        )
        db.add(mapping_a)
        db.add(mapping_b)

    audit = AuditLog(
        cnmc_code=cnmc_code,
        action=merge_type,
        actor=actor,
        details={
            "match_id": match.get("match_id"),
            "item_a": item_a,
            "item_b": item_b,
            "source_cpse_a": source_cpse_a,
            "source_cpse_b": source_cpse_b,
            "confidence_score": confidence,
        },
        timestamp=datetime.utcnow(),
    )

    db.add(audit)
    db.flush()

    return cnmc


def process_match(
    db: Session,
    match: dict[str, Any],
    actor: str = "system",
) -> dict[str, Any]:
    """
    Process one Tier 2 / Tier 3 decision.

    Supported statuses:
      - auto_linked
      - human_approved
      - safety_gate_blocked

    safety_gate_blocked creates ONLY an audit entry.
    """

    status = match.get("status")

    if status not in {
        "auto_linked",
        "human_approved",
        "safety_gate_blocked",
    }:
        raise ValueError(
            f"Unsupported match status: {status}"
        )

    try:
        if status == "safety_gate_blocked":
            audit = AuditLog(
                cnmc_code=None,
                action="safety_gate_blocked",
                actor=actor,
                details={
                    "match_id": match.get("match_id"),
                    "item_a": match.get("item_a"),
                    "item_b": match.get("item_b"),
                    "reason": match.get(
                        "block_reason",
                        "Safety Gate blocked the match",
                    ),
                    "confidence_score": match.get(
                        "confidence_score"
                    ),
                },
                timestamp=datetime.utcnow(),
            )

            db.add(audit)
            db.commit()
            db.refresh(audit)

            return {
                "status": "safety_gate_blocked",
                "cnmc_code": None,
                "audit_entry_id": audit.entry_id,
            }

        cnmc = _create_cnmc_record(
            db=db,
            match=match,
            merge_type=status,
            actor=actor,
        )

        db.commit()
        db.refresh(cnmc)

        return {
            "status": status,
            "cnmc_code": cnmc.cnmc_code,
            "canonical_description": cnmc.canonical_description,
            "confidence_score": cnmc.confidence_at_merge,
            "merge_type": cnmc.merge_type,
            "created_at": cnmc.created_at.isoformat(),
        }

    except Exception:
        db.rollback()
        raise