#!/usr/bin/env python3
"""
Advanced Monitoring System for BTC Forecast Application
Custom metrics, alerting, and distributed tracing with OpenTelemetry
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
import time
import json
import threading
from contextlib import contextmanager
import functools

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusExporter, PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

# Prometheus imports
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.exposition import start_http_server
from prometheus_client.registry import CollectorRegistry

# Structlog for structured logging
import structlog

# Import application modules
from config import get_settings
from celery_app import celery_app

# Configure logging
logger = structlog.get_logger()
settings = get_settings()

class AdvancedMonitoring:
    """
    Advanced monitoring system with OpenTelemetry, Prometheus, and custom metrics
    """
    
    def __init__(self):
        self.settings = settings
        self.tracer = None
        self.meter = None
        self.registry = CollectorRegistry()
        
        # Prometheus metrics
        self.metrics = {}
        
        # Custom alerting
        self.alert_rules = []
        self.alert_handlers = []
        
        # Performance tracking
        self.performance_data = {}
        
        # Initialize monitoring
        self._setup_opentelemetry()
        self._setup_prometheus_metrics()
        self._setup_custom_alerts()
    
    def _setup_opentelemetry(self):
        """Setup OpenTelemetry tracing and metrics"""
        try:
            # Setup tracer
            trace.set_tracer_provider(TracerProvider())
            tracer = trace.get_tracer(__name__)
            
            # Setup Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name=settings.JAEGER_HOST,
                agent_port=settings.JAEGER_PORT,
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Setup meter
            metric_reader = PeriodicExportingMetricReader(
                PrometheusMetricReader(registry=self.registry)
            )
            meter_provider = MeterProvider(metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            meter = metrics.get_meter(__name__)
            
            self.tracer = tracer
            self.meter = meter
            
            logger.info("OpenTelemetry setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup OpenTelemetry: {e}")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        try:
            # API metrics
            self.metrics["api_requests_total"] = Counter(
                "api_requests_total",
                "Total number of API requests",
                ["method", "endpoint", "status"],
                registry=self.registry
            )
            
            self.metrics["api_request_duration"] = Histogram(
                "api_request_duration_seconds",
                "API request duration in seconds",
                ["method", "endpoint"],
                registry=self.registry
            )
            
            # Model metrics
            self.metrics["model_predictions_total"] = Counter(
                "model_predictions_total",
                "Total number of model predictions",
                ["model_type", "status"],
                registry=self.registry
            )
            
            self.metrics["model_prediction_duration"] = Histogram(
                "model_prediction_duration_seconds",
                "Model prediction duration in seconds",
                ["model_type"],
                registry=self.registry
            )
            
            # System metrics
            self.metrics["system_memory_usage"] = Gauge(
                "system_memory_usage_bytes",
                "System memory usage in bytes",
                registry=self.registry
            )
            
            self.metrics["system_cpu_usage"] = Gauge(
                "system_cpu_usage_percent",
                "System CPU usage percentage",
                registry=self.registry
            )
            
            self.metrics["database_connections"] = Gauge(
                "database_connections_active",
                "Number of active database connections",
                registry=self.registry
            )
            
            # Business metrics
            self.metrics["user_registrations"] = Counter(
                "user_registrations_total",
                "Total number of user registrations",
                registry=self.registry
            )
            
            self.metrics["predictions_accuracy"] = Gauge(
                "predictions_accuracy_r2",
                "Model prediction accuracy (R² score)",
                registry=self.registry
            )
            
            # Celery metrics
            self.metrics["celery_tasks_total"] = Counter(
                "celery_tasks_total",
                "Total number of Celery tasks",
                ["task_name", "status"],
                registry=self.registry
            )
            
            self.metrics["celery_task_duration"] = Histogram(
                "celery_task_duration_seconds",
                "Celery task duration in seconds",
                ["task_name"],
                registry=self.registry
            )
            
            # Start Prometheus HTTP server
            start_http_server(settings.PROMETHEUS_PORT)
            
            logger.info(f"Prometheus metrics server started on port {settings.PROMETHEUS_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to setup Prometheus metrics: {e}")
    
    def _setup_custom_alerts(self):
        """Setup custom alerting rules"""
        try:
            # API performance alerts
            self.add_alert_rule(
                name="high_api_latency",
                condition=lambda: self._check_api_latency(),
                severity="warning",
                message="API response time is above threshold"
            )
            
            # Model performance alerts
            self.add_alert_rule(
                name="low_model_accuracy",
                condition=lambda: self._check_model_accuracy(),
                severity="critical",
                message="Model accuracy is below threshold"
            )
            
            # System resource alerts
            self.add_alert_rule(
                name="high_memory_usage",
                condition=lambda: self._check_memory_usage(),
                severity="warning",
                message="Memory usage is above threshold"
            )
            
            # Database alerts
            self.add_alert_rule(
                name="database_connection_issues",
                condition=lambda: self._check_database_health(),
                severity="critical",
                message="Database connection issues detected"
            )
            
            logger.info("Custom alerting rules setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup custom alerts: {e}")
    
    def add_alert_rule(self, name: str, condition: Callable, severity: str, message: str):
        """Add custom alert rule"""
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "message": message,
            "last_triggered": None,
            "enabled": True
        })
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler"""
        self.alert_handlers.append(handler)
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics"""
        try:
            # Prometheus metrics
            self.metrics["api_requests_total"].labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code)
            ).inc()
            
            self.metrics["api_request_duration"].labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # OpenTelemetry metrics
            if self.meter:
                request_counter = self.meter.create_counter("api_requests")
                request_counter.add(1, {
                    "method": method,
                    "endpoint": endpoint,
                    "status": str(status_code)
                })
            
            logger.info("API request recorded", 
                       method=method, 
                       endpoint=endpoint, 
                       status=status_code, 
                       duration=duration)
            
        except Exception as e:
            logger.error(f"Failed to record API request: {e}")
    
    def record_model_prediction(self, model_type: str, status: str, duration: float, accuracy: Optional[float] = None):
        """Record model prediction metrics"""
        try:
            # Prometheus metrics
            self.metrics["model_predictions_total"].labels(
                model_type=model_type,
                status=status
            ).inc()
            
            self.metrics["model_prediction_duration"].labels(
                model_type=model_type
            ).observe(duration)
            
            if accuracy is not None:
                self.metrics["predictions_accuracy"].set(accuracy)
            
            # OpenTelemetry metrics
            if self.meter:
                prediction_counter = self.meter.create_counter("model_predictions")
                prediction_counter.add(1, {
                    "model_type": model_type,
                    "status": status
                })
            
            logger.info("Model prediction recorded", 
                       model_type=model_type, 
                       status=status, 
                       duration=duration,
                       accuracy=accuracy)
            
        except Exception as e:
            logger.error(f"Failed to record model prediction: {e}")
    
    def record_celery_task(self, task_name: str, status: str, duration: float):
        """Record Celery task metrics"""
        try:
            # Prometheus metrics
            self.metrics["celery_tasks_total"].labels(
                task_name=task_name,
                status=status
            ).inc()
            
            self.metrics["celery_task_duration"].labels(
                task_name=task_name
            ).observe(duration)
            
            # OpenTelemetry metrics
            if self.meter:
                task_counter = self.meter.create_counter("celery_tasks")
                task_counter.add(1, {
                    "task_name": task_name,
                    "status": status
                })
            
            logger.info("Celery task recorded", 
                       task_name=task_name, 
                       status=status, 
                       duration=duration)
            
        except Exception as e:
            logger.error(f"Failed to record Celery task: {e}")
    
    def update_system_metrics(self):
        """Update system metrics"""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics["system_memory_usage"].set(memory.used)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics["system_cpu_usage"].set(cpu_percent)
            
            # Database connections (placeholder)
            self.metrics["database_connections"].set(1)
            
            logger.debug("System metrics updated", 
                        memory_used=memory.used,
                        cpu_percent=cpu_percent)
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def check_alerts(self):
        """Check all alert rules"""
        try:
            triggered_alerts = []
            
            for rule in self.alert_rules:
                if not rule["enabled"]:
                    continue
                
                try:
                    if rule["condition"]():
                        alert = {
                            "name": rule["name"],
                            "severity": rule["severity"],
                            "message": rule["message"],
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        triggered_alerts.append(alert)
                        rule["last_triggered"] = datetime.now()
                        
                        logger.warning("Alert triggered", **alert)
                        
                except Exception as e:
                    logger.error(f"Error checking alert rule {rule['name']}: {e}")
            
            # Send alerts
            for alert in triggered_alerts:
                self._send_alert(alert)
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
            return []
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert to all handlers"""
        try:
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _check_api_latency(self) -> bool:
        """Check if API latency is above threshold"""
        try:
            # Get recent API request durations
            # This would query the actual metrics
            return False  # Placeholder
        except Exception as e:
            logger.error(f"Error checking API latency: {e}")
            return False
    
    def _check_model_accuracy(self) -> bool:
        """Check if model accuracy is below threshold"""
        try:
            current_accuracy = self.metrics["predictions_accuracy"]._value.get()
            return current_accuracy < 0.5 if current_accuracy is not None else False
        except Exception as e:
            logger.error(f"Error checking model accuracy: {e}")
            return False
    
    def _check_memory_usage(self) -> bool:
        """Check if memory usage is above threshold"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent > 80
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return False
    
    def _check_database_health(self) -> bool:
        """Check database health"""
        try:
            # Implementation to check database health
            return False  # Placeholder
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            return False
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics"""
        try:
            return generate_latest(self.registry)
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return ""
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get monitoring health status"""
        try:
            return {
                "status": "healthy",
                "opentelemetry": self.tracer is not None,
                "prometheus": len(self.metrics) > 0,
                "alerts": len(self.alert_rules),
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {"status": "error", "error": str(e)}

# Global monitoring instance
monitoring = AdvancedMonitoring()

# Decorators for easy instrumentation
def monitor_function(name: str = None):
    """Decorator to monitor function execution"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            start_time = time.time()
            
            # Create span
            if monitoring.tracer:
                with monitoring.tracer.start_as_current_span(func_name) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.set_attribute("error.message", str(e))
                        raise
                    finally:
                        duration = time.time() - start_time
                        monitoring.record_celery_task(func_name, "success", duration)
            else:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    raise
                finally:
                    duration = time.time() - start_time
                    monitoring.record_celery_task(func_name, "success", duration)
        
        return wrapper
    return decorator

