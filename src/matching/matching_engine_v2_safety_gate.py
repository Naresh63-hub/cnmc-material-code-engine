"""
SIH26099 — Matching Engine v2 — With Safety Gate
====================================================
Core innovation added: even if text similarity is very high, the system will
NOT auto-merge two items if a SAFETY-CRITICAL attribute (pressure class,
material grade) differs. This is what separates this from a generic AI
deduplication tool — text similarity alone is not proof of interchangeability.

Examples corrected to Ministry of Petroleum & Natural Gas CPSEs only:
ONGC, IOCL, BPCL, HPCL, GAIL, Oil India. (SAIL/Coal India removed — wrong
ministry, were leftover from an earlier draft.)
"""

import re
import itertools
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

CONFIDENCE_THRESHOLD = 0.85

# Attributes that MUST match — if either is present and they differ, block
# auto-merge regardless of how high the text/overall confidence is.
SAFETY_CRITICAL_PATTERNS = {
    "pressure_class": r"(\d+)\s?#|class\s?(\d+)",
    "material_grade": r"(A\d{3}(?:\s?F\d{3})?|F\d{3}|WCB)",
}

OTHER_SPEC_PATTERNS = [r"\d+\s?(in|inch|IN|NB)", r"api\s?6d", r"asme\s?b16\.\d+"]

UNIT_EQUIVALENCE = {"EA": "EA", "Nos": "EA", "PCS": "EA", "Each": "EA", "KG": "KG"}

# ---- Sample dataset: petroleum-sector CPSEs only ----
items = [
    # GROUP 1: True match — Flange, Class 150, ASTM A105, 6", worded differently
    {"item_id": "ONGC-F001", "cpse": "ONGC",  "description": "Flange WN RF 150# ASTM A105 6IN ASME B16.5", "unit": "EA"},
    {"item_id": "IOCL-F210", "cpse": "IOCL",  "description": "Weld Neck Flange, Raised Face, Class 150, Carbon Steel A105, 6 inch, per ASME B16.5", "unit": "Nos"},

    # GROUP 2: THE CENTERPIECE CASE — near-identical text, DIFFERENT pressure class
    # These should score high on text similarity but get BLOCKED by the Safety Gate.
    {"item_id": "BPCL-F301", "cpse": "BPCL",  "description": "Flange WN RF 150# ASTM A105 6IN ASME B16.5", "unit": "EA"},
    {"item_id": "HPCL-F302", "cpse": "HPCL",  "description": "Flange WN RF 300# ASTM A105 6IN ASME B16.5", "unit": "EA"},

    # GROUP 3: True match — Ball Valve, Class 800, A105, 2"
    {"item_id": "GAIL-V210", "cpse": "GAIL",  "description": "Ball Valve 2IN A105 800# Screwed End API 6D", "unit": "EA"},
    {"item_id": "OIL-V300",  "cpse": "Oil India", "description": "API 6D Ball Valve, Screwed, 2\", Class 800, A105", "unit": "PCS"},

    # GROUP 4: Near match but different MATERIAL GRADE — should also be blocked
    {"item_id": "ONGC-V450", "cpse": "ONGC",  "description": "Gate Valve 8IN A216 WCB 600# API 6D Flanged", "unit": "EA"},
    {"item_id": "IOCL-V451", "cpse": "IOCL",  "description": "Gate Valve 8IN A182 F316 600# API 6D Flanged", "unit": "Nos"},

    # Unrelated — should score low across the board
    {"item_id": "HPCL-999",  "cpse": "HPCL",  "description": "Welding Electrode 3.15mm E6013", "unit": "KG"},
]


def extract_safety_attrs(desc: str) -> dict:
    """Extract the critical attributes that must match for a safe merge."""
    attrs = {}
    for name, pattern in SAFETY_CRITICAL_PATTERNS.items():
        match = re.search(pattern, desc, flags=re.IGNORECASE)
        if match:
            value = next(g for g in match.groups() if g)
            attrs[name] = value.strip().upper()
    return attrs


