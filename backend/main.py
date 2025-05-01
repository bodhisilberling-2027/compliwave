from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import boto3
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
import uvicorn

from .database import get_db, engine, Base
from .models import User, Organization, Document
from .auth import get_current_user, get_current_organization
from .services.document_processor import DocumentProcessor
from .services.compliance_checker import ComplianceChecker
from .security import (
    rate_limit,
    sanitize_filename,
    validate_file_type,
    validate_file_size,
    security_headers
)
from .services.document_manager import DocumentManager
from .middleware import setup_middleware
from .logging_config import logger

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Compliwave API",
    description="API for document compliance checking and analysis",
    version="1.0.0"
)

# Set up middleware
@app.on_event("startup")
async def startup_event():
    await setup_middleware(app)
    logger.info("Application startup complete")

# Models for request/response
class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    size: int

class ComplianceCheckRequest(BaseModel):
    document_id: str
    rules: List[str]

class ComplianceResult(BaseModel):
    document_id: str
    violations: List[Dict]
    status: str
    timestamp: datetime

# Initialize services
document_processor = DocumentProcessor()
compliance_checker = ComplianceChecker()

# AWS S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    rate_limit(request)
    response = await call_next(request)
    return response

# Routes
@app.get("/")
async def root():
    return security_headers({"message": "Welcome to Compliwave API"})

@app.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate file
        if not validate_file_type(file.content_type):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF, DOCX, and PPTX files are allowed."
            )
        
        # Read file content
        content = await file.read()
        
        if not validate_file_size(len(content)):
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 10MB."
            )
        
        # Create document manager instance
        document_manager = DocumentManager()
        
        # Upload document
        document = await document_manager.upload_document(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            user=current_user,
            db=db
        )
        
        # Start compliance check in background
        background_tasks.add_task(
            process_document,
            document.id,
            content,
            file.content_type,
            db
        )
        
        return security_headers({
            "message": "File uploaded successfully",
            "file_id": document.id,
            "filename": document.filename
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_document(file_id: str, content: bytes, content_type: str, db: Session):
    """Process document and check compliance in the background."""
    try:
        # Extract text
        text = document_processor.extract_text(content, content_type)
        
        # Check compliance
        result = await compliance_checker.check_compliance(file_id, text)
        
        # Update document status
        document = db.query(Document).filter(Document.id == file_id).first()
        if document:
            document.status = "processed"
            db.commit()
        
        # Store compliance check result
        compliance_check = ComplianceCheck(
            document_id=file_id,
            status="completed",
            violations=result["violations"]
        )
        db.add(compliance_check)
        db.commit()
        
    except Exception as e:
        print(f"Error processing document {file_id}: {str(e)}")
        # Update document status to failed
        document = db.query(Document).filter(Document.id == file_id).first()
        if document:
            document.status = "failed"
            db.commit()

@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document from S3."""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if user has access to the document
        if document.user_id != current_user.id and document.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get file from S3
        response = s3_client.get_object(
            Bucket=os.getenv('AWS_S3_BUCKET'),
            Key=document.s3_key
        )
        
        return FileResponse(
            response['Body'],
            media_type=document.content_type,
            filename=document.filename,
            headers=security_headers({})["headers"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{document_id}")
async def get_results(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get compliance check results."""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if user has access to the document
        if document.user_id != current_user.id and document.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        compliance_check = db.query(ComplianceCheck).filter(
            ComplianceCheck.document_id == document_id
        ).first()
        
        if not compliance_check:
            return security_headers({
                "document_id": document_id,
                "status": "pending",
                "violations": [],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return security_headers({
            "document_id": document_id,
            "status": compliance_check.status,
            "violations": compliance_check.violations,
            "timestamp": compliance_check.created_at.isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/organizations")
async def get_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's organizations."""
    try:
        organizations = db.query(Organization).filter(
            Organization.id == current_user.organization_id
        ).all()
        
        return security_headers([{"id": org.id, "name": org.name} for org in organizations])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organizations")
async def create_organization(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new organization."""
    try:
        organization = Organization(name=name)
        db.add(organization)
        db.commit()
        
        # Update user's organization
        current_user.organization_id = organization.id
        db.commit()
        
        return security_headers({"id": organization.id, "name": organization.name})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 