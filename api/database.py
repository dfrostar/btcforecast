"""
Database Module
Provides database models and operations for persistent data storage.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import threading
from pathlib import Path
from config import get_config

class DatabaseManager:
    def __init__(self, db_path: str = "btcforecast.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'free',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    api_key TEXT UNIQUE,
                    subscription_expires TIMESTAMP
                )
            ''')
            
            # API requests audit log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    request_data TEXT,
                    response_status INTEGER,
                    response_time_ms INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Model predictions log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS predictions_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    prediction_type TEXT NOT NULL,
                    input_data TEXT,
                    prediction_result TEXT,
                    confidence_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Model training history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    r2_score REAL,
                    mae_score REAL,
                    rmse_score REAL,
                    training_time_seconds REAL,
                    model_size_kb INTEGER,
                    features_used TEXT,
                    hyperparameters TEXT
                )
            ''')
            
            # System metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    active_connections INTEGER,
                    requests_per_minute REAL
                )
            ''')
            
            # Rate limiting data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rate_limit_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    role TEXT NOT NULL,
                    requests_count INTEGER DEFAULT 0,
                    window_start TIMESTAMP,
                    window_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a SELECT query and return results as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

# Global database manager instance
db_manager = DatabaseManager()

class UserRepository:
    """Repository for user-related database operations."""
    
    @staticmethod
    def create_user(username: str, email: str, hashed_password: str, role: str = "free") -> Dict:
        """Create a new user in the database."""
        query = '''
            INSERT INTO users (username, email, hashed_password, role)
            VALUES (?, ?, ?, ?)
        '''
        db_manager.execute_update(query, (username, email, hashed_password, role))
        
        # Return the created user
        return UserRepository.get_user_by_username(username)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """Get user by username."""
        query = "SELECT * FROM users WHERE username = ?"
        results = db_manager.execute_query(query, (username,))
        return results[0] if results else None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email."""
        query = "SELECT * FROM users WHERE email = ?"
        results = db_manager.execute_query(query, (email,))
        return results[0] if results else None
    
    @staticmethod
    def get_user_by_api_key(api_key: str) -> Optional[Dict]:
        """Get user by API key."""
        query = "SELECT * FROM users WHERE api_key = ?"
        results = db_manager.execute_query(query, (api_key,))
        return results[0] if results else None
    
    @staticmethod
    def update_last_login(username: str):
        """Update user's last login timestamp."""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?"
        db_manager.execute_update(query, (username,))
    
    @staticmethod
    def update_api_key(username: str, api_key: str):
        """Update user's API key."""
        query = "UPDATE users SET api_key = ? WHERE username = ?"
        db_manager.execute_update(query, (api_key, username))
    
    @staticmethod
    def revoke_api_key(username: str):
        """Revoke user's API key."""
        query = "UPDATE users SET api_key = NULL WHERE username = ?"
        db_manager.execute_update(query, (username,))
    
    @staticmethod
    def update_user_role(username: str, role: str):
        """Update user's role."""
        query = "UPDATE users SET role = ? WHERE username = ?"
        db_manager.execute_update(query, (role, username))
    
    @staticmethod
    def deactivate_user(username: str):
        """Deactivate a user."""
        query = "UPDATE users SET is_active = 0 WHERE username = ?"
        db_manager.execute_update(query, (username,))
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """Get all users (admin only)."""
        query = "SELECT id, username, email, role, is_active, created_at, last_login FROM users"
        return db_manager.execute_query(query)

class AuditRepository:
    """Repository for audit logging operations."""
    
    @staticmethod
    def log_api_request(user_id: Optional[int], endpoint: str, method: str, 
                       ip_address: str, user_agent: str, request_data: Dict,
                       response_status: int, response_time_ms: int):
        """Log an API request for audit purposes."""
        query = '''
            INSERT INTO api_audit_log 
            (user_id, endpoint, method, ip_address, user_agent, request_data, 
             response_status, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        request_data_json = json.dumps(request_data) if request_data else None
        db_manager.execute_update(query, (
            user_id, endpoint, method, ip_address, user_agent, 
            request_data_json, response_status, response_time_ms
        ))
    
    @staticmethod
    def get_user_audit_log(user_id: int, limit: int = 100) -> List[Dict]:
        """Get audit log for a specific user."""
        query = '''
            SELECT * FROM api_audit_log 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        return db_manager.execute_query(query, (user_id, limit))
    
    @staticmethod
    def get_system_audit_log(limit: int = 1000) -> List[Dict]:
        """Get system-wide audit log (admin only)."""
        query = '''
            SELECT al.*, u.username 
            FROM api_audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.timestamp DESC 
            LIMIT ?
        '''
        return db_manager.execute_query(query, (limit,))

