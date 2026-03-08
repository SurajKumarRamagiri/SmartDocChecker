"""Rule-based contradiction checker with NER-enhanced detection."""
import re
import logging
from typing import List, Dict

from services.ner_service import check_entity_contradictions
from constants import STOP_WORDS

logger = logging.getLogger(__name__)


def _content_overlap(text_a: str, text_b: str) -> float:
    """Return overlap ratio using content words only (stop words removed)."""
    wa = {w for w in text_a.lower().split() if w not in STOP_WORDS and len(w) > 2}
    wb = {w for w in text_b.lower().split() if w not in STOP_WORDS and len(w) > 2}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def check_contradictions_batch(clauses: List, entities_map: Dict[str, Dict] = None) -> List[Dict]:
    """Check for rule-based contradictions in clause pairs.
    
    Args:
        clauses: List of Clause ORM objects.
        entities_map: Optional mapping of clause_id -> {label: [values]}.
                      If provided, NER-based entity checks are applied.
    """
    violations = []
    
    for i, clause_a in enumerate(clauses):
        for clause_b in clauses[i+1:]:
            # Numeric mismatch
            num_violation = check_numeric_mismatch(clause_a, clause_b)
            if num_violation:
                violations.append(num_violation)
            
            # Modal mismatch
            modal_violation = check_modal_mismatch(clause_a, clause_b)
            if modal_violation:
                violations.append(modal_violation)
            
            # Authority mismatch
            auth_violation = check_authority_mismatch(clause_a, clause_b)
            if auth_violation:
                violations.append(auth_violation)
            
            # NER entity-based checks
            if entities_map:
                ents_a = entities_map.get(clause_a.id, {})
                ents_b = entities_map.get(clause_b.id, {})
                if ents_a or ents_b:
                    entity_violations = check_entity_contradictions(
                        clause_a, clause_b, ents_a, ents_b
                    )
                    violations.extend(entity_violations)
    
    return violations


# Map of number-words to their digit equivalents
_NUMBER_WORDS = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
    'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
    'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
    'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
    'eighty': '80', 'ninety': '90', 'hundred': '100', 'thousand': '1000',
    'once': '1', 'twice': '2', 'thrice': '3',
    'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5',
}


def _extract_numbers(text: str) -> List[str]:
    """Extract all numeric values from text, including number-words."""
    nums = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    for word in text.lower().split():
        clean = re.sub(r'[,;.!?]', '', word)
        if clean in _NUMBER_WORDS:
            nums.append(_NUMBER_WORDS[clean])
    return nums


def _extract_number_with_context(text: str) -> List[Dict]:
    """Extract each number together with the 1-3 surrounding context words."""
    words = text.split()
    results = []
    for i, word in enumerate(words):
        clean = re.sub(r'[,;.!?]', '', word)
        num = None
        # Check digit numbers
        m = re.match(r'^\d+(?:\.\d+)?$', clean)
        if m:
            num = clean
        # Check number-words
        elif clean.lower() in _NUMBER_WORDS:
            num = _NUMBER_WORDS[clean.lower()]
        if num is not None:
            # Grab up to 2 words after the number for context
            context_after = ' '.join(words[i+1:i+3]).rstrip('.,;:!?')
            results.append({'num': num, 'original': clean, 'context': context_after})
    return results


def _build_numeric_description(text_a: str, text_b: str, nums_a: List[str], nums_b: List[str]) -> str:
    """Build a human-readable description highlighting only the differing numbers."""
    details_a = _extract_number_with_context(text_a)
    details_b = _extract_number_with_context(text_b)

    # Find which raw numbers are unique to each side
    set_a = set(nums_a)
    set_b = set(nums_b)
    only_in_a = set_a - set_b
    only_in_b = set_b - set_a

    # Pick the best detail entry: prefer the one whose context words also
    # appear in the OTHER text (= same topic, different number)
    text_b_lower = text_b.lower()
    text_a_lower = text_a.lower()

    def _best_detail(details, only_set, other_text):
        scored = []
        for d in details:
            if d['num'] not in only_set:
                continue
            ctx_words = [w for w in d['context'].lower().split() if len(w) > 2]
            hits = sum(1 for w in ctx_words if w in other_text)
            scored.append((hits, d))
        if scored:
            scored.sort(key=lambda x: -x[0])
            d = scored[0][1]
            return f"{d['original']} {d['context']}".strip()
        return None

    label_a = _best_detail(details_a, only_in_a, text_b_lower)
    label_b = _best_detail(details_b, only_in_b, text_a_lower)

    if label_a and label_b:
        return f"Numeric conflict: {label_a} vs {label_b}"

    # Fallback
    if only_in_a and only_in_b:
        return f"Numeric conflict: {', '.join(sorted(only_in_a))} vs {', '.join(sorted(only_in_b))}"
    return f"Numeric conflict: values differ between statements"


