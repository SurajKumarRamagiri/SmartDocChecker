"""Enhanced embedding service with batch generation and similarity search."""
import logging
import threading
import numpy as np
from typing import List, Tuple
from sqlalchemy.orm import Session
from models.clause import Clause

logger = logging.getLogger(__name__)

import os
from config import settings

_sbert_model = None
_sbert_lock = threading.Lock()

def _load_sbert_model():
    global _sbert_model
    if _sbert_model is None:
        with _sbert_lock:
            if _sbert_model is None:  # double-checked locking
                from sentence_transformers import SentenceTransformer
                model_name = "all-MiniLM-L6-v2"

                # Ensure cache dir exists
                os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)

                try:
                    # Attempt local load first
                    _sbert_model = SentenceTransformer(
                        model_name,
                        cache_folder=settings.MODEL_CACHE_DIR,
                        local_files_only=True
                    )
                    logger.info(f"Loaded SBERT model from local cache: {model_name}")
                except Exception:
                    # Fallback to download
                    logger.info(f"Model {model_name} not found locally. Downloading to {settings.MODEL_CACHE_DIR}...")
                    _sbert_model = SentenceTransformer(
                        model_name,
                        cache_folder=settings.MODEL_CACHE_DIR,
                        token=settings.HF_TOKEN if settings.HF_TOKEN else None
                    )
                    logger.info(f"Downloaded and loaded SBERT model: {model_name}")


def semantic_similarity(text1: str, text2: str) -> float:
    """Return cosine similarity between two texts."""
    _load_sbert_model()
    from sentence_transformers import util
    emb1 = _sbert_model.encode(text1, convert_to_tensor=True)
    emb2 = _sbert_model.encode(text2, convert_to_tensor=True)
    return util.pytorch_cos_sim(emb1, emb2).item()


def generate_embeddings_batch(texts: List[str], chunk_size: int = 50) -> List[List[float]]:
    """Generate embeddings for a batch of texts with interval logging."""
    _load_sbert_model()
    
    if not texts:
        return []

    total_texts = len(texts)
    if total_texts <= chunk_size:
        embeddings = _sbert_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    all_embeddings = []
    for i in range(0, total_texts, chunk_size):
        end = min(i + chunk_size, total_texts)
        chunk = texts[i:end]
        logger.info(f"Generating embeddings: {i}/{total_texts} clauses processed...")
        chunk_embeddings = _sbert_model.encode(chunk, convert_to_numpy=True, show_progress_bar=False)
        all_embeddings.extend(chunk_embeddings.tolist())
    
    logger.info(f"Successfully generated {total_texts} embeddings in total.")
    return all_embeddings


def find_similar_clauses(
    query_embedding: List[float], 
    document_id: str, 
    db: Session = None, 
    top_k: int = 10,
    threshold: float = 0.5,
    preloaded_clauses: List[Clause] = None
) -> List[Tuple[Clause, float]]:
    """Find similar clauses using cosine similarity. Uses preloaded clauses if provided to avoid DB hits."""
    query_vec = np.array(query_embedding)
    
    # Use preloaded clauses or fetch from DB
    if preloaded_clauses is not None:
        clauses = [c for c in preloaded_clauses if c.embedding is not None]
    elif db is not None:
        clauses = db.query(Clause).filter(
            Clause.document_id == document_id,
            Clause.embedding.isnot(None)
        ).all()
    else:
        logger.error("Neither db nor preloaded_clauses provided to find_similar_clauses")
        return []
    
    results = []
    for clause in clauses:
        clause_vec = np.array(clause.embedding)
        denom = np.linalg.norm(query_vec) * np.linalg.norm(clause_vec)
        if denom == 0:
            continue
        similarity = np.dot(query_vec, clause_vec) / denom
        
        if similarity >= threshold:
            results.append((clause, float(similarity)))
    
    # Sort by similarity descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
