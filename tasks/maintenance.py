#!/usr/bin/env python3
"""
Maintenance Background Tasks
System health checks, data cleanup, and automated backups
"""

import os
import sys
import logging
import shutil
import sqlite3
import json
import gzip
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import psutil
import requests
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import current_task
from celery.utils.log import get_task_logger

# Import application modules
from config import get_settings
from health_checks import get_health_status
from api.database import UserRepository

# Configure logging
logger = get_task_logger(__name__)
settings = get_settings()

@current_task.task(bind=True, name="maintenance.system_health_check")
def system_health_check(self) -> Dict[str, Any]:
    """
    Comprehensive system health check
    
    Returns:
        Dict containing health check results
    """
    try:
        logger.info(f"Starting system health check task {self.request.id}")
        
        health_checks = {
            "system_resources": check_system_resources(),
            "database_health": check_database_health(),
            "model_health": check_model_health(),
            "api_health": check_api_health(),
            "celery_health": check_celery_health(),
            "disk_space": check_disk_space(),
            "memory_usage": check_memory_usage(),
            "cpu_usage": check_cpu_usage()
        }
        
        # Determine overall health status
        overall_status = determine_overall_health(health_checks)
        
        # Generate alerts if needed
        alerts = generate_health_alerts(health_checks)
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "overall_health": overall_status,
            "health_checks": health_checks,
            "alerts": alerts,
            "check_time": datetime.now().isoformat()
        }
        
        # Save health check results
        save_health_check_results(result)
        
        # Send alerts if critical issues found
        if alerts:
            send_health_alerts(alerts)
        
        logger.info(f"System health check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="maintenance.cleanup_old_data")
def cleanup_old_data(self, retention_days: int = 90) -> Dict[str, Any]:
    """
    Clean up old data files and logs
    
    Args:
        retention_days: Number of days to retain data
        
    Returns:
        Dict containing cleanup results
    """
    try:
        logger.info(f"Starting data cleanup task {self.request.id}")
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        cleanup_results = {
            "old_logs": cleanup_old_logs(cutoff_date),
            "old_reports": cleanup_old_reports(cutoff_date),
            "old_models": cleanup_old_models(cutoff_date),
            "old_backups": cleanup_old_backups(cutoff_date),
            "temp_files": cleanup_temp_files(),
            "database_cleanup": cleanup_database_old_records(cutoff_date)
        }
        
        # Calculate total space freed
        total_space_freed = sum(result.get("space_freed", 0) for result in cleanup_results.values())
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_results": cleanup_results,
            "total_space_freed": total_space_freed,
            "cleanup_time": datetime.now().isoformat()
        }
        
        logger.info(f"Data cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        if self.request.retries < 2:
            raise self.retry(countdown=300, max_retries=2)
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="maintenance.backup_database")
def backup_database(self, backup_type: str = "full") -> Dict[str, Any]:
    """
    Create database backup
    
    Args:
        backup_type: Type of backup (full, incremental)
        
    Returns:
        Dict containing backup results
    """
    try:
        logger.info(f"Starting database backup task {self.request.id}")
        
        # Create backup directory
        backup_dir = f"backups/{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"btcforecast_db_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Perform backup
        if backup_type == "full":
            backup_result = perform_full_backup(backup_path)
        else:
            backup_result = perform_incremental_backup(backup_path)
        
        # Verify backup
        backup_verification = verify_backup(backup_path)
        
        # Compress backup
        compressed_path = compress_backup(backup_path)
        
        # Update backup metadata
        backup_metadata = {
            "backup_type": backup_type,
            "backup_path": compressed_path,
            "backup_size": os.path.getsize(compressed_path),
            "verification_status": backup_verification["status"],
            "backup_time": datetime.now().isoformat()
        }
        
        save_backup_metadata(backup_metadata)
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "backup_type": backup_type,
            "backup_path": compressed_path,
            "backup_size": backup_metadata["backup_size"],
            "verification_status": backup_verification["status"],
            "backup_time": datetime.now().isoformat()
        }
        
        logger.info(f"Database backup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        if self.request.retries < 2:
            raise self.retry(countdown=600, max_retries=2)
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="maintenance.optimize_database")
def optimize_database(self) -> Dict[str, Any]:
    """
    Optimize database performance
    
    Returns:
        Dict containing optimization results
    """
    try:
        logger.info(f"Starting database optimization task {self.request.id}")
        
        optimization_results = {
            "vacuum": vacuum_database(),
            "reindex": reindex_database(),
            "analyze": analyze_database(),
            "cleanup_indexes": cleanup_indexes()
        }
        
        # Get database statistics
        db_stats = get_database_statistics()
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "optimization_results": optimization_results,
            "database_stats": db_stats,
            "optimization_time": datetime.now().isoformat()
        }
        
        logger.info(f"Database optimization completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="maintenance.monitor_performance")
def monitor_performance(self) -> Dict[str, Any]:
    """
    Monitor system performance metrics
    
    Returns:
        Dict containing performance metrics
    """
    try:
        logger.info(f"Starting performance monitoring task {self.request.id}")
        
        performance_metrics = {
            "api_response_times": measure_api_response_times(),
            "database_query_times": measure_database_performance(),
            "model_inference_times": measure_model_performance(),
            "memory_usage": get_memory_usage_details(),
            "cpu_usage": get_cpu_usage_details(),
            "disk_io": get_disk_io_stats(),
            "network_usage": get_network_usage_stats()
        }
        
        # Store metrics for trending
        store_performance_metrics(performance_metrics)
        
        # Check for performance anomalies
        anomalies = detect_performance_anomalies(performance_metrics)
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "performance_metrics": performance_metrics,
            "anomalies": anomalies,
            "monitoring_time": datetime.now().isoformat()
        }
        
        logger.info(f"Performance monitoring completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Performance monitoring failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

# Health check functions
def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "warning",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "memory_available": memory.available,
            "disk_free": disk.free
        }
    except Exception as e:
        logger.error(f"Error checking system resources: {e}")
        return {"status": "error", "error": str(e)}