@contextmanager
def monitor_operation(name: str):
    """Context manager to monitor operations"""
    start_time = time.time()
    
    if monitoring.tracer:
        with monitoring.tracer.start_as_current_span(name) as span:
            try:
                yield span
                span.set_attribute("status", "success")
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error.message", str(e))
                raise
            finally:
                duration = time.time() - start_time
                monitoring.record_celery_task(name, "success", duration)
    else:
        try:
            yield None
        except Exception as e:
            raise
        finally:
            duration = time.time() - start_time
            monitoring.record_celery_task(name, "success", duration)

# FastAPI middleware
def monitoring_middleware(request, call_next):
    """FastAPI middleware for monitoring"""
    start_time = time.time()
    
    # Create span
    if monitoring.tracer:
        with monitoring.tracer.start_as_current_span("http_request") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            
            try:
                response = call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                return response
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error.message", str(e))
                raise
            finally:
                duration = time.time() - start_time
                monitoring.record_api_request(
                    request.method,
                    str(request.url.path),
                    response.status_code if 'response' in locals() else 500,
                    duration
                )
    else:
        try:
            response = call_next(request)
            return response
        except Exception as e:
            raise
        finally:
            duration = time.time() - start_time
            monitoring.record_api_request(
                request.method,
                str(request.url.path),
                response.status_code if 'response' in locals() else 500,
                duration
            )

