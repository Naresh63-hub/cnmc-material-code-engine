"""
SIH26099 Technical Attribute Extraction & Normalization
Extracts domain-specific parameters and normalizes them using the structural ontology.
"""

import re
from typing import Any, Optional
from .ontology import (
    classify_category,
    canonicalize_size,
    canonicalize_pressure,
    canonicalize_material,
    get_material_details,
)

# Standard abbreviation mappings
ABBREVIATIONS = {
    r"\bWN\b": "Weld Neck",
    r"\bRF\b": "Raised Face",
    r"\bFF\b": "Flat Face",
    r"\bRTJ\b": "Ring Type Joint",
    r"\bSO\b": "Slip-On",
    r"\bSS\b": "Stainless Steel",
    r"\bCS\b": "Carbon Steel",
    r"\bMS\b": "Mild Steel",
    r"\bSMLS\b": "Seamless",
    r"\bNRV\b": "Non Return Valve",
    r"\bSW\b": "Spiral Wound",
    r"\bNPT\b": "Screwed NPT",
    r"\bTEFC\b": "Totally Enclosed Fan Cooled",
    r"\bFLG\b": "Flange",
    r"\bVLV\b": "Valve",
    r"\bGSK\b": "Gasket",
    r"\bPIP\b": "Pipe",
    r"\bPMP\b": "Pump",
}

UNIT_EQUIVALENCE = {
    "EA": "EA", "NOS": "EA", "PCS": "EA", "EACH": "EA", "NO": "EA",
    "KG": "KG", "KGS": "KG", "KILOGRAM": "KG",
    "MTR": "MTR", "METER": "MTR", "METRE": "MTR", "M": "MTR",
    "TON": "TON", "TONS": "TON", "MT": "TON", "METRIC TON": "TON",
    "SET": "SET", "SETS": "SET",
    "LTR": "LTR", "LITRE": "LTR",
}


