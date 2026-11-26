from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.schemas.auth import UserCreate


# Bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with safe defaults."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary to encode in the token
        expires_delta: Optional expiration time delta
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return its payload.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user with hashed password.
    
    Args:
        db: Database session
        user_data: User creation data
    
    Returns:
        Created user
    
    Raises:
        ValueError: If username already exists
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise ValueError(f"Username '{user_data.username}' already exists")
    
    # Create new user with hashed password
    hashed_pwd = hash_password(user_data.password)
    user = User(username=user_data.username, hashed_password=hashed_pwd)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username
        password: Plain text password
    
    Returns:
        User if authenticated, None otherwise
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user
