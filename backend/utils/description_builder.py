"""
Shared utility for building human-readable semantic contradiction descriptions.

Used by both processing_worker.py (single-doc) and comparison_worker.py (multi-doc)
to avoid code duplication.
"""
from typing import List, Tuple

from constants import STOP_WORDS


def build_semantic_description(
    clause_a_id: str,
    clause_b_id: str,
    nli_pairs: List[Tuple[str, str, str, str]],
    confidence_pct: float,
) -> str:
    """Build a human-readable description for a semantic contradiction.

    Extracts the best contiguous span of differing words from each clause
    so the description reads like natural text, not a bag of words.

    Args:
        clause_a_id: ID of the first clause.
        clause_b_id: ID of the second clause.
        nli_pairs: List of (text_a, text_b, id_a, id_b) tuples from NLI batch.
        confidence_pct: Confidence percentage (0-100) for fallback description.

    Returns:
        Human-readable contradiction description string.
    """
    # Find the matching pair texts
    text_a = text_b = None
    for t_a, t_b, id_a, id_b in nli_pairs:
        if id_a == clause_a_id and id_b == clause_b_id:
            text_a, text_b = t_a, t_b
            break
        if id_a == clause_b_id and id_b == clause_a_id:
            text_a, text_b = t_b, t_a
            break

    if not text_a or not text_b:
        return f"Semantic conflict detected (confidence: {confidence_pct:.0f}%)"

    # Build cleaned word sets for diff computation
    words_a_clean = [w.strip('.,;:!?\'"()').lower() for w in text_a.split()]
    words_b_clean = [w.strip('.,;:!?\'"()').lower() for w in text_b.split()]
    set_a = {w for w in words_a_clean if w not in STOP_WORDS and len(w) > 2}
    set_b = {w for w in words_b_clean if w not in STOP_WORDS and len(w) > 2}

    unique_a = set_a - set_b
    unique_b = set_b - set_a

    span_a = _extract_best_span(text_a, unique_a)
    span_b = _extract_best_span(text_b, unique_b)

    if span_a and span_b:
        return f"Semantic conflict: '{span_a}' vs '{span_b}'"
    return f"Semantic conflict detected (confidence: {confidence_pct:.0f}%)"


def _extract_best_span(original_text: str, unique_words: set, max_words: int = 12) -> str:
    """Find the longest contiguous run of unique content words in the *original*
    text and return the span with one word of leading context, preserving
    original casing and punctuation."""
    orig_words = original_text.split()
    clean = [w.strip('.,;:!?\'"()').lower() for w in orig_words]

    # Mark each position that contains a unique content word
    hits = [c in unique_words for c in clean]

    # Find the longest contiguous run of True values
    best_start = best_end = 0
    cur_start = None
    for i, hit in enumerate(hits):
        if hit:
            if cur_start is None:
                cur_start = i
            run_len = i - cur_start + 1
            if run_len > (best_end - best_start):
                best_start, best_end = cur_start, i + 1
        else:
            cur_start = None

    if best_start == best_end:
        # No contiguous run found — fall back to first few unique words in order
        fallback = [w for w, c in zip(orig_words, clean) if c in unique_words]
        return ' '.join(fallback[:max_words])

    # Add one word of leading context for readability
    ctx_start = max(0, best_start - 1)
    span = orig_words[ctx_start:best_end]

    # If span is too long, trim to max_words from the start
    if len(span) > max_words:
        span = span[:max_words]

    return ' '.join(span).strip('.,;:!?\'"()')
