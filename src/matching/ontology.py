"""
SIH26099 Structural Engineering Ontology & Knowledge Base
Defines engineering categories, attribute criticality profiles, nominal dimension conversions,
pressure ratings, and material family compatibility hierarchies.
"""

import re
from typing import Optional, Any

# -----------------------------------------------------------------------------
# 1. CATEGORY DEFINITIONS & RECOGNITION PATTERNS
# -----------------------------------------------------------------------------

CATEGORIES = [
    "VALVE",
    "FLANGE",
    "GASKET",
    "PIPE",
    "PUMP",
    "MOTOR",
    "BEARING",
    "COMPRESSOR",
    "ELECTRICAL",
    "INSTRUMENT",
    "FITTING",
    "FASTENER",
    "STRUCTURAL_STEEL",
    "CONSUMABLE",
    "OTHER",
]

# Structural recognition keywords and subtypes (with flexible modifier tolerance)
CATEGORY_SUBTYPES = {
    "VALVE": [
        ("GATE_VALVE", [r"\bgate\b", r"\bknife\s*edge\b"]),
        ("BALL_VALVE", [r"\bball\b"]),
        ("GLOBE_VALVE", [r"\bglobe\b"]),
        ("CHECK_VALVE", [r"\bcheck\b", r"\bnon\s*return\b", r"\bnrv\b", r"\bswing\s*check\b", r"\bnon[- ]slam\b", r"\bdual\s*plate\b"]),
        ("BUTTERFLY_VALVE", [r"\bbutterfly\b"]),
        ("PLUG_VALVE", [r"\bplug\b"]),
        ("NEEDLE_VALVE", [r"\bneedle\b"]),
        ("CONTROL_VALVE", [r"\bcontrol\s*valve\b"]),
        ("SAFETY_VALVE", [r"\bsafety\s*valve\b", r"\brelief\s*valve\b", r"\bpsv\b", r"\bprv\b"]),
    ],
    "FLANGE": [
        ("WELD_NECK", [r"\bweld\s*neck\b", r"\bwn\b", r"\bwnrf\b"]),
        ("SLIP_ON", [r"\bslip\s*on\b", r"\bso\b", r"\bsorf\b"]),
        ("BLIND", [r"\bblind\b", r"\bblrf\b", r"\bspectacle\s*blind\b", r"\bfigure\s*8\b"]),
        ("SOCKET_WELD", [r"\bsocket\s*weld\b", r"\bsw\s*flange\b"]),
        ("THREADED", [r"\bthreaded\s*flange\b", r"\bscrewed\s*flange\b"]),
        ("LAP_JOINT", [r"\blap\s*joint\b", r"\blj\b"]),
    ],
    "GASKET": [
        ("SPIRAL_WOUND", [r"\bspiral\s*wound\b", r"\bswg\b"]),
        ("RING_JOINT", [r"\bring\s*joint\b", r"\brtj\b", r"\bring\s*type\s*joint\b"]),
        ("NON_ASBESTOS", [r"\bnon\s*asbestos\b", r"\bcna\b", r"\bcaf\b"]),
        ("PTFE_GASKET", [r"\bptfe\b", r"\bteflon\b", r"\bexpanded\s*ptfe\b"]),
        ("O_RING", [r"\bo[- ]?ring\b", r"\bseal\s*ring\b"]),
    ],
    "PIPE": [
        ("SEAMLESS_PIPE", [r"\bseamless\b", r"\bsmls\b"]),
        ("ERW_PIPE", [r"\berw\b"]),
        ("SAW_PIPE", [r"\bsaw\b", r"\blsaw\b", r"\bhss\b"]),
        ("CASING_TUBING", [r"\bcasing\b", r"\btubing\b", r"\bdrill\s*pipe\b"]),
    ],
    "PUMP": [
        ("CENTRIFUGAL_PUMP", [r"\bcentrifugal\b", r"\bmultistage\b", r"\bmulti[- ]stage\b", r"\bbooster\b"]),
        ("SUBMERSIBLE_PUMP", [r"\bsubmersible\b"]),
        ("RECIPROCATING_PUMP", [r"\breciprocating\b", r"\bplunger\b", r"\bpiston\b"]),
        ("GEAR_PUMP", [r"\bgear\s*pump\b", r"\bscrew\s*pump\b"]),
        ("DOSING_PUMP", [r"\bdosing\b", r"\bmetering\b", r"\bdiaphragm\s*pump\b"]),
    ],
    "MOTOR": [
        ("INDUCTION_MOTOR", [r"\binduction\b", r"\bsquirrel\s*cage\b", r"\bsq\s*cage\b", r"\btefc\b"]),
        ("FLAMEPROOF_MOTOR", [r"\bflameproof\b", r"\bflp\b", r"\bexplosion\s*proof\b", r"\bexd\b"]),
        ("SYNCHRONOUS_MOTOR", [r"\bsynchronous\b"]),
    ],
    "BEARING": [
        ("DEEP_GROOVE_BALL", [r"\bdeep\s*groove\b", r"\bball\s*bearing\b"]),
        ("ROLLER_BEARING", [r"\broller\s*bearing\b", r"\btaper\s*roller\b", r"\bspherical\s*roller\b", r"\bcylindrical\s*roller\b"]),
        ("THRUST_BEARING", [r"\bthrust\s*bearing\b"]),
        ("PILLOW_BLOCK", [r"\bpillow\s*block\b", r"\bplummer\s*block\b"]),
    ],
}

