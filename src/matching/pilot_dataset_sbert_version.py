"""
SIH26099 — Pilot Sample Dataset + Matching Engine Demo
========================================================
Dataset is NOT scraped from a live tender (CPPP requires DSC + registration,
not accessible for this prototype stage). Instead, every item below is built
using REAL, verifiable industry standards that CPSEs actually procure against:

  - ASME B16.5   — pipe flange dimensions & pressure classes (150/300/600/900...)
  - API 6D       — pipeline valve standard (ball/gate/check valves, oil & gas)
  - ASTM grades  — material grades (A105 carbon steel, A182 F316 stainless, etc.)
  - ASME B16.20  — spiral wound gasket standard

Each "duplicate group" below represents the same real-world item, described
the way different CPSEs would realistically phrase it (different naming
conventions, same underlying ASME/API/ASTM spec) — grounded in real
engineering standards, not randomly invented.
"""

import re
import itertools
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz

# ---- Pilot sample dataset (grounded in real ASME/API/ASTM standards) ----
items = [
    # GROUP 1: Flange — ASME B16.5, Class 150, RF, ASTM A105 (carbon steel), 6"
    {"item_id": "ONGC-F001",  "cpse": "ONGC",       "description": "Flange WN RF 150# ASTM A105 6IN ASME B16.5", "unit": "EA"},
    {"item_id": "SAIL-F045",  "cpse": "SAIL",       "description": "Weld Neck Flange, Raised Face, Class 150, Carbon Steel A105, 6 inch, per ASME B16.5", "unit": "Nos"},
    {"item_id": "COAL-F112",  "cpse": "Coal India", "description": "Flange, WN type, RF, 150 class, A105 CS, 6\" NB", "unit": "PCS"},

    # GROUP 2: Flange — ASME B16.5, Class 300, RF, ASTM A182 F316 (stainless), 4"
    {"item_id": "GAIL-F210",  "cpse": "GAIL",       "description": "Flange SO RF 300# ASTM A182 F316 4IN", "unit": "EA"},
    {"item_id": "ONGC-F088",  "cpse": "ONGC",       "description": "Slip-On Flange, Raised Face, Class 300, SS A182 F316, 4 inch", "unit": "Nos"},

    # GROUP 3: Ball Valve — API 6D, Class 800, ASTM A105, 2", screwed end
    {"item_id": "ONGC-V002",  "cpse": "ONGC",       "description": "Ball Valve 2IN A105 800# Screwed End API 6D", "unit": "EA"},
    {"item_id": "SAIL-V046",  "cpse": "SAIL",       "description": "Valve, Ball Type, Carbon Steel A105, 2 inch, 800 class, Screwed End, API 6D compliant", "unit": "Nos"},
    {"item_id": "OIL-V300",   "cpse": "Oil India",  "description": "API 6D Ball Valve, Screwed, 2\", Class 800, A105", "unit": "PCS"},

    # GROUP 4: Gasket — ASME B16.20 Spiral Wound, Class 150, 4"
    {"item_id": "ONGC-G003",  "cpse": "ONGC",       "description": "Gasket Spiral Wound 4IN 150# ASME B16.20", "unit": "EA"},
    {"item_id": "COAL-G113",  "cpse": "Coal India", "description": "Spiral Wound Gasket, 4 inch, Class 150, per ASME B16.20", "unit": "PCS"},

    # GROUP 5: Gate Valve — API 6D, Class 600, ASTM A216 WCB, 8"
    {"item_id": "GAIL-V405",  "cpse": "GAIL",       "description": "Gate Valve 8IN A216 WCB 600# API 6D Flanged", "unit": "EA"},
    {"item_id": "OIL-V301",   "cpse": "Oil India",  "description": "API 6D Gate Valve, Flanged Ends, 8 inch, Class 600, Cast Steel A216 WCB", "unit": "Nos"},

    # Unique / unrelated items — should NOT match anything above
    {"item_id": "SAIL-047",   "cpse": "SAIL",       "description": "Welding Electrode 3.15mm E6013", "unit": "KG"},
    {"item_id": "COAL-114",   "cpse": "Coal India", "description": "Safety Helmet, ISI Marked, Yellow", "unit": "EA"},
    {"item_id": "ONGC-P004",  "cpse": "ONGC",       "description": "Centrifugal Pump 5HP 415V 3Phase", "unit": "EA"},
    {"item_id": "OIL-P201",   "cpse": "Oil India",  "description": "Pump, Centrifugal Type, 5 HP, 415 Volt, Three Phase", "unit": "Nos"},
]

