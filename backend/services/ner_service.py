"""
Named Entity Recognition (NER) service using spaCy.

Extracts structured entities from clause text and provides entity-based
contradiction detection (dates, money, people, orgs, locations, etc.).
"""
import logging
import re
import threading
from typing import List, Dict, Optional, Tuple

from constants import STOP_WORDS

logger = logging.getLogger(__name__)

_nlp = None
_nlp_lock = threading.Lock()


def _load_nlp():
    """Lazy-load the spaCy model once (thread-safe)."""
    global _nlp
    if _nlp is None:
        with _nlp_lock:
            if _nlp is None:  # double-checked locking
                import spacy
                try:
                    _nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
                except OSError:
                    logger.warning("spaCy model 'en_core_web_sm' not found – NER features disabled")
                    return None
                # Increase max_length for long clauses
                _nlp.max_length = 200_000
                logger.info("Loaded spaCy NER model: en_core_web_sm")
    return _nlp


# ── Entity labels we care about for contradiction detection ──
_ENTITY_LABELS = {
    "PERSON", "ORG", "GPE", "LOC",     # who / where
    "DATE", "TIME",                      # when
    "MONEY", "PERCENT", "QUANTITY",      # how much
    "CARDINAL", "ORDINAL",               # numbers
    "LAW", "PRODUCT", "EVENT",           # what
}


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from a clause and return them grouped by label.

    Returns:
        {
          "PERSON": ["John Smith"],
          "ORG": ["Acme Corp"],
          "DATE": ["January 2024", "30 days"],
          "MONEY": ["$5,000"],
          ...
        }
    """
    nlp = _load_nlp()
    if nlp is None:
        return {}

    doc = nlp(text)
    entities: Dict[str, List[str]] = {}
    seen: set = set()

    for ent in doc.ents:
        if ent.label_ not in _ENTITY_LABELS:
            continue
        # Normalise whitespace
        val = " ".join(ent.text.split())
        key = (ent.label_, val.lower())
        if key in seen:
            continue
        seen.add(key)
        entities.setdefault(ent.label_, []).append(val)

    return entities


def extract_entities_batch(texts: List[str]) -> List[Dict[str, List[str]]]:
    """
    Extract entities from a batch of texts using spaCy's nlp.pipe() for speed.

    Returns:
        List of entity dicts, one per input text (same order).
    """
    nlp = _load_nlp()
    if nlp is None:
        return [{} for _ in texts]

    total = len(texts)
    log_interval = max(1, total // 5)  # log at ~20%, 40%, 60%, 80%, 100%
    results: List[Dict[str, List[str]]] = []
    for i, doc in enumerate(nlp.pipe(texts, batch_size=128)):
        entities: Dict[str, List[str]] = {}
        seen: set = set()
        for ent in doc.ents:
            if ent.label_ not in _ENTITY_LABELS:
                continue
            val = " ".join(ent.text.split())
            key = (ent.label_, val.lower())
            if key in seen:
                continue
            seen.add(key)
            entities.setdefault(ent.label_, []).append(val)
        results.append(entities)

        if (i + 1) % log_interval == 0 or (i + 1) == total:
            logger.info(f"NER progress: {i + 1}/{total} clauses processed")

    return results


# ─────────────────────────────────────────────────────────────────
#  Entity-based contradiction detection
# ─────────────────────────────────────────────────────────────────

def check_entity_contradictions(clause_a, clause_b,
                                 ents_a: Dict[str, List[str]],
                                 ents_b: Dict[str, List[str]]) -> List[Dict]:
    """
    Detect contradictions between two clauses based on their named entities.

    Checks:
        1. Date / time conflicts   — same topic, different dates
        2. Money / percent conflicts — same topic, different amounts
        3. Person / org conflicts   — same role/context, different people or orgs
        4. Location conflicts       — same context, different places
        5. Quantity conflicts       — same subject, different quantities

    Only fires when the clauses share enough topical overlap (>40% word overlap)
    so we don't flag unrelated clauses that happen to mention different entities.

    Returns list of violation dicts (may be empty).
    """
    if not ents_a or not ents_b:
        return []

    # ── Guard: require minimum clause length ──
    words_a_list = clause_a.text.lower().split()
    words_b_list = clause_b.text.lower().split()
    if len(words_a_list) < 8 or len(words_b_list) < 8:
        return []

    # ── Guard: require topical overlap (content words only) ──
    words_a = {w for w in words_a_list if w not in STOP_WORDS and len(w) > 2}
    words_b = {w for w in words_b_list if w not in STOP_WORDS and len(w) > 2}
    if not words_a or not words_b:
        return []
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    # Require near-identical sentence structure before flagging entity conflicts
    if overlap < 0.50:
        return []

    violations: List[Dict] = []

    # 1. Date / time conflicts
    _check_label_conflict(
        clause_a, clause_b, ents_a, ents_b,
        labels=["DATE", "TIME"],
        contra_type="date",
        severity="high",
        desc_template="Date/time conflict: {a} vs {b}",
        confidence=0.85,
        violations=violations,
    )

    # 2. Money / percent conflicts
    _check_label_conflict(
        clause_a, clause_b, ents_a, ents_b,
        labels=["MONEY", "PERCENT"],
        contra_type="financial",
        severity="high",
        desc_template="Financial conflict: {a} vs {b}",
        confidence=0.88,
        violations=violations,
    )

    # 3. Person / org conflicts
    _check_label_conflict(
        clause_a, clause_b, ents_a, ents_b,
        labels=["PERSON", "ORG"],
        contra_type="entity",
        severity="medium",
        desc_template="Entity conflict: {a} vs {b}",
        confidence=0.75,
        violations=violations,
    )

    # 4. Location conflicts
    _check_label_conflict(
        clause_a, clause_b, ents_a, ents_b,
        labels=["GPE", "LOC"],
        contra_type="location",
        severity="medium",
        desc_template="Location conflict: {a} vs {b}",
        confidence=0.78,
        violations=violations,
    )

    # 5. Quantity conflicts
    _check_label_conflict(
        clause_a, clause_b, ents_a, ents_b,
        labels=["QUANTITY", "CARDINAL"],
        contra_type="quantity",
        severity="medium",
        desc_template="Quantity conflict: {a} vs {b}",
        confidence=0.80,
        violations=violations,
    )

    return violations


def _check_label_conflict(
    clause_a, clause_b,
    ents_a: Dict[str, List[str]],
    ents_b: Dict[str, List[str]],
    labels: List[str],
    contra_type: str,
    severity: str,
    desc_template: str,
    confidence: float,
    violations: List[Dict],
):
    """
    Compare entities of given label(s) between two clauses.
    If both clauses contain entities of the same label but with different
    values, record a violation.
    """
    vals_a: List[str] = []
    vals_b: List[str] = []
    for label in labels:
        vals_a.extend(ents_a.get(label, []))
        vals_b.extend(ents_b.get(label, []))

    if not vals_a or not vals_b:
        return

    set_a = {v.lower() for v in vals_a}
    set_b = {v.lower() for v in vals_b}

    # Only flag if the sets are completely disjoint (different values)
    # AND the overlap is not caused by additive/enumerative clauses
    if set_a and set_b and set_a.isdisjoint(set_b):
        # Extra guard: if combined entity count is very high (>4), it is
        # likely an enumeration ("members include A, B, C") not a conflict
        if len(set_a) + len(set_b) > 4:
            return

        violations.append({
            "clause_a": clause_a,
            "clause_b": clause_b,
            "type": contra_type,
            "severity": severity,
            "description": desc_template.format(
                a=", ".join(vals_a[:3]),
                b=", ".join(vals_b[:3]),
            ),
            "confidence": confidence,
        })
