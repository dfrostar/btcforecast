#!/usr/bin/env python3
"""
Production-ready error handling and resilience patterns for BTC Forecast application
"""

import asyncio
import time
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps
from enum import Enum
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception
    monitor_interval: int = 10  # seconds

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.utcnow()
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._call_sync(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_state(CircuitState.HALF_OPEN)
            else:
                raise self.config.expected_exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute sync function with circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._set_state(CircuitState.HALF_OPEN)
            else:
                raise self.config.expected_exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return (datetime.utcnow() - self.last_failure_time).total_seconds() >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self._set_state(CircuitState.CLOSED)
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.config.failure_threshold:
            self._set_state(CircuitState.OPEN)
    
    def _set_state(self, new_state: CircuitState):
        """Set circuit breaker state."""
        if self.state != new_state:
            logger.warning(f"Circuit breaker '{self.name}' state changed from {self.state.value} to {new_state.value}")
            self.state = new_state
            self.last_state_change = datetime.utcnow()
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_state_change": self.last_state_change.isoformat()
        }

class RetryHandler:
    """Retry mechanism with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply retry logic to a function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._retry_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._retry_sync(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """Retry async function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for {func.__name__}")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay:.2f}s")
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _retry_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Retry sync function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for {func.__name__}")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay:.2f}s")
                time.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter."""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)  # Add 50% jitter
        
        return delay

class GracefulDegradation:
    """Graceful degradation pattern for handling service failures."""
    
    def __init__(self, fallback_func: Optional[Callable] = None):
        self.fallback_func = fallback_func
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply graceful degradation to a function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function {func.__name__} failed, using fallback")
                if self.fallback_func:
                    return await self.fallback_func(*args, **kwargs)
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function {func.__name__} failed, using fallback")
                if self.fallback_func:
                    return self.fallback_func(*args, **kwargs)
                raise e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

class ErrorHandler:
    """Centralized error handling and logging."""
    
    @staticmethod
    def handle_api_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle API errors and return appropriate response."""
        error_id = str(int(time.time() * 1000))
        
        # Log the error
        logger.error(f"API Error {error_id}: {str(error)}", exc_info=True, extra=context or {})
        
        # Return user-friendly error response
        return {
            "error": {
                "id": error_id,
                "message": "An error occurred while processing your request",
                "type": type(error).__name__,
                "timestamp": time.time()
            }
        }
    
    @staticmethod
    def handle_database_error(error: Exception, operation: str) -> Dict[str, Any]:
        """Handle database errors specifically."""
        error_id = str(int(time.time() * 1000))
        
        logger.error(f"Database Error {error_id} during {operation}: {str(error)}", exc_info=True)
        
        return {
            "error": {
                "id": error_id,
                "message": "Database operation failed",
                "operation": operation,
                "timestamp": time.time()
            }
        }
    
    @staticmethod
    def handle_external_api_error(error: Exception, service: str) -> Dict[str, Any]:
        """Handle external API errors."""
        error_id = str(int(time.time() * 1000))
        
        logger.error(f"External API Error {error_id} from {service}: {str(error)}", exc_info=True)
        
        return {
            "error": {
                "id": error_id,
                "message": f"External service ({service}) is temporarily unavailable",
                "service": service,
                "timestamp": time.time()
            }
        }

# Pre-configured circuit breakers for common external services
external_api_circuit_breaker = CircuitBreaker(
    "external_api",
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
)

database_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

# Pre-configured retry handlers
api_retry_handler = RetryHandler(max_retries=3, base_delay=1.0)
database_retry_handler = RetryHandler(max_retries=2, base_delay=0.5) 