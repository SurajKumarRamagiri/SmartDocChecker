"""
Dashboard analytics API routes.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies import get_current_user, get_db
from models.user import User
from models.document import Document
from models.contradiction import Contradiction
from models.clause import Clause
from models.cross_contradiction import CrossContradiction
from models.comparison import ComparisonSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return real-time analytics for the current user's dashboard."""
    user_id = current_user["user_id"]

    # ── User's documents ──
    user_doc_ids = db.query(Document.id).filter(Document.user_id == user_id).subquery()

    total_docs = db.query(func.count(Document.id)).filter(
        Document.user_id == user_id
    ).scalar() or 0

    docs_completed = db.query(func.count(Document.id)).filter(
        Document.user_id == user_id, Document.status == "completed"
    ).scalar() or 0

    docs_pending = db.query(func.count(Document.id)).filter(
        Document.user_id == user_id, Document.status == "pending"
    ).scalar() or 0

    docs_failed = db.query(func.count(Document.id)).filter(
        Document.user_id == user_id, Document.status == "failed"
    ).scalar() or 0

    # ── Single-doc contradictions ──
    single_total = db.query(func.count(Contradiction.id)).filter(
        Contradiction.document_id.in_(db.query(user_doc_ids))
    ).scalar() or 0

    single_severity = {}
    for severity in ["high", "medium", "low"]:
        count = db.query(func.count(Contradiction.id)).filter(
            Contradiction.document_id.in_(db.query(user_doc_ids)),
            Contradiction.severity == severity,
        ).scalar() or 0
        single_severity[severity] = count

    single_type_rows = (
        db.query(Contradiction.type, func.count(Contradiction.id))
        .filter(Contradiction.document_id.in_(db.query(user_doc_ids)))
        .group_by(Contradiction.type)
        .all()
    )

    # ── Cross-doc contradictions (from user's comparison sessions) ──
    user_comparison_ids = (
        db.query(ComparisonSession.id)
        .filter(ComparisonSession.user_id == user_id)
        .subquery()
    )

    cross_total = db.query(func.count(CrossContradiction.id)).filter(
        CrossContradiction.comparison_id.in_(db.query(user_comparison_ids))
    ).scalar() or 0

    cross_severity = {}
    for severity in ["high", "medium", "low"]:
        count = db.query(func.count(CrossContradiction.id)).filter(
            CrossContradiction.comparison_id.in_(db.query(user_comparison_ids)),
            CrossContradiction.severity == severity,
        ).scalar() or 0
        cross_severity[severity] = count

    cross_type_rows = (
        db.query(CrossContradiction.type, func.count(CrossContradiction.id))
        .filter(CrossContradiction.comparison_id.in_(db.query(user_comparison_ids)))
        .group_by(CrossContradiction.type)
        .all()
    )

    # ── Merge totals ──
    total_contradictions = single_total + cross_total

    severity_counts = {}
    for severity in ["high", "medium", "low"]:
        severity_counts[severity] = single_severity.get(severity, 0) + cross_severity.get(severity, 0)

    type_counts = {}
    for ctype, count in single_type_rows:
        type_counts[ctype or "unknown"] = type_counts.get(ctype or "unknown", 0) + count
    for ctype, count in cross_type_rows:
        type_counts[ctype or "unknown"] = type_counts.get(ctype or "unknown", 0) + count

    # ── Total clauses ──
    total_clauses = db.query(func.count(Clause.id)).filter(
        Clause.document_id.in_(db.query(user_doc_ids))
    ).scalar() or 0

    # ── Average analysis duration (SQL aggregate — avoids loading all rows) ──
    from sqlalchemy import extract as sa_extract

    avg_doc_dur = (
        db.query(
            func.avg(
                sa_extract('epoch', Document.analysis_end_time)
                - sa_extract('epoch', Document.analysis_start_time)
            )
        )
        .filter(
            Document.user_id == user_id,
            Document.status == "completed",
            Document.analysis_start_time.isnot(None),
            Document.analysis_end_time.isnot(None),
        )
        .scalar()
    )
    avg_doc_dur = float(avg_doc_dur) if avg_doc_dur is not None else 0.0

    avg_comp_dur = (
        db.query(
            func.avg(
                sa_extract('epoch', ComparisonSession.completed_at)
                - sa_extract('epoch', ComparisonSession.started_at)
            )
        )
        .filter(
            ComparisonSession.user_id == user_id,
            ComparisonSession.status == "completed",
            ComparisonSession.started_at.isnot(None),
            ComparisonSession.completed_at.isnot(None),
        )
        .scalar()
    )
    avg_comp_dur = float(avg_comp_dur) if avg_comp_dur is not None else 0.0

    # ── Comparison sessions count ──
    total_comparisons = db.query(func.count(ComparisonSession.id)).filter(
        ComparisonSession.user_id == user_id,
    ).scalar() or 0

    comparisons_completed = db.query(func.count(ComparisonSession.id)).filter(
        ComparisonSession.user_id == user_id,
        ComparisonSession.status == "completed",
    ).scalar() or 0

    # Weighted average across both
    count_doc = docs_completed
    count_comp = comparisons_completed
    total_count = count_doc + count_comp
    avg_duration = round(
        (avg_doc_dur * count_doc + avg_comp_dur * count_comp) / total_count, 1
    ) if total_count > 0 else 0.0

    # ── Recent activity (last 5 single-doc + last 5 comparisons, merged & sorted) ──
    recent_docs = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.status.in_(["completed", "failed"]),
        )
        .order_by(Document.analysis_end_time.desc())
        .limit(5)
        .all()
    )

    recent_activity = []

    # Batch query contradiction counts for recent docs (avoids N+1)
    recent_doc_ids = [doc.id for doc in recent_docs]
    if recent_doc_ids:
        contradiction_counts = dict(
            db.query(Contradiction.document_id, func.count(Contradiction.id))
            .filter(Contradiction.document_id.in_(recent_doc_ids))
            .group_by(Contradiction.document_id)
            .all()
        )
    else:
        contradiction_counts = {}

    for doc in recent_docs:
        recent_activity.append({
            "document_name": doc.name,
            "status": doc.status,
            "contradictions_found": contradiction_counts.get(doc.id, 0),
            "date": str(doc.analysis_end_time or doc.upload_date),
            "activity_type": "single",
        })

    # Recent comparison sessions
    recent_comparisons = (
        db.query(ComparisonSession)
        .filter(
            ComparisonSession.user_id == user_id,
            ComparisonSession.status.in_(["completed", "failed"]),
        )
        .order_by(ComparisonSession.completed_at.desc())
        .limit(5)
        .all()
    )

    # Batch query cross-contradiction counts and doc names for comparisons (avoids N+1)
    recent_comp_ids = [s.id for s in recent_comparisons]
    if recent_comp_ids:
        cross_counts = dict(
            db.query(CrossContradiction.comparison_id, func.count(CrossContradiction.id))
            .filter(CrossContradiction.comparison_id.in_(recent_comp_ids))
            .group_by(CrossContradiction.comparison_id)
            .all()
        )
    else:
        cross_counts = {}

    # Collect all doc IDs referenced by comparison sessions for batch name lookup
    all_comp_doc_ids = set()
    for session in recent_comparisons:
        doc_ids = json.loads(session.document_ids) if session.document_ids else []
        all_comp_doc_ids.update(doc_ids)
    if all_comp_doc_ids:
        doc_name_rows = db.query(Document.id, Document.name).filter(Document.id.in_(all_comp_doc_ids)).all()
        doc_name_map = {d_id: d_name for d_id, d_name in doc_name_rows}
    else:
        doc_name_map = {}

    for session in recent_comparisons:
        doc_ids = json.loads(session.document_ids) if session.document_ids else []
        doc_names = [doc_name_map.get(did, "Unknown") for did in doc_ids]

        display_name = " vs ".join(doc_names[:2])
        if len(doc_names) > 2:
            display_name += f" (+{len(doc_names) - 2} more)"

        recent_activity.append({
            "document_name": display_name or "Multi-doc comparison",
            "status": session.status,
            "contradictions_found": cross_counts.get(session.id, 0),
            "date": str(session.completed_at or session.created_at),
            "activity_type": "comparison",
        })

    # Sort all recent activity by date descending, take top 5
    recent_activity.sort(key=lambda x: x["date"], reverse=True)
    recent_activity = recent_activity[:5]

    return {
        "total_documents": total_docs,
        "documents_analyzed": docs_completed,
        "documents_pending": docs_pending,
        "documents_failed": docs_failed,
        "total_contradictions": total_contradictions,
        "total_clauses": total_clauses,
        "contradictions_by_severity": severity_counts,
        "contradictions_by_type": type_counts,
        "avg_analysis_duration": avg_duration,
        "recent_activity": recent_activity,
        "total_comparisons": total_comparisons,
        "comparisons_completed": comparisons_completed,
        "cross_doc_contradictions": cross_total,
        "single_doc_contradictions": single_total,
    }
