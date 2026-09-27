import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAFETY_FILE = PROJECT_ROOT / "src" / "matching" / "output_v2.txt"


def parse_safety_gate_output():
    blocked = []

    current_a = None
    current_b = None
    current_confidence = None

    with SAFETY_FILE.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()

            # Read item A
            if line.startswith("A:"):
                match = re.search(r"A:\s*([A-Z0-9-]+)", line)
                if match:
                    current_a = match.group(1)

            # Read item B
            elif line.startswith("B:"):
                match = re.search(r"B:\s*([A-Z0-9-]+)", line)
                if match:
                    current_b = match.group(1)

            # Read blocked confidence
            elif "[BLOCKED" in line and "SAFETY GATE" in line:
                match = re.search(r"confidence=([0-9.]+)", line)

                current_confidence = (
                    float(match.group(1))
                    if match
                    else None
                )

            # Read the exact Safety Gate reason
            elif "SAFETY GATE TRIGGERED:" in line:
                reason = line.split(
                    "SAFETY GATE TRIGGERED:",
                    1
                )[1].strip()

                if current_a and current_b:
                    blocked.append({
                        "match_id": f"BLOCKED-{current_a}-{current_b}",
                        "item_a": current_a,
                        "item_b": current_b,
                        "confidence_score": current_confidence,
                        "status": "safety_gate_blocked",
                        "block_reason": reason,
                    })

                current_a = None
                current_b = None
                current_confidence = None

    return blocked


if __name__ == "__main__":
    blocked = parse_safety_gate_output()

    print(f"Safety Gate blocked matches: {len(blocked)}")
    print()

    for match in blocked:
        print(
            f"[BLOCKED] "
            f"{match['item_a']} <-> "
            f"{match['item_b']} "
            f"confidence={match['confidence_score']}"
        )

        print(f"    Reason: {match['block_reason']}")