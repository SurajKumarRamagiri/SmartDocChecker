"""
Multi-document comparison worker.

Processes multiple documents and detects cross-document contradictions using:
1. Per-document clause extraction & embedding (reuses single-doc pipeline steps)
2. Cross-document similarity search (SBERT cosine similarity)
3. Rule-based contradiction detection across documents
4. NLI verification on candidate pairs
5. Persists results as CrossContradiction rows tied to a ComparisonSession
"""
import logging
import uuid
import json
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Tuple

from db.session import SessionLocal
from models.document import Document
from models.clause import Clause
from models.contradiction import Contradiction
from models.comparison import ComparisonSession
from models.cross_contradiction import CrossContradiction
from utils.text_extractor import extract_and_clean_text
from utils.clause_segmenter import segment_clauses
from utils.description_builder import build_semantic_description
from services.supabase_storage import get_signed_url
from services.embedding_service import generate_embeddings_batch
from services.rule_checker import check_contradictions_batch
from services.nli_service import batch_nli_check
from services.ner_service import extract_entities_batch
from constants import STOP_WORDS
from config import settings
import httpx

logger = logging.getLogger(__name__)

# ── Similarity threshold for cross-document clause matching ──
CROSS_DOC_SIMILARITY_THRESHOLD = 0.75  # High — only near-paraphrase clauses across docs
CONTRADICTION_CONFIDENCE_THRESHOLD = 0.75  # NLI confidence to store a contradiction