def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        
        if not os.path.exists(db_path):
            return {"status": "error", "error": "Database file not found"}
        
        # Check database integrity
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        
        # Check table count
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "healthy" if integrity_result[0] == "ok" else "error",
            "integrity_check": integrity_result[0],
            "table_count": table_count,
            "file_size": os.path.getsize(db_path)
        }
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        return {"status": "error", "error": str(e)}

def check_model_health() -> Dict[str, Any]:
    """Check ML model health"""
    try:
        model_path = "models/btc_model.h5"
        
        if not os.path.exists(model_path):
            return {"status": "error", "error": "Model file not found"}
        
        model_size = os.path.getsize(model_path)
        model_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(model_path))
        
        return {
            "status": "healthy" if model_age.days < 7 else "warning",
            "model_size": model_size,
            "model_age_days": model_age.days,
            "last_updated": datetime.fromtimestamp(os.path.getmtime(model_path)).isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking model health: {e}")
        return {"status": "error", "error": str(e)}

def check_api_health() -> Dict[str, Any]:
    """Check API health"""
    try:
        import requests
        
        # Check API endpoint
        response = requests.get(f"{settings.API_BASE_URL}/health", timeout=5)
        
        return {
            "status": "healthy" if response.status_code == 200 else "error",
            "response_time": response.elapsed.total_seconds(),
            "status_code": response.status_code
        }
    except Exception as e:
        logger.error(f"Error checking API health: {e}")
        return {"status": "error", "error": str(e)}

def check_celery_health() -> Dict[str, Any]:
    """Check Celery worker health"""
    try:
        from celery_app import celery_app
        
        # Check worker status
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        registered_workers = inspect.registered()
        
        worker_count = len(registered_workers) if registered_workers else 0
        active_task_count = sum(len(tasks) for tasks in active_workers.values()) if active_workers else 0
        
        return {
            "status": "healthy" if worker_count > 0 else "error",
            "worker_count": worker_count,
            "active_task_count": active_task_count
        }
    except Exception as e:
        logger.error(f"Error checking Celery health: {e}")
        return {"status": "error", "error": str(e)}

def check_disk_space() -> Dict[str, Any]:
    """Check disk space"""
    try:
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024**3)
        total_gb = disk.total / (1024**3)
        
        return {
            "status": "healthy" if free_gb > 10 else "warning",
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "usage_percent": disk.percent
        }
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return {"status": "error", "error": str(e)}

