"""NLI service using lightweight cross-encoder model."""
import logging
import threading
import numpy as np
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

_nli_model = None
_nli_lock = threading.Lock()

import os
from config import settings

def _load_nli_model():
    global _nli_model
    if _nli_model is None:
        with _nli_lock:
            if _nli_model is None:  # double-checked locking
                from sentence_transformers import CrossEncoder
                model_name = 'cross-encoder/nli-distilroberta-base'

                # Ensure cache dir exists
                os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)

                try:
                    # Attempt local load first
                    _nli_model = CrossEncoder(
                        model_name,
                        cache_folder=settings.MODEL_CACHE_DIR,
                        local_files_only=True
                    )
                    logger.info(f"Loaded NLI model from local cache: {model_name}")
                except Exception:
                    # Fallback to download
                    logger.info(f"Model {model_name} not found locally. Downloading to {settings.MODEL_CACHE_DIR}...")
                    _nli_model = CrossEncoder(
                        model_name,
                        cache_folder=settings.MODEL_CACHE_DIR,
                        token=settings.HF_TOKEN if settings.HF_TOKEN else None
                    )
                    logger.info(f"Downloaded and loaded NLI model: {model_name}")


def detect_contradiction(text1: str, text2: str) -> float:
    """Return contradiction probability (0-1) between two texts."""
    _load_nli_model()
    logits = _nli_model.predict([(text1, text2)])
    # logits[0]: [contradiction, entailment, neutral] — raw logits
    probs = _softmax(logits[0])
    return float(probs[0])  # contradiction probability


def batch_nli_check(pairs: List[Tuple[str, str, str, str]]) -> List[Dict]:
    """Batch NLI check on clause pairs. Returns softmax probabilities."""
    if not pairs:
        return []
    
    _load_nli_model()
    
    # Prepare pairs for model
    text_pairs = [(p[0], p[1]) for p in pairs]
    logits = _nli_model.predict(text_pairs, batch_size=settings.NLI_BATCH_SIZE)
    
    # Convert all logits to probabilities in one vectorized call
    all_probs = _softmax_batch(np.array(logits))
    
    results = []
    for i, (text1, text2, id1, id2) in enumerate(pairs):
        # all_probs[i]: [contradiction_prob, entailment_prob, neutral_prob]
        results.append({
            "clause_a_id": id1,
            "clause_b_id": id2,
            "contradiction_score": float(all_probs[i][0]),
            "entailment_score": float(all_probs[i][1]),
            "neutral_score": float(all_probs[i][2])
        })
    
    return results


def _softmax(logits) -> np.ndarray:
    """Numerically stable softmax for a single logit vector."""
    x = np.array(logits, dtype=np.float64)
    x = x - np.max(x)  # stability
    e = np.exp(x)
    return e / e.sum()


def _softmax_batch(logits: np.ndarray) -> np.ndarray:
    """Vectorized softmax over rows of a 2-D logit matrix."""
    x = logits.astype(np.float64)
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)
