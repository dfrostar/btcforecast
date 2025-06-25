"""
Monitoring and health check system for BTC Forecasting API
"""
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_available: float
    disk_usage_percent: float
    timestamp: datetime

@dataclass
class APIMetrics:
    """API performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    model_loaded: bool = False
    model_accuracy: Optional[float] = None

class HealthMonitor:
    """Health monitoring system for the API"""
    
    def __init__(self, metrics_file: str = "api_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.api_metrics = APIMetrics()
        self.start_time = datetime.now()
        self.request_times = []
        
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=psutil.virtual_memory().percent,
                memory_available=psutil.virtual_memory().available / (1024**3),  # GB
                disk_usage_percent=psutil.disk_usage('/').percent,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return SystemMetrics(0, 0, 0, 0, datetime.now())
    
    def record_request(self, success: bool, response_time: float):
        """Record API request metrics"""
        self.api_metrics.total_requests += 1
        if success:
            self.api_metrics.successful_requests += 1
        else:
            self.api_metrics.failed_requests += 1
            
        self.request_times.append(response_time)
        self.api_metrics.last_request_time = datetime.now()
        
        # Keep only last 1000 requests for average calculation
        if len(self.request_times) > 1000:
            self.request_times = self.request_times[-1000:]
            
        self.api_metrics.average_response_time = sum(self.request_times) / len(self.request_times)
    
    def update_model_status(self, loaded: bool, accuracy: Optional[float] = None):
        """Update model status"""
        self.api_metrics.model_loaded = loaded
        if accuracy is not None:
            self.api_metrics.model_accuracy = accuracy
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        system_metrics = self.get_system_metrics()
        uptime = datetime.now() - self.start_time
        
        # Calculate success rate
        success_rate = 0
        if self.api_metrics.total_requests > 0:
            success_rate = (self.api_metrics.successful_requests / self.api_metrics.total_requests) * 100
        
        health_status = {
            "status": "healthy" if success_rate > 95 and system_metrics.cpu_percent < 80 else "degraded",
            "uptime_seconds": uptime.total_seconds(),
            "system": asdict(system_metrics),
            "api": {
                "total_requests": self.api_metrics.total_requests,
                "successful_requests": self.api_metrics.successful_requests,
                "failed_requests": self.api_metrics.failed_requests,
                "success_rate_percent": success_rate,
                "average_response_time_ms": self.api_metrics.average_response_time * 1000,
                "last_request_time": self.api_metrics.last_request_time.isoformat() if self.api_metrics.last_request_time else None,
                "model_loaded": self.api_metrics.model_loaded,
                "model_accuracy": self.api_metrics.model_accuracy
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return health_status
    
    def save_metrics(self):
        """Save metrics to file"""
        try:
            health_status = self.get_health_status()
            with open(self.metrics_file, 'w') as f:
                json.dump(health_status, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def load_metrics(self) -> Dict[str, Any]:
        """Load metrics from file"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
        return {}

# Global health monitor instance
health_monitor = HealthMonitor()

def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance"""
    return health_monitor 