CATEGORY_KEYWORDS = {
    "GASKET": [
        "gasket", "gaskets", "gsk", "spiral wound", "ring joint", "rtj",
        "metallic gasket", "non asbestos", "caf gasket", "ptfe gasket", "o-ring", "seal ring"
    ],
    "FITTING": [
        "elbow", "tee", "reducer", "coupling", "union", "nipple", "bushing", "cross", "pipe fitting"
    ],
    "FASTENER": [
        "stud bolt", "hex bolt", "bolt", "nut", "screw", "washer", "fastener", "threaded rod"
    ],
    "CONSUMABLE": [
        "welding electrode", "electrode", "welding wire", "flux", "grinding wheel", "cutting wheel", "lubricant", "grease"
    ],
    "STRUCTURAL_STEEL": [
        "steel plate", "ms plate", "structural plate", "beam", "channel",
        "angle", "chequered plate", "joist", "isnb", "isjb", "iswb", "isjc"
    ],
    "VALVE": [
        "valve", "valves", "vlv", "gate valve", "ball valve", "globe valve",
        "check valve", "non return valve", "nrv", "butterfly valve", "plug valve",
        "needle valve", "control valve", "safety valve", "relief valve", "psv", "cock"
    ],
    "FLANGE": [
        "flange", "flanges", "flg", "weld neck", "slip on", "blind flange",
        "socket weld flange", "threaded flange", "lap joint flange", "spectacle blind"
    ],
    "PIPE": [
        "pipe", "pipes", "piping", "casing", "tubing", "drill pipe", "conduit",
        "seamless pipe", "smls pipe", "erw pipe", "saw pipe", "line pipe"
    ],
    "PUMP": [
        "pump", "pumps", "pmp", "centrifugal pump", "multistage pump",
        "submersible pump", "reciprocating pump", "gear pump", "screw pump", "dosing pump", "booster pump"
    ],
    "MOTOR": [
        "motor", "motors", "electric motor", "induction motor", "flameproof motor",
        "tefc motor", "synchronous motor", "sq cage motor"
    ],
    "BEARING": [
        "bearing", "bearings", "brg", "ball bearing", "roller bearing",
        "taper roller", "spherical roller", "thrust bearing", "pillow block"
    ],
    "COMPRESSOR": [
        "compressor", "air compressor", "reciprocating compressor", "screw compressor", "centrifugal compressor"
    ],
    "ELECTRICAL": [
        "transformer", "switchgear", "circuit breaker", "mcb", "mccb", "relay",
        "cable", "wire", "junction box", "starter", "vfd", "inverter"
    ],
    "INSTRUMENT": [
        "transmitter", "pressure gauge", "temperature gauge", "flow meter",
        "thermocouple", "rtd", "sensor", "rotameter", "level switch", "manometer", "actuator"
    ],
}


