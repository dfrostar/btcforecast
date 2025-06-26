#!/usr/bin/env python3
"""
Enhanced BTC Forecast API with Background Processing, Advanced Monitoring, Security, and Multi-Region Support
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, status, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
import json
import asyncio

# Import production-ready modules
from logging_config import setup_logging, get_correlation_id, log_request, log_error, log_security_event
from error_handling import ErrorHandler, external_api_circuit_breaker, api_retry_handler
from health_checks import get_health_status, get_simple_health_status

# Import authentication and security modules
from api.auth import (
    User, UserCreate, UserLogin, Token, get_current_user, 
    authenticate_user, create_user, hash_password
)
from api.database import UserRepository

# Import new modules
from celery_app import celery_app
from monitoring.advanced_monitoring import (
    AdvancedMonitoring, instrument_fastapi, get_monitoring_instance,
    monitor_celery_task, monitor_model_prediction
)
from security.advanced_security import (
    AdvancedSecurity, get_current_api_key, get_current_oauth_user,
    require_permission, get_security_system
)

# Import background tasks
from tasks.model_training import retrain_model, optimize_model_hyperparameters, evaluate_model_performance
from tasks.data_processing import update_bitcoin_data, validate_data_quality, backfill_missing_data
from tasks.notifications import send_price_alert, send_system_alert, send_daily_report
from tasks.analytics import generate_daily_report, backtest_strategy, generate_market_insights
from tasks.maintenance import system_health_check, cleanup_old_data, backup_database

# Import configuration
from config import get_settings

# Setup structured logging
logger = setup_logging()

# Get settings
settings = get_settings()

# Initialize monitoring and security
monitoring = get_monitoring_instance()
security_system = get_security_system()

# Create FastAPI app
app = FastAPI(
    title="BTC Forecast API - Enhanced Production Ready",
    description="Advanced Bitcoin forecasting API with background processing, monitoring, security, and multi-region support",
    version="3.0.0"
)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Request/Response middleware for logging and monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses with correlation IDs and monitoring."""
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
        
        # Record API metrics
        monitoring.record_api_request(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            duration=response_time
        )
        
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

# Pydantic models for new endpoints
class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str]
    expires_in_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    key_id: str
    api_key: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]

class PriceAlertCreate(BaseModel):
    alert_type: str  # "above", "below", "change"
    price_threshold: float
    notification_method: str = "email"  # "email", "sms", "push"

class BackgroundTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_completion: Optional[datetime]

class SystemMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    request_rate: float
    error_rate: float

# Health check endpoints
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return await get_simple_health_status()

@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check endpoint."""
    return await get_health_status()

@app.get("/health/advanced")
async def advanced_health_check():
    """Advanced health check with monitoring metrics."""
    try:
        # Get basic health status
        basic_health = await get_health_status()
        
        # Get monitoring metrics
        monitoring_metrics = monitoring.get_metrics_summary()
        
        # Get system metrics
        system_metrics = await get_system_metrics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "basic_health": basic_health,
            "monitoring_metrics": monitoring_metrics,
            "system_metrics": system_metrics
        }
    except Exception as e:
        logger.error(f"Advanced health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )

# Authentication endpoints with enhanced security
@app.post("/auth/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Register a new user with enhanced security."""
    correlation_id = get_correlation_id()
    
    try:
        logger.info(f"Registration attempt for user: {user_data.username}")
        
        # Validate password strength
        password_strength = security_system.validate_password_strength(user_data.password)
        if not password_strength["is_acceptable"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password too weak: {', '.join(password_strength['feedback'])}"
            )
        
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
        
        # Send welcome email
        send_welcome_email.delay(user["id"])
        
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
        
        # Create access token
        from api.auth import create_access_token
        access_token = create_access_token(
            data={"sub": user_data["username"], "role": user_data["role"]}
        )
        
        # Update last login
        UserRepository.update_last_login(user_data["id"])
        
        logger.info(f"User {user_credentials.username} logged in successfully")
        
        return {"access_token": access_token, "token_type": "bearer"}
        
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

