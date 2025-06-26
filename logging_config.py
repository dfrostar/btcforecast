#!/usr/bin/env python3
"""
Production-ready logging configuration for BTC Forecast application
"""

import logging
import logging.handlers
import json
import uuid
from datetime import datetime
from typing import Dict, Any
import os
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', None),
            "user_id": getattr(record, 'user_id', None),
            "endpoint": getattr(record, 'endpoint', None),
            "method": getattr(record, 'method', None),
            "ip_address": getattr(record, 'ip_address', None),
            "response_time": getattr(record, 'response_time', None),
            "status_code": getattr(record, 'status_code', None),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)

class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def __init__(self, correlation_id: str = None):
        super().__init__()
        self.correlation_id = correlation_id or str(uuid.uuid4())
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.correlation_id
        return True

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/btcforecast.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """Set up production-ready logging configuration."""
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    structured_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(structured_formatter)
        root_logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = str(log_path.parent / "btcforecast_error.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(structured_formatter)
    root_logger.addHandler(error_handler)
    
    # Create application logger
    app_logger = logging.getLogger("btcforecast")
    app_logger.setLevel(logging.DEBUG)
    
    return app_logger

def get_correlation_id() -> str:
    """Generate a correlation ID for request tracking."""
    return str(uuid.uuid4())

def log_request(
    logger: logging.Logger,
    correlation_id: str,
    method: str,
    endpoint: str,
    user_id: str = None,
    ip_address: str = None,
    status_code: int = None,
    response_time: float = None,
    extra: Dict[str, Any] = None
):
    """Log API request details."""
    log_data = {
        "correlation_id": correlation_id,
        "method": method,
        "endpoint": endpoint,
        "user_id": user_id,
        "ip_address": ip_address,
        "status_code": status_code,
        "response_time": response_time,
        "event_type": "api_request"
    }
    
    if extra:
        log_data.update(extra)
    
    logger.info("API Request", extra=log_data)

def log_error(
    logger: logging.Logger,
    correlation_id: str,
    error: Exception,
    context: Dict[str, Any] = None
):
    """Log error with context."""
    log_data = {
        "correlation_id": correlation_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "event_type": "error"
    }
    
    if context:
        log_data.update(context)
    
    logger.error("Application Error", extra=log_data, exc_info=True)

def log_security_event(
    logger: logging.Logger,
    correlation_id: str,
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    details: Dict[str, Any] = None
):
    """Log security-related events."""
    log_data = {
        "correlation_id": correlation_id,
        "user_id": user_id,
        "ip_address": ip_address,
        "event_type": f"security_{event_type}",
        "severity": "high" if event_type in ["login_failed", "unauthorized_access"] else "medium"
    }
    
    if details:
        log_data.update(details)
    
    logger.warning("Security Event", extra=log_data)

def log_performance(
    logger: logging.Logger,
    correlation_id: str,
    operation: str,
    duration: float,
    success: bool = True,
    details: Dict[str, Any] = None
):
    """Log performance metrics."""
    log_data = {
        "correlation_id": correlation_id,
        "operation": operation,
        "duration": duration,
        "success": success,
        "event_type": "performance"
    }
    
    if details:
        log_data.update(details)
    
    logger.info("Performance Metric", extra=log_data)

# Initialize logging
app_logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_console=True,
    enable_file=True
) 