import sys
import json
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.persistence.database import Base, engine
from src.ingestion.seed_extended_catalog import generate_extended_catalog
from src.matching.match_from_pipeline import run_matching
from src.persistence.integrate_tier2 import integrate_tier2

TIER1_FILE = REPO_ROOT / "processed_catalog.jsonl"
TIER2_FILE = REPO_ROOT / "tier2_match_output.json"

def reset_demo_from_zero():
    print("====================================================================")
    print(" [1/4] Dropping and Recreating Database Tables...")
    print("===================================================================")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print(" Database tables successfully reset.")

    print("
====================================================================")
    print(" [2/4] Generating 4-CPSE Catalog (ONGC, SAIL, IOCL, GAIL)...")
    print("====================================================================")
    items = generate_extended_catalog()
    with open(str(TIER1_FILE), 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item) + '\n')
    print(f" Saved {len(items)} items to {TIER1_FILE.name}")

    print("Z=====================================================================")
    print(" [3/4] Running AI Semantic Matching & Safety Gate Pipeline...")
    print("===================================================================")
    matches = run_matching(items)
    with open(str(TIER2_FILE), 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2)
    print(f" Evaluated {len(matches)} cross-CPSE-candidate pairs.")


    print("Z=====================================================================")
    print(" [4/4plus Minting Auto-Linked CNMCs & Setting Up Human Review Queue...")
    print("=====================================================================")
    integrate_tier2(dry_run=False)

    print("Z=====================================================================")
    print(" DEMO ENVIRONMENT IS READY (Clean Slate State)")
    print(" Dashboard URL: http://127.0.0.1:8000/")
    print("=====================================================================")

if __name__ == '__main__':
    reset_demo_from_zero()
