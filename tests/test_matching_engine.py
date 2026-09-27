"""
Comprehensive Unit Test Suite for SIH26099 Redesigned Matching Engine
Covers all 10 required benchmark scenarios from Phase 13.
"""

import pytest
from src.ingestion.ingest import extract_specs, clean_description, normalize_unit
from src.matching.ontology import (
    classify_category,
    canonicalize_size,
    canonicalize_pressure,
    canonicalize_material,
    are_materials_compatible,
)
from src.matching.match_from_pipeline import (
    run_matching,
    evaluate_technical_compatibility,
    calculate_semantic_similarity,
)


def build_item(item_id: str, cpse: str, desc: str, unit: str = "EA") -> dict:
    specs = extract_specs(desc)
    return {
        "item_id": item_id,
        "source_cpse": cpse,
        "raw_description": desc,
        "clean_description": clean_description(desc),
        "category": specs["category"],
        "category_subtype": specs["category_subtype"],
        "specs": specs,
        "unit_of_measure": normalize_unit(unit),
        "category_hint": specs["category"],
    }


class TestMatchingEngine:

    # -------------------------------------------------------------------------
    # TEST 1: Gate Valve 4" CS Class 150 == 4 Inch Gate Valve Carbon Steel 150#
    # -------------------------------------------------------------------------
    def test_01_exact_duplicate_gate_valve(self):
        item_a = build_item("ONGC-V01", "ONGC", "Gate Valve 4\" CS Class 150")
        item_b = build_item("SAIL-V01", "SAIL", "4 Inch Gate Valve Carbon Steel 150#")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]

        assert m["status"] == "auto_linked"
        assert m["sub_classification"] == "EXACT_DUPLICATE"
        assert m["confidence_score"] >= 0.85
        assert m["explanation"]["critical_conflicts_count"] == 0

    # -------------------------------------------------------------------------
    # TEST 2: Gate Valve DN100 CS Class 150 vs Class 600 -> CRITICAL CONFLICT
    # -------------------------------------------------------------------------
    def test_02_pressure_class_conflict_safety_gate(self):
        item_a = build_item("ONGC-V02", "ONGC", "Gate Valve DN100 CS Class 150")
        item_b = build_item("SAIL-V02", "SAIL", "Gate Valve DN100 CS Class 600")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]

        assert m["status"] == "safety_gate_blocked"
        assert "Pressure class mismatch" in m["block_reason"]
        assert m["sub_classification"] == "CONFLICT_BLOCKED"

    # -------------------------------------------------------------------------
    # TEST 3: Flange 6" Class 150 vs Ball Valve 2" Class 800 -> CATEGORY BLOCK
    # -------------------------------------------------------------------------
    def test_03_category_blocking_flange_vs_valve(self):
        item_a = build_item("ONGC-F01", "ONGC", "Flange 6\" Class 150 Raised Face A105")
        item_b = build_item("SAIL-V03", "SAIL", "Ball Valve 2\" Class 800 A105")

        matches = run_matching([item_a, item_b])
        # Category blocking eliminates cross-category noise
        assert len(matches) == 0 or matches[0]["status"] == "no_match"

    # -------------------------------------------------------------------------
    # TEST 4: Non Return Valve vs Check Valve -> DOMAIN SYNONYM MATCH
    # -------------------------------------------------------------------------
    def test_04_synonym_non_return_valve_vs_check_valve(self):
        item_a = build_item("ONGC-V04", "ONGC", "Non Return Valve 4IN 300# Flanged WCB")
        item_b = build_item("IOCL-V04", "IOCL", "Swing Check Valve 4\" 300# Flanged RF WCB")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]

        assert m["status"] in ("auto_linked", "needs_review")
        assert m["confidence_score"] >= 0.75
        assert m["category"] == "VALVE"

    # -------------------------------------------------------------------------
    # TEST 5: Multistage Pump 15HP 415V -> HIGH COMPATIBILITY SCORE
    # -------------------------------------------------------------------------
    def test_05_multistage_pump_electrical_specs(self):
        item_a = build_item("ONGC-P05", "ONGC", "Centrifugal Multi-Stage Pump 15HP 415V 3Phase Heavy Duty")
        item_b = build_item("SAIL-P05", "SAIL", "Pump Centrifugal Multistage 15 HP 415 Volt 3 Phase 50Hz for Industrial Feed")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]

        # Significantly higher than the old 0.608
        assert m["confidence_score"] >= 0.80
        assert m["explanation"]["technical_score_pct"] >= 80

    # -------------------------------------------------------------------------
    # TEST 6: Flange 6" Class 150 vs Gasket 4" Class 150 -> NO MATCH
    # -------------------------------------------------------------------------
    def test_06_category_blocking_flange_vs_gasket(self):
        item_a = build_item("ONGC-F06", "ONGC", "Flange Weld Neck 6\" Class 150 A105")
        item_b = build_item("IOCL-G06", "IOCL", "Gasket Spiral Wound 4\" Class 150 SS316")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 0 or matches[0]["status"] == "no_match"

    # -------------------------------------------------------------------------
    # TEST 7: Missing Pressure on one item -> NEEDS_REVIEW, NEVER AUTO_LINKED
    # -------------------------------------------------------------------------
    def test_07_unverified_critical_attribute_prevents_auto_link(self):
        item_a = build_item("ONGC-V07", "ONGC", "Gate Valve 4\" Class 150 A105")
        item_b = build_item("SAIL-V07", "SAIL", "Gate Valve 4\" A105 Flanged")  # Pressure missing!

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]

        assert m["status"] == "needs_review"
        assert m["sub_classification"] == "NEEDS_SPEC_VALIDATION"
        assert "pressure_rating" in m["explanation"]["unverified_critical"]

    # -------------------------------------------------------------------------
    # TEST 8: A216 WCB vs WCB -> COMPATIBLE REPRESENTATION
    # -------------------------------------------------------------------------
    def test_08_wcb_vs_a216_wcb_normalization(self):
        mat_a = canonicalize_material("A216 WCB")
        mat_b = canonicalize_material("WCB")

        status, score = are_materials_compatible(mat_a, mat_b)
        assert status == "EXACT_MATCH"
        assert score == 1.0

    # -------------------------------------------------------------------------
    # TEST 9: CL.150 vs Class 150 -> EQUAL (CL150)
    # -------------------------------------------------------------------------
    def test_09_pressure_class_canonicalization(self):
        p1 = canonicalize_pressure("CL.150")
        p2 = canonicalize_pressure("Class 150")
        p3 = canonicalize_pressure("150#")

        assert p1 == "CL150"
        assert p2 == "CL150"
        assert p3 == "CL150"

    # -------------------------------------------------------------------------
    # TEST 10: 4" vs DN100 -> EQUAL (DN100)
    # -------------------------------------------------------------------------
    def test_10_size_canonicalization_inch_to_dn(self):
        s1 = canonicalize_size('4"')
        s2 = canonicalize_size("4 IN")
        s3 = canonicalize_size("4 inch")
        s4 = canonicalize_size("DN100")
        s5 = canonicalize_size("100 NB")

        assert s1 == "DN100"
        assert s2 == "DN100"
        assert s3 == "DN100"
        assert s4 == "DN100"
        assert s5 == "DN100"

    # -------------------------------------------------------------------------
    # TEST A: 15 HP 415V 3PH 2900 RPM vs 1440 RPM -> SAFETY GATE BLOCKED
    # -------------------------------------------------------------------------
    def test_safety_a_motor_speed_mismatch_blocked(self):
        item_a = build_item("ONGC-M01", "ONGC", "INDUCTION MOTOR 15 HP 415V 50HZ 3PH 2900 RPM")
        item_b = build_item("SAIL-M01", "SAIL", "INDUCTION MOTOR 15 HP 415V 50HZ 3PH 1440 RPM")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert m["sub_classification"] == "CONFLICT_BLOCKED"
        assert "speed_rpm mismatch" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST B: 15 HP 415V 3PH 2900 RPM vs 2900 RPM -> ELIGIBLE FOR MATCHING
    # -------------------------------------------------------------------------
    def test_safety_b_motor_speed_match_eligible(self):
        item_a = build_item("ONGC-M02", "ONGC", "INDUCTION MOTOR 15 HP 415V 50HZ 3PH 2900 RPM")
        item_b = build_item("IOCL-M02", "IOCL", "Squirrel Cage Induction Motor 15HP 415V 3 Phase 2900 RPM")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "auto_linked"
        assert m["confidence_score"] >= 0.85

    # -------------------------------------------------------------------------
    # TEST C: 4" CS CL150 vs 4" CS CL600 -> SAFETY GATE BLOCKED
    # -------------------------------------------------------------------------
    def test_safety_c_gate_valve_pressure_mismatch_blocked(self):
        item_a = build_item("ONGC-V03", "ONGC", "Gate Valve 4\" Carbon Steel Class 150 RF")
        item_b = build_item("SAIL-V03", "SAIL", "Gate Valve 4\" Carbon Steel Class 600 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Pressure class mismatch" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST D: 4" CS vs 6" CS -> SAFETY GATE BLOCKED
    # -------------------------------------------------------------------------
    def test_safety_d_gate_valve_size_mismatch_blocked(self):
        item_a = build_item("ONGC-V04", "ONGC", "Gate Valve 4\" CS Class 150 RF")
        item_b = build_item("SAIL-V04", "SAIL", "Gate Valve 6\" CS Class 150 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Size mismatch" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST E: CS vs SS316 -> SAFETY GATE BLOCKED
    # -------------------------------------------------------------------------
    def test_safety_e_gate_valve_material_mismatch_blocked(self):
        item_a = build_item("ONGC-V05", "ONGC", "Gate Valve 4\" CS Class 150 RF")
        item_b = build_item("SAIL-V05", "SAIL", "Gate Valve 4\" SS316 Class 150 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Material incompatibility" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST F: 5 HP vs 15 HP -> SAFETY GATE BLOCKED
    # -------------------------------------------------------------------------
    def test_safety_f_pump_power_mismatch_blocked(self):
        item_a = build_item("ONGC-P06", "ONGC", "Centrifugal Pump 5HP 415V 3 Phase")
        item_b = build_item("SAIL-P06", "SAIL", "Centrifugal Pump 15HP 415V 3 Phase")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "power_hp mismatch" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST G: GATE VALVE vs BUTTERFLY VALVE -> NOT AUTO-LINKED
    # -------------------------------------------------------------------------
    def test_safety_g_valve_subtype_mismatch_not_auto_linked(self):
        item_a = build_item("ONGC-V07", "ONGC", "Gate Valve 4\" CS Class 150 RF")
        item_b = build_item("SAIL-V07", "SAIL", "Butterfly Valve 4\" CS Class 150 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] != "auto_linked"
        assert m["status"] in ("safety_gate_blocked", "needs_review", "no_match")
        if m["status"] == "safety_gate_blocked":
            assert "Subtype conflict" in m["block_reason"]

    # -------------------------------------------------------------------------
    # TEST H: Equivalent wording -> ELIGIBLE FOR AUTO-LINK
    # -------------------------------------------------------------------------
    def test_safety_h_equivalent_wording_auto_linked(self):
        item_a = build_item("ONGC-V08", "ONGC", "VLV GATE 100NB CS 150# RF")
        item_b = build_item("IOCL-V08", "IOCL", "Gate Valve DN100 Carbon Steel Class 150 Raised Face")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "auto_linked"
        assert m["confidence_score"] >= 0.85

    # =========================================================================
    # STEP 1 SPECIFIED REGRESSION TESTS (TEST 1 to TEST 8)
    # =========================================================================

    def test_req_01_motor_rpm_conflict(self):
        """TEST 1: Motor RPM Conflict (2900 RPM vs 1440 RPM) -> CRITICAL CONFLICT, SAFETY BLOCKED"""
        item_a = build_item("ONGC-MTR-1501", "ONGC", "Induction Motor 15 HP 415V 50Hz 3PH 2900 RPM")
        item_b = build_item("SAIL-MTR-4501", "SAIL", "Induction Motor 15 HP 415V 50Hz 3PH 1440 RPM")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "speed_rpm mismatch" in m["block_reason"]
        assert m["status"] != "auto_linked"

    def test_req_02_same_motor(self):
        """TEST 2: Same Motor (2900 RPM vs 2900 RPM) -> ELIGIBLE, NO RPM CONFLICT"""
        item_a = build_item("ONGC-MTR-1501", "ONGC", "Induction Motor 15 HP 415V 50Hz 3PH 2900 RPM")
        item_b = build_item("SAIL-MTR-1502", "SAIL", "Induction Motor 15 HP 415V 50Hz 3PH 2900 RPM")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] != "safety_gate_blocked"
        assert m["status"] == "auto_linked"
        assert m["confidence_score"] >= 0.85

    def test_req_03_valve_pressure_conflict(self):
        """TEST 3: Valve Pressure Conflict (CL150 vs CL600) -> SAFETY BLOCKED"""
        item_a = build_item("ONGC-V01", "ONGC", "GATE VALVE 4\" CS CL150 RF")
        item_b = build_item("SAIL-V01", "SAIL", "GATE VALVE 4\" CS CL600 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Pressure class mismatch" in m["block_reason"]

    def test_req_04_valve_size_conflict(self):
        """TEST 4: Valve Size Conflict (4\" vs 6\") -> SAFETY BLOCKED"""
        item_a = build_item("ONGC-V02", "ONGC", "GATE VALVE 4\" CS CL150 RF")
        item_b = build_item("SAIL-V02", "SAIL", "GATE VALVE 6\" CS CL150 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Size mismatch" in m["block_reason"]

    def test_req_05_material_conflict(self):
        """TEST 5: Material Conflict (CS vs SS316) -> SAFETY BLOCKED"""
        item_a = build_item("ONGC-V03", "ONGC", "GATE VALVE 4\" CS CL150 RF")
        item_b = build_item("SAIL-V03", "SAIL", "GATE VALVE 4\" SS316 CL150 RF")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "safety_gate_blocked"
        assert "Material incompatibility" in m["block_reason"]

    def test_req_06_normalized_equivalence(self):
        """TEST 6: Normalized Equivalence (4\" CS CL150 RF vs DN100 Carbon Steel Class 150 Raised Face)"""
        item_a = build_item("ONGC-V04", "ONGC", "GATE VALVE 4\" CS CL150 RF")
        item_b = build_item("IOCL-V04", "IOCL", "GATE VALVE DN100 CARBON STEEL CLASS 150 RAISED FACE")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] == "auto_linked"
        assert m["confidence_score"] >= 0.85

    def test_req_07_pipe_schedule_conflict(self):
        """TEST 7: Pipe Schedule Conflict (SCH40 vs SCH80) -> NOT AUTO-LINKED, CONFLICT BLOCKED"""
        item_a = build_item("ONGC-P01", "ONGC", "PIPE DN100 SCH40 A106 GR B")
        item_b = build_item("SAIL-P01", "SAIL", "PIPE DN100 SCH80 A106 GR B")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] != "auto_linked"
        assert m["status"] == "safety_gate_blocked"
        assert "Schedule mismatch" in m["block_reason"]

    def test_req_08_pump_power_representation(self):
        """TEST 8: Pump Power Representation (5 HP vs 3.7 kW) -> TECHNICALLY COMPATIBLE"""
        item_a = build_item("ONGC-PMP-01", "ONGC", "Centrifugal Pump 5 HP 415V 3 Phase")
        item_b = build_item("SAIL-PMP-01", "SAIL", "Centrifugal Pump 3.7 kW 415V 3 Phase")

        matches = run_matching([item_a, item_b])
        assert len(matches) == 1
        m = matches[0]
        assert m["status"] != "safety_gate_blocked"
        # Verify power was normalized to 5 HP on both
        assert item_a["specs"]["power_hp"] == "5 HP"
        assert item_b["specs"]["power_hp"] == "5 HP"
        assert m["confidence_score"] >= 0.80

