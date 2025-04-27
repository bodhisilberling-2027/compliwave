from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time
import os
from dotenv import load_dotenv

load_dotenv()

# Security settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate limiting settings
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100

# Store for rate limiting
request_counts: Dict[str, tuple[int, float]] = {}

# File validation settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
]

# Security headers
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}

def rate_limit(request: Request):
    """Rate limiting middleware."""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean up old entries
    for ip in list(request_counts.keys()):
        count, timestamp = request_counts[ip]
        if current_time - timestamp > RATE_LIMIT_WINDOW:
            del request_counts[ip]
    
    # Check rate limit
    if client_ip in request_counts:
        count, timestamp = request_counts[client_ip]
        if count >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        request_counts[client_ip] = (count + 1, timestamp)
    else:
        request_counts[client_ip] = (1, current_time)

def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Remove any directory components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric characters except for ._- 
    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
    return filename

def validate_file_type(content_type: str) -> bool:
    """Validate file type to prevent malicious uploads."""
    return content_type in ALLOWED_FILE_TYPES

def validate_file_size(size: int) -> bool:
    """Validate file size to prevent large file uploads."""
    return size <= MAX_FILE_SIZE

def security_headers(response: dict) -> dict:
    """Add security headers to response."""
    return {**response, "headers": SECURITY_HEADERS} 