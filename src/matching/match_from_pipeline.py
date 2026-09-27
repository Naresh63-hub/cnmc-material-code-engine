"""
Tier 2 — Explainable Two-Stage Material Matching & Technical Compatibility Engine
SIH26099: AI-Driven Material Code Standardization Across CPSEs

Modular Architecture:
1. Category & Domain Partitioning (ontology.py)
2. Dense Neural Embedding Discovery & Ranking (embedding.py, semantic.py)
3. Multi-Notation Technical Attribute Evaluation (technical.py)
4. Category-Specific Critical/Important Attribute Safety Gate (classifier.py)
5. Coverage-Aware Spec Scoring & Classification (classifier.py)
6. Structured, Audit-Ready Explainability (explainability.py)
"""

import json
import itertools
import numpy as np
from typing import Any, Optional
from sklearn.neighbors import NearestNeighbors

from .ontology import (
    classify_category,
    canonicalize_size,
    canonicalize_pressure,
    canonicalize_material,
    are_materials_compatible,
    get_category_rules,
)
from .technical import clean_description, normalize_unit, extract_specs, UNIT_EQUIVALENCE
from .embedding import get_embedding_service
from .semantic import calculate_semantic_similarity, domain_expand_text
from .classifier import evaluate_technical_compatibility, CONFIDENCE_THRESHOLD, REVIEW_THRESHOLD
from .explainability import build_explanation_payload


def load_tier1_output(path: str) -> list[dict]:
    """Load Tier 1 standardized JSONL output."""
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def unit_compat_score(unit_a: str, unit_b: str) -> float:
    """Return unit compatibility score."""
    u_a = UNIT_EQUIVALENCE.get(str(unit_a).upper().strip(), str(unit_a).upper().strip())
    u_b = UNIT_EQUIVALENCE.get(str(unit_b).upper().strip(), str(unit_b).upper().strip())
    return 1.0 if u_a == u_b else 0.4


