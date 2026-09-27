"""
Unit & Integration Tests for SIH26099 CSV Data Ingestion & Canonical Schema
Covers all 16 required test scenarios:
A. Standard comma CSV
B. Semicolon CSV
C. Tab-delimited CSV
D. UTF-8 BOM
E. Windows CRLF
F. Quoted comma inside description
G. Quoted newline inside description
H. SAP-style aliases: MATNR, MAKTX, MEINS
I. Lowercase canonical fields
J. Missing required column
K. Missing material code (row level)
L. Missing description (row level)
M. Missing UOM (row level)
N. Blank rows
O. Duplicate source rows
P. The actual 26-row demo CPSE CSV
"""

import io
import csv
from pathlib import Path
import pytest
from src.ingestion.ingest import (
    parse_and_validate_csv,
    detect_column_mapping,
    CANONICAL_FIELD_ALIASES,
)


class TestIngestionEngine:

    # -------------------------------------------------------------------------
    # TEST A: Standard comma CSV
    # -------------------------------------------------------------------------
    def test_a_standard_comma_csv(self):
        csv_data = (
            "material_code,material_description,uom,plant\n"
            "ONGC-101,Gate Valve 4IN CS Class 150 RF,EA,PLANT-01\n"
            "ONGC-102,Centrifugal Pump 15HP 415V,EA,PLANT-02\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 2
        assert report["invalid_rows"] == 0
        assert len(records) == 2
        assert records[0]["material_code"] == "ONGC-101"
        assert records[0]["source_cpse"] == "ONGC"
        assert records[0]["plant"] == "PLANT-01"
        assert records[0]["uom"] == "EA"

    # -------------------------------------------------------------------------
    # TEST B: Semicolon CSV
    # -------------------------------------------------------------------------
    def test_b_semicolon_csv(self):
        csv_data = (
            "material_code;material_description;uom;plant\n"
            "SAIL-S01;Gate Valve 6IN CS Class 300;EA;BOKARO\n"
            "SAIL-S02;Weld Neck Flange 4IN 150# RF;Nos;BHILAI\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="SAIL")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 2
        assert records[0]["material_code"] == "SAIL-S01"
        assert records[1]["plant"] == "BHILAI"

    # -------------------------------------------------------------------------
    # TEST C: Tab-delimited CSV
    # -------------------------------------------------------------------------
    def test_c_tab_delimited_csv(self):
        csv_data = (
            "material_code\tmaterial_description\tuom\n"
            "IOCL-T01\tCentrifugal Pump 5HP 415V\tEA\n"
            "IOCL-T02\tSeamless Pipe DN100 Sch40\tM\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="IOCL")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 2
        assert records[0]["material_code"] == "IOCL-T01"
        assert records[1]["uom"] == "M"

    # -------------------------------------------------------------------------
    # TEST D: UTF-8 BOM
    # -------------------------------------------------------------------------
    def test_d_utf8_bom(self):
        csv_text = (
            "material_code,material_description,uom\n"
            "GAIL-G01,Spiral Wound Gasket 4IN 150#,EA\n"
        )
        csv_data = b"\xef\xbb\xbf" + csv_text.encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="GAIL")
        assert report["valid_rows"] == 1
        assert records[0]["material_code"] == "GAIL-G01"
        assert records[0]["source_cpse"] == "GAIL"

    # -------------------------------------------------------------------------
    # TEST E: Windows CRLF
    # -------------------------------------------------------------------------
    def test_e_windows_crlf(self):
        csv_data = (
            "material_code,material_description,uom\r\n"
            "ONGC-PIP-01,Seamless Pipe 4IN Sch40 CS ASTM A106 Gr B,MTR\r\n"
            "ONGC-PIP-02,Seamless Pipe 6IN Sch80 CS ASTM A106 Gr B,MTR\r\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 2
        assert records[0]["unit_of_measure"] == "MTR"

    # -------------------------------------------------------------------------
    # TEST F: Quoted comma inside description
    # -------------------------------------------------------------------------
    def test_f_quoted_comma_inside_description(self):
        csv_data = (
            'material_code,material_description,uom\n'
            'SAIL-001,"Flange, Weld Neck, Raised Face, 150#, ASTM A105, 6IN",Nos\n'
            'SAIL-002,"Valve, Ball Type, Carbon Steel, 2IN, 800 Class",Nos\n'
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="SAIL")
        assert report["valid_rows"] == 2
        assert records[0]["material_description"] == "Flange, Weld Neck, Raised Face, 150#, ASTM A105, 6IN"
        assert records[0]["clean_description"] == "Flange, Weld Neck, Raised Face, 150#, ASTM A105, 6IN"

    # -------------------------------------------------------------------------
    # TEST G: Quoted newline inside description
    # -------------------------------------------------------------------------
    def test_g_quoted_newline_inside_description(self):
        csv_data = (
            'material_code,material_description,uom\n'
            'IOCL-P01,"Centrifugal Pump\n15HP 415V 3Phase\n2900 RPM",EA\n'
            'IOCL-V01,"Gate Valve 4IN\nClass 150 RF CS",EA\n'
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="IOCL")
        assert report["valid_rows"] == 2
        assert "\n" in records[0]["material_description"]
        assert records[0]["specs"]["power_hp"] == "15 HP"

    # -------------------------------------------------------------------------
    # TEST H: SAP-style aliases (MATNR, MAKTX, MEINS, MATKL, WERKS)
    # -------------------------------------------------------------------------
    def test_h_sap_style_aliases(self):
        csv_data = (
            "MATNR,MAKTX,MEINS,MATKL,WERKS\n"
            "SAP-10001,BALL VALVE 2IN 800# A105,ST,VALV,1001\n"
            "SAP-10002,WELD NECK FLANGE 6IN 150# A105,ST,FLAN,1002\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["valid_rows"] == 2
        assert report["column_mapping"]["MATNR"] == "material_code"
        assert report["column_mapping"]["MAKTX"] == "material_description"
        assert report["column_mapping"]["MEINS"] == "uom"
        assert report["column_mapping"]["MATKL"] == "material_group"
        assert report["column_mapping"]["WERKS"] == "plant"

        assert records[0]["material_code"] == "SAP-10001"
        assert records[0]["material_group"] == "VALV"
        assert records[0]["plant"] == "1001"

    # -------------------------------------------------------------------------
    # TEST I: Lowercase canonical fields
    # -------------------------------------------------------------------------
    def test_i_lowercase_canonical_fields(self):
        csv_data = (
            "material_code,material_description,uom\n"
            "LC-001,Seamless Pipe 2IN Sch40,M\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="IOCL")
        assert report["valid_rows"] == 1
        assert report["column_mapping"]["material_code"] == "material_code"
        assert report["column_mapping"]["material_description"] == "material_description"
        assert report["column_mapping"]["uom"] == "uom"

    # -------------------------------------------------------------------------
    # TEST J: Missing required column (Header Level)
    # -------------------------------------------------------------------------
    def test_j_missing_required_column(self):
        csv_data = (
            "material_code,material_description\n"
            "ONGC-001,Gate Valve 4IN CS Class 150\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert any("Missing mandatory column mapping for: uom" in err for err in report["errors"])
        assert report["valid_rows"] == 0

    # -------------------------------------------------------------------------
    # TEST K: Missing material code (Row Level)
    # -------------------------------------------------------------------------
    def test_k_missing_material_code(self):
        csv_data = (
            "material_code,material_description,uom\n"
            ",Gate Valve 4IN CS Class 150,EA\n"
            "ONGC-002,Valid Gate Valve 4IN CS,EA\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 1
        assert report["invalid_rows"] == 1
        assert report["missing_material_codes"] == 1
        assert len(records) == 1

    # -------------------------------------------------------------------------
    # TEST L: Missing description (Row Level)
    # -------------------------------------------------------------------------
    def test_l_missing_description(self):
        csv_data = (
            "material_code,material_description,uom\n"
            "ONGC-001,,EA\n"
            "ONGC-002,Valid Gate Valve 4IN CS,EA\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 1
        assert report["invalid_rows"] == 1
        assert report["missing_descriptions"] == 1
        assert len(records) == 1

    # -------------------------------------------------------------------------
    # TEST M: Missing UOM (Row Level)
    # -------------------------------------------------------------------------
    def test_m_missing_uom(self):
        csv_data = (
            "material_code,material_description,uom\n"
            "ONGC-001,Gate Valve 4IN CS Class 150,\n"
            "ONGC-002,Valid Gate Valve 4IN CS,EA\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 1
        assert report["invalid_rows"] == 1
        assert report["missing_uom"] == 1
        assert len(records) == 1

    # -------------------------------------------------------------------------
    # TEST N: Blank rows
    # -------------------------------------------------------------------------
    def test_n_blank_rows(self):
        csv_data = (
            "material_code,material_description,uom\n"
            "ONGC-001,Gate Valve 4IN CS Class 150,EA\n"
            "\n"
            "   ,   ,   \n"
            "ONGC-002,Globe Valve 4IN CS Class 150,EA\n"
            "\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data, default_cpse="ONGC")
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 2
        assert report["invalid_rows"] == 0
        assert len(records) == 2

    # -------------------------------------------------------------------------
    # TEST O: Duplicate source rows
    # -------------------------------------------------------------------------
    def test_o_duplicate_source_rows(self):
        csv_data = (
            "cpse,material_code,material_description,uom\n"
            "ONGC,ONGC-V01,Gate Valve 4IN CS Class 150,EA\n"
            "ONGC,ONGC-V01,Gate Valve 4IN CS Class 150 Duplicate,EA\n"
        ).encode("utf-8")

        records, report = parse_and_validate_csv(csv_data)
        assert report["total_rows"] == 2
        assert report["valid_rows"] == 1
        assert report["invalid_rows"] == 1
        assert report["duplicate_source_rows"] == 1
        assert len(records) == 1

    # -------------------------------------------------------------------------
    # TEST P: The actual 26-row demo CPSE CSV
    # -------------------------------------------------------------------------
    def test_p_actual_26_row_demo_csv(self):
        demo_paths = [
            Path(r"C:\Users\saich\Downloads\demo_cpse_material_master.csv"),
            Path("demo_cpse_material_master.csv"),
            Path("../demo_cpse_material_master.csv"),
        ]
        demo_file = None
        for p in demo_paths:
            if p.exists():
                demo_file = p
                break

        assert demo_file is not None, "demo_cpse_material_master.csv not found on disk"

        with open(demo_file, "rb") as f:
            content = f.read()

        records, report = parse_and_validate_csv(content)
        assert report["total_rows"] == 26
        assert report["valid_rows"] == 26
        assert report["invalid_rows"] == 0
        assert report["duplicate_source_rows"] == 0
        assert report["missing_material_codes"] == 0
        assert report["missing_descriptions"] == 0
        assert report["missing_uom"] == 0
        assert len(records) == 26

        # Check preserved raw fields and derived specs
        for r in records:
            assert r["source_cpse"] in ("ONGC", "SAIL", "IOCL", "GAIL")
            assert r["material_code"]
            assert r["material_description"]
            assert r["uom"]
            assert "raw_data" in r
            assert r["raw_description"] == r["material_description"]