def clean_description(desc: str) -> str:
    """Preprocess description: expand abbreviations, normalize spaces & casing."""
    if not desc or not isinstance(desc, str):
        return ""
    cleaned = desc.strip()
    for pattern, replacement in ABBREVIATIONS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[\t\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_unit(unit: Any) -> str:
    """Standardize unit of measure."""
    if not unit:
        return "EA"
    u = str(unit).strip().upper()
    return UNIT_EQUIVALENCE.get(u, u)


def extract_specs(desc: str) -> dict[str, Any]:
    """
    Extract multi-notation structured specifications using domain regex patterns
    and canonicalize them via the domain ontology.
    """
    category, subtype = classify_category(desc)

    # 1. Size Extraction (4", 4 IN, 4 inch, 4 NB, 100 NB, 100NB, DN100, 1/2 Inch, 25mm OD)
    size_match = re.search(
        r"\b(?:DN|NB)\s*(\d+(?:\.\d+)?)\b|"
        r"\b(\d+(?:\.\d+)?)\s*(?:DN|NB)\b|"
        r"(\d+(?:\.\d+)?|\d+\s*[-/]\s*\d+)\s*(?:IN|INCH|''|\")\b|"
        r"\b(\d+(?:\.\d+)?)\s*\"|"
        r"\b(\d+(?:\.\d+)?)\s*(?:MM|M)\b",
        desc,
        flags=re.IGNORECASE,
    )
    raw_size = None
    if size_match:
        for grp in size_match.groups():
            if grp:
                raw_size = grp.strip()
                break
    size_canonical = canonicalize_size(raw_size)

    # 2. Pressure Rating Extraction (150#, Class 150, CL.150, 150 RF, 150 CLASS, 3000 PSI, PN16)
    pressure_match = re.search(
        r"(\d+)\s*#|"
        r"\b(?:CLASS|CL|CL\.)\s*(\d+)\b|"
        r"\b(\d+)\s*(?:CLASS|LBS|LB|PSI)\b|"
        r"\b(PN\s*\d+)\b|"
        r"\b(\d+)\s*(?:RF|FF|RTJ)\b",
        desc,
        flags=re.IGNORECASE,
    )
    raw_pressure = None
    if pressure_match:
        for grp in pressure_match.groups():
            if grp:
                raw_pressure = grp.strip()
                break
    pressure_canonical = canonicalize_pressure(raw_pressure)

    # 3. Material Grade Extraction (ASTM A105, A216 WCB, SS316, SS316L, Carbon Steel, CS, Stainless Steel, SS, IS 2062, AWS E6013)
    material_match = re.search(
        r"\b(ASTM\s*A\d{3}(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"A\d{3}(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"A\d{3}\s*F\d{3}|F\d{3}|WCB|A216\s*WCB|"
        r"SS\s*316L?|316L?\s*SS|STAINLESS\s*STEEL\s*316L?|"
        r"SS\s*304L?|304L?\s*SS|STAINLESS\s*STEEL\s*304L?|"
        r"FORGED\s*CARBON\s*STEEL|FORGED\s*STEEL|CAST\s*CARBON\s*STEEL|CAST\s*STEEL|"
        r"CARBON\s*STEEL|STAINLESS\s*STEEL|MILD\s*STEEL|\bCS\b|\bSS\b|\bMS\b|"
        r"IS\s*2062(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"AWS\s*(?:A\d\.\d\s*)?E\d{4}|E\d{4})\b",
        desc,
        flags=re.IGNORECASE,
    )
    raw_material = material_match.group(0).strip() if material_match else None
    material_info = get_material_details(raw_material) if raw_material else None

    # 4. Schedule & Wall Extraction (Sch 40, SCH40, Schedule 80, Sch.80, 2mm Wall)
    sch_match = re.search(r"\b(?:SCH|SCHEDULE)\.?\s*([A-Z0-9]+)\b", desc, flags=re.IGNORECASE)
    schedule = f"SCH_{sch_match.group(1).upper()}" if sch_match else None

    # 5. Electrical & Power Attributes (15HP, 1.5 KW, 415V, 230V, 3Phase, 50Hz, 1450 RPM)
    hp_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:HP|H\.P\.|KW)\b", desc, flags=re.IGNORECASE)
    power_hp = f"{hp_match.group(1)} HP" if hp_match else None

    v_match = re.search(r"\b(\d+)\s*(?:V|VOLT|VOLTS)\b", desc, flags=re.IGNORECASE)
    voltage = f"{v_match.group(1)}V" if v_match else None

    phase_match = re.search(r"\b(1|3)\s*(?:PHASE|PH)\b", desc, flags=re.IGNORECASE)
    phase = f"{phase_match.group(1)}_PHASE" if phase_match else None

    rpm_match = re.search(r"\b(\d+)\s*RPM\b", desc, flags=re.IGNORECASE)
    speed_rpm = f"{rpm_match.group(1)}_RPM" if rpm_match else None

    hz_match = re.search(r"\b(\d+)\s*HZ\b", desc, flags=re.IGNORECASE)
    frequency = f"{hz_match.group(1)}HZ" if hz_match else None

    # 6. Bearing Attributes (SKF 6205 2RS C3)
    brg_match = re.search(r"\b(\d{4,5})\s*(?:-?([A-Z0-9]+))?\s*(C[1-5])?\b", desc, flags=re.IGNORECASE)
    bearing_number = None
    seal_type = None
    clearance = None
    if category == "BEARING" and brg_match:
        bearing_number = brg_match.group(1)
        seal_type = brg_match.group(2) if brg_match.group(2) else "OPEN"
        clearance = brg_match.group(3) if brg_match.group(3) else "CN"

    # 7. Connection Type & Facing (Screwed, Flanged, Beveled, RF, FF, RTJ)
    conn_match = re.search(r"\b(SCREWED(?:\s*END)?|NPT|FLANGED(?:\s*ENDS)?|BEVELED(?:\s*ENDS)?|SOCKET\s*WELD)\b", desc, flags=re.IGNORECASE)
    connection_type = conn_match.group(0).upper().replace(" ", "_") if conn_match else None

    facing_match = re.search(r"\b(RAISED\s*FACE|RF|FLAT\s*FACE|FULL\s*FACE|FF|RING\s*TYPE\s*JOINT|RTJ)\b", desc, flags=re.IGNORECASE)
    facing = None
    if facing_match:
        f_raw = facing_match.group(0).upper()
        if "RAISED" in f_raw or f_raw == "RF":
            facing = "RF"
        elif "FLAT" in f_raw or "FULL" in f_raw or f_raw == "FF":
            facing = "FF"
        elif "RING" in f_raw or f_raw == "RTJ":
            facing = "RTJ"
        else:
            facing = f_raw

    # 8. Standards & Specifications
    standards = []
    for std_regex in [r"API\s*6D", r"API\s*600", r"API\s*594", r"BS\s*1868", r"ASME\s*B16\.\d+", r"IS\s*2062", r"AWS\s*A\d\.\d"]:
        sm = re.search(std_regex, desc, flags=re.IGNORECASE)
        if sm:
            standards.append(sm.group(0).upper())

    # 9. Gasket Filler
    gasket_filler = "GRAPHITE" if ("GRAPHITE" in desc.upper()) else ("PTFE" if ("PTFE" in desc.upper()) else None)

    return {
        "category": category,
        "category_subtype": subtype,
        "size": size_canonical,
        "raw_size": raw_size,
        "pressure_rating": pressure_canonical,
        "raw_pressure": raw_pressure,
        "material_grade": material_info["canonical_grade"] if material_info else None,
        "material_family": material_info["family"] if material_info else None,
        "material_base": material_info["base_metal"] if material_info else None,
        "raw_material": raw_material,
        "schedule": schedule,
        "power_hp": power_hp,
        "voltage": voltage,
        "phase": phase,
        "speed_rpm": speed_rpm,
        "frequency": frequency,
        "connection_type": connection_type,
        "facing": facing,
        "standards": standards,
        "bearing_number": bearing_number,
        "seal_type": seal_type,
        "clearance": clearance,
        "gasket_filler": gasket_filler,
        "other_attrs": {
            "standards": standards,
            "facing": facing,
            "schedule": schedule,
        }
    }