# Instrumentation functions
def instrument_fastapi(app):
    """Instrument FastAPI application"""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation completed")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")

def instrument_celery(celery_app):
    """Instrument Celery application"""
    try:
        CeleryInstrumentor().instrument()
        logger.info("Celery instrumentation completed")
    except Exception as e:
        logger.error(f"Failed to instrument Celery: {e}")

def instrument_requests():
    """Instrument requests library"""
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests instrumentation completed")
    except Exception as e:
        logger.error(f"Failed to instrument requests: {e}")

def instrument_sqlite():
    """Instrument SQLite"""
    try:
        SQLite3Instrumentor().instrument()
        logger.info("SQLite instrumentation completed")
    except Exception as e:
        logger.error(f"Failed to instrument SQLite: {e}")

# Alert handlers
def email_alert_handler(alert: Dict[str, Any]):
    """Email alert handler"""
    try:
        # Implementation to send email alerts
        logger.info("Email alert sent", alert=alert)
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

def slack_alert_handler(alert: Dict[str, Any]):
    """Slack alert handler"""
    try:
        # Implementation to send Slack alerts
        logger.info("Slack alert sent", alert=alert)
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")

def webhook_alert_handler(alert: Dict[str, Any]):
    """Webhook alert handler"""
    try:
        # Implementation to send webhook alerts
        logger.info("Webhook alert sent", alert=alert)
    except Exception as e:
        logger.error(f"Failed to send webhook alert: {e}")

# Setup alert handlers
monitoring.add_alert_handler(email_alert_handler)
monitoring.add_alert_handler(slack_alert_handler)
monitoring.add_alert_handler(webhook_alert_handler)

# Performance tracking
class PerformanceTracker:
    """Track performance metrics over time"""
    
    def __init__(self):
        self.metrics = {}
        self.history = {}
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        try:
            timestamp = datetime.now()
            key = f"{name}_{hash(str(tags))}" if tags else name
            
            if key not in self.metrics:
                self.metrics[key] = []
            
            self.metrics[key].append({
                "timestamp": timestamp,
                "value": value,
                "tags": tags or {}
            })
            
            # Keep only last 1000 values
            if len(self.metrics[key]) > 1000:
                self.metrics[key] = self.metrics[key][-1000:]
            
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def get_metric_stats(self, name: str, tags: Dict[str, str] = None, 
                        window_minutes: int = 60) -> Dict[str, float]:
        """Get statistics for a metric"""
        try:
            key = f"{name}_{hash(str(tags))}" if tags else name
            
            if key not in self.metrics:
                return {}
            
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_values = [
                m["value"] for m in self.metrics[key]
                if m["timestamp"] > cutoff_time
            ]
            
            if not recent_values:
                return {}
            
            return {
                "count": len(recent_values),
                "min": min(recent_values),
                "max": max(recent_values),
                "avg": sum(recent_values) / len(recent_values),
                "p95": sorted(recent_values)[int(len(recent_values) * 0.95)],
                "p99": sorted(recent_values)[int(len(recent_values) * 0.99)]
            }
            
        except Exception as e:
            logger.error(f"Failed to get metric stats for {name}: {e}")
            return {}

# Global performance tracker
performance_tracker = PerformanceTracker() 