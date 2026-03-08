"""
Clause SQLAlchemy ORM model.

Represents an atomic clause extracted from a document.
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship

from db.base import Base
from config import settings

# ── Conditional column types: PostgreSQL-specific or fallback ──
_is_postgres = settings.DATABASE_URL.startswith("postgresql")

if _is_postgres:
    from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        Vector = None
    _search_vector_type = TSVECTOR
    _embedding_type = Vector(384) if Vector else Text
    _entities_type = JSONB
else:
    _search_vector_type = Text  # unused on SQLite, but column still exists
    _embedding_type = Text      # store JSON-serialised list on SQLite
    _entities_type = JSON       # SQLAlchemy generic JSON


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String, primary_key=True)  # UUID
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    text = Column(Text, nullable=False)
    section = Column(String, nullable=True)  # section heading
    position = Column(Integer, nullable=False)  # order in document (0-indexed)

    # Full-text search (PostgreSQL: TSVECTOR, SQLite: plain Text placeholder)
    search_vector = Column(_search_vector_type, nullable=True)

    # Semantic embeddings (pgvector 384-d on PG, JSON text on SQLite)
    embedding = Column(_embedding_type, nullable=True)

    # Named entities extracted via spaCy NER (cached per clause)
    entities = Column(_entities_type, nullable=True, default=None)

    # Relationships
    document = relationship("Document", back_populates="clauses")

    # Indexes — GIN index only on PostgreSQL
    __table_args__ = (
        Index('ix_clauses_document_id', 'document_id'),
        *((
            Index('ix_clauses_search_vector', 'search_vector', postgresql_using='gin'),
        ) if _is_postgres else ()),
    )