def classify_category(desc: str, hint: Optional[str] = None) -> tuple[str, Optional[str]]:
    """
    Deterministically classify material description into structural category and subtype
    using head-noun priority resolution (e.g. 'Flange Gasket' -> GASKET, 'Pipe Elbow' -> FITTING).
    """
    text = desc.lower()

    # Head noun disambiguation rules
    # 1. Gasket applied to Flange -> GASKET
    if re.search(r"\b(gasket|gsk|spiral\s*wound|o[- ]ring|seal\s*ring)\b", text):
        matched_cat = "GASKET"
    # 2. Actuator for Valve -> INSTRUMENT
    elif re.search(r"\b(actuator)\b", text):
        matched_cat = "INSTRUMENT"
    # 3. Fitting for Pipe (elbow, tee, reducer) -> FITTING
    elif re.search(r"\b(elbow|tee|reducer|nipple|coupling|union)\b", text):
        matched_cat = "FITTING"
    # 4. Motor for Pump/Compressor (e.g. Pump Motor, Fan Motor) -> MOTOR
    elif re.search(r"\b(?:pump|fan|blower|compressor)\s+(?:motor|motors)\b", text) or re.search(r"\b(?:electric\s*motor|induction\s*motor)\b", text):
        matched_cat = "MOTOR"
    # 5. Consumable (electrode, welding wire) -> CONSUMABLE
    elif re.search(r"\b(electrode|welding\s*wire|flux|grinding\s*wheel)\b", text):
        matched_cat = "CONSUMABLE"
    # 6. Fastener (stud bolt, hex bolt) -> FASTENER
    elif re.search(r"\b(stud\s*bolt|hex\s*bolt|fastener)\b", text):
        matched_cat = "FASTENER"
    # 6. Fallback to hint if provided
    elif hint and hint.upper() in CATEGORIES:
        matched_cat = hint.upper()
    else:
        # Standard keyword scan with ordered priority
        matched_cat = "OTHER"
        for cat, kw_list in CATEGORY_KEYWORDS.items():
            for kw in kw_list:
                if re.search(r"\b" + re.escape(kw) + r"\b", text):
                    matched_cat = cat
                    break
            if matched_cat != "OTHER":
                break

    # Subtype detection
    subtype = None
    if matched_cat in CATEGORY_SUBTYPES:
        for st_name, patterns in CATEGORY_SUBTYPES[matched_cat]:
            for pat in patterns:
                if re.search(pat, text, flags=re.IGNORECASE):
                    subtype = st_name
                    break
            if subtype:
                break

    return matched_cat, subtype


# -----------------------------------------------------------------------------
# 2. CATEGORY ATTRIBUTE PROFILES (CRITICAL / IMPORTANT / OPTIONAL)
# -----------------------------------------------------------------------------

CATEGORY_PROFILES = {
    "VALVE": {
        "critical": ["category", "subtype", "size", "pressure_rating", "pressure_class", "material_family", "material_grade"],
        "important": ["material_grade", "connection_type", "standards", "facing"],
        "optional": ["actuation", "schedule", "trim", "manufacturer"],
    },
    "FLANGE": {
        "critical": ["category", "subtype", "size", "pressure_rating", "pressure_class", "material_family", "material_grade"],
        "important": ["facing", "standards", "material_grade", "schedule"],
        "optional": ["manufacturer"],
    },
    "GASKET": {
        "critical": ["category", "size", "pressure_rating", "pressure_class", "material_family", "material_grade"],
        "important": ["gasket_filler", "facing", "standards", "subtype"],
        "optional": ["thickness", "manufacturer"],
    },
    "PIPE": {
        "critical": ["category", "size", "schedule", "material_family", "material_grade"],
        "important": ["material_grade", "standards", "connection_type", "subtype"],
        "optional": ["length", "coating", "manufacturer"],
    },
    "PUMP": {
        "critical": ["category", "power_hp", "voltage", "phase"],
        "important": ["subtype", "speed_rpm", "frequency", "material_family"],
        "optional": ["flow_rate", "head", "standards", "manufacturer"],
    },
    "MOTOR": {
        "critical": ["category", "power_hp", "voltage", "phase", "speed_rpm"],
        "important": ["subtype", "frequency", "enclosure"],
        "optional": ["efficiency_class", "frame_size", "manufacturer"],
    },
    "BEARING": {
        "critical": ["category", "bearing_number", "seal_type", "clearance"],
        "important": ["subtype", "material_family", "manufacturer"],
        "optional": ["cage_material", "lubricant"],
    },
    "STRUCTURAL_STEEL": {
        "critical": ["category", "dimension", "material_grade"],
        "important": ["standards", "subtype"],
        "optional": ["length", "surface_finish"],
    },
    "CONSUMABLE": {
        "critical": ["category", "material_grade", "dimension"],
        "important": ["standards", "subtype"],
        "optional": ["package_size", "manufacturer"],
    },
    "DEFAULT": {
        "critical": ["category", "size", "material_family", "material_grade"],
        "important": ["pressure_rating", "standards", "material_grade"],
        "optional": ["other_attributes"],
    }
}


