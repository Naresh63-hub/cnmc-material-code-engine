"""
SIH26099 Explainability & Audit Trail Generator
Produces structured evidence payloads and human-readable decision summaries.
"""

from typing import Any


def build_explanation_payload(
    cat_a: str,
    cat_b: str,
    status: str,
    sub_class: str,
    confidence: float,
    semantic_sim: float,
    tech_score: float,
    tech_eval: dict[str, Any],
    block_reason: str | None = None,
) -> dict[str, Any]:
    """
    Build structured, audit-ready explanation payload for dashboard and exports.
    """
    critical_conflicts = tech_eval.get("critical_conflicts", [])
    unverified_critical = tech_eval.get("unverified_critical", [])

    if status == "safety_gate_blocked":
        summary = f"Safety Gate Blocked: {block_reason or 'Critical specification conflict detected'}"
    elif status == "auto_linked":
        summary = f"Auto-Linked as {sub_class} (Confidence: {int(confidence * 100)}%)"
    elif status == "needs_review":
        if sub_class == "NEEDS_SPEC_VALIDATION":
            summary = f"Routed to Human Review: Unverified critical attributes ({', '.join(unverified_critical)})"
        elif sub_class == "FUNCTIONALLY_EQUIVALENT":
            summary = "Routed to Human Review: Functionally equivalent material family requiring engineering sign-off"
        else:
            summary = f"Routed to Human Review: {block_reason or 'Plausible candidate pair requiring engineer confirmation'}"
    else:
        summary = f"No Match: {block_reason or 'Different items'}"

    return {
        "category": f"{cat_a} (Matched: {cat_a} == {cat_b})" if cat_a == cat_b else f"{cat_a} ≠ {cat_b}",
        "classification_type": sub_class,
        "semantic_similarity_pct": int(semantic_sim * 100),
        "technical_score_pct": int(tech_score * 100),
        "coverage": f"{tech_eval.get('evaluated_specs', 0)}/{tech_eval.get('total_expected', 1)} specs verified",
        "critical_conflicts_count": len(critical_conflicts),
        "unverified_critical": unverified_critical,
        "spec_details": tech_eval.get("spec_details", []),
        "summary": summary,
    }