CONFIDENCE_THRESHOLD = 0.85

# Real spec token patterns: pressure class, ASTM grade, size, standard reference
SPEC_PATTERNS = [
    r"\d+#", r"class\s?\d+", r"\d+\s?(in|inch|IN|NB)", r"A\d{3}(\s?[A-Z0-9]+)?",
    r"F\d{3}", r"WCB", r"api\s?6d", r"asme\s?b16\.\d+", r"\d+\s?(hp|HP)", r"\d+\s?(v|V)",
]

def extract_specs(desc):
    tokens = set()
    for pattern in SPEC_PATTERNS:
        for m in re.findall(pattern, desc, flags=re.IGNORECASE):
            tokens.add(re.sub(r"\s+", "", str(m)).lower())
    return tokens

def spec_match_score(desc_a, desc_b):
    specs_a, specs_b = extract_specs(desc_a), extract_specs(desc_b)
    if not specs_a and not specs_b:
        return 0.5
    if not specs_a or not specs_b:
        return 0.3
    overlap = len(specs_a & specs_b)
    total = len(specs_a | specs_b)
    return overlap / total if total else 0.5

def unit_compat_score(unit_a, unit_b):
    equivalence = {"EA": "EA", "Nos": "EA", "PCS": "EA", "KG": "KG"}
    return 1.0 if equivalence.get(unit_a) == equivalence.get(unit_b) else 0.4

print("Loading SBERT semantic model (all-MiniLM-L6-v2)... first run will download it")
model = SentenceTransformer("all-MiniLM-L6-v2")
descriptions = [it["description"] for it in items]
embeddings = model.encode(descriptions, convert_to_tensor=True)

results = []
for i, j in itertools.combinations(range(len(items)), 2):
    a, b = items[i], items[j]
    if a["cpse"] == b["cpse"]:
        continue

    text_sim = float(util.cos_sim(embeddings[i], embeddings[j]))
    fuzzy_sim = fuzz.token_sort_ratio(a["description"], b["description"]) / 100.0
    text_score = 0.7 * text_sim + 0.3 * fuzzy_sim
    spec_score = spec_match_score(a["description"], b["description"])
    unit_score = unit_compat_score(a["unit"], b["unit"])

    confidence = 0.5 * text_score + 0.3 * spec_score + 0.2 * unit_score
    status = "AUTO-LINK" if confidence >= CONFIDENCE_THRESHOLD else "NEEDS REVIEW"

    results.append({
        "a": f"{a['item_id']} ({a['cpse']})", "a_desc": a["description"],
        "b": f"{b['item_id']} ({b['cpse']})", "b_desc": b["description"],
        "text": round(text_score, 3), "spec": round(spec_score, 3), "unit": round(unit_score, 3),
        "confidence": round(confidence, 3), "status": status
    })

results.sort(key=lambda r: -r["confidence"])

print(f"\n{'='*100}")
print(f"MATCHING ENGINE OUTPUT — {len(results)} cross-CPSE pairs scored (real-standard-grounded dataset, SBERT semantic matching)")
print(f"{'='*100}\n")

for r in results:
    print(f"[{r['status']:12}] confidence={r['confidence']}  (text={r['text']} | spec={r['spec']} | unit={r['unit']})")
    print(f"    A: {r['a']:20} — \"{r['a_desc']}\"")
    print(f"    B: {r['b']:20} — \"{r['b_desc']}\"")
    print()

auto_linked = sum(1 for r in results if r["status"] == "AUTO-LINK")
needs_review = len(results) - auto_linked
print(f"{'='*100}")
print(f"SUMMARY: {auto_linked} auto-linked (>={CONFIDENCE_THRESHOLD}), {needs_review} flagged for human review, out of {len(results)} cross-CPSE pairs")
print(f"{'='*100}")