class PredictionRepository:
    """Repository for prediction logging operations."""
    
    @staticmethod
    def log_prediction(user_id: Optional[int], prediction_type: str, 
                      input_data: Dict, prediction_result: Dict, 
                      confidence_score: Optional[float] = None):
        """Log a prediction for analysis and monitoring."""
        query = '''
            INSERT INTO predictions_log 
            (user_id, prediction_type, input_data, prediction_result, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        '''
        input_data_json = json.dumps(input_data) if input_data else None
        prediction_result_json = json.dumps(prediction_result) if prediction_result else None
        
        db_manager.execute_update(query, (
            user_id, prediction_type, input_data_json, 
            prediction_result_json, confidence_score
        ))
    
    @staticmethod
    def get_user_predictions(user_id: int, limit: int = 100) -> List[Dict]:
        """Get prediction history for a user."""
        query = '''
            SELECT * FROM predictions_log 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        return db_manager.execute_query(query, (user_id, limit))
    
    @staticmethod
    def get_prediction_analytics(days: int = 30) -> Dict:
        """Get prediction analytics for the specified period."""
        query = '''
            SELECT 
                COUNT(*) as total_predictions,
                AVG(confidence_score) as avg_confidence,
                prediction_type,
                DATE(timestamp) as prediction_date
            FROM predictions_log 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY prediction_type, DATE(timestamp)
            ORDER BY prediction_date DESC
        '''.format(days)
        
        return db_manager.execute_query(query)

class ModelRepository:
    """Repository for model training history."""
    
    @staticmethod
    def log_training_session(model_version: str, r2_score: float, mae_score: float,
                           rmse_score: float, training_time_seconds: float,
                           model_size_kb: int, features_used: List[str],
                           hyperparameters: Dict):
        """Log a model training session."""
        query = '''
            INSERT INTO model_training_history 
            (model_version, r2_score, mae_score, rmse_score, training_time_seconds,
             model_size_kb, features_used, hyperparameters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        features_json = json.dumps(features_used)
        hyperparams_json = json.dumps(hyperparameters)
        
        db_manager.execute_update(query, (
            model_version, r2_score, mae_score, rmse_score, 
            training_time_seconds, model_size_kb, features_json, hyperparams_json
        ))
    
    @staticmethod
    def get_training_history(limit: int = 50) -> List[Dict]:
        """Get model training history."""
        query = '''
            SELECT * FROM model_training_history 
            ORDER BY training_date DESC 
            LIMIT ?
        '''
        return db_manager.execute_query(query, (limit,))
    
    @staticmethod
    def get_best_model() -> Optional[Dict]:
        """Get the best performing model based on R² score."""
        query = '''
            SELECT * FROM model_training_history 
            ORDER BY r2_score DESC 
            LIMIT 1
        '''
        results = db_manager.execute_query(query)
        return results[0] if results else None

class MetricsRepository:
    """Repository for system metrics."""
    
    @staticmethod
    def log_system_metrics(cpu_usage: float, memory_usage: float, 
                          disk_usage: float, active_connections: int,
                          requests_per_minute: float):
        """Log system metrics."""
        query = '''
            INSERT INTO system_metrics 
            (cpu_usage, memory_usage, disk_usage, active_connections, requests_per_minute)
            VALUES (?, ?, ?, ?, ?)
        '''
        db_manager.execute_update(query, (
            cpu_usage, memory_usage, disk_usage, 
            active_connections, requests_per_minute
        ))
    
    @staticmethod
    def get_recent_metrics(hours: int = 24) -> List[Dict]:
        """Get recent system metrics."""
        query = '''
            SELECT * FROM system_metrics 
            WHERE timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(hours)
        
        return db_manager.execute_query(query)
    
    @staticmethod
    def get_metrics_summary(hours: int = 24) -> Dict:
        """Get metrics summary for the specified period."""
        query = '''
            SELECT 
                AVG(cpu_usage) as avg_cpu,
                AVG(memory_usage) as avg_memory,
                AVG(disk_usage) as avg_disk,
                MAX(active_connections) as max_connections,
                AVG(requests_per_minute) as avg_requests_per_minute
            FROM system_metrics 
            WHERE timestamp >= datetime('now', '-{} hours')
        '''.format(hours)
        
        results = db_manager.execute_query(query)
        return results[0] if results else {}

# Database utilities
def backup_database(backup_path: str = None):
    """Create a backup of the database."""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_btcforecast_{timestamp}.db"
    
    import shutil
    shutil.copy2(db_manager.db_path, backup_path)
    return backup_path

def cleanup_old_data(days_to_keep: int = 90):
    """Clean up old audit logs and metrics data."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Clean up old audit logs
    query = "DELETE FROM api_audit_log WHERE timestamp < ?"
    db_manager.execute_update(query, (cutoff_date,))
    
    # Clean up old metrics (keep more recent data)
    metrics_cutoff = datetime.now() - timedelta(days=30)
    query = "DELETE FROM system_metrics WHERE timestamp < ?"
    db_manager.execute_update(query, (metrics_cutoff,))
    
    # Clean up old predictions (keep more recent data)
    predictions_cutoff = datetime.now() - timedelta(days=60)
    query = "DELETE FROM predictions_log WHERE timestamp < ?"
    db_manager.execute_update(query, (predictions_cutoff,)) 