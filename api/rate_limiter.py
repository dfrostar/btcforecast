"""
Rate Limiting Middleware
Provides rate limiting functionality with tiered limits for different user roles.
"""

import time
from typing import Dict, Tuple, Optional
from fastapi import HTTPException, Request, status
from collections import defaultdict
import threading
import os

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
        
        # Rate limits per role (requests per minute)
        self.rate_limits = {
            "free": int(os.getenv("RATE_LIMIT_FREE", "60")),
            "premium": int(os.getenv("RATE_LIMIT_PREMIUM", "300")),
            "admin": int(os.getenv("RATE_LIMIT_ADMIN", "1000"))
        }
        
        # Window size in seconds
        self.window_size = 60
        
    def is_allowed(self, identifier: str, role: str = "free") -> Tuple[bool, Dict]:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            identifier: User identifier (IP, user ID, or API key)
            role: User role for tiered rate limiting
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        with self.lock:
            current_time = time.time()
            window_start = current_time - self.window_size
            
            # Clean old requests outside the window
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
            
            # Get rate limit for role
            rate_limit = self.rate_limits.get(role, self.rate_limits["free"])
            
            # Check if request is allowed
            if len(self.requests[identifier]) >= rate_limit:
                return False, {
                    "limit": rate_limit,
                    "remaining": 0,
                    "reset_time": window_start + self.window_size,
                    "retry_after": int(window_start + self.window_size - current_time)
                }
            
            # Add current request
            self.requests[identifier].append(current_time)
            
            return True, {
                "limit": rate_limit,
                "remaining": rate_limit - len(self.requests[identifier]),
                "reset_time": window_start + self.window_size
            }
    
    def get_rate_limit_info(self, identifier: str, role: str = "free") -> Dict:
        """Get current rate limit information for an identifier."""
        with self.lock:
            current_time = time.time()
            window_start = current_time - self.window_size
            
            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
            
            rate_limit = self.rate_limits.get(role, self.rate_limits["free"])
            
            return {
                "limit": rate_limit,
                "remaining": max(0, rate_limit - len(self.requests[identifier])),
                "reset_time": window_start + self.window_size,
                "used": len(self.requests[identifier])
            }

# Global rate limiter instance
rate_limiter = RateLimiter()

def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client.
    Prioritizes API key, then user ID, then IP address.
    """
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"
    
    # Check for user ID in JWT token (if available)
    # This would be extracted from the JWT token in the auth middleware
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    
    return f"ip:{request.client.host}"

def get_user_role(request: Request) -> str:
    """
    Get the user role for rate limiting.
    Falls back to 'free' if no role is available.
    """
    # Check if user role is available in request state
    user_role = getattr(request.state, "user_role", None)
    if user_role:
        return user_role
    
    # Check for API key and get associated user role
    api_key = request.headers.get("X-API-Key")
    if api_key:
        from api.auth import verify_api_key
        user = verify_api_key(api_key)
        if user:
            return user.role
    
    return "free"

async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting.
    """
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/health", "/health/detailed", "/health/metrics"]:
        response = await call_next(request)
        return response
    
    # Get client identifier and role
    identifier = get_client_identifier(request)
    role = get_user_role(request)
    
    # Check rate limit
    is_allowed, rate_info = rate_limiter.is_allowed(identifier, role)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_info["limit"],
                "remaining": rate_info["remaining"],
                "reset_time": rate_info["reset_time"],
                "retry_after": rate_info["retry_after"]
            },
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset_time"]),
                "Retry-After": str(rate_info["retry_after"])
            }
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])
    
    return response

def get_rate_limit_status(identifier: str, role: str = "free") -> Dict:
    """
    Get current rate limit status for monitoring.
    """
    return rate_limiter.get_rate_limit_info(identifier, role)

# Rate limit decorator for specific endpoints
def rate_limit(role: str = "free"):
    """
    Decorator to apply rate limiting to specific endpoints.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if hasattr(arg, 'url'):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if hasattr(value, 'url'):
                        request = value
                        break
            
            if request:
                identifier = get_client_identifier(request)
                user_role = get_user_role(request)
                
                is_allowed, rate_info = rate_limiter.is_allowed(identifier, user_role)
                
                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "limit": rate_info["limit"],
                            "remaining": rate_info["remaining"],
                            "reset_time": rate_info["reset_time"]
                        }
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 