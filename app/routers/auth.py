from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_username,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Register a new user.
    
    **Security:**
    - Password is hashed with bcrypt before storage
    - Username must be unique
    - Minimum password length: 8 characters
    """
    try:
        user = create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Login and get a JWT access token.
    
    **Security:**
    - Returns 401 for invalid credentials (no user/password hints)
    - Token expires in 30 minutes (configurable)
    - Password is verified against bcrypt hash
    - Only active users can login
    """
    user = authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        # Don't reveal if username exists or password is wrong
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,  # in seconds
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get information about the current authenticated user."""
    return current_user