def process_multi_documents(comparison_id: str):
    """
    Full multi-document comparison pipeline.
    Runs synchronously so FastAPI dispatches it to a thread pool, keeping the
    event loop free for polling requests.

    Steps:
        1. Ensure every document has clauses + embeddings (reuse or generate)
        2. Build per-document clause+embedding arrays
        3. Cross-compare clause embeddings between each document pair
        4. Run rule-based checks on cross-document clause pairs
        5. NLI-verify all candidate pairs
        6. Persist CrossContradiction rows
    """
    db = SessionLocal()
    try:
        # ── 0. Load comparison session ──
        session = db.query(ComparisonSession).filter(ComparisonSession.id == comparison_id).first()
        if not session:
            raise ValueError(f"ComparisonSession {comparison_id} not found")

        def _update_session_stage(stage: str, progress: int):
            session.processing_stage = stage
            session.progress_percent = progress
            db.commit()

        session.status = "processing"
        session.started_at = datetime.now(timezone.utc)
        _update_session_stage("preparing", 5)

        document_ids: List[str] = json.loads(session.document_ids)
        logger.info(f"[Multi] Starting comparison {comparison_id} for {len(document_ids)} documents")

        # ── 1. Ensure each document is processed (clauses + embeddings) ──
        _update_session_stage("extracting", 10)
        doc_clauses: Dict[str, List[Clause]] = {}  # doc_id -> [Clause]

        for doc_id in document_ids:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            existing_clauses = (
                db.query(Clause)
                .filter(Clause.document_id == doc_id, Clause.embedding.isnot(None))
                .order_by(Clause.position)
                .all()
            )

            if existing_clauses:
                logger.info(f"[Multi] Reusing {len(existing_clauses)} existing clauses for doc {doc.name}")
                doc_clauses[doc_id] = existing_clauses
            else:
                logger.info(f"[Multi] Processing doc {doc.name} from scratch...")
                clauses = _process_single_doc_clauses(doc, db)
                doc_clauses[doc_id] = clauses

        # ── 2. Build a mapping doc_id -> (clause, embedding_vector) ──
        _update_session_stage("embedding", 30)
        doc_embeddings: Dict[str, List[Tuple[Clause, np.ndarray]]] = {}
        for doc_id, clauses in doc_clauses.items():
            pairs = []
            for c in clauses:
                if c.embedding is not None:
                    pairs.append((c, np.array(c.embedding)))
            doc_embeddings[doc_id] = pairs
            logger.info(f"[Multi] Doc {doc_id}: {len(pairs)} clauses with embeddings")

        # ── 3. Cross-document similarity search ──
        _update_session_stage("similarity", 45)
        candidate_pairs: List[Tuple[Clause, Clause, float, str, str]] = []
        doc_id_list = list(doc_embeddings.keys())

        for i in range(len(doc_id_list)):
            for j in range(i + 1, len(doc_id_list)):
                doc_a_id = doc_id_list[i]
                doc_b_id = doc_id_list[j]
                pairs_a = doc_embeddings[doc_a_id]
                pairs_b = doc_embeddings[doc_b_id]

                if not pairs_a or not pairs_b:
                    continue

                # Vectorized cosine similarity matrix for speed
                emb_a = np.array([p[1] for p in pairs_a])
                emb_b = np.array([p[1] for p in pairs_b])

                # Normalize
                norms_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
                norms_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
                emb_a_norm = emb_a / (norms_a + 1e-10)
                emb_b_norm = emb_b / (norms_b + 1e-10)

                # Cosine similarity matrix: (n_a, n_b)
                sim_matrix = emb_a_norm @ emb_b_norm.T

                # Extract pairs above threshold
                indices = np.argwhere(sim_matrix >= CROSS_DOC_SIMILARITY_THRESHOLD)
                for idx_a, idx_b in indices:
                    clause_a = pairs_a[idx_a][0]
                    clause_b = pairs_b[idx_b][0]
                    score = float(sim_matrix[idx_a, idx_b])
                    candidate_pairs.append((clause_a, clause_b, score, doc_a_id, doc_b_id))

                logger.info(
                    f"[Multi] Docs ({doc_a_id[:8]}.. vs {doc_b_id[:8]}..): "
                    f"{len(indices)} similar clause pairs found"
                )

        # ── 3b. Build global entities map for NER-aware rule checking ──
        global_entities_map: Dict[str, Dict] = {}
        for doc_id, clauses in doc_clauses.items():
            for c in clauses:
                if c.entities:
                    global_entities_map[c.id] = c.entities

        # ── 4. Cross-document rule-based checks (NER-enhanced) ──
        _update_session_stage("rules", 58)
        rule_violations: List[Dict] = []
        for i in range(len(doc_id_list)):
            for j in range(i + 1, len(doc_id_list)):
                doc_a_id = doc_id_list[i]
                doc_b_id = doc_id_list[j]
                combined_clauses = doc_clauses[doc_a_id] + doc_clauses[doc_b_id]
                boundary = len(doc_clauses[doc_a_id])

                # Run rule checker on the combined set (with entities)
                violations = check_contradictions_batch(combined_clauses, entities_map=global_entities_map)

                # Build a clause-id → position map (avoids .index() identity issues)
                clause_pos_map = {c.id: idx for idx, c in enumerate(combined_clauses)}

                # Keep only cross-document violations
                for v in violations:
                    ca = v["clause_a"]
                    cb = v["clause_b"]
                    pos_a = clause_pos_map.get(ca.id)
                    pos_b = clause_pos_map.get(cb.id)
                    if pos_a is None or pos_b is None:
                        continue  # safety guard
                    is_cross = (pos_a < boundary) != (pos_b < boundary)
                    if is_cross:
                        v["document_a_id"] = doc_a_id if pos_a < boundary else doc_b_id
                        v["document_b_id"] = doc_b_id if pos_a < boundary else doc_a_id
                        rule_violations.append(v)

        logger.info(f"[Multi] {len(rule_violations)} cross-doc rule violations found")

        # ── 5. NLI verification on all candidates ──
        _update_session_stage("nli", 70)
        nli_pairs = []
        pair_meta = []  # track doc IDs for each NLI pair
        seen_pair_keys = set()  # B14: deduplicate candidate pairs

        for clause_a, clause_b, sim_score, doc_a_id, doc_b_id in candidate_pairs:
            pair_key = tuple(sorted([clause_a.id, clause_b.id]))
            if pair_key not in seen_pair_keys:
                seen_pair_keys.add(pair_key)
                nli_pairs.append((clause_a.text, clause_b.text, clause_a.id, clause_b.id))
                pair_meta.append((doc_a_id, doc_b_id))

        for v in rule_violations:
            pair_key = tuple(sorted([v["clause_a"].id, v["clause_b"].id]))
            if pair_key not in seen_pair_keys:
                seen_pair_keys.add(pair_key)
                nli_pairs.append((
                    v["clause_a"].text, v["clause_b"].text,
                    v["clause_a"].id, v["clause_b"].id
                ))
                pair_meta.append((v["document_a_id"], v["document_b_id"]))

        # Clear existing cross contradictions for this session
        db.query(CrossContradiction).filter(CrossContradiction.comparison_id == comparison_id).delete()
        db.commit()

        stored_count = 0

        # Pre-filter: drop pairs with very low content-word overlap
        if nli_pairs:
            filtered = []
            filtered_meta = []
            for idx, (text_a, text_b, id_a, id_b) in enumerate(nli_pairs):
                wa = {w for w in text_a.lower().split() if w not in STOP_WORDS and len(w) > 2}
                wb = {w for w in text_b.lower().split() if w not in STOP_WORDS and len(w) > 2}
                if wa and wb:
                    overlap = len(wa & wb) / max(len(wa), len(wb))
                    # Require substantial shared vocabulary — same/similar structure
                    if overlap < 0.30:
                        continue
                filtered.append((text_a, text_b, id_a, id_b))
                filtered_meta.append(pair_meta[idx])
            logger.info(f"[Multi] Word-overlap filter: {len(nli_pairs)} → {len(filtered)} pairs")
            nli_pairs = filtered
            pair_meta = filtered_meta

        if nli_pairs:
            _update_session_stage("nli", 78)
            logger.info(f"[Multi] Running NLI verification on {len(nli_pairs)} candidate pairs...")
            nli_results = batch_nli_check(nli_pairs)
            logger.info("[Multi] NLI verification complete")

            # Build rule map for fast lookup
            rule_map_cross = {}
            for v in rule_violations:
                rk = tuple(sorted([v["clause_a"].id, v["clause_b"].id]))
                rule_map_cross[rk] = v

            # ── 6. Store cross-document contradictions ──
            _update_session_stage("storing", 90)
            seen_pairs = set()  # Deduplicate
            for idx, result in enumerate(nli_results):
                c_score = result["contradiction_score"]
                e_score = result["entailment_score"]
                n_score = result["neutral_score"]

                pair_key = tuple(sorted([result["clause_a_id"], result["clause_b_id"]]))
                has_rule_backing = pair_key in rule_map_cross

                # Rule-backed pairs get a lower NLI threshold
                min_score = 0.50 if has_rule_backing else CONTRADICTION_CONFIDENCE_THRESHOLD
                rv_entry = rule_map_cross.get(pair_key)
                is_numeric_rule = rv_entry is not None and rv_entry.get("type") == "numeric"

                # Gate 1: contradiction score must exceed threshold
                if c_score < min_score:
                    if not is_numeric_rule:
                        continue
                # Gate 2: contradiction must be the dominant label
                if c_score <= e_score or c_score <= n_score:
                    if not is_numeric_rule:
                        continue
                # Gate 3: entailment veto
                # (numeric mismatches bypass — NLI often misjudges number conflicts)
                if e_score > 0.5:
                    if not is_numeric_rule:
                        continue

                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                doc_a_id, doc_b_id = pair_meta[idx]

                # For numeric-rule overrides, use rule confidence
                rv_for_conf = rule_map_cross.get(pair_key)
                is_num_rule = rv_for_conf is not None and rv_for_conf.get("type") == "numeric"
                c_conf = rv_for_conf["confidence"] if is_num_rule and c_score < 0.50 else c_score
                # Scale confidence to 0-100 range
                c_conf_pct = round(c_conf * 100, 1)

                # Determine type, severity, and description
                rv = rule_map_cross.get(pair_key)
                if rv:
                    severity = rv.get("severity", "medium")
                else:
                    severity = "high" if c_conf_pct >= 90 else ("medium" if c_conf_pct >= 60 else "low")
                if rv:
                    cc_type = rv["type"]
                    cc_desc = rv["description"]
                else:
                    cc_type = "semantic"
                    cc_desc = build_semantic_description(
                        result["clause_a_id"], result["clause_b_id"],
                        nli_pairs, c_conf_pct
                    )

                cc = CrossContradiction(
                    id=str(uuid.uuid4()),
                    comparison_id=comparison_id,
                    clause_a_id=result["clause_a_id"],
                    document_a_id=doc_a_id,
                    clause_b_id=result["clause_b_id"],
                    document_b_id=doc_b_id,
                    type=cc_type,
                    severity=severity,
                    description=cc_desc,
                    confidence=c_conf_pct,
                )
                db.add(cc)
                stored_count += 1

        session.total_cross_contradictions = stored_count
        session.status = "completed"
        session.processing_stage = "completed"
        session.progress_percent = 100
        session.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"[Multi] Comparison {comparison_id} complete: "
            f"{stored_count} cross-document contradictions stored"
        )

    except Exception as e:
        logger.error(f"[Multi] Error in comparison {comparison_id}: {e}", exc_info=True)
        try:
            session = db.query(ComparisonSession).filter(ComparisonSession.id == comparison_id).first()
            if session:
                session.status = "failed"
                session.error_message = str(e)[:500]
                db.commit()
        except Exception as inner_e:
            logger.error(f"[Multi] Could not update status to failed: {inner_e}")
        raise
    finally:
        db.close()


