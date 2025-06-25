"""
Authentication and Authorization Module
Provides JWT token authentication, user management, and role-based access control.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import secrets
import string
import os
from config import get_config

# Security configuration
SECRET_KEY = get_config().jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# In-memory user storage (replace with database in production)
users_db = {}
api_keys_db = {}

# Security scheme
security = HTTPBearer()

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "free"

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    email: EmailStr
    role: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

def generate_api_key() -> str:
    """Generate a secure API key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        token_type: str = payload.get("type")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(username=username, role=role)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get the current authenticated user."""
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data.username not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = users_db[token_data.username]
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return User(**user)

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(required_role: str):
    """Decorator to require specific role for endpoint access."""
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker

def require_premium():
    """Decorator to require premium role for endpoint access."""
    return require_role("premium")

def require_admin():
    """Decorator to require admin role for endpoint access."""
    return require_role("admin")

def verify_api_key(api_key: str) -> Optional[User]:
    """Verify an API key and return the associated user."""
    if api_key not in api_keys_db:
        return None
    
    username = api_keys_db[api_key]
    if username not in users_db:
        return None
    
    user_data = users_db[username]
    if not user_data["is_active"]:
        return None
    
    return User(**user_data)

# User management functions
def create_user(username: str, email: str, password: str, role: str = "free") -> User:
    """Create a new user."""
    if username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = hash_password(password)
    user_data = {
        "username": username,
        "email": email,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None,
        "hashed_password": hashed_password
    }
    
    users_db[username] = user_data
    return User(**user_data)

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    if username not in users_db:
        return None
    
    user_data = users_db[username]
    if not verify_password(password, user_data.get("hashed_password", "")):
        return None
    
    # Update last login
    user_data["last_login"] = datetime.utcnow()
    users_db[username] = user_data
    
    return User(**user_data)

def generate_user_api_key(username: str) -> str:
    """Generate an API key for a user."""
    if username not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    api_key = generate_api_key()
    api_keys_db[api_key] = username
    return api_key

def revoke_user_api_key(api_key: str) -> bool:
    """Revoke a user's API key."""
    if api_key in api_keys_db:
        del api_keys_db[api_key]
        return True
    return False

# Initialize default admin user
def initialize_default_users():
    """Initialize default users for development."""
    if "admin" not in users_db:
        admin_user = create_user(
            username="admin",
            email="admin@btcforecast.com",
            password="admin123",  # Change in production
            role="admin"
        )
        print(f"Created default admin user: {admin_user.username}")
    
    if "demo" not in users_db:
        demo_user = create_user(
            username="demo",
            email="demo@btcforecast.com",
            password="demo123",  # Change in production
            role="premium"
        )
        print(f"Created demo user: {demo_user.username}")

# Call initialization
initialize_default_users() 