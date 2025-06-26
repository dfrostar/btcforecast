#!/usr/bin/env python3
"""
Production-ready health check system for BTC Forecast application
"""

import time
import psutil
import sqlite3
import requests
import logging
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    duration: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class HealthChecker:
    """Comprehensive health check system."""
    
    def __init__(self):
        self.checks: List[callable] = []
        self.startup_time = time.time()
    
    def add_check(self, check_func: callable):
        """Add a health check function."""
        self.checks.append(check_func)
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        results = []
        overall_status = HealthStatus.HEALTHY
        
        for check_func in self.checks:
            start_time = time.time()
            try:
                result = await check_func()
                result.duration = time.time() - start_time
                results.append(result)
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check {check_func.__name__} failed: {e}")
                result = HealthCheckResult(
                    name=check_func.__name__,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(e)}",
                    duration=time.time() - start_time
                )
                results.append(result)
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": time.time() - self.startup_time,
            "checks": [self._serialize_result(result) for result in results]
        }
    
    def _serialize_result(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Serialize health check result for JSON response."""
        return {
            "name": result.name,
            "status": result.status.value,
            "message": result.message,
            "details": result.details or {},
            "duration": round(result.duration, 3),
            "timestamp": result.timestamp.isoformat()
        }

# Health check functions
async def check_database_health() -> HealthCheckResult:
    """Check database connectivity and performance."""
    try:
        start_time = time.time()
        
        # Check if using PostgreSQL or SQLite
        database_url = os.getenv('DATABASE_URL', '')
        
        if database_url and database_url.startswith('postgresql://'):
            # PostgreSQL connection
            try:
                from database.postgres_adapter import postgres_manager
                await postgres_manager.initialize()
                
                # Test basic query
                results = await postgres_manager.execute_query("SELECT COUNT(*) as count FROM users")
                user_count = results[0]['count'] if results else 0
                
                # Test write operation
                await postgres_manager.execute_query("SELECT 1")
                
                duration = time.time() - start_time
                
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message=f"PostgreSQL database is healthy. {user_count} users found.",
                    details={
                        "database_type": "postgresql",
                        "user_count": user_count,
                        "response_time_ms": round(duration * 1000, 2)
                    }
                )
            except Exception as e:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"PostgreSQL database check failed: {str(e)}",
                    details={"database_type": "postgresql"}
                )
        else:
            # SQLite connection (fallback)
            conn = sqlite3.connect('btcforecast.db')
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Test write operation
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            conn.close()
            
            duration = time.time() - start_time
            
            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message=f"SQLite database is healthy. {user_count} users found.",
                details={
                    "database_type": "sqlite",
                    "user_count": user_count,
                    "response_time_ms": round(duration * 1000, 2)
                }
            )
        
    except Exception as e:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database check failed: {str(e)}"
        )

async def check_memory_usage() -> HealthCheckResult:
    """Check memory usage and availability."""
    try:
        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent
        
        if memory_usage_percent < 80:
            status = HealthStatus.HEALTHY
        elif memory_usage_percent < 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return HealthCheckResult(
            name="memory",
            status=status,
            message=f"Memory usage: {memory_usage_percent:.1f}%",
            details={
                "usage_percent": memory_usage_percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            }
        )
        
    except Exception as e:
        return HealthCheckResult(
            name="memory",
            status=HealthStatus.UNHEALTHY,
            message=f"Memory check failed: {str(e)}"
        )

async def check_disk_usage() -> HealthCheckResult:
    """Check disk usage and availability."""
    try:
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        
        if disk_usage_percent < 85:
            status = HealthStatus.HEALTHY
        elif disk_usage_percent < 95:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return HealthCheckResult(
            name="disk",
            status=status,
            message=f"Disk usage: {disk_usage_percent:.1f}%",
            details={
                "usage_percent": disk_usage_percent,
                "available_gb": round(disk.free / (1024**3), 2),
                "total_gb": round(disk.total / (1024**3), 2)
            }
        )
        
    except Exception as e:
        return HealthCheckResult(
            name="disk",
            status=HealthStatus.UNHEALTHY,
            message=f"Disk check failed: {str(e)}"
        )

async def check_cpu_usage() -> HealthCheckResult:
    """Check CPU usage and load."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        if cpu_percent < 80:
            status = HealthStatus.HEALTHY
        elif cpu_percent < 90:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return HealthCheckResult(
            name="cpu",
            status=status,
            message=f"CPU usage: {cpu_percent:.1f}%",
            details={
                "usage_percent": cpu_percent,
                "cpu_count": cpu_count,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        )
        
    except Exception as e:
        return HealthCheckResult(
            name="cpu",
            status=HealthStatus.UNHEALTHY,
            message=f"CPU check failed: {str(e)}"
        )

async def check_external_apis() -> HealthCheckResult:
    """Check external API connectivity with circuit breaker pattern."""
    try:
        # Test external APIs (example: crypto price APIs)
        apis_to_check = [
            ("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
            ("Binance", "https://api.binance.com/api/v3/ping")
        ]
        
        failed_apis = []
        successful_apis = []
        
        for api_name, api_url in apis_to_check:
            try:
                # Implement circuit breaker pattern with retry logic
                max_retries = 2
                timeout = 5
                
                for attempt in range(max_retries + 1):
                    try:
                        response = requests.get(api_url, timeout=timeout)
                        if response.status_code == 200:
                            successful_apis.append(api_name)
                            break
                        else:
                            if attempt == max_retries:
                                failed_apis.append(f"{api_name} (HTTP {response.status_code})")
                            else:
                                time.sleep(1)  # Wait before retry
                    except requests.exceptions.Timeout:
                        if attempt == max_retries:
                            failed_apis.append(f"{api_name} (timeout)")
                        else:
                            time.sleep(1)
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries:
                            failed_apis.append(f"{api_name} ({str(e)})")
                        else:
                            time.sleep(1)
                            
            except Exception as e:
                failed_apis.append(f"{api_name} ({str(e)})")
        
        if len(failed_apis) == 0:
            status = HealthStatus.HEALTHY
            message = "All external APIs are accessible"
        elif len(successful_apis) > 0:
            status = HealthStatus.DEGRADED
            message = f"Some external APIs are down: {', '.join(failed_apis)}"
        else:
            status = HealthStatus.UNHEALTHY
            message = "All external APIs are down"
        
        return HealthCheckResult(
            name="external_apis",
            status=status,
            message=message,
            details={
                "successful_apis": successful_apis,
                "failed_apis": failed_apis,
                "total_apis": len(apis_to_check),
                "retry_attempts": max_retries,
                "timeout_seconds": timeout
            }
        )
        
    except Exception as e:
        return HealthCheckResult(
            name="external_apis",
            status=HealthStatus.UNHEALTHY,
            message=f"External API check failed: {str(e)}"
        )

async def check_model_health() -> HealthCheckResult:
    """Check ML model availability and performance."""
    try:
        import os
        import pickle
        
        # Get model path from environment variable
        model_path = os.getenv("MODEL_PATH", ".")
        
        # Check if model files exist
        model_files = [
            os.path.join(model_path, 'btc_model.pkl'),
            os.path.join(model_path, 'btc_scaler.pkl')
        ]
        missing_files = []
        existing_files = []
        
        for file in model_files:
            if os.path.exists(file):
                existing_files.append(os.path.basename(file))
            else:
                missing_files.append(os.path.basename(file))
        
        if len(missing_files) == 0:
            # Try to load the model
            try:
                model_file_path = os.path.join(model_path, 'btc_model.pkl')
                with open(model_file_path, 'rb') as f:
                    model = pickle.load(f)
                
                status = HealthStatus.HEALTHY
                message = "ML model is loaded and ready"
                details = {
                    "model_type": type(model).__name__,
                    "model_files": existing_files,
                    "model_path": model_path
                }
            except Exception as e:
                status = HealthStatus.DEGRADED
                message = f"Model files exist but failed to load: {str(e)}"
                details = {
                    "model_files": existing_files,
                    "model_path": model_path,
                    "error": str(e)
                }
        else:
            status = HealthStatus.UNHEALTHY
            message = f"Missing model files: {', '.join(missing_files)}"
            details = {
                "missing_files": missing_files,
                "existing_files": existing_files,
                "model_path": model_path
            }
        
        return HealthCheckResult(
            name="ml_model",
            status=status,
            message=message,
            details=details
        )
        
    except Exception as e:
        return HealthCheckResult(
            name="ml_model",
            status=HealthStatus.UNHEALTHY,
            message=f"Model health check failed: {str(e)}"
        )

# Create health checker instance
health_checker = HealthChecker()

# Add all health checks
health_checker.add_check(check_database_health)
health_checker.add_check(check_memory_usage)
health_checker.add_check(check_disk_usage)
health_checker.add_check(check_cpu_usage)
health_checker.add_check(check_external_apis)
health_checker.add_check(check_model_health)

async def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status."""
    return await health_checker.run_all_checks()

async def get_simple_health_status() -> Dict[str, Any]:
    """Get simple health status for basic monitoring."""
    try:
        # Check database connection
        database_url = os.getenv('DATABASE_URL', '')
        
        if database_url and database_url.startswith('postgresql://'):
            # PostgreSQL connection
            try:
                from database.postgres_adapter import postgres_manager
                await postgres_manager.initialize()
                await postgres_manager.execute_query("SELECT 1")
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": f"PostgreSQL connection failed: {str(e)}"
                }
        else:
            # SQLite connection (fallback)
            conn = sqlite3.connect('btcforecast.db')
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Service is operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Service is down: {str(e)}"
        } 