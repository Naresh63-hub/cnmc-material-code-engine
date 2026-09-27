from . import init_db
from .database import SessionLocal
from .service import process_match


def main():
    init_db()
    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # TEST 1: HUMAN APPROVED
        # ---------------------------------------------------------
        human_approved = {
            "match_id": "TEST-HUMAN-001",
            "item_a": "GAIL-V210",
            "item_b": "OIL-V300",
            "source_cpse_a": "GAIL",
            "source_cpse_b": "OIL",
            "canonical_description": (
                "Valve Gate 300# RF ASTM A216 WCB"
            ),
            "confidence_score": 0.85,
            "status": "human_approved",
        }

        result = process_match(
            db,
            human_approved,
            actor="reviewer_demo",
        )

        print("\nHUMAN APPROVED RESULT:")
        print(result)

        # ---------------------------------------------------------
        # TEST 2: SAFETY GATE BLOCKED
        # ---------------------------------------------------------
        safety_blocked = {
            "match_id": "TEST-BLOCKED-001",
            "item_a": "ONGC-F001",
            "item_b": "BPCL-F999",
            "source_cpse_a": "ONGC",
            "source_cpse_b": "BPCL",
            "confidence_score": 0.97,
            "status": "safety_gate_blocked",
            "block_reason": (
                "Pressure class mismatch: 150 vs 300"
            ),
        }

        result = process_match(
            db,
            safety_blocked,
            actor="system",
        )

        print("\nSAFETY GATE BLOCKED RESULT:")
        print(result)

    finally:
        db.close()


if __name__ == "__main__":
    main()