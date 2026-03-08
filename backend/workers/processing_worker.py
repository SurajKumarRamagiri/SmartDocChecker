"""Processing worker for document analysis pipeline."""
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from models.document import Document
from models.clause import Clause
from models.contradiction import Contradiction
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
import numpy as np

logger = logging.getLogger(__name__)

from db.session import SessionLocal


def _update_stage(db, doc, stage: str, progress: int):
    """Update the document's processing stage and progress percent."""
    doc.processing_stage = stage
    doc.progress_percent = progress
    db.commit()


def process_document(document_id: str):
    """
    Process document: extract text -> segment clauses -> generate embeddings -> detect contradictions.
    Runs synchronously so FastAPI dispatches it to a thread pool, keeping the
    event loop free for polling requests.
    """
    db = SessionLocal()
    try:
        # 1. Fetch document
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        doc.status = "processing"
        doc.analysis_start_time = datetime.now(timezone.utc)
        doc.analysis_end_time = None
        _update_stage(db, doc, "downloading", 5)
        
        # 2. Download file from Supabase
        signed_url = get_signed_url(doc.file_path, expires_in=300)
        with httpx.Client() as client:
            response = client.get(signed_url)
            response.raise_for_status()
            file_content = response.content
        
        # 3. Cleanup existing data (prevent duplication)
        logger.info(f"Clearing existing clauses and contradictions for document {document_id}...")
        db.query(Contradiction).filter(Contradiction.document_id == document_id).delete()
        db.query(Clause).filter(Clause.document_id == document_id).delete()
        db.commit()

        # 4. Extract text
        _update_stage(db, doc, "extracting", 15)
        raw_text = extract_and_clean_text(file_content, doc.name)
        logger.info(f"Extracted {len(raw_text)} chars from {doc.name}")
        
        # 4. Segment clauses
        _update_stage(db, doc, "segmenting", 25)
        clause_texts = segment_clauses(raw_text)
        logger.info(f"Segmented {len(clause_texts)} clauses")

        # Guard against pathologically long documents
        MAX_CLAUSES = 500
        if len(clause_texts) > MAX_CLAUSES:
            logger.warning(
                f"Document {document_id} has {len(clause_texts)} clauses, "
                f"capping at {MAX_CLAUSES}"
            )
            clause_texts = clause_texts[:MAX_CLAUSES]
        
        # 5. Bulk insert clauses
        clauses = []
        for i, text in enumerate(clause_texts):
            clause = Clause(
                id=str(uuid.uuid4()),
                document_id=document_id,
                text=text,
                position=i,
                section=None  # TODO: extract section headings
            )
            clauses.append(clause)
        
        db.bulk_save_objects(clauses)
        db.commit()
        
        # Re-fetch clauses to get their IDs and ensure they are attached to current session
        clauses = db.query(Clause).filter(Clause.document_id == document_id).order_by(Clause.position).all()
        
        # 6. Generate embeddings (batch)
        _update_stage(db, doc, "embedding", 40)
        logger.info(f"Generating embeddings for {len(clauses)} clauses...")
        clause_texts_for_emb = [c.text for c in clauses]
        embeddings = generate_embeddings_batch(clause_texts_for_emb)
        logger.info("Embeddings generation complete")
        
        for clause, embedding in zip(clauses, embeddings):
            clause.embedding = embedding
        
        # Update search vectors (PostgreSQL only)
        if not settings.DATABASE_URL.startswith("sqlite"):
            logger.info("Updating search vectors for full-text search...")
            from sqlalchemy import text
            db.execute(
                text("UPDATE clauses SET search_vector = to_tsvector('english', text) WHERE document_id = :doc_id"),
                {"doc_id": document_id}
            )
        db.commit()
        
        # 7. NER – extract named entities for all clauses (batch)
        _update_stage(db, doc, "ner", 55)
        logger.info(f"Extracting named entities for {len(clauses)} clauses...")
        clause_texts_for_ner = [c.text for c in clauses]
        all_entities = extract_entities_batch(clause_texts_for_ner)
        entities_map = {}
        for clause, ents in zip(clauses, all_entities):
            clause.entities = ents if ents else None
            entities_map[clause.id] = ents
        db.commit()
        logger.info("NER extraction complete")

        # 8. Find similar clause pairs — vectorized matrix multiply (fast)
        _update_stage(db, doc, "similarity", 65)
        logger.info("Identifying candidate contradiction pairs (vectorized)...")
        similar_pairs = []
        emb_list = [c.embedding for c in clauses if c.embedding is not None]
        valid_clauses = [c for c in clauses if c.embedding is not None]

        if len(valid_clauses) > 1:
            emb_matrix = np.array(emb_list)
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            emb_norm = emb_matrix / (norms + 1e-10)
            sim_matrix = emb_norm @ emb_norm.T

            # Extract upper-triangle pairs above threshold (avoid self and duplicates)
            # High threshold: only near-paraphrase clauses (same structure) are candidates
            indices = np.argwhere((sim_matrix >= 0.82) & (np.triu(np.ones_like(sim_matrix, dtype=bool), k=1)))
            for idx_a, idx_b in indices:
                similar_pairs.append((valid_clauses[idx_a], valid_clauses[idx_b], float(sim_matrix[idx_a, idx_b])))

        logger.info(f"Found {len(similar_pairs)} similar clause pairs")

        # 9. Rule-based checks (now includes NER entity-based detection)
        _update_stage(db, doc, "rules", 72)
        logger.info("Running rule-based contradiction checks (with NER)...")
        rule_violations = check_contradictions_batch(clauses, entities_map=entities_map)

        # 10. Merge all candidates, deduplicate, and NLI-verify everything
        seen_pair_keys = set()
        nli_pairs = []

        for clause_a, clause_b, _ in similar_pairs:
            pair_key = tuple(sorted([clause_a.id, clause_b.id]))
            if pair_key not in seen_pair_keys:
                seen_pair_keys.add(pair_key)
                nli_pairs.append((clause_a.text, clause_b.text, clause_a.id, clause_b.id))

        # Track which rule violations exist so we can tag type/severity after NLI
        rule_map = {}  # (id_a, id_b) -> violation dict
        for violation in rule_violations:
            pair_key = tuple(sorted([violation["clause_a"].id, violation["clause_b"].id]))
            rule_map[pair_key] = violation
            if pair_key not in seen_pair_keys:
                seen_pair_keys.add(pair_key)
                nli_pairs.append((violation["clause_a"].text, violation["clause_b"].text,
                                  violation["clause_a"].id, violation["clause_b"].id))

        # Pre-filter: drop pairs with very low word overlap (unrelated topics)
        if nli_pairs:
            filtered_nli = []
            for text_a, text_b, id_a, id_b in nli_pairs:
                wa = {w for w in text_a.lower().split() if w not in STOP_WORDS and len(w) > 2}
                wb = {w for w in text_b.lower().split() if w not in STOP_WORDS and len(w) > 2}
                if wa and wb:
                    overlap = len(wa & wb) / max(len(wa), len(wb))
                    # Require substantial shared vocabulary — same/similar structure
                    if overlap < 0.30:
                        continue
                filtered_nli.append((text_a, text_b, id_a, id_b))
            logger.info(f"Word-overlap filter: {len(nli_pairs)} → {len(filtered_nli)} pairs")
            nli_pairs = filtered_nli

        if nli_pairs:
            _update_stage(db, doc, "nli", 80)
            logger.info(f"Running NLI verification for {len(nli_pairs)} candidate pairs...")
            nli_results = batch_nli_check(nli_pairs)
            logger.info("NLI verification complete")

            # 11. Store only NLI-verified contradictions
            for result in nli_results:
                c_score = result["contradiction_score"]
                e_score = result["entailment_score"]
                n_score = result["neutral_score"]

                pair_key = tuple(sorted([result["clause_a_id"], result["clause_b_id"]]))
                rule_v = rule_map.get(pair_key)
                has_rule_backing = rule_v is not None

                # Rule-backed pairs get a lower NLI threshold (they already
                # have structural evidence of a mismatch)
                min_score = 0.50 if has_rule_backing else 0.75
                is_numeric_rule = has_rule_backing and rule_v.get("type") == "numeric"

                # Gate 1: contradiction score must exceed threshold
                if c_score <= min_score:
                    # Numeric-rule override: if the rule checker found concrete
                    # different numbers in structurally-similar sentences, trust
                    # the structural evidence even when NLI is unsure
                    if not is_numeric_rule:
                        continue
                # Gate 2: contradiction must be the dominant label
                if c_score <= e_score or c_score <= n_score:
                    if not is_numeric_rule:
                        continue
                # Gate 3: entailment veto — if model thinks they agree, skip
                # (numeric mismatches bypass this since NLI often misjudges numbers)
                if e_score > 0.5:
                    if not is_numeric_rule:
                        continue
                c_type = rule_v["type"] if rule_v else "semantic"
                # For numeric-rule overrides, use rule confidence since NLI is unreliable on numbers
                c_conf = rule_v["confidence"] if is_numeric_rule and c_score < 0.50 else c_score
                # Scale confidence to 0-100 range
                c_conf_pct = round(c_conf * 100, 1)
                # Use rule severity when available; derive from confidence only for semantic
                if rule_v:
                    c_severity = rule_v["severity"]
                else:
                    c_severity = "high" if c_conf_pct >= 90 else ("medium" if c_conf_pct >= 60 else "low")
                if rule_v:
                    c_desc = rule_v["description"]
                else:
                    c_desc = build_semantic_description(
                        result["clause_a_id"], result["clause_b_id"],
                        nli_pairs, c_conf_pct
                    )
                contradiction = Contradiction(
                    id=str(uuid.uuid4()),
                    clause_a_id=result["clause_a_id"],
                    clause_b_id=result["clause_b_id"],
                    type=c_type,
                    severity=c_severity,
                    description=c_desc,
                    confidence=c_conf_pct,
                    document_id=document_id
                )
                db.add(contradiction)

        _update_stage(db, doc, "storing", 90)
        
        doc.status = "completed"
        doc.processing_stage = "completed"
        doc.progress_percent = 100
        doc.analysis_end_time = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Document {document_id} processing complete")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                doc.processing_stage = "failed"
                doc.progress_percent = 0
                db.commit()
        except Exception as inner_e:
            logger.error(f"Could not update status to failed: {inner_e}")
        raise
    finally:
        db.close()
