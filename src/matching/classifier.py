"""
SIH26099 Technical Compatibility Evaluation & Safety Gate Classifier
Evaluates multi-factor compatibility, enforces category safety gates,
and classifies matches into Exact/Near Duplicate vs Functional Equivalence.
"""

from typing import Any, Optional
from .ontology import (
    get_category_rules,
    are_materials_compatible,
    canonicalize_size,
    canonicalize_pressure,
    canonicalize_material,
)

CONFIDENCE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.60


def evaluate_technical_compatibility(item_a: dict, item_b: dict) -> dict[str, Any]:
    """
    Evaluate structural and technical attribute compatibility.
    Enforces category attribute criticality profiles, safety gates, and coverage-aware scoring.
    """
    specs_a = item_a.get("specs", {})
    specs_b = item_b.get("specs", {})

    category_a = item_a.get("category") or specs_a.get("category") or "OTHER"
    category_b = item_b.get("category") or specs_b.get("category") or "OTHER"

    rules = get_category_rules(category_a)
    critical_attrs = rules.get("critical", [])
    important_attrs = rules.get("important", [])

    spec_details = []
    critical_conflicts = []
    unverified_critical = []
    matching_specs = 0
    conflicting_specs = 0
    evaluated_specs = 0

    # 1. Category Check
    if category_a != category_b:
        critical_conflicts.append(f"Category mismatch: {category_a} vs {category_b}")
        spec_details.append({
            "attribute": "category",
            "val_a": category_a,
            "val_b": category_b,
            "status": "CONFLICT",
            "priority": "CRITICAL"
        })
        return {
            "technical_score": 0.0,
            "match_ratio": 0.0,
            "coverage_ratio": 0.0,
            "total_expected": len(critical_attrs) + len(important_attrs),
            "evaluated_specs": 1,
            "matching_specs": 0,
            "critical_conflicts": critical_conflicts,
            "unverified_critical": unverified_critical,
            "spec_details": spec_details,
            "is_category_compatible": False,
        }

    spec_details.append({
        "attribute": "category",
        "val_a": category_a,
        "val_b": category_b,
        "status": "MATCH",
        "priority": "CRITICAL"
    })
    matching_specs += 1
    evaluated_specs += 1

    # 2. Subtype Check (Gate Valve vs Ball Valve, Weld Neck vs Slip-On)
    sub_a = specs_a.get("category_subtype")
    sub_b = specs_b.get("category_subtype")
    if sub_a and sub_b:
        evaluated_specs += 1
        if sub_a == sub_b:
            matching_specs += 1
            spec_details.append({"attribute": "subtype", "val_a": sub_a, "val_b": sub_b, "status": "MATCH", "priority": "CRITICAL"})
        else:
            conflicting_specs += 1
            critical_conflicts.append(f"Subtype conflict: {sub_a} vs {sub_b}")
            spec_details.append({"attribute": "subtype", "val_a": sub_a, "val_b": sub_b, "status": "CONFLICT", "priority": "CRITICAL"})
    elif ("subtype" in critical_attrs or "category_subtype" in critical_attrs) and (sub_a or sub_b):
        unverified_critical.append("subtype")
        spec_details.append({"attribute": "subtype", "val_a": sub_a or "UNKNOWN", "val_b": sub_b or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # 3. Size Check (Canonical DN / Inch / MM)
    size_a = specs_a.get("size")
    size_b = specs_b.get("size")
    if size_a and size_b:
        evaluated_specs += 1
        if size_a == size_b:
            matching_specs += 1
            spec_details.append({"attribute": "size", "val_a": size_a, "val_b": size_b, "status": "MATCH", "priority": "CRITICAL"})
        else:
            conflicting_specs += 1
            critical_conflicts.append(f"Size mismatch: {size_a} vs {size_b}")
            spec_details.append({"attribute": "size", "val_a": size_a, "val_b": size_b, "status": "CONFLICT", "priority": "CRITICAL"})
    elif "size" in critical_attrs and (size_a or size_b):
        unverified_critical.append("size")
        spec_details.append({"attribute": "size", "val_a": size_a or "UNKNOWN", "val_b": size_b or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # 4. Pressure Rating Check (CL150, CL300, CL600, CL800, PN16)
    pres_a = specs_a.get("pressure_rating") or specs_a.get("pressure_class")
    pres_b = specs_b.get("pressure_rating") or specs_b.get("pressure_class")
    is_pressure_critical = "pressure_rating" in critical_attrs or "pressure_class" in critical_attrs
    if pres_a and pres_b:
        evaluated_specs += 1
        if pres_a == pres_b:
            matching_specs += 1
            spec_details.append({"attribute": "pressure_rating", "val_a": pres_a, "val_b": pres_b, "status": "MATCH", "priority": "CRITICAL"})
        else:
            conflicting_specs += 1
            critical_conflicts.append(f"Pressure class mismatch: {pres_a} vs {pres_b}")
            spec_details.append({"attribute": "pressure_rating", "val_a": pres_a, "val_b": pres_b, "status": "CONFLICT", "priority": "CRITICAL"})
    elif is_pressure_critical and (pres_a or pres_b):
        unverified_critical.append("pressure_rating")
        spec_details.append({"attribute": "pressure_rating", "val_a": pres_a or "UNKNOWN", "val_b": pres_b or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # 5. Material Grade & Base Metal Check
    mat_a_raw = specs_a.get("material_grade") or specs_a.get("material_family") or specs_a.get("raw_material")
    mat_b_raw = specs_b.get("material_grade") or specs_b.get("material_family") or specs_b.get("raw_material")
    is_material_critical = "material_grade" in critical_attrs or "material_family" in critical_attrs

    if mat_a_raw and mat_b_raw:
        evaluated_specs += 1
        mat_status, mat_val = are_materials_compatible(mat_a_raw, mat_b_raw)
        if mat_status == "EXACT_MATCH":
            matching_specs += 1.0
            spec_details.append({
                "attribute": "material_grade",
                "val_a": mat_a_raw,
                "val_b": mat_b_raw,
                "status": "MATCH",
                "priority": "CRITICAL"
            })
        elif mat_status == "COMPATIBLE_FAMILY":
            matching_specs += 0.85
            spec_details.append({
                "attribute": "material_grade",
                "val_a": mat_a_raw,
                "val_b": mat_b_raw,
                "status": "EQUIVALENT",
                "priority": "CRITICAL"
            })
        elif mat_status == "INCOMPATIBLE_FAMILY":
            conflicting_specs += 1
            critical_conflicts.append(f"Material incompatibility: {mat_a_raw} vs {mat_b_raw}")
            spec_details.append({
                "attribute": "material_grade",
                "val_a": mat_a_raw,
                "val_b": mat_b_raw,
                "status": "CONFLICT",
                "priority": "CRITICAL"
            })
        else:
            matching_specs += 0.5
            spec_details.append({
                "attribute": "material_grade",
                "val_a": mat_a_raw,
                "val_b": mat_b_raw,
                "status": "UNVERIFIED",
                "priority": "IMPORTANT"
            })
    elif is_material_critical and (mat_a_raw or mat_b_raw):
        unverified_critical.append("material_grade")
        spec_details.append({"attribute": "material_grade", "val_a": mat_a_raw or "UNKNOWN", "val_b": mat_b_raw or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # 6. Electrical Attributes (Power, Voltage, Phase, Speed RPM) for Pumps/Motors
    for elec_attr in ["power_hp", "voltage", "phase", "speed_rpm"]:
        val_a = specs_a.get(elec_attr)
        val_b = specs_b.get(elec_attr)
        if val_a and val_b:
            evaluated_specs += 1
            if val_a == val_b:
                matching_specs += 1
                spec_details.append({"attribute": elec_attr, "val_a": val_a, "val_b": val_b, "status": "MATCH", "priority": "CRITICAL" if elec_attr in critical_attrs else "IMPORTANT"})
            else:
                conflicting_specs += 1
                if elec_attr in critical_attrs:
                    critical_conflicts.append(f"{elec_attr} mismatch: {val_a} vs {val_b}")
                    spec_details.append({"attribute": elec_attr, "val_a": val_a, "val_b": val_b, "status": "CONFLICT", "priority": "CRITICAL"})
                else:
                    spec_details.append({"attribute": elec_attr, "val_a": val_a, "val_b": val_b, "status": "DIFFERENT", "priority": "IMPORTANT"})
        elif elec_attr in critical_attrs and (val_a or val_b):
            unverified_critical.append(elec_attr)
            spec_details.append({"attribute": elec_attr, "val_a": val_a or "UNKNOWN", "val_b": val_b or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # 7. Additional Attributes (Schedule, Connection, Facing, Bearing Number)
    for imp_attr in ["schedule", "connection_type", "facing", "bearing_number"]:
        val_a = specs_a.get(imp_attr)
        val_b = specs_b.get(imp_attr)
        is_attr_critical = imp_attr in critical_attrs
        if val_a and val_b:
            evaluated_specs += 1
            if val_a == val_b:
                matching_specs += 1
                spec_details.append({"attribute": imp_attr, "val_a": val_a, "val_b": val_b, "status": "MATCH", "priority": "CRITICAL" if is_attr_critical else "IMPORTANT"})
            else:
                if is_attr_critical:
                    conflicting_specs += 1
                    critical_conflicts.append(f"{imp_attr.capitalize()} mismatch: {val_a} vs {val_b}")
                    spec_details.append({"attribute": imp_attr, "val_a": val_a, "val_b": val_b, "status": "CONFLICT", "priority": "CRITICAL"})
                else:
                    conflicting_specs += 0.5
                    spec_details.append({"attribute": imp_attr, "val_a": val_a, "val_b": val_b, "status": "DIFFERENT", "priority": "IMPORTANT"})
        elif is_attr_critical and (val_a or val_b):
            unverified_critical.append(imp_attr)
            spec_details.append({"attribute": imp_attr, "val_a": val_a or "UNKNOWN", "val_b": val_b or "UNKNOWN", "status": "UNVERIFIED", "priority": "CRITICAL"})

    # Coverage & Spec Score calculation
    total_expected = len(critical_attrs) + len(important_attrs)
    coverage_ratio = round(evaluated_specs / max(total_expected, 1), 3)
    match_ratio = round(matching_specs / max(evaluated_specs, 1), 3)

    # Coverage-aware spec score
    spec_score = round(0.70 * match_ratio + 0.30 * min(coverage_ratio, 1.0), 3)

    return {
        "technical_score": spec_score,
        "match_ratio": match_ratio,
        "coverage_ratio": coverage_ratio,
        "total_expected": total_expected,
        "evaluated_specs": evaluated_specs,
        "matching_specs": matching_specs,
        "critical_conflicts": critical_conflicts,
        "unverified_critical": unverified_critical,
        "spec_details": spec_details,
        "is_category_compatible": True,
    }