def check_numeric_mismatch(clause_a, clause_b) -> Dict:
    """Detect numeric contradictions between structurally similar sentences."""
    # Skip clauses that are too short to carry meaningful numeric context
    if len(clause_a.text.split()) < 8 or len(clause_b.text.split()) < 8:
        return None

    nums_a = _extract_numbers(clause_a.text)
    nums_b = _extract_numbers(clause_b.text)

    if not nums_a or not nums_b:
        return None

    # Numbers must actually differ
    if sorted(nums_a) == sorted(nums_b):
        return None

    # Sentences must share substantial structure (content-word overlap)
    overlap = _content_overlap(clause_a.text, clause_b.text)
    if overlap < 0.40:
        return None

    description = _build_numeric_description(clause_a.text, clause_b.text, nums_a, nums_b)

    return {
        "clause_a": clause_a,
        "clause_b": clause_b,
        "type": "numeric",
        "severity": "high",
        "description": description,
        "confidence": 0.9
    }


def check_modal_mismatch(clause_a, clause_b) -> Dict:
    """Detect modal contradictions (must vs may, required vs optional)."""
    modals_strong = r'\b(must|shall|required|mandatory|obligatory)\b'
    modals_weak = r'\b(may|can|optional|permitted|allowed)\b'
    
    has_strong_a = bool(re.search(modals_strong, clause_a.text, re.IGNORECASE))
    has_weak_a = bool(re.search(modals_weak, clause_a.text, re.IGNORECASE))
    has_strong_b = bool(re.search(modals_strong, clause_b.text, re.IGNORECASE))
    has_weak_b = bool(re.search(modals_weak, clause_b.text, re.IGNORECASE))
    
    # Check if same topic with conflicting modals
    if (has_strong_a and has_weak_b) or (has_weak_a and has_strong_b):
        # Skip short noise clauses
        if len(clause_a.text.split()) < 8 or len(clause_b.text.split()) < 8:
            return None
        # Require near-identical sentence structure (high content-word overlap)
        overlap = _content_overlap(clause_a.text, clause_b.text)
        
        if overlap > 0.55:
            return {
                "clause_a": clause_a,
                "clause_b": clause_b,
                "type": "modal",
                "severity": "medium",
                "description": "Modal mismatch: mandatory vs optional",
                "confidence": 0.75
            }
    return None


def check_authority_mismatch(clause_a, clause_b) -> Dict:
    """Detect authority/responsibility contradictions."""
    # Look for authority patterns
    authority_pattern = r'\b(responsible|authority|department|team|manager|director)\b'
    
    if re.search(authority_pattern, clause_a.text, re.IGNORECASE) and \
       re.search(authority_pattern, clause_b.text, re.IGNORECASE):
        # Skip noise clauses
        if len(clause_a.text.split()) < 8 or len(clause_b.text.split()) < 8:
            return None
        # Extract potential authority entities
        entities_a = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', clause_a.text)
        entities_b = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', clause_b.text)
        
        # Check for different entities with similar context
        if entities_a and entities_b and set(entities_a) != set(entities_b):
            # Require near-identical sentence structure
            overlap = _content_overlap(clause_a.text, clause_b.text)
            
            if overlap > 0.55:
                return {
                    "clause_a": clause_a,
                    "clause_b": clause_b,
                    "type": "authority",
                    "severity": "medium",
                    "description": f"Authority mismatch: {entities_a} vs {entities_b}",
                    "confidence": 0.7
                }
    return None