def get_category_profile(category: Optional[str]) -> dict[str, list[str]]:
    """Retrieve the attribute criticality profile for an engineering category."""
    if not category or category not in CATEGORY_PROFILES:
        return CATEGORY_PROFILES["DEFAULT"]
    return CATEGORY_PROFILES[category]


def get_category_rules(category: Optional[str]) -> dict[str, list[str]]:
    """Alias for get_category_profile."""
    return get_category_profile(category)


# -----------------------------------------------------------------------------
# 3. NOMINAL DIMENSION NORMALIZATION (INCH -> DN -> MM)
# -----------------------------------------------------------------------------

INCH_TO_DN_MAP = {
    "1/4": "DN8", "0.25": "DN8",
    "3/8": "DN10", "0.375": "DN10",
    "1/2": "DN15", "0.5": "DN15", "0.50": "DN15",
    "3/4": "DN20", "0.75": "DN20",
    "1": "DN25", "1.0": "DN25", "1.00": "DN25",
    "1-1/4": "DN32", "1 1/4": "DN32", "1.25": "DN32",
    "1-1/2": "DN40", "1 1/2": "DN40", "1.5": "DN40", "1.50": "DN40",
    "2": "DN50", "2.0": "DN50", "2.00": "DN50",
    "2-1/2": "DN65", "2 1/2": "DN65", "2.5": "DN65",
    "3": "DN80", "3.0": "DN80",
    "4": "DN100", "4.0": "DN100",
    "5": "DN125", "5.0": "DN125",
    "6": "DN150", "6.0": "DN150",
    "8": "DN200", "8.0": "DN200",
    "10": "DN250", "10.0": "DN250",
    "12": "DN300", "12.0": "DN300",
    "14": "DN350", "14.0": "DN350",
    "16": "DN400", "16.0": "DN400",
    "18": "DN450", "18.0": "DN450",
    "20": "DN500", "20.0": "DN500",
    "24": "DN600", "24.0": "DN600",
    "28": "DN700", "30": "DN750", "32": "DN800", "36": "DN900", "40": "DN1000",
}

MM_TO_DN_MAP = {
    "8": "DN8", "10": "DN10", "15": "DN15", "20": "DN20", "25": "DN25",
    "32": "DN32", "40": "DN40", "50": "DN50", "65": "DN65", "80": "DN80",
    "100": "DN100", "125": "DN125", "150": "DN150", "200": "DN200", "250": "DN250",
    "300": "DN300", "350": "DN350", "400": "DN400", "450": "DN450", "500": "DN500",
    "600": "DN600", "700": "DN700", "750": "DN750", "800": "DN800", "900": "DN900", "1000": "DN1000",
}


def canonicalize_size(val: Any) -> Optional[str]:
    """
    Standardize size representation to canonical DN format (e.g. 4", 4 IN, 4 inch, DN100, 100 NB, 100 -> DN100).
    Robustly avoids numeric stripping bugs (e.g. 100 does not become 1).
    """
    if not val:
        return None
    s = str(val).strip().upper()

    # Already DN format (DN100, DN50, etc.)
    if re.match(r"^DN\d+$", s):
        return s

    # NB format e.g. 100 NB, 100NB, 4 NB, 4NB
    nb_m = re.match(r"^(\d+(?:\.\d+)?)\s*NB$", s)
    if nb_m:
        num = nb_m.group(1)
        if num in MM_TO_DN_MAP:
            return MM_TO_DN_MAP[num]
        if num in INCH_TO_DN_MAP:
            return INCH_TO_DN_MAP[num]
        return f"DN{num}"

    # Metric mm format e.g. 25MM, 100MM
    mm_m = re.match(r"^(\d+(?:\.\d+)?)\s*MM$", s)
    if mm_m:
        num = mm_m.group(1)
        if num in MM_TO_DN_MAP:
            return MM_TO_DN_MAP[num]
        return f"DN{num}"

    # Inch formats e.g. 4", 4IN, 4 INCH, 1-1/2", 1 1/2 INCH, 0.5"
    inch_m = re.match(r"^(\d+(?:[ -]\d+/\d+|\.\d+|/\d+)?)\s*(?:\"|INCH|IN|INCHES)?$", s)
    if inch_m:
        frac = inch_m.group(1).replace(" ", "-")
        # Direct inch lookup
        if frac in INCH_TO_DN_MAP:
            return INCH_TO_DN_MAP[frac]
        # Metric MM / DN lookup
        if frac in MM_TO_DN_MAP:
            return MM_TO_DN_MAP[frac]
        # Decimal float check e.g. 4.0 -> 4 -> DN100
        try:
            f_val = float(frac)
            if f_val.is_integer():
                int_str = str(int(f_val))
                if int_str in INCH_TO_DN_MAP and int_str in ("1", "2", "3", "4", "5", "6", "8", "10", "12", "14", "16", "18", "20", "24"):
                    return INCH_TO_DN_MAP[int_str]
                elif int_str in MM_TO_DN_MAP:
                    return MM_TO_DN_MAP[int_str]
        except ValueError:
            pass

    # Direct digit lookup
    if s in MM_TO_DN_MAP:
        return MM_TO_DN_MAP[s]
    if s in INCH_TO_DN_MAP:
        return INCH_TO_DN_MAP[s]

    return s


