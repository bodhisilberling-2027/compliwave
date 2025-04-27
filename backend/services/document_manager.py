from typing import List, Dict, Any, Optional
import boto3
import os
from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from ..models import Document, DocumentVersion, AuditLog, User
from .document_processor import DocumentProcessor
import io

class DocumentManager:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('AWS_S3_BUCKET')
        if not self.bucket_name:
            raise ValueError("AWS_S3_BUCKET environment variable is not set")
        self.document_processor = DocumentProcessor()

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user: User,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Upload a new document and create version."""
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Upload to S3
            s3_key = f"uploads/{file_id}/{filename}"
            self.s3_client.upload_fileobj(
                file_content,
                self.bucket_name,
                s3_key
            )
            
            # Create document record
            document = Document(
                id=file_id,
                filename=filename,
                content_type=content_type,
                size=len(file_content),
                s3_key=s3_key,
                user_id=user.id,
                organization_id=user.organization_id,
                metadata=metadata or {}
            )
            db.add(document)
            db.commit()
            
            # Create initial version
            version = DocumentVersion(
                document_id=file_id,
                version_number=1,
                s3_key=s3_key,
                created_by=user.id,
                changes="Initial version"
            )
            db.add(version)
            
            # Create audit log
            audit_log = AuditLog(
                user_id=user.id,
                document_id=file_id,
                action="upload",
                details={
                    "filename": filename,
                    "size": len(file_content),
                    "content_type": content_type
                }
            )
            db.add(audit_log)
            
            db.commit()
            return document
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload document: {str(e)}"
            )

    async def create_version(
        self,
        document_id: str,
        file_content: bytes,
        filename: str,
        user: User,
        db: Session,
        changes: str
    ) -> DocumentVersion:
        """Create a new version of an existing document."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Get next version number
        latest_version = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Upload to S3
        s3_key = f"uploads/{document_id}/v{version_number}/{filename}"
        self.s3_client.upload_fileobj(
            file_content,
            self.bucket_name,
            s3_key
        )
        
        # Create version record
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            s3_key=s3_key,
            created_by=user.id,
            changes=changes
        )
        db.add(version)
        
        # Update document
        document.updated_at = datetime.utcnow()
        document.s3_key = s3_key
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user.id,
            document_id=document_id,
            action="version",
            details={
                "version": version_number,
                "changes": changes
            }
        )
        db.add(audit_log)
        
        db.commit()
        return version

    async def get_document(
        self,
        document_id: str,
        user: User,
        db: Session,
        version: Optional[int] = None
    ) -> bytes:
        """Get document content from S3."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Check access permissions
        if document.user_id != user.id and document.organization_id != user.organization_id:
            raise ValueError("Access denied")
        
        # Get specific version if requested
        if version:
            version_record = db.query(DocumentVersion).filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == version
            ).first()
            if not version_record:
                raise ValueError("Version not found")
            s3_key = version_record.s3_key
        else:
            s3_key = document.s3_key
        
        # Get from S3
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user.id,
            document_id=document_id,
            action="download",
            details={
                "version": version,
                "filename": document.filename
            }
        )
        db.add(audit_log)
        db.commit()
        
        return response['Body'].read()

    async def list_versions(
        self,
        document_id: str,
        user: User,
        db: Session
    ) -> List[Dict[str, Any]]:
        """List all versions of a document."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Check access permissions
        if document.user_id != user.id and document.organization_id != user.organization_id:
            raise ValueError("Access denied")
        
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).all()
        
        return [
            {
                "version": v.version_number,
                "created_at": v.created_at,
                "created_by": v.creator.email,
                "changes": v.changes
            }
            for v in versions
        ]

    async def delete_document(
        self,
        document_id: str,
        user: User,
        db: Session
    ) -> None:
        """Delete a document and all its versions."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")
        
        # Check access permissions
        if document.user_id != user.id and document.organization_id != user.organization_id:
            raise ValueError("Access denied")
        
        # Delete from S3
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).all()
        
        for version in versions:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=version.s3_key
            )
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user.id,
            document_id=document_id,
            action="delete",
            details={
                "filename": document.filename
            }
        )
        db.add(audit_log)
        
        # Delete from database
        db.delete(document)
        db.commit() 