"""
Analysis and contradiction results API routes.
"""
import json
import logging
import uuid
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from schemas.result_schema import ContradictionOut
from dependencies import get_current_user, get_db, limiter
from config import settings
from workers.comparison_worker import process_multi_documents
from workers.processing_worker import process_document
from models.document import Document
from models.clause import Clause
from models.contradiction import Contradiction
from models.comparison import ComparisonSession
from models.cross_contradiction import CrossContradiction
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Analysis"])


# ── Request schema ──
class MultiAnalyzeRequest(BaseModel):
    document_ids: List[str]


def _verify_document_ownership(document_id: str, current_user: dict, db: Session):
    """Ensure the document belongs to the current user."""
    user_id = current_user["user_id"]
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied")


@router.post("/analyze/single")
@limiter.limit("10/minute")
async def analyze_single(
    request: Request,
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Analyze single document in background."""
    _verify_document_ownership(document_id, current_user, db)
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    background_tasks.add_task(process_document, document_id)
    return {"message": "Analysis started", "document_id": document_id}


@router.get("/documents/{document_id}/results")
async def get_results(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get analysis results for a document."""
    _verify_document_ownership(document_id, current_user, db)
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    clauses = db.query(Clause).filter(Clause.document_id == document_id).all()
    contradictions = db.query(Contradiction).filter(Contradiction.document_id == document_id).all()
    
    # Build clause map for O(1) lookups (avoids N+1)
    clause_map = {c.id: c for c in clauses}
    
    # Group by severity
    grouped = {"high": [], "medium": [], "low": []}
    for c in contradictions:
        clause_a = clause_map.get(c.clause_a_id)
        clause_b = clause_map.get(c.clause_b_id)
        
        grouped[c.severity or "medium"].append({
            "id": c.id,
            "type": c.type,
            "description": c.description,
            "confidence": c.confidence,
            "clause_a": {"id": clause_a.id, "text": clause_a.text} if clause_a else None,
            "clause_b": {"id": clause_b.id, "text": clause_b.text} if clause_b else None
        })
    
    analysis_duration = 0
    if doc.analysis_start_time and doc.analysis_end_time:
        analysis_duration = (doc.analysis_end_time - doc.analysis_start_time).total_seconds()
    
    return {
        "document_id": document_id,
        "status": doc.status,
        "analysis_start_time": doc.analysis_start_time,
        "analysis_end_time": doc.analysis_end_time,
        "analysis_duration": round(analysis_duration, 2),
        "total_clauses": len(clauses),
        "total_contradictions": len(contradictions),
        "contradictions_by_severity": grouped
    }


@router.get("/documents/{document_id}/clauses")
async def search_clauses(
    document_id: str,
    q: str = None,
    section: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search clauses with full-text search."""
    _verify_document_ownership(document_id, current_user, db)
    query = db.query(Clause).filter(Clause.document_id == document_id)
    
    if section:
        query = query.filter(Clause.section == section)
    
    if q:
        # Full-text search — PostgreSQL only; fall back to LIKE on SQLite
        if settings.DATABASE_URL.startswith("sqlite"):
            query = query.filter(Clause.text.ilike(f"%{q}%"))
        else:
            query = query.filter(Clause.search_vector.match(q))
    
    clauses = query.all()
    return {"clauses": [{"id": c.id, "text": c.text, "section": c.section, "position": c.position} for c in clauses]}


@router.post("/analyze/multi")
@limiter.limit("5/minute")
async def analyze_multi(
    request: Request,
    body: MultiAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Start a multi-document comparison.
    Accepts 2-10 document IDs, runs the comparison in the background,
    and returns a comparison_id for polling.
    """
    doc_ids = body.document_ids

    if len(doc_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 documents are required for comparison")
    if len(doc_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 documents per comparison")

    # Verify all documents exist and belong to the user
    user_id = current_user["user_id"]

    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or not yours")

    # Create comparison session
    comparison_id = str(uuid.uuid4())
    session = ComparisonSession(
        id=comparison_id,
        user_id=user_id,
        status="pending",
        document_ids=json.dumps(doc_ids),
    )
    db.add(session)
    db.commit()

    # Kick off background worker
    background_tasks.add_task(process_multi_documents, comparison_id)

    return {"message": "Multi-document comparison started", "comparison_id": comparison_id}


@router.get("/comparison/{comparison_id}/status")
async def get_comparison_status(
    comparison_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Poll comparison status."""
    user_id = current_user["user_id"]
    session = db.query(ComparisonSession).filter(
        ComparisonSession.id == comparison_id,
        ComparisonSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Comparison not found")

    return {
        "comparison_id": comparison_id,
        "status": session.status,
        "processing_stage": session.processing_stage,
        "progress_percent": session.progress_percent or 0,
        "error_message": session.error_message,
    }


@router.get("/comparison/{comparison_id}/results")
async def get_comparison_results(
    comparison_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Fetch full comparison results."""
    user_id = current_user["user_id"]
    session = db.query(ComparisonSession).filter(
        ComparisonSession.id == comparison_id,
        ComparisonSession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Comparison not found")

    document_ids = json.loads(session.document_ids)

    # Fetch document names
    docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
    doc_map = {d.id: d.name for d in docs}

    # Fetch cross contradictions
    cross_contras = (
        db.query(CrossContradiction)
        .filter(CrossContradiction.comparison_id == comparison_id)
        .all()
    )

    # Build clause map for efficient lookup
    clause_ids = set()
    for cc in cross_contras:
        if cc.clause_a_id:
            clause_ids.add(cc.clause_a_id)
        if cc.clause_b_id:
            clause_ids.add(cc.clause_b_id)

    clauses = db.query(Clause).filter(Clause.id.in_(clause_ids)).all() if clause_ids else []
    clause_map = {c.id: c for c in clauses}

    # Group by severity
    grouped = {"high": [], "medium": [], "low": []}
    for cc in cross_contras:
        clause_a = clause_map.get(cc.clause_a_id)
        clause_b = clause_map.get(cc.clause_b_id)

        entry = {
            "id": cc.id,
            "type": cc.type,
            "severity": cc.severity,
            "description": cc.description,
            "confidence": cc.confidence,
            "document_a": {
                "id": cc.document_a_id,
                "name": doc_map.get(cc.document_a_id, "Unknown"),
            },
            "document_b": {
                "id": cc.document_b_id,
                "name": doc_map.get(cc.document_b_id, "Unknown"),
            },
            "clause_a": {"id": clause_a.id, "text": clause_a.text} if clause_a else None,
            "clause_b": {"id": clause_b.id, "text": clause_b.text} if clause_b else None,
        }
        grouped[cc.severity or "medium"].append(entry)

    # Compute duration
    duration = 0
    if session.started_at and session.completed_at:
        duration = (session.completed_at - session.started_at).total_seconds()

    # Total clauses across all compared documents
    total_clauses = db.query(Clause).filter(Clause.document_id.in_(document_ids)).count()

    return {
        "comparison_id": comparison_id,
        "status": session.status,
        "documents": [{"id": did, "name": doc_map.get(did, "Unknown")} for did in document_ids],
        "total_clauses": total_clauses,
        "total_contradictions": len(cross_contras),
        "analysis_duration": round(duration, 2),
        "contradictions_by_severity": grouped,
    }