def run_matching(items: list[dict], top_k_neighbors: int = 15) -> list[dict]:
    """
    Execute explainable two-stage matching pipeline:
    1. Category & Domain Partitioning
    2. Dense Embedding Nearest-Neighbor Discovery (all-MiniLM-L6-v2)
    3. Multi-Factor Technical Compatibility & Safety Gate
    4. Exact / Near Duplicate vs Functional Equivalence Classification
    """
    if not items:
        return []

    # Preprocess & Enrich items
    enriched_items = []
    descriptions = []
    for item in items:
        raw_desc = item.get("raw_description") or item.get("description") or item.get("raw", "")
        desc = item.get("clean_description") or clean_description(raw_desc)
        specs = item.get("specs") or extract_specs(desc)
        cat = item.get("category") or specs.get("category") or classify_category(desc)[0]
        enriched = dict(
            item,
            clean_description=desc,
            category=cat,
            specs=specs,
            unit_of_measure=normalize_unit(item.get("unit_of_measure") or item.get("unit", "EA"))
        )
        enriched_items.append(enriched)
        descriptions.append(desc)

    # Compute dense embeddings for all catalog items in batch
    emb_service = get_embedding_service()
    embeddings = emb_service.encode(descriptions)

    # Build Candidate Pairs via Category Partitioning + Dense Embedding Similarity
    candidate_pairs = set()
    num_items = len(enriched_items)

    # If small catalog (< 100 items), evaluate all cross-CPSE within-category pairs
    # For larger catalogs, use NearestNeighbors to discover top-K semantic candidates
    if num_items <= 100:
        for i in range(num_items):
            for j in range(i + 1, num_items):
                cat_a = enriched_items[i]["category"]
                cat_b = enriched_items[j]["category"]
                if cat_a != "OTHER" and cat_b != "OTHER" and cat_a != cat_b:
                    continue
                candidate_pairs.add((i, j))
    else:
        # Dense KNN Index for scalable candidate discovery
        k = min(top_k_neighbors + 1, num_items)
        nn = NearestNeighbors(n_neighbors=k, metric="cosine")
        nn.fit(embeddings)
        distances, indices = nn.kneighbors(embeddings)

        for i in range(num_items):
            for neighbor_idx in indices[i]:
                if neighbor_idx == i:
                    continue
                pair = (min(i, neighbor_idx), max(i, neighbor_idx))
                cat_a = enriched_items[pair[0]]["category"]
                cat_b = enriched_items[pair[1]]["category"]
                if cat_a != "OTHER" and cat_b != "OTHER" and cat_a != cat_b:
                    continue
                candidate_pairs.add(pair)

    results = []
    for i, j in candidate_pairs:
        a = enriched_items[i]
        b = enriched_items[j]

        # Only compare items from different CPSEs if source_cpse is specified
        cpse_a = a.get("source_cpse") or a.get("cpse", "")
        cpse_b = b.get("source_cpse") or b.get("cpse", "")
        if cpse_a and cpse_b and cpse_a == cpse_b:
            continue

        desc_a = a["clean_description"]
        desc_b = b["clean_description"]
        cat_a = a["category"]
        cat_b = b["category"]

        # Stage 1: Category Blocking
        if cat_a != "OTHER" and cat_b != "OTHER" and cat_a != cat_b:
            continue

        # Stage 2: Multi-Signal Semantic Similarity (50% Dense Embedding + 25% TF-IDF + 25% Fuzzy)
        semantic_sim = calculate_semantic_similarity(desc_a, desc_b)

        # Pre-filter very low semantic similarity unless same category with matching specs
        if semantic_sim < 0.20:
            continue

        # Stage 3: Technical Compatibility Evaluation
        tech_eval = evaluate_technical_compatibility(a, b)

        # Stage 4: Unit Compatibility
        unit_score = unit_compat_score(a["unit_of_measure"], b["unit_of_measure"])

        # Composite Confidence Equation
        tech_score = tech_eval["technical_score"]
        critical_conflicts = tech_eval["critical_conflicts"]
        unverified_critical = tech_eval["unverified_critical"]

        confidence = (
            0.45 * semantic_sim +
            0.40 * tech_score +
            0.15 * unit_score
        )
        confidence = round(confidence, 3)

        # -------------------------------------------------------------
        # CLASSIFICATION & SAFETY GATE DECISION MATRIX
        # -------------------------------------------------------------
        if critical_conflicts:
            status = "safety_gate_blocked"
            sub_class = "CONFLICT_BLOCKED"
            block_reason = "; ".join(critical_conflicts)
        elif not tech_eval["is_category_compatible"]:
            status = "no_match"
            sub_class = "INCOMPATIBLE_CATEGORY"
            block_reason = f"Category mismatch: {cat_a} vs {cat_b}"
        elif confidence < REVIEW_THRESHOLD:
            status = "no_match"
            sub_class = "DIFFERENT"
            block_reason = None
        elif (
            confidence >= CONFIDENCE_THRESHOLD and
            not critical_conflicts and
            len(unverified_critical) == 0 and
            tech_eval["match_ratio"] >= 0.90 and
            semantic_sim >= 0.65
        ):
            status = "auto_linked"
            sub_class = "EXACT_DUPLICATE" if tech_eval["match_ratio"] == 1.0 else "NEAR_DUPLICATE"
            block_reason = None
        else:
            status = "needs_review"
            if len(unverified_critical) > 0:
                sub_class = "NEEDS_SPEC_VALIDATION"
                block_reason = f"Unverified critical specifications: {', '.join(unverified_critical)}"
            elif any(d.get("status") == "EQUIVALENT" for d in tech_eval["spec_details"]):
                sub_class = "FUNCTIONALLY_EQUIVALENT"
                block_reason = "Functionally equivalent material family requiring engineering review"
            else:
                sub_class = "POTENTIAL_DUPLICATE"
                block_reason = None

        explanation = build_explanation_payload(
            cat_a=cat_a,
            cat_b=cat_b,
            status=status,
            sub_class=sub_class,
            confidence=confidence,
            semantic_sim=semantic_sim,
            tech_score=tech_score,
            tech_eval=tech_eval,
            block_reason=block_reason,
        )

        item_a_id = a.get("item_id") or a.get("id", "ITEM_A")
        item_b_id = b.get("item_id") or b.get("id", "ITEM_B")

        result = {
            "match_id": f"M-{item_a_id}-{item_b_id}",
            "item_a": item_a_id,
            "item_b": item_b_id,
            "source_cpse_a": cpse_a or "UNKNOWN",
            "source_cpse_b": cpse_b or "UNKNOWN",
            "category": cat_a,
            "sub_classification": sub_class,
            "confidence_score": confidence,
            "score_breakdown": {
                "text_similarity": round(semantic_sim, 3),
                "spec_match": round(tech_score, 3),
                "unit_compatibility": round(unit_score, 3),
            },
            "status": status,
            "explanation": explanation,
        }

        if block_reason:
            result["block_reason"] = block_reason

        results.append(result)

    results.sort(key=lambda r: -r["confidence_score"])
    return results


if __name__ == "__main__":
    items = load_tier1_output("processed_catalog.jsonl")
    print(f"Loaded {len(items)} items. Running explainable matching engine with Dense Embeddings...\n")

    matches = run_matching(items)

    print(f"{'=' * 90}")
    print(f"MATCH RESULTS — {len(matches)} pairs evaluated across categories")
    print(f"{'=' * 90}\n")

    for match in matches[:10]:
        print(f"[{match['status']:20}] [{match['sub_classification']:22}] confidence={match['confidence_score']}")
        print(f"    {match['item_a']} ({match['source_cpse_a']}) <-> {match['item_b']} ({match['source_cpse_b']})")
        print(f"    Summary: {match['explanation']['summary']}\n")

    with open("tier2_match_output.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2)

    print(f"Saved {len(matches)} match records to tier2_match_output.json")