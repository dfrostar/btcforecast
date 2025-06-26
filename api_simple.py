#!/usr/bin/env python3
"""
Production-ready simplified API for BTC Forecast application
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, UTC
import time
from contextlib import asynccontextmanager

# Import production-ready modules
from logging_config import setup_logging, get_correlation_id, log_request, log_error, log_security_event
from error_handling import ErrorHandler, external_api_circuit_breaker, api_retry_handler
from health_checks import get_health_status, get_simple_health_status

# Import authentication modules
from api.auth import (
    User, UserCreate, UserLogin, Token, get_current_user, 
    authenticate_user, create_user, hash_password
)
from api.database import UserRepository

# Setup structured logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI."""
    # Startup
    logger.info("Starting BTC Forecast API - Production Ready")
    create_default_users()
    logger.info("Application startup complete")
    yield
    # Shutdown
    logger.info("Shutting down BTC Forecast API")

# Create FastAPI app
app = FastAPI(
    title="BTC Forecast API - Production Ready",
    description="Production-ready Bitcoin forecasting API with comprehensive monitoring and security",
    version="2.0.0",
    lifespan=lifespan
)

# Parse CORS origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins != "*":
    try:
        # Try to parse as JSON array first
        cors_origins = json.loads(cors_origins)
    except json.JSONDecodeError:
        # Fall back to comma-separated string
        cors_origins = [origin.strip() for origin in cors_origins.split(",")]

# Add CORS middleware with production-ready configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Requested-With"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Request/Response middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses with correlation IDs."""
    correlation_id = get_correlation_id()
    start_time = time.time()
    
    # Add correlation ID to request state
    request.state.correlation_id = correlation_id
    
    # Log request
    log_request(
        logger=logger,
        correlation_id=correlation_id,
        method=request.method,
        endpoint=str(request.url.path),
        ip_address=request.client.host if request.client else None
    )
    
    try:
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # Log response
        log_request(
            logger=logger,
            correlation_id=correlation_id,
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            response_time=response_time
        )
        
        return response
    except Exception as e:
        response_time = time.time() - start_time
        
        # Log error
        log_error(
            logger=logger,
            correlation_id=correlation_id,
            error=e,
            context={
                "method": request.method,
                "endpoint": str(request.url.path),
                "response_time": response_time
            }
        )
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content=ErrorHandler.handle_api_error(e, {
                "correlation_id": correlation_id,
                "endpoint": str(request.url.path)
            })
        )

# Health check endpoints
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return await get_simple_health_status()

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check endpoint."""
    return await get_health_status()

# Authentication endpoints with enhanced security
@app.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Register a new user with enhanced security."""
    correlation_id = get_correlation_id()
    
    try:
        logger.info(f"Registration attempt for user: {user_data.username}")
        
        # Check if user already exists
        existing_user = UserRepository.get_user_by_username(user_data.username)
        if existing_user:
            log_security_event(
                logger=logger,
                correlation_id=correlation_id,
                event_type="registration_duplicate",
                details={"username": user_data.username}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create user with enhanced password security
        hashed_password = hash_password(user_data.password)
        user = UserRepository.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role
        )
        
        logger.info(f"User {user_data.username} registered successfully")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger=logger,
            correlation_id=correlation_id,
            error=e,
            context={"username": user_data.username, "operation": "registration"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Login user and return JWT tokens with enhanced security."""
    correlation_id = get_correlation_id()
    
    try:
        logger.info(f"Login attempt for user: {user_credentials.username}")
        
        # Get user from database
        user_data = UserRepository.get_user_by_username(user_credentials.username)
        if not user_data:
            log_security_event(
                logger=logger,
                correlation_id=correlation_id,
                event_type="login_failed",
                details={"username": user_credentials.username, "reason": "user_not_found"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password with enhanced security
        from api.auth import verify_password
        if not verify_password(user_credentials.password, user_data["hashed_password"]):
            log_security_event(
                logger=logger,
                correlation_id=correlation_id,
                event_type="login_failed",
                details={"username": user_credentials.username, "reason": "invalid_password"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login
        UserRepository.update_last_login(user_credentials.username)
        
        # Create tokens
        from api.auth import create_access_token, create_refresh_token
        access_token = create_access_token(data={"sub": user_data["username"], "role": user_data["role"]})
        refresh_token = create_refresh_token(data={"sub": user_data["username"], "role": user_data["role"]})
        
        logger.info(f"User {user_credentials.username} logged in successfully")
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger=logger,
            correlation_id=correlation_id,
            error=e,
            context={"username": user_credentials.username, "operation": "login"}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# Protected endpoints
@app.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@app.get("/users/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get detailed user profile."""
    try:
        user_data = UserRepository.get_user_by_username(current_user.username)
        return {
            "username": user_data["username"],
            "email": user_data["email"],
            "role": user_data["role"],
            "is_active": user_data["is_active"],
            "created_at": user_data["created_at"],
            "last_login": user_data["last_login"]
        }
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

# System status endpoint
@app.get("/status")
async def system_status():
    """Get system status and metrics."""
    try:
        import psutil
        
        return {
            "status": "operational",
            "timestamp": datetime.now(UTC).isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "database": {
                "status": "connected",
                "user_count": UserRepository.get_user_count()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e)
        }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "BTC Forecast API - Production Ready",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.now(UTC).isoformat(),
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "status": "/status",
            "auth": {
                "register": "/auth/register",
                "login": "/auth/login"
            },
            "user": {
                "profile": "/users/profile",
                "me": "/users/me"
            }
        }
    }

# Create default users on startup
def create_default_users():
    """Create default users for testing if enabled."""
    create_defaults = os.getenv("CREATE_DEFAULT_USERS", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "production").lower()
    
    if not create_defaults and environment == "production":
        logger.info("Default user creation disabled in production")
        return
        
    try:
        # Create admin user if not exists
        if not UserRepository.get_user_by_username("admin"):
            hashed_password = hash_password("admin123")
            UserRepository.create_user(
                username="admin",
                email="admin@btcforecast.com",
                hashed_password=hashed_password,
                role="admin"
            )
            logger.info("Created default admin user: admin")
        
        # Create demo user if not exists
        if not UserRepository.get_user_by_username("demo"):
            hashed_password = hash_password("demo123")
            UserRepository.create_user(
                username="demo",
                email="demo@btcforecast.com",
                hashed_password=hashed_password,
                role="premium"
            )
            logger.info("Created demo user: demo")
            
    except Exception as e:
        logger.error(f"Failed to create default users: {e}")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable (Render.com sets PORT)
    port = int(os.getenv("PORT", 8001))
    
    uvicorn.run(
        app,
        host="0.0.0.0",  # Changed from 127.0.0.1 for production
        port=port,
        log_level="info"
    ) 