#!/usr/bin/env python3
"""
Celery Configuration for BTC Forecasting Application
Background task processing with Redis broker and monitoring integration
"""

import os
import sys
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config import get_settings

# Get settings
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "btcforecast",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.model_training",
        "tasks.data_processing", 
        "tasks.notifications",
        "tasks.analytics",
        "tasks.maintenance"
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "tasks.model_training.*": {"queue": "model_training"},
        "tasks.data_processing.*": {"queue": "data_processing"},
        "tasks.notifications.*": {"queue": "notifications"},
        "tasks.analytics.*": {"queue": "analytics"},
        "tasks.maintenance.*": {"queue": "maintenance"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Data processing tasks
        "update-bitcoin-data": {
            "task": "tasks.data_processing.update_bitcoin_data",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },
        "validate-data-quality": {
            "task": "tasks.data_processing.validate_data_quality",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        
        # Model training tasks
        "retrain-model-daily": {
            "task": "tasks.model_training.retrain_model",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "evaluate-model-performance": {
            "task": "tasks.model_training.evaluate_model_performance",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        
        # Analytics tasks
        "generate-daily-report": {
            "task": "tasks.analytics.generate_daily_report",
            "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
        },
        "generate-market-insights": {
            "task": "tasks.analytics.generate_market_insights",
            "schedule": crontab(minute="*/60"),  # Every hour
        },
        
        # Maintenance tasks
        "system-health-check": {
            "task": "tasks.maintenance.system_health_check",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "cleanup-old-data": {
            "task": "tasks.maintenance.cleanup_old_data",
            "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
        },
        "backup-database": {
            "task": "tasks.maintenance.backup_database",
            "schedule": crontab(hour=0, minute=0),  # Daily at midnight
        },
        
        # Notification tasks
        "send-daily-report": {
            "task": "tasks.notifications.send_daily_report",
            "schedule": crontab(hour=7, minute=0),  # Daily at 7 AM
        },
    },
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
    
    # Error handling
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Performance optimization
    worker_max_memory_per_child=200000,  # 200MB
    task_compression="gzip",
    result_compression="gzip",
)

# Task routing for different environments
if settings.ENVIRONMENT == "production":
    celery_app.conf.update(
        # Production-specific settings
        worker_prefetch_multiplier=4,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_max_memory_per_child=500000,  # 500MB
    )
elif settings.ENVIRONMENT == "development":
    celery_app.conf.update(
        # Development-specific settings
        task_always_eager=False,
        worker_prefetch_multiplier=1,
        task_acks_late=False,
    )

# Task error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f"Request: {self.request!r}")

# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Health check task for monitoring"""
    return {
        "status": "healthy",
        "worker_id": self.request.id,
        "timestamp": self.request.timestamp,
    }

if __name__ == "__main__":
    celery_app.start() 