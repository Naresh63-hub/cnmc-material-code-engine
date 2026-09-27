import io
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from ..persistence.database import get_db, SessionLocal, Base, engine
from ..persistence.models import CNMCRegistry, CodeMapping, AuditLog
from ..ingestion.ingest import load_catalog, clean_description, extract_specs, normalize_unit, parse_catalog_file, parse_and_validate_csv
from ..ingestion.seed_extended_catalog import generate_extended_catalog
from ..matching.match_from_pipeline import run_matching
from ..persistence.integrate_tier2 import integrate_tier2


router = APIRouter(prefix="/api", tags=["Tier 5 Dashboard, Analytics & ERP Sync"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TIER1_FILE = PROJECT_ROOT / "processed_catalog.jsonl"
TIER2_FILE = PROJECT_ROOT / "tier2_match_output.json"


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Return comprehensive analytics for executive dashboard and savings estimates.
    """
    catalog_items = []
    if TIER1_FILE.exists():
        with TIER1_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    catalog_items.append(json.loads(line.strip()))

    cpse_counts = {}
    for item in catalog_items:
        cpse = item.get("source_cpse", "UNKNOWN")
        cpse_counts[cpse] = cpse_counts.get(cpse, 0) + 1

    matches = []
    if TIER2_FILE.exists():
        with TIER2_FILE.open("r", encoding="utf-8") as f:
            matches = json.load(f)

    auto_linked_count = sum(1 for m in matches if m.get("status") == "auto_linked")
    needs_review_count = sum(1 for m in matches if m.get("status") == "needs_review")
    safety_blocked_count = sum(1 for m in matches if m.get("status") == "safety_gate_blocked")

    total_cnmc = db.execute(select(func.count(CNMCRegistry.cnmc_code))).scalar() or 0
    total_mappings = db.execute(select(func.count(CodeMapping.id))).scalar() or 0
    total_audits = db.execute(select(func.count(AuditLog.entry_id))).scalar() or 0

    human_approved_count = db.execute(
        select(func.count(AuditLog.entry_id)).where(AuditLog.action == "human_approved")
    ).scalar() or 0

    duplicate_identified = total_cnmc
    duplicate_percentage = round((duplicate_identified / max(len(catalog_items), 1)) * 100, 1)

    return {
        "catalog_summary": {
            "total_items": len(catalog_items),
            "cpse_breakdown": cpse_counts,
        },
        "matching_engine": {
            "total_pairs_evaluated": len(matches),
            "auto_linked": auto_linked_count,
            "needs_review": needs_review_count,
            "safety_gate_blocked": safety_blocked_count,
            "human_approved": human_approved_count,
        },
        "cnmc_registry": {
            "total_cnmc_generated": total_cnmc,
            "total_legacy_codes_mapped": total_mappings,
            "total_audit_events": total_audits,
            "duplicate_percentage": duplicate_percentage,
        },
        "default_savings_model": {
            "annual_spend_cr": 500.0,
            "duplicate_rate_pct": duplicate_percentage or 25.0,
            "bulk_discount_pct": 12.0,
            "estimated_annual_savings_cr": round(500.0 * ((duplicate_percentage or 25.0) / 100) * 0.12, 2)
        }
    }


@router.get("/catalog")
def get_catalog_items(
    cpse: Optional[str] = None,
    search: Optional[str] = None,
):
    """List and search all standardized material catalog items."""
    if not TIER1_FILE.exists():
        return []

    items = []
    with TIER1_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line.strip())
                if cpse and item.get("source_cpse", "").upper() != cpse.upper():
                    continue
                if search:
                    q = search.lower()
                    if (
                        q not in item.get("clean_description", "").lower()
                        and q not in item.get("item_id", "").lower()
                        and q not in item.get("raw_description", "").lower()
                    ):
                        continue
                items.append(item)

    return items


@router.post("/demo/reset-from-zero")
def reset_from_zero():
    """
    Wipes DB, catalog files, and match output to a clean zero state.
    Does NOT seed data. Click 'Load 4-CPSE Pilot Data' afterwards.
    """
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        TIER1_FILE.write_text("", encoding="utf-8")
        TIER2_FILE.write_text("[]", encoding="utf-8")
        return {"status": "success", "message": "System wiped to clean slate. Click 'Load 4-CPSE Pilot Data' to populate."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset demo: {str(e)}")


@router.post("/demo/seed-pilot")
def seed_pilot_dataset():
    """
    1-Click Seeder: Seeds the 4-CPSE Pilot Dataset (ONGC, SAIL, IOCL, GAIL),
    runs Tier 1 Ingestion, Tier 2 AI Matching, and Tier 4 Auto-linking.
    Always resets DB first so results are clean.
    """
    try:
        # Always start from clean DB so no duplicates accumulate
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        extended_items = generate_extended_catalog()

        with open(str(TIER1_FILE), "w", encoding="utf-8") as f:
            for item in extended_items:
                f.write(json.dumps(item) + "\n")

        matches = run_matching(extended_items)
        with open(str(TIER2_FILE), "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2)

        integrate_tier2(dry_run=False)

        return {
            "status": "success",
            "message": "Loaded 4-CPSE Pilot Dataset (ONGC, SAIL, IOCL, GAIL) and executed matching pipeline.",
            "total_items": len(extended_items),
            "total_pairs_evaluated": len(matches),
            "auto_linked": sum(1 for m in matches if m.get("status") == "auto_linked"),
            "needs_review": sum(1 for m in matches if m.get("status") == "needs_review"),
            "safety_gate_blocked": sum(1 for m in matches if m.get("status") == "safety_gate_blocked"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed pilot dataset: {str(e)}")


@router.post("/catalog/preview-csv")
async def preview_csv_catalog(
    cpse_name: str = Form("GENERIC"),
    file: UploadFile = File(...),
):
    """
    Previews column mapping and validation report for a CSV file before full import.
    """
    if not (file.filename and file.filename.lower().endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for this ingestion workflow.")

    try:
        content = await file.read()
        valid_records, validation_report = parse_and_validate_csv(content, default_cpse=cpse_name)
        return {
            "status": "success",
            "filename": file.filename,
            "validation_report": validation_report,
            "preview_sample": valid_records[:5],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV preview failed: {str(e)}")


@router.post("/catalog/upload")
async def upload_cpse_catalog(
    cpse_name: str = Form("GENERIC"),
    file: UploadFile = File(...),
):
    """
    Ingests and validates CSV catalog upload, maps to canonical schema, and runs pipeline.
    """
    if not (file.filename and file.filename.lower().endswith(".csv")):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for this ingestion workflow.")

    try:
        content = await file.read()
        new_items, validation_report = parse_and_validate_csv(content, default_cpse=cpse_name)

        if not new_items:
            err_msg = "; ".join(validation_report.get("errors", [])) or "No valid material records found."
            raise HTTPException(status_code=400, detail=f"Validation failed: {err_msg}")

        # Append or merge with existing catalog
        existing_items = []
        if TIER1_FILE.exists():
            with TIER1_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        existing_items.append(json.loads(line.strip()))

        existing_ids = {it["item_id"] for it in existing_items}
        added_count = 0
        for it in new_items:
            if it["item_id"] not in existing_ids:
                existing_items.append(it)
                existing_ids.add(it["item_id"])
                added_count += 1

        with open(str(TIER1_FILE), "w", encoding="utf-8") as f:
            for item in existing_items:
                f.write(json.dumps(item) + "\n")

        # Re-run matching
        matches = run_matching(existing_items)
        with open(str(TIER2_FILE), "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2)

        integrate_tier2(dry_run=False)

        return {
            "status": "success",
            "message": f"Successfully ingested {len(new_items)} items for {cpse_name.upper()}.",
            "total_items": len(existing_items),
            "new_items_added": added_count,
            "total_pairs_evaluated": len(matches),
            "validation_report": validation_report,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Catalog upload failed: {str(e)}")


@router.get("/export/sap-matmas")
def export_sap_matmas(db: Session = Depends(get_db)):
    """
    Exports CNMC and Legacy mappings in SAP MATMAS-compatible migration CSV format.
    """
    query = (
        select(CNMCRegistry)
        .options(selectinload(CNMCRegistry.mappings))
        .order_by(CNMCRegistry.cnmc_code.asc())
    )
    records = db.execute(query).scalars().unique().all()

    catalog_map = {}
    if TIER1_FILE.exists():
        with TIER1_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    catalog_map[(item.get("source_cpse", "").upper(), item.get("item_id", ""))] = item

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "CNMC_RECOMMENDED_CODE",
        "SOURCE_CPSE",
        "LEGACY_MATERIAL_CODE",
        "ORIGINAL_DESCRIPTION",
        "STANDARDIZED_DESCRIPTION",
        "UOM",
        "CATEGORY",
        "KEY_SPECIFICATIONS",
        "CONFIDENCE_SCORE",
        "MERGE_TYPE",
        "MAPPING_STATUS",
        "EXPORT_TIMESTAMP"
    ])

    for r in records:
        for m in r.mappings:
            cat_item = catalog_map.get((m.source_cpse.upper(), m.original_code), {})
            specs = cat_item.get("specs", {})
            spec_parts = []
            if specs.get("size"): spec_parts.append(f"Size: {specs['size']}")
            if specs.get("pressure_rating"): spec_parts.append(f"Rating: {specs['pressure_rating']}")
            if specs.get("material_grade") or specs.get("material_family"): spec_parts.append(f"Material: {specs.get('material_grade') or specs.get('material_family')}")
            if specs.get("facing"): spec_parts.append(f"Facing: {specs['facing']}")
            if specs.get("schedule"): spec_parts.append(f"Sch: {specs['schedule']}")
            if specs.get("power_hp"): spec_parts.append(f"Power: {specs['power_hp']}")
            if specs.get("speed_rpm"): spec_parts.append(f"Speed: {specs['speed_rpm']}")

            writer.writerow([
                r.cnmc_code,
                m.source_cpse,
                m.original_code,
                cat_item.get("raw_description") or cat_item.get("clean_description") or r.canonical_description,
                r.canonical_description,
                cat_item.get("unit_of_measure", "EA"),
                specs.get("category") or cat_item.get("category_hint", "GENERAL"),
                "; ".join(spec_parts) if spec_parts else "N/A",
                f"{r.confidence_at_merge:.2f}",
                r.merge_type,
                "READY_FOR_SAP_ERP_IMPORT",
                r.created_at.isoformat()
            ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=SAP_MATMAS_CNMC_MIGRATION.csv"}
    )


@router.get("/export/audit-csv")
def export_audit_csv(db: Session = Depends(get_db)):
    """
    Exports full audit trail as governance CSV.
    """
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    records = db.execute(query).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ENTRY_ID",
        "TIMESTAMP",
        "ACTION",
        "CNMC_CODE",
        "ACTOR",
        "MATCH_ID",
        "ITEM_A",
        "ITEM_B",
        "CONFIDENCE_SCORE",
        "REASON_OR_NOTES"
    ])

    for a in records:
        d = a.details or {}
        writer.writerow([
            a.entry_id,
            a.timestamp.isoformat(),
            a.action,
            a.cnmc_code or "N/A",
            a.actor,
            d.get("match_id", ""),
            d.get("item_a", ""),
            d.get("item_b", ""),
            d.get("confidence_score", ""),
            d.get("reason", "") or d.get("notes", "")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=NATIONAL_MATERIAL_AUDIT_LOG.csv"}
    )


@router.get("/search/procurement")
def search_procurement(q: str, db: Session = Depends(get_db)):
    """
    Unified National Material Search:
    Searches CNMC registry and catalog items to display multi-CPSE stock & demand aggregation opportunities.
    """
    query = (
        select(CNMCRegistry)
        .options(selectinload(CNMCRegistry.mappings))
        .where(
            CNMCRegistry.canonical_description.ilike(f"%{q}%") |
            CNMCRegistry.cnmc_code.ilike(f"%{q}%") |
            CNMCRegistry.mappings.any(CodeMapping.original_code.ilike(f"%{q}%"))
        )
    )
    cnmc_results = db.execute(query).scalars().unique().all()

    # Also search catalog items
    catalog_items = []
    if TIER1_FILE.exists():
        with TIER1_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line.strip())
                    if q.lower() in item.get("clean_description", "").lower() or q.lower() in item.get("item_id", "").lower():
                        catalog_items.append(item)

    return {
        "query": q,
        "cnmc_matches": [
            {
                "cnmc_code": c.cnmc_code,
                "canonical_description": c.canonical_description,
                "confidence_score": c.confidence_at_merge,
                "merge_type": c.merge_type,
                "participating_cpses": list({m.source_cpse for m in c.mappings}),
                "mapped_legacy_codes": [
                    {"cpse": m.source_cpse, "code": m.original_code} for m in c.mappings
                ]
            }
            for c in cnmc_results
        ],
        "catalog_items_found": catalog_items[:10]
    }