def extract_other_specs(desc: str) -> set:
    tokens = set()
    for pattern in OTHER_SPEC_PATTERNS:
        for m in re.findall(pattern, desc, flags=re.IGNORECASE):
            tokens.add(re.sub(r"\s+", "", str(m)).lower())
    return tokens


def safety_gate_check(attrs_a: dict, attrs_b: dict) -> tuple:
    """Returns (blocked: bool, reason: str or None)."""
    for attr_name in SAFETY_CRITICAL_PATTERNS:
        val_a, val_b = attrs_a.get(attr_name), attrs_b.get(attr_name)
        if val_a and val_b and val_a != val_b:
            return True, f"{attr_name} differs: {val_a} vs {val_b}"
    return False, None


def spec_match_score(desc_a: str, desc_b: str) -> float:
    specs_a, specs_b = extract_other_specs(desc_a), extract_other_specs(desc_b)
    if not specs_a and not specs_b:
        return 0.5
    if not specs_a or not specs_b:
        return 0.3
    overlap = len(specs_a & specs_b)
    total = len(specs_a | specs_b)
    return overlap / total if total else 0.5


def unit_compat_score(unit_a: str, unit_b: str) -> float:
    return 1.0 if UNIT_EQUIVALENCE.get(unit_a) == UNIT_EQUIVALENCE.get(unit_b) else 0.4


# ---- Compute text similarity (TF-IDF stand-in for SBERT, same sandbox limitation) ----
descriptions = [it["description"] for it in items]
vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
tfidf_matrix = vectorizer.fit_transform(descriptions)
sim_matrix = cosine_similarity(tfidf_matrix)

results = []
for i, j in itertools.combinations(range(len(items)), 2):
    a, b = items[i], items[j]
    if a["cpse"] == b["cpse"]:
        continue

    text_sim = float(sim_matrix[i][j])
    fuzzy_sim = fuzz.token_sort_ratio(a["description"], b["description"]) / 100.0
    text_score = 0.7 * text_sim + 0.3 * fuzzy_sim
    spec_score = spec_match_score(a["description"], b["description"])
    unit_score = unit_compat_score(a["unit"], b["unit"])
    confidence = 0.5 * text_score + 0.3 * spec_score + 0.2 * unit_score

    attrs_a, attrs_b = extract_safety_attrs(a["description"]), extract_safety_attrs(b["description"])
    blocked, reason = safety_gate_check(attrs_a, attrs_b)

    if blocked:
        status = "BLOCKED — SAFETY GATE"
    elif confidence >= CONFIDENCE_THRESHOLD:
        status = "AUTO-LINK"
    else:
        status = "NEEDS REVIEW"

    results.append({
        "a": f"{a['item_id']} ({a['cpse']})", "a_desc": a["description"],
        "b": f"{b['item_id']} ({b['cpse']})", "b_desc": b["description"],
        "confidence": round(confidence, 3), "status": status,
        "safety_attrs_a": attrs_a, "safety_attrs_b": attrs_b, "block_reason": reason,
    })

results.sort(key=lambda r: -r["confidence"])

print(f"{'='*100}\nMATCHING ENGINE v2 — WITH SAFETY GATE — {len(results)} cross-CPSE pairs\n{'='*100}\n")
for r in results:
    print(f"[{r['status']:24}] confidence={r['confidence']}")
    print(f"    A: {r['a']:20} — \"{r['a_desc']}\"  attrs={r['safety_attrs_a']}")
    print(f"    B: {r['b']:20} — \"{r['b_desc']}\"  attrs={r['safety_attrs_b']}")
    if r["block_reason"]:
        print(f"    >>> SAFETY GATE TRIGGERED: {r['block_reason']}")
    print()

blocked = sum(1 for r in results if "BLOCKED" in r["status"])
auto = sum(1 for r in results if r["status"] == "AUTO-LINK")
review = len(results) - blocked - auto
print(f"{'='*100}\nSUMMARY: {auto} auto-linked | {review} needs review | {blocked} BLOCKED by Safety Gate\n{'='*100}")