def check_memory_usage() -> Dict[str, Any]:
    """Check memory usage"""
    try:
        memory = psutil.virtual_memory()
        
        return {
            "status": "healthy" if memory.percent < 80 else "warning",
            "used_percent": memory.percent,
            "available_gb": round(memory.available / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2)
        }
    except Exception as e:
        logger.error(f"Error checking memory usage: {e}")
        return {"status": "error", "error": str(e)}

def check_cpu_usage() -> Dict[str, Any]:
    """Check CPU usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        return {
            "status": "healthy" if cpu_percent < 80 else "warning",
            "usage_percent": cpu_percent,
            "cpu_count": cpu_count
        }
    except Exception as e:
        logger.error(f"Error checking CPU usage: {e}")
        return {"status": "error", "error": str(e)}

def determine_overall_health(health_checks: Dict[str, Any]) -> str:
    """Determine overall system health"""
    critical_count = 0
    warning_count = 0
    
    for check_name, check_result in health_checks.items():
        status = check_result.get("status", "unknown")
        if status == "error":
            critical_count += 1
        elif status == "warning":
            warning_count += 1
    
    if critical_count > 0:
        return "critical"
    elif warning_count > 2:
        return "warning"
    else:
        return "healthy"

def generate_health_alerts(health_checks: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate health alerts"""
    alerts = []
    
    for check_name, check_result in health_checks.items():
        status = check_result.get("status", "unknown")
        if status in ["error", "critical"]:
            alerts.append({
                "type": "health_alert",
                "severity": "critical" if status == "error" else "warning",
                "check": check_name,
                "details": check_result,
                "timestamp": datetime.now().isoformat()
            })
    
    return alerts

# Cleanup functions
def cleanup_old_logs(cutoff_date: datetime) -> Dict[str, Any]:
    """Clean up old log files"""
    try:
        log_dir = "logs"
        deleted_files = 0
        space_freed = 0
        
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        space_freed += file_size
        
        return {
            "deleted_files": deleted_files,
            "space_freed": space_freed
        }
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        return {"error": str(e)}