# API Key Management endpoints
@app.post("/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new API key for the current user."""
    try:
        api_key = security_system.create_api_key(
            user_id=current_user["id"],
            name=api_key_data.name,
            permissions=api_key_data.permissions,
            expires_in_days=api_key_data.expires_in_days
        )
        
        # Get API key record
        api_key_record = security_system.validate_api_key(api_key)
        
        return APIKeyResponse(
            key_id=api_key_record.key_id,
            api_key=api_key,
            name=api_key_record.name,
            permissions=api_key_record.permissions,
            created_at=api_key_record.created_at,
            expires_at=api_key_record.expires_at
        )
        
    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

@app.get("/auth/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """List API keys for the current user."""
    try:
        api_keys = security_system.list_api_keys(current_user["id"])
        return {"api_keys": api_keys}
        
    except Exception as e:
        logger.error(f"API key listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )

@app.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key."""
    try:
        success = security_system.revoke_api_key(key_id, current_user["id"])
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {"message": "API key revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )

# Background Task Management endpoints
@app.post("/tasks/model/retrain", response_model=BackgroundTaskResponse)
async def trigger_model_retrain(
    background_tasks: BackgroundTasks,
    force_retrain: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Trigger model retraining as a background task."""
    try:
        # Submit background task
        task = retrain_model.delay(
            user_id=current_user["id"],
            force_retrain=force_retrain
        )
        
        return BackgroundTaskResponse(
            task_id=task.id,
            status="queued",
            message="Model retraining task queued successfully",
            estimated_completion=datetime.utcnow() + timedelta(hours=2)
        )
        
    except Exception as e:
        logger.error(f"Model retrain task submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue model retraining task"
        )

@app.post("/tasks/data/update", response_model=BackgroundTaskResponse)
async def trigger_data_update(
    background_tasks: BackgroundTasks,
    force_update: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Trigger data update as a background task."""
    try:
        # Submit background task
        task = update_bitcoin_data.delay(force_update=force_update)
        
        return BackgroundTaskResponse(
            task_id=task.id,
            status="queued",
            message="Data update task queued successfully",
            estimated_completion=datetime.utcnow() + timedelta(minutes=30)
        )
        
    except Exception as e:
        logger.error(f"Data update task submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue data update task"
        )

@app.post("/tasks/analytics/report", response_model=BackgroundTaskResponse)
async def trigger_daily_report(
    background_tasks: BackgroundTasks,
    report_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Trigger daily report generation as a background task."""
    try:
        # Submit background task
        task = generate_daily_report.delay(report_date=report_date)
        
        return BackgroundTaskResponse(
            task_id=task.id,
            status="queued",
            message="Daily report generation task queued successfully",
            estimated_completion=datetime.utcnow() + timedelta(minutes=15)
        )
        
    except Exception as e:
        logger.error(f"Daily report task submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue daily report task"
        )

# Task Status endpoints
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """Get the status of a background task."""
    try:
        # Get task result from Celery
        task_result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
            "info": task_result.info if hasattr(task_result, 'info') else None
        }
        
    except Exception as e:
        logger.error(f"Task status retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status"
        )

# Price Alert endpoints
@app.post("/alerts/price")
async def create_price_alert(
    alert_data: PriceAlertCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a price alert for the current user."""
    try:
        # Get current Bitcoin price
        from data.realtime_data import get_realtime_price
        current_price = get_realtime_price()
        
        # Create alert record in database
        alert_id = f"alert_{int(time.time())}"
        
        # Submit background task for alert monitoring
        task = send_price_alert.delay(
            user_id=current_user["id"],
            alert_type=alert_data.alert_type,
            price_threshold=alert_data.price_threshold,
            current_price=current_price,
            alert_id=alert_id
        )
        
        return {
            "alert_id": alert_id,
            "status": "created",
            "current_price": current_price,
            "threshold": alert_data.price_threshold,
            "alert_type": alert_data.alert_type
        }
        
    except Exception as e:
        logger.error(f"Price alert creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price alert"
        )

# Monitoring and Metrics endpoints
@app.get("/metrics/system")
async def get_system_metrics():
    """Get system metrics."""
    try:
        metrics = await get_system_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"System metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system metrics"
        )

@app.get("/metrics/application")
async def get_application_metrics():
    """Get application metrics."""
    try:
        metrics = monitoring.get_metrics_summary()
        return metrics
        
    except Exception as e:
        logger.error(f"Application metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application metrics"
        )

@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus metrics."""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return StreamingResponse(
            iter([generate_latest()]),
            media_type=CONTENT_TYPE_LATEST
        )
        
    except Exception as e:
        logger.error(f"Prometheus metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get Prometheus metrics"
        )

# Security Audit endpoints
@app.get("/security/audit-logs")
async def get_security_audit_logs(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get security audit logs."""
    try:
        # Only admins can view audit logs
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        
        audit_logs = security_system.get_security_audit_logs(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        return {"audit_logs": audit_logs}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Security audit logs retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security audit logs"
        )

# User Management endpoints
@app.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@app.get("/users/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get detailed user profile."""
    try:
        # Get user profile from database
        user_profile = UserRepository.get_user_by_id(current_user["id"])
        
        # Add additional profile information
        profile = {
            "id": user_profile["id"],
            "username": user_profile["username"],
            "email": user_profile["email"],
            "role": user_profile["role"],
            "created_at": user_profile["created_at"],
            "last_login": user_profile["last_login"],
            "subscription_status": "active",  # Placeholder
            "api_usage": {
                "requests_today": 0,  # Placeholder
                "requests_this_month": 0,  # Placeholder
                "rate_limit_remaining": 100  # Placeholder
            }
        }
        
        return profile
        
    except Exception as e:
        logger.error(f"User profile retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )

# System Status endpoints
@app.get("/status")
async def system_status():
    """Get comprehensive system status."""
    try:
        # Get basic status
        basic_status = {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "3.0.0",
            "environment": settings.deployment.environment,
            "region": settings.deployment.region
        }
        
        # Get health status
        health_status = await get_health_status()
        
        # Get monitoring metrics
        monitoring_metrics = monitoring.get_metrics_summary()
        
        # Get system metrics
        system_metrics = await get_system_metrics()
        
        return {
            **basic_status,
            "health": health_status,
            "monitoring": monitoring_metrics,
            "system": system_metrics
        }
        
    except Exception as e:
        logger.error(f"System status retrieval failed: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/status/simple")
async def simple_status():
    """Get simple system status."""
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "BTC Forecast API - Enhanced Production Ready",
        "version": "3.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "Background Processing (Celery)",
            "Advanced Monitoring (OpenTelemetry)",
            "Enhanced Security (API Keys, OAuth)",
            "Multi-Region Support",
            "Real-time Metrics",
            "Automated Alerts",
            "Distributed Tracing"
        ],
        "documentation": "/docs",
        "health_check": "/health",
        "metrics": "/metrics/prometheus"
    }

# Helper functions
async def get_system_metrics() -> SystemMetrics:
    """Get system metrics."""
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Placeholder values for application metrics
        active_connections = 0
        request_rate = 0.0
        error_rate = 0.0
        
        return SystemMetrics(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            active_connections=active_connections,
            request_rate=request_rate,
            error_rate=error_rate
        )
        
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return SystemMetrics(
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            active_connections=0,
            request_rate=0.0,
            error_rate=0.0
        )

def create_default_users():
    """Create default users for testing."""
    try:
        # Create admin user
        admin_user = UserRepository.get_user_by_username("admin")
        if not admin_user:
            hashed_password = hash_password("admin123")
            UserRepository.create_user(
                username="admin",
                email="admin@btcforecast.com",
                hashed_password=hashed_password,
                role="admin"
            )
            logger.info("Created default admin user: admin")
        
        # Create demo user
        demo_user = UserRepository.get_user_by_username("demo")
        if not demo_user:
            hashed_password = hash_password("demo123")
            UserRepository.create_user(
                username="demo",
                email="demo@btcforecast.com",
                hashed_password=hashed_password,
                role="user"
            )
            logger.info("Created demo user: demo")
            
    except Exception as e:
        logger.error(f"Failed to create default users: {e}")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    try:
        logger.info("Starting BTC Forecast API - Enhanced Production Ready")
        
        # Create default users
        create_default_users()
        
        # Start monitoring system
        monitoring.start_monitoring()
        
        # Initialize security system
        logger.info("Security system initialized")
        
        # Initialize Celery
        logger.info("Celery background processing initialized")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    try:
        logger.info("Shutting down BTC Forecast API")
        
        # Stop monitoring system
        monitoring.stop_monitoring()
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Application shutdown failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_enhanced:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        log_level=settings.api.log_level.lower()
    ) 