# -----------------------------------------------------------------------------
# 4. PRESSURE CLASS CANONICAL MAPPINGS
# -----------------------------------------------------------------------------

PRESSURE_CANONICAL_MAP = {
    "150": "CL150", "150#": "CL150", "CLASS 150": "CL150", "CL 150": "CL150", "CL.150": "CL150",
    "150 LBS": "CL150", "150 LB": "CL150", "150 CLASS": "CL150", "150# RF": "CL150",
    "300": "CL300", "300#": "CL300", "CLASS 300": "CL300", "CL 300": "CL300", "CL.300": "CL300",
    "300 LBS": "CL300", "300 LB": "CL300", "300 CLASS": "CL300",
    "600": "CL600", "600#": "CL600", "CLASS 600": "CL600", "CL 600": "CL600", "CL.600": "CL600",
    "800": "CL800", "800#": "CL800", "CLASS 800": "CL800", "CL 800": "CL800", "CL.800": "CL800",
    "900": "CL900", "900#": "CL900", "CLASS 900": "CL900", "CL 900": "CL900",
    "1500": "CL1500", "1500#": "CL1500", "CLASS 1500": "CL1500", "CL 1500": "CL1500",
    "2500": "CL2500", "2500#": "CL2500", "CLASS 2500": "CL2500", "CL 2500": "CL2500",
    "3000": "CL3000", "3000#": "CL3000", "3000 PSI": "CL3000", "3000 LBS": "CL3000",
    "PN10": "PN10", "PN16": "PN16", "PN25": "PN25", "PN40": "PN40", "PN64": "PN64", "PN100": "PN100",
}


def canonicalize_pressure(val: Any) -> Optional[str]:
    """
    Standardize pressure class into canonical format (e.g. CL.150, Class 150, 150#, 150 RF, 3000 PSI, PN16 -> CL150 / CL3000 / PN16).
    """
    if not val:
        return None
    p = str(val).strip().upper()
    p_clean = re.sub(r"[#\s\.]+", " ", p).strip()

    if p in PRESSURE_CANONICAL_MAP:
        return PRESSURE_CANONICAL_MAP[p]
    if p_clean in PRESSURE_CANONICAL_MAP:
        return PRESSURE_CANONICAL_MAP[p_clean]

    # Handle PN ratings e.g. PN16, PN 16, PN40
    pn_m = re.match(r"^PN\s*(\d+)$", p)
    if pn_m:
        return f"PN{pn_m.group(1)}"

    # Match digits
    m = re.search(r"(\d+)", p)
    if m:
        num = m.group(1)
        if num in PRESSURE_CANONICAL_MAP:
            return PRESSURE_CANONICAL_MAP[num]
        return f"CL{num}"
    return p


