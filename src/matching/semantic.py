"""
SIH26099 Domain-Aware Semantic Understanding & Candidate Discovery
Combines Neural Dense Embeddings (all-MiniLM-L6-v2), Character n-gram TF-IDF,
and Token Fuzzy Matching for robust semantic understanding of unseen descriptions.
"""

import re
from typing import Optional, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

from .embedding import get_embedding_service

DOMAIN_SYNONYM_RULES = [
    # Units and structural terms
    (r"\bmulti[- ]stage\b", "multistage"),
    (r"(\d+)\s*(?:hp|h\.p\.)\b", r"\1 hp"),
    (r"(\d+)\s*(?:volt|volts|v)\b", r"\1 v"),
    (r"(\d+)\s*(?:phase|ph)\b", r"\1 phase"),
    (r"(\d+)\s*(?:hz|hertz)\b", r"\1 hz"),
    (r"(\d+)\s*(?:rpm)\b", r"\1 rpm"),
    (r"(\d+)\s*(?:in|inch|inches|\")\b", r"\1 inch"),
    (r"(\d+)\s*(?:mm)\b", r"\1 mm"),
    (r"(\d+)\s*#\b", r"class \1"),
    (r"\bcl\.?\s*(\d+)\b", r"class \1"),

    # Common domain synonyms
    (r"\bnon\s*return\s*valve\b", "check valve non return valve nrv"),
    (r"\bnrv\b", "check valve non return valve nrv"),
    (r"\bcarbon\s*steel\b", "carbon steel cs"),
    (r"\bcs\b", "carbon steel cs"),
    (r"\bstainless\s*steel\b", "stainless steel ss"),
    (r"\bss\b", "stainless steel ss"),
    (r"\bweld\s*neck\b", "weld neck wn"),
    (r"\bwn\b", "weld neck wn"),
    (r"\bslip\s*on\b", "slip on so"),
    (r"\bso\b", "slip on so"),
    (r"\braised\s*face\b", "raised face rf"),
    (r"\brf\b", "raised face rf"),
    (r"\bspiral\s*wound\b", "spiral wound sw"),
    (r"\bsw\b", "spiral wound sw"),
]


def domain_expand_text(text: str) -> str:
    """
    Standardize common structural tokens before vectorization.
    """
    if not text:
        return ""
    expanded = text.lower()
    for pattern, repl in DOMAIN_SYNONYM_RULES:
        expanded = re.sub(pattern, repl, expanded, flags=re.IGNORECASE)
    return expanded


def calculate_semantic_similarity(desc_a: str, desc_b: str, vectorizer: Optional[TfidfVectorizer] = None) -> float:
    """
    Calculate multi-signal semantic similarity combining:
    1. Dense Transformer Embedding Cosine Similarity (all-MiniLM-L6-v2) - Weight 50%
       Captures deep semantic equivalence across unseen terminology without manual enumeration.
    2. Character n-gram TF-IDF Cosine Similarity - Weight 25%
       Captures subword morphological overlap.
    3. Fuzzy Token Set & Sort Similarity - Weight 25%
       Captures token-level word order invariance.
    """
    if not desc_a or not desc_b:
        return 0.0

    # 1. Dense Neural Embedding Similarity
    try:
        emb_service = get_embedding_service()
        dense_sim = emb_service.compute_similarity(desc_a, desc_b)
    except Exception:
        dense_sim = 0.50

    # Cleaned text for lexical metrics
    exp_a = domain_expand_text(desc_a)
    exp_b = domain_expand_text(desc_b)

    # 2. Fuzzy Token Similarity
    token_set_score = fuzz.token_set_ratio(exp_a, exp_b) / 100.0
    token_sort_score = fuzz.token_sort_ratio(exp_a, exp_b) / 100.0
    fuzzy_sim = 0.5 * token_set_score + 0.5 * token_sort_score

    # 3. Character n-gram TF-IDF Similarity
    try:
        if vectorizer is None:
            v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
            mat = v.fit_transform([exp_a, exp_b])
            tfidf_sim = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
        else:
            mat = vectorizer.transform([exp_a, exp_b])
            tfidf_sim = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
    except Exception:
        tfidf_sim = fuzzy_sim

    # Weighted composite semantic score
    composite_sim = (
        0.50 * dense_sim +
        0.25 * tfidf_sim +
        0.25 * fuzzy_sim
    )

    return max(0.0, min(1.0, round(composite_sim, 3)))
