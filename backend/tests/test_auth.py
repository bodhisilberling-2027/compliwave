from fastapi.testclient import TestClient
import pytest
from models import User

def test_register_user(client: TestClient, test_db):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "organization_name": "Test Org"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    
    # Check database
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert user.organization.name == "Test Org"

def test_login_user(client: TestClient, test_db):
    # First register a user
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "organization_name": "Test Org"
        }
    )
    
    # Try logging in
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401 