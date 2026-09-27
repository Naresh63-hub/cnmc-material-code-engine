"""
Realistic 4-CPSE Pilot Dataset Seeder
Includes ONGC, SAIL, IOCL, and GAIL engineering items:
- Flanges (WN, SO, Blind, RF, Class 150/300/600, ASTM A105, A182 F316)
- Valves (Gate, Ball, Globe, Check, Class 150/300/800, API 6D, ASME B16.34)
- Gaskets (Spiral Wound, 150#/300#, ASME B16.20, SS316 with Graphite filler)
- Pipes (Seamless, CS A106 Gr B, SS 316, Sch 40/80, 2IN, 4IN, 6IN)
- Pumps & Motors (Centrifugal, 5HP, 15HP, 415V, 3Phase)
- Bearings & Fasteners (Deep groove ball bearings, Stud bolts B7/2H)
"""

import json
from pathlib import Path
from .ingest import clean_description, extract_specs, normalize_unit


def generate_extended_catalog() -> list[dict]:
    raw_entries = [
        # --- FLANGES (Duplicates & Equivalents across ONGC, SAIL, IOCL, GAIL) ---
        {
            "id": "ONGC-FLG-101",
            "cpse": "ONGC",
            "raw": "Flange WN RF 150# ASTM A105 6IN ASME B16.5",
            "unit": "EA"
        },
        {
            "id": "SAIL-FLG-201",
            "cpse": "SAIL",
            "raw": "Weld Neck Flange, Raised Face, Class 150, Carbon Steel A105, 6 inch, per ASME B16.5",
            "unit": "EA"
        },
        {
            "id": "IOCL-FLG-301",
            "cpse": "IOCL",
            "raw": "FLANGE WELDNECK RF CL.150 MAT: A105 SIZE: 6\" SCH 40 STD ASME B16.5",
            "unit": "Nos"
        },
        {
            "id": "GAIL-FLG-401",
            "cpse": "GAIL",
            "raw": "6 INCH WELD NECK FLANGE 150 CLASS RAISED FACE ASTM A105 FOR GAS PIPELINE",
            "unit": "EA"
        },
        {
            "id": "ONGC-FLG-102",
            "cpse": "ONGC",
            "raw": "Slip-On Flange RF Class 300 SS A182 F316 4IN",
            "unit": "EA"
        },
        {
            "id": "IOCL-FLG-302",
            "cpse": "IOCL",
            "raw": "FLANGE SLIP ON RAISED FACE 300# STAINLESS STEEL 316 4 INCH",
            "unit": "PCS"
        },
        {
            "id": "GAIL-FLG-402",
            "cpse": "GAIL",
            "raw": "Flange SO RF 300# ASTM A182 F316 4IN ASME B16.5",
            "unit": "EA"
        },
        {
            "id": "SAIL-FLG-202",
            "cpse": "SAIL",
            "raw": "Blind Flange Class 150 Raised Face Carbon Steel A105 8 inch",
            "unit": "EA"
        },
        {
            "id": "ONGC-FLG-103",
            "cpse": "ONGC",
            "raw": "Flange Blind RF 150# ASTM A105 8IN ASME B16.5",
            "unit": "EA"
        },

        # --- VALVES (Ball, Gate, Globe, Check Valves across CPSEs) ---
        {
            "id": "ONGC-VLV-111",
            "cpse": "ONGC",
            "raw": "Ball Valve 2IN A105 800# Screwed End API 6D",
            "unit": "EA"
        },
        {
            "id": "SAIL-VLV-211",
            "cpse": "SAIL",
            "raw": "Valve, Ball Type, Carbon Steel A105, 2 inch, 800 class, Screwed End, API 6D compliant",
            "unit": "EA"
        },
        {
            "id": "IOCL-VLV-311",
            "cpse": "IOCL",
            "raw": "BALL VALVE 2\" 800# SCREWED NPT BODY ASTM A105 BALL SS316 API-6D",
            "unit": "Nos"
        },
        {
            "id": "GAIL-VLV-411",
            "cpse": "GAIL",
            "raw": "2 INCH BALL VALVE CLASS 800 FORGED CARBON STEEL A105 SCREWED ENDS TO API 6D",
            "unit": "EA"
        },
        {
            "id": "ONGC-VLV-112",
            "cpse": "ONGC",
            "raw": "Gate Valve 6IN 150# Flanged WCB API 600",
            "unit": "EA"
        },
        {
            "id": "SAIL-VLV-212",
            "cpse": "SAIL",
            "raw": "Valve Gate Type Cast Carbon Steel WCB 6 inch Class 150 Flanged Ends",
            "unit": "EA"
        },
        {
            "id": "IOCL-VLV-312",
            "cpse": "IOCL",
            "raw": "GATE VALVE 6\" 150# FLANGED RF BODY ASTM A216 WCB TRIM 13CR PER API 600",
            "unit": "EA"
        },
        {
            "id": "GAIL-VLV-412",
            "cpse": "GAIL",
            "raw": "Gate Valve 6IN Class 150 RF Body WCB Trim 8 to API 600",
            "unit": "Nos"
        },
        {
            "id": "ONGC-VLV-113",
            "cpse": "ONGC",
            "raw": "Check Valve 4IN 300# Flanged Swing Type WCB",
            "unit": "EA"
        },
        {
            "id": "IOCL-VLV-313",
            "cpse": "IOCL",
            "raw": "NON RETURN VALVE SWING CHECK 4\" 300# WCB FLANGED RF BS 1868",
            "unit": "EA"
        },

        # --- GASKETS (Spiral Wound Gaskets) ---
        {
            "id": "ONGC-GSK-121",
            "cpse": "ONGC",
            "raw": "Gasket Spiral Wound 4IN 150# ASME B16.20 SS316 with Graphite Filler",
            "unit": "EA"
        },
        {
            "id": "SAIL-GSK-221",
            "cpse": "SAIL",
            "raw": "Spiral Wound Metallic Gasket 4 inch 150 class SS 316 / Graphite filler to ASME B16.20",
            "unit": "EA"
        },
        {
            "id": "IOCL-GSK-321",
            "cpse": "IOCL",
            "raw": "GASKET METALLIC SPIRAL WOUND 4\" 150# WINDING SS316 GRAPHITE FILLER ASME B16.20",
            "unit": "PCS"
        },
        {
            "id": "GAIL-GSK-421",
            "cpse": "GAIL",
            "raw": "Gasket SW 4IN 150# SS316/Graphite with CS Outer Ring ASME B16.20",
            "unit": "Nos"
        },
        {
            "id": "ONGC-GSK-122",
            "cpse": "ONGC",
            "raw": "Gasket Spiral Wound 6IN 300# ASME B16.20 SS316/Graphite",
            "unit": "EA"
        },
        {
            "id": "IOCL-GSK-322",
            "cpse": "IOCL",
            "raw": "GASKET SW 6\" 300# RF SS316 FILLER GRAPHITE ASME B16.20",
            "unit": "EA"
        },

        # --- PIPES (Seamless Steel Pipes) ---
        {
            "id": "ONGC-PIP-131",
            "cpse": "ONGC",
            "raw": "Pipe Seamless Carbon Steel 4IN Sch 40 ASTM A106 Gr B",
            "unit": "MTR"
        },
        {
            "id": "SAIL-PIP-231",
            "cpse": "SAIL",
            "raw": "Seamless CS Pipe 4 inch Schedule 40 to ASTM A106 Grade B Beveled Ends",
            "unit": "MTR"
        },
        {
            "id": "IOCL-PIP-331",
            "cpse": "IOCL",
            "raw": "PIPE SMLS CS 4\" NB SCH.40 ASTM A106 GR.B BEVERAGE ENDS",
            "unit": "MTR"
        },
        {
            "id": "GAIL-PIP-431",
            "cpse": "GAIL",
            "raw": "Pipe CS SMLS 4IN Sch 40 ASTM A106 Gr B for Hydrocarbon Service",
            "unit": "MTR"
        },
        {
            "id": "ONGC-PIP-132",
            "cpse": "ONGC",
            "raw": "Pipe Seamless Stainless Steel 2IN Sch 80 ASTM A312 TP316",
            "unit": "MTR"
        },
        {
            "id": "IOCL-PIP-332",
            "cpse": "IOCL",
            "raw": "PIPE SMLS SS316 2\" SCH.80 ASTM A312 TP 316",
            "unit": "MTR"
        },

        # --- PUMPS & ELECTRICAL MOTORS ---
        {
            "id": "ONGC-PMP-141",
            "cpse": "ONGC",
            "raw": "Centrifugal Pump 5HP 415V 3Phase 2900 RPM for Cooling Water",
            "unit": "EA"
        },
        {
            "id": "IOCL-PMP-341",
            "cpse": "IOCL",
            "raw": "PUMP CENTRIFUGAL 5 HP 415 VOLT 3 PH 50 HZ FLAMEPROOF MOTOR",
            "unit": "Nos"
        },
        {
            "id": "GAIL-PMP-441",
            "cpse": "GAIL",
            "raw": "Centrifugal Water Pump 5HP 415V 3-Phase TEFC Motor",
            "unit": "EA"
        },
        {
            "id": "ONGC-PMP-142",
            "cpse": "ONGC",
            "raw": "Centrifugal Multi-Stage Pump 15HP 415V 3Phase Heavy Duty",
            "unit": "EA"
        },
        {
            "id": "SAIL-PMP-242",
            "cpse": "SAIL",
            "raw": "Pump Centrifugal Multistage 15 HP 415 Volt 3 Phase 50Hz for Industrial Feed",
            "unit": "EA"
        },

        # --- BEARINGS & CONSUMABLES (Distinct & Mis-match items for Safety Gate test) ---
        {
            "id": "ONGC-BRG-151",
            "cpse": "ONGC",
            "raw": "Deep Groove Ball Bearing SKF 6205 2RS C3",
            "unit": "EA"
        },
        {
            "id": "SAIL-BRG-251",
            "cpse": "SAIL",
            "raw": "Bearing Deep Groove Ball 6205-2RS1/C3 SKF Make",
            "unit": "EA"
        },
        {
            "id": "IOCL-BRG-351",
            "cpse": "IOCL",
            "raw": "BALL BEARING DEEP GROOVE 6205 2RS C3 CLEARANCE FAG/SKF",
            "unit": "Nos"
        },
        {
            "id": "SAIL-ELD-261",
            "cpse": "SAIL",
            "raw": "Welding Electrode 3.15mm AWS E6013 for Mild Steel",
            "unit": "KG"
        },
        {
            "id": "IOCL-ELD-361",
            "cpse": "IOCL",
            "raw": "ELECTRODE WELDING 3.15MM X 350MM AWS A5.1 E6013",
            "unit": "KG"
        },
        {
            "id": "GAIL-ELD-461",
            "cpse": "GAIL",
            "raw": "Welding Electrode Dia 3.15 mm Spec AWS E6013",
            "unit": "KG"
        },
        {
            "id": "SAIL-STL-271",
            "cpse": "SAIL",
            "raw": "Mild Steel Plate 12mm Thick IS 2062 Grade E250",
            "unit": "TON"
        },
        {
            "id": "ONGC-STL-171",
            "cpse": "ONGC",
            "raw": "MS Structural Plate 12mm Thk IS 2062 Gr E250",
            "unit": "TON"
        }
    ]

    standardized = []
    for item in raw_entries:
        raw_desc = item["raw"]
        clean_desc = clean_description(raw_desc)
        specs = extract_specs(raw_desc)
        uom = normalize_unit(item["unit"])

        standardized.append({
            "item_id": item["id"],
            "source_cpse": item["cpse"],
            "raw_description": raw_desc,
            "clean_description": clean_desc,
            "specs": specs,
            "unit_of_measure": uom,
            "category_hint": None,
        })

    return standardized
