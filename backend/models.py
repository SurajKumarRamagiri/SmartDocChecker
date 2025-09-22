from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime)

class Document(Base):
    __tablename__ = 'documents'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    upload_date = Column(DateTime)
    user_id = Column(Integer, ForeignKey('users.id'))
    contradictions = relationship('Contradiction', back_populates='document')

class Contradiction(Base):
    __tablename__ = 'contradictions'
    id = Column(String, primary_key=True)
    type = Column(String)
    description = Column(String)
    confidence = Column(Float)
    document_id = Column(String, ForeignKey('documents.id'))
    document = relationship('Document', back_populates='contradictions')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String)
    timestamp = Column(DateTime)
