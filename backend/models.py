from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    organization_id = Column(String, ForeignKey("organizations.id"))
    role = Column(String, default="user")  # user, admin, compliance_officer
    
    organization = relationship("Organization", back_populates="users")
    documents = relationship("Document", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSON, default={})
    
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    compliance_rules = relationship("ComplianceRule", back_populates="organization")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    content_type = Column(String)
    size = Column(Integer)
    s3_key = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, ForeignKey("users.id"))
    organization_id = Column(String, ForeignKey("organizations.id"))
    status = Column(String, default="pending")  # pending, processing, completed, failed
    document_metadata = Column(JSON, default={})
    
    user = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    compliance_checks = relationship("ComplianceCheck", back_populates="document")
    versions = relationship("DocumentVersion", back_populates="document")
    audit_logs = relationship("AuditLog", back_populates="document")

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"))
    version_number = Column(Integer)
    s3_key = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    changes = Column(Text)
    
    document = relationship("Document", back_populates="versions")
    creator = relationship("User")

class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"))
    status = Column(String)  # pending, processing, completed, failed
    violations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    checked_by = Column(String, ForeignKey("users.id"))
    
    document = relationship("Document", back_populates="compliance_checks")
    checker = relationship("User")

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"))
    name = Column(String)
    description = Column(Text)
    pattern = Column(String)
    severity = Column(String)  # low, medium, high
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    organization = relationship("Organization", back_populates="compliance_rules")
    creator = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    document_id = Column(String, ForeignKey("documents.id"))
    action = Column(String)  # upload, download, check, approve, reject
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    
    user = relationship("User", back_populates="audit_logs")
    document = relationship("Document", back_populates="audit_logs") 