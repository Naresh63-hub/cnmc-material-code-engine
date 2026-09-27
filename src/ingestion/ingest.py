"""
Tier 1 — Data Ingestion & Preprocessing
Reads raw multi-CPSE catalog files (different column names per source) and
outputs a standardized list of items matching the schema in ARCHITECTURE.md,
enriched with deterministic categorization and multi-notation technical extraction.
"""

import io
import csv
import re
import json
import pandas as pd
from typing import Optional, Any

from ..matching.ontology import (
    classify_category,
    canonicalize_size,
    canonicalize_pressure,
    canonicalize_material,
    canonicalize_power,
    get_material_details,
)

# Config: maps each CPSE's actual column names to our standard field names.
COLUMN_MAP = {
    "ONGC": {"id": "Material Code", "desc": "Description", "unit": "UOM"},
    "SAIL": {"id": "Item No", "desc": "Material Description", "unit": "Unit"},
    "IOCL": {"id": "Material Code", "desc": "Description", "unit": "UOM"},
    "GAIL": {"id": "Item No", "desc": "Description", "unit": "UOM"},
    "CIL": {"id": "Material Code", "desc": "Description", "unit": "UOM"},
}

# Domain Abbreviation Expansion Dictionary
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


def clean_description(raw_desc: str) -> str:
    """Expand common abbreviations, normalize punctuation, whitespace, and casing."""
    cleaned = raw_desc
    for pattern, expansion in ABBREVIATIONS.items():
        cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_specs(desc: str) -> dict[str, Any]:
    """
    Extract multi-notation structured specifications using domain regex patterns
    and canonicalize them via the domain ontology.
    """
    category, subtype = classify_category(desc)

    # 1. Size Extraction (4", 4 IN, 4 inch, 4 NB, DN100, 3.15mm, 12mm)
    size_match = re.search(
        r"\b(?:DN|NB)\s*(\d+)\b|\b(\d+)\s*(?:DN|NB)\b|"
        r"(\d+(?:\.\d+)?|\d+\s*[-/]\s*\d+)\s*(?:IN|INCH|''|\")\b|\b(\d+(?:\.\d+)?)\s*\"|"
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

    # 2. Pressure Rating Extraction (150#, Class 150, CL.150, 800 class, PN16)
    pressure_match = re.search(
        r"(\d+)\s*#|\b(?:CLASS|CL|CL\.)\s*(\d+)\b|\b(\d+)\s*(?:CLASS|LBS|LB)\b|\b(PN\s*\d+)\b",
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

    # 3. Material Grade Extraction (A105, A216 WCB, WCB, SS316, A182 F316, A106 Gr B, IS 2062, AWS E6013, CS, Carbon Steel)
    material_match = re.search(
        r"\b(ASTM\s*A\d{3}(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"A\d{3}(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"A\d{3}\s*F\d{3}|F\d{3}|WCB|A216\s*WCB|SS\s*316|SS\s*304|316\s*SS|304\s*SS|"
        r"IS\s*2062(?:\s*(?:Gr\.?|Grade)?\s*[A-Z0-9]+)?|"
        r"AWS\s*(?:A\d\.\d\s*)?E\d{4}|E\d{4}|"
        r"CARBON\s*STEEL|CAST\s*STEEL|FORGED\s*STEEL|STAINLESS\s*STEEL|CS)\b",
        desc,
        flags=re.IGNORECASE,
    )
    raw_material = material_match.group(0).strip() if material_match else None
    material_info = get_material_details(raw_material) if raw_material else None

    # 4. Schedule Extraction (Sch 40, SCH40, Schedule 80, Sch.80)
    sch_match = re.search(r"\b(?:SCH|SCHEDULE)\.?\s*([A-Z0-9]+)\b", desc, flags=re.IGNORECASE)
    schedule = f"SCH_{sch_match.group(1).upper()}" if sch_match else None

    # 5. Electrical & Power Attributes (15HP, 415V, 3Phase, 50Hz, 2900 RPM)
    hp_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:HP|H\.P\.|KW|KILOWATT)\b", desc, flags=re.IGNORECASE)
    power_hp = canonicalize_power(hp_match.group(0)) if hp_match else None

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

    facing_match = re.search(r"\b(RAISED\s*FACE|RF|FLAT\s*FACE|FF|RING\s*TYPE\s*JOINT|RTJ)\b", desc, flags=re.IGNORECASE)
    if facing_match:
        f_raw = facing_match.group(0).upper()
        if "RF" in f_raw or "RAISED" in f_raw:
            facing = "RF"
        elif "FF" in f_raw or "FLAT" in f_raw:
            facing = "FF"
        elif "RTJ" in f_raw or "RING" in f_raw:
            facing = "RTJ"
        else:
            facing = f_raw
    else:
        facing = None

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


def normalize_unit(unit: str) -> str:
    cleaned = unit.strip().upper()
    return UNIT_EQUIVALENCE.get(cleaned, cleaned)


# Canonical Field Aliases Mapping
CANONICAL_FIELD_ALIASES = {
    "material_code": [
        "material_code", "material code", "material", "item_code", "item code",
        "item_no", "item no", "code", "matnr", "material number",
        "material_no", "material_num", "materialnum", "id", "item_id", "itemid"
    ],
    "material_description": [
        "material_description", "material description", "description",
        "short_text", "short text", "short description", "short_description",
        "item description", "item_description", "maktx",
        "desc", "raw_description", "raw description", "material_desc", "material desc"
    ],
    "uom": [
        "uom", "unit", "unit of measure", "unit_of_measure", "base unit",
        "base_unit", "meins", "ea", "uom_code"
    ],
    "material_group": [
        "material_group", "material group", "matkl", "group", "category",
        "material category", "material_category", "item_group", "item group"
    ],
    "plant": [
        "plant", "plant code", "plant_code", "werks", "facility", "site", "location"
    ],
    "specification": [
        "specification", "specifications", "specs", "technical specification",
        "technical_specification", "tech_spec", "standard", "standards"
    ],
    "source_cpse": [
        "source_cpse", "source cpse", "cpse", "company", "organization", "org", "source"
    ],
    "manufacturer": [
        "manufacturer", "mfr", "make", "vendor", "brand", "producer"
    ],
    "manufacturer_part_no": [
        "manufacturer_part_no", "manufacturer part no", "part_no", "part no",
        "mpn", "part_number", "part number", "mfr_part_no"
    ],
}


def decode_csv_bytes(content: bytes) -> str:
    """
    Safely decode CSV bytes handling UTF-8, UTF-8 with BOM, and fallback encodings.
    """
    if content.startswith(b"\xef\xbb\xbf"):
        return content.decode("utf-8-sig")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except UnicodeDecodeError:
            return content.decode("cp1252", errors="replace")


def detect_delimiter(text: str) -> str:
    """
    Automatically detects delimiter (, or ; or \t) by analyzing the header line.
    """
    sample = text[:4096]
    first_line = sample.split("\n", 1)[0].split("\r", 1)[0]
    semicolons = first_line.count(";")
    commas = first_line.count(",")
    tabs = first_line.count("\t")

    if semicolons > commas and semicolons > tabs:
        return ";"
    if tabs > commas and tabs > semicolons:
        return "\t"
    return ","


def detect_column_mapping(headers: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    Map raw CSV headers to internal canonical field names using alias lookup.
    Returns:
        (detected_mapping: {source_header: canonical_field}, unmapped_columns: list[source_header])
    """
    detected_mapping = {}
    unmapped_columns = []
    mapped_canonicals = set()

    for header in headers:
        if not header:
            continue
        h_clean = header.strip().strip("'\"").strip().lstrip("\ufeff").strip()
        if not h_clean:
            continue
        h_norm = h_clean.lower().replace("-", "_").replace(" ", "_")
        h_norm_space = h_clean.lower().replace("-", " ").replace("_", " ")

        matched_field = None
        for canon_field, aliases in CANONICAL_FIELD_ALIASES.items():
            if canon_field in mapped_canonicals:
                continue
            for alias in aliases:
                a_norm = alias.lower().replace("-", "_").replace(" ", "_")
                a_norm_space = alias.lower().replace("-", " ").replace("_", " ")
                if h_norm == a_norm or h_norm_space == a_norm_space or h_clean.lower() == alias.lower():
                    matched_field = canon_field
                    break
            if matched_field:
                break

        if matched_field:
            detected_mapping[h_clean] = matched_field
            mapped_canonicals.add(matched_field)
        else:
            unmapped_columns.append(h_clean)

    return detected_mapping, unmapped_columns


def parse_and_validate_csv(
    content_or_path: Any,
    default_cpse: Optional[str] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Core Ingestion Engine for SIH26099.
    1. Reads .csv with newline="" and proper UTF-8/BOM/Windows/Linux newline handling.
    2. Uses Python's standard csv module (no naive string.split).
    3. Maps columns to canonical internal schema and validates mandatory fields.
    4. Preserves raw_data, raw_description, normalized_description, and extracted specs.
    5. Returns (valid_records, validation_report).
    """
    # 1. Read / decode text
    if isinstance(content_or_path, bytes):
        text = decode_csv_bytes(content_or_path)
    elif isinstance(content_or_path, str):
        path = Path(content_or_path)
        if path.exists() and path.is_file():
            with open(path, "rb") as f:
                text = decode_csv_bytes(f.read())
        else:
            text = content_or_path
    elif hasattr(content_or_path, "read"):
        raw_b = content_or_path.read()
        if isinstance(raw_b, str):
            text = raw_b
        else:
            text = decode_csv_bytes(raw_b)
    else:
        raise ValueError("Unsupported CSV content type. Expected bytes, str, or file-like object.")

    # Strip any leading BOM in string representation
    text = text.lstrip("\ufeff")

    if not text.strip():
        report = {
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "duplicate_source_rows": 0,
            "missing_material_codes": 0,
            "missing_descriptions": 0,
            "missing_uom": 0,
            "column_mapping": {},
            "unmapped_columns": [],
            "errors": ["CSV file is empty."],
        }
        return [], report

    delimiter = detect_delimiter(text)

    # 2. Open with newline="" for RFC 4180 parsing
    string_io = io.StringIO(text, newline="")
    try:
        reader = csv.reader(string_io, delimiter=delimiter)
        headers = next(reader, None)
    except csv.Error as e:
        raise ValueError(f"CSV parsing failed at row 1: malformed header ({str(e)})")

    if not headers or not [h for h in headers if h.strip()]:
        report = {
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "duplicate_source_rows": 0,
            "missing_material_codes": 0,
            "missing_descriptions": 0,
            "missing_uom": 0,
            "column_mapping": {},
            "unmapped_columns": [],
            "errors": ["CSV header is missing or empty."],
        }
        return [], report

    # Clean headers
    headers = [h.strip().strip("'\"").strip().lstrip("\ufeff").strip() for h in headers]
    detected_mapping, unmapped_columns = detect_column_mapping(headers)
    canon_to_src = {canon: src for src, canon in detected_mapping.items()}

    # Check required canonical columns presence
    missing_req_cols = []
    for req_field in ["material_code", "material_description", "uom"]:
        if req_field not in canon_to_src:
            missing_req_cols.append(req_field)

    validation_report = {
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "duplicate_source_rows": 0,
        "missing_material_codes": 0,
        "missing_descriptions": 0,
        "missing_uom": 0,
        "column_mapping": detected_mapping,
        "unmapped_columns": unmapped_columns,
        "errors": [],
    }

    if missing_req_cols:
        validation_report["errors"].append(
            f"Missing mandatory column mapping for: {', '.join(missing_req_cols)}"
        )

    # 3. Read data rows
    string_io.seek(0)
    try:
        dict_reader = csv.DictReader(string_io, delimiter=delimiter)
    except csv.Error as e:
        raise ValueError(f"CSV parsing failed: {str(e)}")

    valid_records = []
    seen_keys = set()
    row_idx = 0

    try:
        for row in dict_reader:
            # Clean keys in row
            clean_row = {
                (k.strip().strip("'\"").strip().lstrip("\ufeff").strip() if k else ""): v
                for k, v in row.items()
            }

            # Skip entirely blank rows
            if not any(str(v).strip() for v in clean_row.values() if v is not None):
                continue

            row_idx += 1
            validation_report["total_rows"] += 1
            row_errors = []

            # Extract fields via mapped columns
            raw_code = clean_row.get(canon_to_src.get("material_code", ""), "")
            raw_desc = clean_row.get(canon_to_src.get("material_description", ""), "")
            raw_uom = clean_row.get(canon_to_src.get("uom", ""), "")
            raw_cpse = clean_row.get(canon_to_src.get("source_cpse", ""), "")

            mat_group = clean_row.get(canon_to_src.get("material_group", ""), None) or None
            plant = clean_row.get(canon_to_src.get("plant", ""), None) or None
            spec = clean_row.get(canon_to_src.get("specification", ""), None) or None
            mfr = clean_row.get(canon_to_src.get("manufacturer", ""), None) or None
            mfr_part = clean_row.get(canon_to_src.get("manufacturer_part_no", ""), None) or None

            # Determine CPSE
            source_cpse = (raw_cpse or default_cpse or "GENERIC").strip().upper()

            code = str(raw_code).strip() if raw_code is not None else ""
            desc = str(raw_desc).strip() if raw_desc is not None else ""
            uom = str(raw_uom).strip() if raw_uom is not None else ""

            # Auto-fallback code if column was not present
            if not code and "material_code" not in canon_to_src:
                code = f"MAT-{row_idx:03d}"

            # Validate mandatory fields
            if not code:
                validation_report["missing_material_codes"] += 1
                row_errors.append("Missing material_code")
            if not desc:
                validation_report["missing_descriptions"] += 1
                row_errors.append("Missing material_description")
            if not uom:
                validation_report["missing_uom"] += 1
                row_errors.append("Missing uom")

            # Duplicate check across source CPSE + material_code
            source_key = (source_cpse, code)
            if code and source_key in seen_keys:
                validation_report["duplicate_source_rows"] += 1
                row_errors.append(f"Duplicate source item '{code}' for CPSE '{source_cpse}'")
            elif code:
                seen_keys.add(source_key)

            if row_errors:
                validation_report["invalid_rows"] += 1
                validation_report["errors"].append(f"Row {row_idx}: {'; '.join(row_errors)}")
                continue

            # Build canonical record
            validation_report["valid_rows"] += 1

            if code.upper().startswith(f"{source_cpse}-"):
                item_id = code
            else:
                item_id = f"{source_cpse}-{code}"

            clean_desc = clean_description(desc)
            specs = extract_specs(desc)

            if spec and spec not in (specs.get("standards") or []):
                stds = specs.get("standards") or []
                stds.append(spec)
                specs["standards"] = stds
                if "other_attrs" in specs:
                    specs["other_attrs"]["standards"] = stds

            if mat_group and not specs.get("category"):
                specs["category"] = mat_group.strip().upper()

            record = {
                # 1. Canonical Schema (Requirements 2 & 3)
                "source_cpse": source_cpse,
                "material_code": code,
                "material_description": desc,
                "uom": uom,
                "material_group": mat_group.strip() if mat_group else None,
                "plant": plant.strip() if plant else None,
                "specification": spec.strip() if spec else None,
                "manufacturer": mfr.strip() if mfr else None,
                "manufacturer_part_no": mfr_part.strip() if mfr_part else None,
                "raw_data": {str(k): v for k, v in clean_row.items() if k is not None},

                # 2. Downstream Harmonization Pipeline Fields (Requirements 3 & 10)
                "item_id": item_id,
                "raw_description": desc,
                "normalized_description": clean_desc,
                "clean_description": clean_desc,
                "category": specs.get("category"),
                "category_subtype": specs.get("category_subtype"),
                "specs": specs,
                "unit_of_measure": normalize_unit(uom),
                "category_hint": specs.get("category") or mat_group,
            }
            valid_records.append(record)

    except csv.Error as e:
        raise ValueError(f"CSV parsing failed at row {row_idx + 1}: malformed quoted field ({str(e)})")

    return valid_records, validation_report


def parse_catalog_file(
    content_or_path: Any,
    filename: Optional[str] = None,
    default_cpse: str = "GENERIC"
) -> list[dict]:
    """
    Public entrypoint for catalog parsing. Returns list of standardized records.
    """
    records, _ = parse_and_validate_csv(content_or_path, default_cpse=default_cpse)
    return records


def load_catalog(filepath: str, cpse: str) -> list[dict]:
    """Load one CPSE's catalog file and return standardized records."""
    return parse_catalog_file(filepath, filename=filepath, default_cpse=cpse)


if __name__ == "__main__":
    all_items = []
    all_items += load_catalog("src/ingestion/sample_ongc_catalog.csv", "ONGC")
    all_items += load_catalog("src/ingestion/sample_sail_catalog.csv", "SAIL")

    print(f"Loaded and standardized {len(all_items)} items from sample catalogs\n")
    for item in all_items[:2]:
        print(json.dumps(item, indent=2))
        print()

    with open("processed_catalog.jsonl", "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item) + "\n")
    print("Saved standardized output to processed_catalog.jsonl — ready for Tier 2")
