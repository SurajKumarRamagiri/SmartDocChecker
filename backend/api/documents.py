"""
Document management API routes.
"""
import re
import uuid
import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, selectinload

from schemas.document_schema import DocumentOut, DocumentUploadResponse
from dependencies import get_current_user, get_db, limiter
from models.user import User
from models.document import Document
from services import supabase_storage
from constants import SUPPORTED_FILE_TYPES, MAX_FILE_SIZE_MB
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── Validate file extension ──
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(SUPPORTED_FILE_TYPES)}",
        )

    user_id = current_user["user_id"]

    doc_id = str(uuid.uuid4())

    # ── Pre-check file size via UploadFile.size (avoids reading huge files) ──
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE_MB} MB",
        )

    # ── Upload file to Supabase Storage ──
    file_bytes = await file.read()

    # ── Validate file size ──
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(file_bytes) / (1024*1024):.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB",
        )
    # Sanitize filename: strip path traversal, keep only safe characters
    safe_name = os.path.basename(file.filename or "upload")
    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)  # allow alphanumeric, dot, hyphen, underscore
    if not safe_name or safe_name.startswith('.'):
        safe_name = f"upload_{doc_id}{file_ext}"

    storage_path = f"user_{user_id}/{doc_id}/{safe_name}"
    content_type = file.content_type or "application/octet-stream"

    try:
        supabase_storage.upload_file(file_bytes, storage_path, content_type)
    except Exception as e:
        logger.error(f"Failed to upload to Supabase Storage: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")

    # ── Save metadata to DB ──
    doc = Document(
        id=doc_id,
        name=safe_name,
        file_path=storage_path,
        status="pending",
        upload_date=datetime.now(timezone.utc),
        user_id=user_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info(f"Document uploaded: {doc.name} (id={doc.id})")

    return DocumentUploadResponse(
        id=doc.id,
        name=doc.name,
        status=doc.status,
        upload_date=str(doc.upload_date),
        contradictions=[],
    )


@router.get("/", response_model=list[DocumentOut])
async def list_documents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max documents to return"),
):
    user_id = current_user["user_id"]

    docs = (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .options(selectinload(Document.contradictions))
        .order_by(Document.upload_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        DocumentOut(
            id=doc.id,
            name=doc.name,
            status=doc.status,
            upload_date=str(doc.upload_date),
            contradictions=[c.id for c in doc.contradictions],
        )
        for doc in docs
    ]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get metadata for a single document."""
    user_id = current_user["user_id"]

    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == user_id
    ).options(selectinload(Document.contradictions)).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentOut(
        id=doc.id,
        name=doc.name,
        status=doc.status,
        upload_date=str(doc.upload_date),
        processing_stage=doc.processing_stage,
        progress_percent=doc.progress_percent or 0,
        contradictions=[c.id for c in doc.contradictions],
    )


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a signed download URL for a document."""
    user_id = current_user["user_id"]

    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == user_id
    ).first()
    if not doc or not doc.file_path:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        signed_url = supabase_storage.get_signed_url(doc.file_path)
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        raise HTTPException(status_code=500, detail="Could not generate download link")

    return {"download_url": signed_url, "filename": doc.name}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document (DB record + Supabase Storage file)."""
    from models.cross_contradiction import CrossContradiction
    from models.contradiction import Contradiction
    from models.clause import Clause

    user_id = current_user["user_id"]

    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == user_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_name = doc.name
    file_path = doc.file_path

    try:
        # 1. Collect clause IDs for this document
        clause_ids = [
            row[0]
            for row in db.query(Clause.id).filter(Clause.document_id == doc_id).all()
        ]

        # 2. Delete cross_contradictions that reference these clauses or this document
        if clause_ids:
            db.query(CrossContradiction).filter(
                (CrossContradiction.clause_a_id.in_(clause_ids))
                | (CrossContradiction.clause_b_id.in_(clause_ids))
            ).delete(synchronize_session="fetch")

        db.query(CrossContradiction).filter(
            (CrossContradiction.document_a_id == doc_id)
            | (CrossContradiction.document_b_id == doc_id)
        ).delete(synchronize_session="fetch")

        # 3. Delete contradictions (must go before clauses because of clause FK)
        db.query(Contradiction).filter(
            Contradiction.document_id == doc_id
        ).delete(synchronize_session="fetch")

        # 4. Delete clauses
        db.query(Clause).filter(
            Clause.document_id == doc_id
        ).delete(synchronize_session="fetch")

        # 5. Expire the cached doc object so SQLAlchemy doesn't try to
        #    cascade-delete already-removed children
        db.expire(doc)

        # 6. Delete the document row itself
        db.delete(doc)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete document {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")

    # 7. Remove from Supabase Storage (after DB commit so a storage error
    #    doesn't leave orphaned DB rows)
    if file_path:
        try:
            supabase_storage.delete_file(file_path)
        except Exception as e:
            logger.warning(f"Could not delete from storage: {e}")

    logger.info(f"Document deleted: id={doc_id} by user_id={current_user['user_id']}")
    return {"detail": "Document deleted"}
