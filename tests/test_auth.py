import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User
from app.services.auth import hash_password
from main import app


client = TestClient(app)


@pytest.fixture
def cleanup_users(db: Session):
    """Clean up users table after each test."""
    yield
    db.query(User).delete()
    db.commit()


class TestRegister:
    def test_register_success(self, db: Session, cleanup_users):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={"username": "testuser", "password": "securepassword123"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "testuser"
        assert data["is_active"] is True
        assert "id" in data
        assert "password" not in data  # Password never returned
        
    def test_register_username_too_short(self):
        """Test registration with username too short."""
        response = client.post(
            "/auth/register",
            json={"username": "ab", "password": "securepassword123"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
    def test_register_password_too_short(self):
        """Test registration with password too short."""
        response = client.post(
            "/auth/register",
            json={"username": "testuser", "password": "short"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
    def test_register_duplicate_username(self, db: Session):
        """Test registration with duplicate username."""
        # Create first user
        user = User(username="testuser", hashed_password=hash_password("password123"))
        db.add(user)
        db.commit()
        
        # Try to create duplicate
        response = client.post(
            "/auth/register",
            json={"username": "testuser", "password": "securepassword123"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]


class TestLogin:
    def test_login_success(self, db: Session, cleanup_users):
        """Test successful login."""
        # Register user
        client.post(
            "/auth/register",
            json={"username": "testuser", "password": "securepassword123"},
        )
        
        # Login
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "securepassword123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        
    def test_login_invalid_username(self):
        """Test login with invalid username."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid credentials"
        
    def test_login_invalid_password(self, db: Session):
        """Test login with invalid password."""
        # Register user
        user = User(username="testuser", hashed_password=hash_password("correctpassword"))
        db.add(user)
        db.commit()
        
        # Try login with wrong password
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid credentials"
        
    def test_login_inactive_user(self, db: Session):
        """Test login with inactive user."""
        # Create inactive user
        user = User(
            username="testuser",
            hashed_password=hash_password("password123"),
            is_active=False,
        )
        db.add(user)
        db.commit()
        
        # Try login
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUser:
    def test_get_current_user_success(self, db: Session, cleanup_users):
        """Test getting current user info."""
        # Register and login
        register_resp = client.post(
            "/auth/register",
            json={"username": "testuser", "password": "securepassword123"},
        )
        user_id = register_resp.json()["id"]
        
        login_resp = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "securepassword123"},
        )
        token = login_resp.json()["access_token"]
        
        # Get current user
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == "testuser"
        assert "password" not in data
        
    def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        response = client.get("/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