def canonicalize_power(val: Any) -> Optional[str]:
    """
    Standardize power rating to canonical HP (e.g. 5 HP, 5HP, 3.7 kW, 3.7kW -> 5 HP).
    Converts kW to HP using standard 1 kW = 1.34102 HP (1 HP = 0.7457 kW) with standard industrial ratings.
    """
    if not val:
        return None
    s = str(val).strip().upper()
    # Check kW
    kw_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:KW|KILOWATT)", s)
    if kw_m:
        kw = float(kw_m.group(1))
        kw_to_hp = {
            0.37: 0.5, 0.75: 1.0, 1.1: 1.5, 1.5: 2.0, 2.2: 3.0,
            3.7: 5.0, 5.5: 7.5, 7.5: 10.0, 11.0: 15.0, 15.0: 20.0,
            18.5: 25.0, 22.0: 30.0, 30.0: 40.0, 37.0: 50.0, 45.0: 60.0,
            55.0: 75.0, 75.0: 100.0, 90.0: 125.0, 110.0: 150.0
        }
        if kw in kw_to_hp:
            hp = kw_to_hp[kw]
        else:
            hp = round(kw * 1.341022, 1)
        hp_str = f"{int(hp)}" if hp == int(hp) else f"{hp}"
        return f"{hp_str} HP"

    hp_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:HP|H\.P\.)", s)
    if hp_m:
        hp_val = float(hp_m.group(1))
        hp_str = f"{int(hp_val)}" if hp_val == int(hp_val) else f"{hp_val}"
        return f"{hp_str} HP"

    return s



# -----------------------------------------------------------------------------
# 5. MATERIAL TAXONOMY & COMPATIBILITY FAMILIES
# -----------------------------------------------------------------------------

MATERIAL_FAMILIES = {
    "CARBON_STEEL": {
        "base_metal": "CARBON_STEEL",
        "grades": {
            "A105": {"standard": "ASTM A105", "form": "FORGED", "aliases": ["A105", "ASTM A105", "A 105", "CS A105", "FORGED CS A105", "CARBON STEEL A105", "FORGED CARBON STEEL", "FORGED STEEL"]},
            "A216_WCB": {"standard": "ASTM A216", "form": "CAST", "aliases": ["A216 WCB", "WCB", "A216-WCB", "A216 GR WCB", "ASTM A216 WCB", "CAST WCB", "CARBON STEEL WCB", "CAST CARBON STEEL WCB", "A216", "A216WCB", "CAST STEEL"]},
            "A106_GR_B": {"standard": "ASTM A106", "form": "SEAMLESS_PIPE", "aliases": ["A106 GR B", "A106 GR.B", "A106 GRADE B", "A106B", "ASTM A106 GR B", "CS A106 B", "ASTM A106 GRADE B"]},
            "A234_WPB": {"standard": "ASTM A234", "form": "FITTING", "aliases": ["A234 WPB", "WPB", "A234-WPB", "ASTM A234 WPB"]},
            "IS_2062_E250": {"standard": "IS 2062", "form": "STRUCTURAL", "aliases": ["IS 2062 E250", "IS 2062 GR E250", "IS 2062", "IS2062", "IS 2062 GRADE E250", "MS IS 2062", "MILD STEEL"]},
            "AWS_E6013": {"standard": "AWS A5.1", "form": "ELECTRODE", "aliases": ["AWS E6013", "E6013", "AWS A5.1 E6013", "E 6013"]},
        }
    },
    "STAINLESS_STEEL_316": {
        "base_metal": "STAINLESS_STEEL",
        "grades": {
            "A182_F316": {"standard": "ASTM A182", "form": "FORGED", "aliases": ["A182 F316", "F316", "A182-F316", "SS316", "SS 316", "316 SS", "316SS", "STAINLESS STEEL 316", "AISI 316", "ASTM A182 F316", "SS316L", "SS 316L", "316L"]},
            "A351_CF8M": {"standard": "ASTM A351", "form": "CAST", "aliases": ["A351 CF8M", "CF8M", "A351-CF8M", "CAST SS316", "ASTM A351 CF8M", "CF 8M"]},
            "A312_TP316": {"standard": "ASTM A312", "form": "SEAMLESS_PIPE", "aliases": ["A312 TP316", "TP316", "A312-TP316", "ASTM A312 TP316", "SS316 PIPE", "TP316L"]},
            "A403_WP316": {"standard": "ASTM A403", "form": "FITTING", "aliases": ["A403 WP316", "WP316", "ASTM A403 WP316"]},
        }
    },
    "STAINLESS_STEEL_304": {
        "base_metal": "STAINLESS_STEEL",
        "grades": {
            "A182_F304": {"standard": "ASTM A182", "form": "FORGED", "aliases": ["A182 F304", "F304", "SS304", "SS 304", "304 SS", "STAINLESS STEEL 304", "ASTM A182 F304"]},
            "A351_CF8": {"standard": "ASTM A351", "form": "CAST", "aliases": ["A351 CF8", "CF8", "A351-CF8", "CAST SS304"]},
            "A312_TP304": {"standard": "ASTM A312", "form": "SEAMLESS_PIPE", "aliases": ["A312 TP304", "TP304", "ASTM A312 TP304"]},
        }
    },
    "ALLOY_STEEL": {
        "base_metal": "ALLOY_STEEL",
        "grades": {
            "A182_F11": {"standard": "ASTM A182", "form": "FORGED", "aliases": ["A182 F11", "F11", "1.25CR-0.5MO"]},
            "A182_F22": {"standard": "ASTM A182", "form": "FORGED", "aliases": ["A182 F22", "F22", "2.25CR-1MO"]},
        }
    }
}