def _process_single_doc_clauses(doc: Document, db) -> List[Clause]:
    """
    Process a single document: download → extract → segment → embed → store clauses.
    Reuses the same pipeline as the single-doc worker but operates within the caller's session.
    """
    # Download file from Supabase
    signed_url = get_signed_url(doc.file_path, expires_in=300)
    with httpx.Client() as client:
        response = client.get(signed_url)
        response.raise_for_status()
        file_content = response.content

    # Clean existing data for this doc (FK-safe order: contradictions → clauses)
    existing_clause_ids = [
        cid for (cid,) in db.query(Clause.id).filter(Clause.document_id == doc.id).all()
    ]
    if existing_clause_ids:
        db.query(Contradiction).filter(Contradiction.document_id == doc.id).delete()
        db.query(CrossContradiction).filter(
            CrossContradiction.clause_a_id.in_(existing_clause_ids)
            | CrossContradiction.clause_b_id.in_(existing_clause_ids)
        ).delete(synchronize_session="fetch")
    db.query(Clause).filter(Clause.document_id == doc.id).delete()
    db.commit()

    # Extract text
    raw_text = extract_and_clean_text(file_content, doc.name)
    logger.info(f"[Multi] Extracted {len(raw_text)} chars from {doc.name}")

    # Segment clauses
    clause_texts = segment_clauses(raw_text)
    logger.info(f"[Multi] Segmented {len(clause_texts)} clauses from {doc.name}")

    # Guard against pathologically long documents
    MAX_CLAUSES = 500
    if len(clause_texts) > MAX_CLAUSES:
        logger.warning(
            f"[Multi] Doc {doc.name} has {len(clause_texts)} clauses, "
            f"capping at {MAX_CLAUSES}"
        )
        clause_texts = clause_texts[:MAX_CLAUSES]

    if not clause_texts:
        return []

    # Create clause records
    clauses = []
    for i, text in enumerate(clause_texts):
        clause = Clause(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            text=text,
            position=i,
            section=None,
        )
        clauses.append(clause)

    db.bulk_save_objects(clauses)
    db.commit()

    # Re-fetch to get attached ORM objects
    clauses = (
        db.query(Clause)
        .filter(Clause.document_id == doc.id)
        .order_by(Clause.position)
        .all()
    )

    # Generate embeddings
    logger.info(f"[Multi] Generating embeddings for {len(clauses)} clauses...")
    texts_for_emb = [c.text for c in clauses]
    embeddings = generate_embeddings_batch(texts_for_emb)

    for clause, embedding in zip(clauses, embeddings):
        clause.embedding = embedding

    # NER – extract named entities (batch)
    logger.info(f"[Multi] Extracting named entities for {len(clauses)} clauses...")
    ner_results = extract_entities_batch(texts_for_emb)
    for clause, ents in zip(clauses, ner_results):
        clause.entities = ents if ents else None

    # Update search vectors (PostgreSQL only)
    if not settings.DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        db.execute(
            text("UPDATE clauses SET search_vector = to_tsvector('english', text) WHERE document_id = :doc_id"),
            {"doc_id": doc.id},
        )
    db.commit()

    # Mark doc as completed if it was pending
    if doc.status == "pending":
        doc.status = "completed"
        doc.analysis_start_time = datetime.now(timezone.utc)
        doc.analysis_end_time = datetime.now(timezone.utc)
        db.commit()

    return clauses
