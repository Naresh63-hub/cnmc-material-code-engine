
import json
from pathlib import Path

from . import init_db
from .database import SessionLocal
from .service import process_match


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Tier 1 actual output
TIER1_FILE = PROJECT_ROOT / "processed_catalog.jsonl"

# Tier 2 actual output
TIER2_FILE = PROJECT_ROOT / "tier2_match_output.json"


def load_tier1_catalog():
    """Load Tier 1 standardized records indexed by item_id."""
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
    """Load Tier 2 match records."""
    with TIER2_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def enrich_match(match, catalog):
    """Add Tier 1 information required by Tier 4."""

    item_a = catalog.get(match["item_a"])
    item_b = catalog.get(match["item_b"])

    if not item_a:
        raise ValueError(
            f"Tier 1 item not found: {match['item_a']}"
        )

    if not item_b:
        raise ValueError(
            f"Tier 1 item not found: {match['item_b']}"
        )

    enriched = dict(match)

    # Preserve original CPSE ownership
    enriched["source_cpse_a"] = item_a["source_cpse"]
    enriched["source_cpse_b"] = item_b["source_cpse"]

    # Use Tier 1 canonical standardized description
    enriched["canonical_description"] = item_a["clean_description"]

    # Additional Tier 1 information
    enriched["description_a"] = item_a["clean_description"]
    enriched["description_b"] = item_b["clean_description"]

    enriched["specs_a"] = item_a.get("specs", {})
    enriched["specs_b"] = item_b.get("specs", {})

    enriched["unit_a"] = item_a.get("unit_of_measure")
    enriched["unit_b"] = item_b.get("unit_of_measure")

    return enriched


def integrate_tier2(dry_run=False):
    """
    Integrate real Tier 2 results into Tier 4.

    Rules:
    - auto_linked -> create CNMC + mappings + audit
    - needs_review -> wait for Tier 3 approval
    - safety_gate_blocked -> audit only, no CNMC, no mappings
    """

    print("=" * 70)
    print("TIER 2 -> TIER 4 INTEGRATION")
    print("=" * 70)
    print()

    init_db()
    catalog = load_tier1_catalog()
    tier2_matches = load_tier2_matches()

    print(f"Tier 1 catalog items  : {len(catalog)}")
    print(f"Tier 2 match records  : {len(tier2_matches)}")
    print()

    auto_linked = 0
    needs_review = 0
    blocked = 0

    db = SessionLocal() if not dry_run else None

    try:

        for match in tier2_matches:

            status = match.get("status")

            enriched = enrich_match(
                match,
                catalog
            )

            # --------------------------------------------------
            # AUTO-LINKED
            # --------------------------------------------------

            if status == "auto_linked":

                auto_linked += 1

                print(
                    f"[AUTO-LINK] "
                    f"{match['item_a']} <-> "
                    f"{match['item_b']} "
                    f"confidence="
                    f"{match['confidence_score']}"
                )

                if not dry_run:

                    result = process_match(
                        db,
                        enriched,
                        actor="tier2_system"
                    )

                    print(
                        f"    -> CNMC: "
                        f"{result['cnmc_code']}"
                    )

            # --------------------------------------------------
            # NEEDS REVIEW
            # --------------------------------------------------

            elif status == "needs_review":

                needs_review += 1

                print(
                    f"[NEEDS REVIEW] "
                    f"{match['item_a']} <-> "
                    f"{match['item_b']} "
                    f"confidence="
                    f"{match['confidence_score']}"
                )

                print(
                    "    -> Waiting for Tier 3 human approval"
                )

            # --------------------------------------------------
            # SAFETY GATE BLOCKED
            # --------------------------------------------------

            elif status == "safety_gate_blocked":

                blocked += 1

                print(
                    f"[SAFETY GATE BLOCKED] "
                    f"{match['item_a']} <-> "
                    f"{match['item_b']}"
                )

                print(
                    f"    Reason: "
                    f"{match.get('block_reason', 'Safety Gate blocked the match')}"
                )

                if not dry_run:

                    result = process_match(
                        db,
                        enriched,
                        actor="safety_gate"
                    )

                    print(
                        f"    -> Audit entry: "
                        f"{result['audit_entry_id']}"
                    )

            else:

                print(
                    f"[SKIPPED] Unknown status: {status}"
                )

        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------

        print()
        print("=" * 70)
        print("TIER 2 -> TIER 4 SUMMARY")
        print("=" * 70)

        print(f"Auto-linked          : {auto_linked}")
        print(f"Needs review         : {needs_review}")
        print(f"Safety Gate blocked  : {blocked}")
        print(
            f"Total records       : "
            f"{auto_linked + needs_review + blocked}"
        )
        print(f"Dry run              : {dry_run}")

        print("=" * 70)

    finally:

        if db:
            db.close()


if __name__ == "__main__":
    integrate_tier2(dry_run=False)

