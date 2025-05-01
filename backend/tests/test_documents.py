import pytest
from fastapi.testclient import TestClient
from models import Document, User, Organization
import io

def test_upload_document(client: TestClient, test_db):
    # Create test user and organization
    org = Organization(name="Test Org")
    test_db.add(org)
    test_db.commit()
    
    user = User(
        email="test@example.com",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()
    
    # Create test file
    file_content = b"Test document content"
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/documents/upload",
        files={"file": ("test.txt", file, "text/plain")},
        headers={"Authorization": f"Bearer {get_test_token(user)}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["content_type"] == "text/plain"
    assert "id" in data
    
    # Check database
    document = test_db.query(Document).filter(Document.id == data["id"]).first()
    assert document is not None
    assert document.user_id == user.id
    assert document.organization_id == org.id

def test_get_document_list(client: TestClient, test_db):
    # Create test user and organization
    org = Organization(name="Test Org")
    test_db.add(org)
    test_db.commit()
    
    user = User(
        email="test@example.com",
        organization_id=org.id
    )
    test_db.add(user)
    test_db.commit()
    
    # Create test documents
    doc1 = Document(
        filename="test1.txt",
        content_type="text/plain",
        size=100,
        user_id=user.id,
        organization_id=org.id
    )
    doc2 = Document(
        filename="test2.txt",
        content_type="text/plain",
        size=200,
        user_id=user.id,
        organization_id=org.id
    )
    test_db.add(doc1)
    test_db.add(doc2)
    test_db.commit()
    
    response = client.get(
        "/documents",
        headers={"Authorization": f"Bearer {get_test_token(user)}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["filename"] == "test1.txt"
    assert data[1]["filename"] == "test2.txt"

def get_test_token(user: User) -> str:
    # Helper function to generate test JWT token
    from datetime import datetime, timedelta
    from jose import jwt
    from security import SECRET_KEY, ALGORITHM
    
    access_token_expires = timedelta(minutes=30)
    expire = datetime.utcnow() + access_token_expires
    to_encode = {
        "sub": user.email,
        "exp": expire,
        "user_id": user.id,
        "organization_id": user.organization_id
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) 