def get_material_details(val: Any) -> Optional[dict[str, str]]:
    """
    Retrieve canonical grade, family, and base metal for a material value.
    """
    if not val:
        return None
    s = str(val).strip().upper()

    # Search known families and grade aliases
    for fam_name, fam_data in MATERIAL_FAMILIES.items():
        for grade_name, grade_data in fam_data["grades"].items():
            if s == grade_name:
                return {"canonical_grade": grade_name, "family": fam_name, "base_metal": fam_data["base_metal"]}
            for alias in grade_data["aliases"]:
                if alias == s or re.search(r"\b" + re.escape(alias) + r"\b", s):
                    return {
                        "canonical_grade": grade_name,
                        "family": fam_name,
                        "base_metal": fam_data["base_metal"]
                    }

    # General keywords
    if re.search(r"\b(CARBON\s*STEEL|CS|CAST\s*STEEL|FORGED\s*STEEL|FORGED\s*CS)\b", s):
        return {"canonical_grade": "CARBON_STEEL", "family": "CARBON_STEEL", "base_metal": "CARBON_STEEL"}
    if re.search(r"\b(SS316|316\s*SS|SS\s*316|316|SS316L)\b", s):
        return {"canonical_grade": "A182_F316", "family": "STAINLESS_STEEL_316", "base_metal": "STAINLESS_STEEL"}
    if re.search(r"\b(SS304|304\s*SS|SS\s*304|304)\b", s):
        return {"canonical_grade": "A182_F304", "family": "STAINLESS_STEEL_304", "base_metal": "STAINLESS_STEEL"}
    if re.search(r"\b(STAINLESS\s*STEEL|SS|STAINLESS)\b", s):
        return {"canonical_grade": "STAINLESS_STEEL", "family": "STAINLESS_STEEL_316", "base_metal": "STAINLESS_STEEL"}
    if re.search(r"\b(MILD\s*STEEL|MS)\b", s):
        return {"canonical_grade": "IS_2062_E250", "family": "CARBON_STEEL", "base_metal": "CARBON_STEEL"}

    return {"canonical_grade": s, "family": s, "base_metal": s}


def canonicalize_material(val: Any) -> Optional[str]:
    """
    Standardize material string to canonical grade representation.
    """
    if not val:
        return None
    if isinstance(val, dict):
        return val.get("canonical_grade") or val.get("family")
    details = get_material_details(val)
    return details["canonical_grade"] if details else str(val).strip().upper()


def are_materials_compatible(mat_a: Optional[str], mat_b: Optional[str]) -> tuple[str, float]:
    """
    Evaluate compatibility between two materials using ontology hierarchy.
    Returns (status, score):
    - EXACT_MATCH: 1.0 (identical canonical grade)
    - COMPATIBLE_FAMILY: 0.85 (e.g. cast WCB vs forged A105 both Carbon Steel)
    - INCOMPATIBLE_FAMILY: 0.0 (e.g. Carbon Steel vs SS316)
    - UNKNOWN: 0.5 (one or both unknown)
    """
    if not mat_a or not mat_b:
        return "UNKNOWN", 0.5

    can_a = canonicalize_material(mat_a)
    can_b = canonicalize_material(mat_b)

    if can_a == can_b:
        return "EXACT_MATCH", 1.0

    # Determine families for both
    details_a = get_material_details(can_a)
    details_b = get_material_details(can_b)

    fam_a = details_a["family"] if details_a else None
    fam_b = details_b["family"] if details_b else None

    if fam_a and fam_b:
        if fam_a == fam_b:
            return "COMPATIBLE_FAMILY", 0.85
        else:
            return "INCOMPATIBLE_FAMILY", 0.0

    return "UNKNOWN", 0.5