def cleanup_old_reports(cutoff_date: datetime) -> Dict[str, Any]:
    """Clean up old report files"""
    try:
        report_dir = "reports"
        deleted_files = 0
        space_freed = 0
        
        if os.path.exists(report_dir):
            for filename in os.listdir(report_dir):
                file_path = os.path.join(report_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_files += 1
                        space_freed += file_size
        
        return {
            "deleted_files": deleted_files,
            "space_freed": space_freed
        }
    except Exception as e:
        logger.error(f"Error cleaning up old reports: {e}")
        return {"error": str(e)}

def cleanup_old_models(cutoff_date: datetime) -> Dict[str, Any]:
    """Clean up old model files"""
    try:
        model_dir = "models"
        deleted_files = 0
        space_freed = 0
        
        if os.path.exists(model_dir):
            for filename in os.listdir(model_dir):
                if filename.startswith("btc_model_") and filename.endswith(".h5"):
                    file_path = os.path.join(model_dir, filename)
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_date:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_files += 1
                            space_freed += file_size
        
        return {
            "deleted_files": deleted_files,
            "space_freed": space_freed
        }
    except Exception as e:
        logger.error(f"Error cleaning up old models: {e}")
        return {"error": str(e)}

def cleanup_old_backups(cutoff_date: datetime) -> Dict[str, Any]:
    """Clean up old backup files"""
    try:
        backup_dir = "backups"
        deleted_files = 0
        space_freed = 0
        
        if os.path.exists(backup_dir):
            for folder in os.listdir(backup_dir):
                folder_path = os.path.join(backup_dir, folder)
                if os.path.isdir(folder_path):
                    folder_time = datetime.fromtimestamp(os.path.getmtime(folder_path))
                    if folder_time < cutoff_date:
                        folder_size = get_folder_size(folder_path)
                        shutil.rmtree(folder_path)
                        deleted_files += 1
                        space_freed += folder_size
        
        return {
            "deleted_files": deleted_files,
            "space_freed": space_freed
        }
    except Exception as e:
        logger.error(f"Error cleaning up old backups: {e}")
        return {"error": str(e)}

def cleanup_temp_files() -> Dict[str, Any]:
    """Clean up temporary files"""
    try:
        temp_patterns = ["*.tmp", "*.temp", "*.log.tmp"]
        deleted_files = 0
        space_freed = 0
        
        for pattern in temp_patterns:
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith(pattern.split("*")[-1]):
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            deleted_files += 1
                            space_freed += file_size
                        except Exception:
                            pass
        
        return {
            "deleted_files": deleted_files,
            "space_freed": space_freed
        }
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")
        return {"error": str(e)}

def cleanup_database_old_records(cutoff_date: datetime) -> Dict[str, Any]:
    """Clean up old database records"""
    try:
        # Implementation to clean old records from database
        # Placeholder implementation
        return {
            "deleted_records": 0,
            "space_freed": 0
        }
    except Exception as e:
        logger.error(f"Error cleaning up database records: {e}")
        return {"error": str(e)}

# Backup functions
def perform_full_backup(backup_path: str) -> Dict[str, Any]:
    """Perform full database backup"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        shutil.copy2(db_path, backup_path)
        
        return {
            "status": "success",
            "backup_size": os.path.getsize(backup_path)
        }
    except Exception as e:
        logger.error(f"Error performing full backup: {e}")
        return {"status": "error", "error": str(e)}

def perform_incremental_backup(backup_path: str) -> Dict[str, Any]:
    """Perform incremental database backup"""
    try:
        # Implementation for incremental backup
        # Placeholder implementation
        return perform_full_backup(backup_path)
    except Exception as e:
        logger.error(f"Error performing incremental backup: {e}")
        return {"status": "error", "error": str(e)}

def verify_backup(backup_path: str) -> Dict[str, Any]:
    """Verify backup integrity"""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        
        conn.close()
        
        return {
            "status": "success" if integrity_result[0] == "ok" else "error",
            "integrity_check": integrity_result[0]
        }
    except Exception as e:
        logger.error(f"Error verifying backup: {e}")
        return {"status": "error", "error": str(e)}

def compress_backup(backup_path: str) -> str:
    """Compress backup file"""
    try:
        import gzip
        
        compressed_path = backup_path + ".gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        os.remove(backup_path)
        
        return compressed_path
    except Exception as e:
        logger.error(f"Error compressing backup: {e}")
        return backup_path

# Database optimization functions
def vacuum_database() -> Dict[str, Any]:
    """Vacuum database to reclaim space"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error vacuuming database: {e}")
        return {"status": "error", "error": str(e)}

def reindex_database() -> Dict[str, Any]:
    """Reindex database"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.execute("REINDEX")
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error reindexing database: {e}")
        return {"status": "error", "error": str(e)}

def analyze_database() -> Dict[str, Any]:
    """Analyze database for optimization"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.execute("ANALYZE")
        conn.close()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error analyzing database: {e}")
        return {"status": "error", "error": str(e)}

def cleanup_indexes() -> Dict[str, Any]:
    """Clean up unused indexes"""
    try:
        # Implementation to clean up unused indexes
        # Placeholder implementation
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error cleaning up indexes: {e}")
        return {"status": "error", "error": str(e)}

# Performance monitoring functions
def measure_api_response_times() -> Dict[str, Any]:
    """Measure API response times"""
    try:
        # Implementation to measure API response times
        # Placeholder implementation
        return {
            "average_response_time": 0.15,
            "p95_response_time": 0.25,
            "p99_response_time": 0.35
        }
    except Exception as e:
        logger.error(f"Error measuring API response times: {e}")
        return {"error": str(e)}

def measure_database_performance() -> Dict[str, Any]:
    """Measure database performance"""
    try:
        # Implementation to measure database performance
        # Placeholder implementation
        return {
            "average_query_time": 0.05,
            "slow_queries": 2
        }
    except Exception as e:
        logger.error(f"Error measuring database performance: {e}")
        return {"error": str(e)}

def measure_model_performance() -> Dict[str, Any]:
    """Measure model inference performance"""
    try:
        # Implementation to measure model performance
        # Placeholder implementation
        return {
            "average_inference_time": 0.1,
            "throughput": 10
        }
    except Exception as e:
        logger.error(f"Error measuring model performance: {e}")
        return {"error": str(e)}

def get_memory_usage_details() -> Dict[str, Any]:
    """Get detailed memory usage"""
    try:
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent
        }
    except Exception as e:
        logger.error(f"Error getting memory usage details: {e}")
        return {"error": str(e)}

def get_cpu_usage_details() -> Dict[str, Any]:
    """Get detailed CPU usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        return {
            "overall_percent": psutil.cpu_percent(interval=1),
            "per_core": cpu_percent,
            "core_count": psutil.cpu_count()
        }
    except Exception as e:
        logger.error(f"Error getting CPU usage details: {e}")
        return {"error": str(e)}

def get_disk_io_stats() -> Dict[str, Any]:
    """Get disk I/O statistics"""
    try:
        disk_io = psutil.disk_io_counters()
        return {
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count
        }
    except Exception as e:
        logger.error(f"Error getting disk I/O stats: {e}")
        return {"error": str(e)}

def get_network_usage_stats() -> Dict[str, Any]:
    """Get network usage statistics"""
    try:
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
    except Exception as e:
        logger.error(f"Error getting network usage stats: {e}")
        return {"error": str(e)}

# Utility functions
def get_folder_size(folder_path: str) -> int:
    """Get total size of folder"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    return total_size

def save_health_check_results(results: Dict[str, Any]) -> None:
    """Save health check results"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"health_checks/health_check_{timestamp}.json"
        os.makedirs("health_checks", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Health check results saved: {filename}")
    except Exception as e:
        logger.error(f"Error saving health check results: {e}")

def send_health_alerts(alerts: List[Dict[str, Any]]) -> None:
    """Send health alerts"""
    try:
        # Implementation to send alerts
        # This would integrate with the notification system
        for alert in alerts:
            logger.warning(f"Health alert: {alert}")
    except Exception as e:
        logger.error(f"Error sending health alerts: {e}")

def save_backup_metadata(metadata: Dict[str, Any]) -> None:
    """Save backup metadata"""
    try:
        metadata_file = "backups/backup_metadata.json"
        os.makedirs("backups", exist_ok=True)
        
        # Load existing metadata
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                existing_metadata = json.load(f)
        else:
            existing_metadata = []
        
        # Add new metadata
        existing_metadata.append(metadata)
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(existing_metadata, f, indent=2)
        
        logger.info("Backup metadata saved")
    except Exception as e:
        logger.error(f"Error saving backup metadata: {e}")

def store_performance_metrics(metrics: Dict[str, Any]) -> None:
    """Store performance metrics for trending"""
    try:
        # Implementation to store metrics for trending analysis
        # Placeholder implementation
        pass
    except Exception as e:
        logger.error(f"Error storing performance metrics: {e}")

def detect_performance_anomalies(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect performance anomalies"""
    try:
        # Implementation to detect anomalies
        # Placeholder implementation
        return []
    except Exception as e:
        logger.error(f"Error detecting performance anomalies: {e}")
        return []

def get_database_statistics() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table statistics
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        stats = {
            "table_count": len(tables),
            "tables": {}
        }
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            stats["tables"][table_name] = row_count
        
        conn.close()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return {"error": str(e)} 