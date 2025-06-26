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
                    subscription_expires TIMESTAMP,
                    stripe_customer_id TEXT
                )
            ''')
            
            # Subscriptions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_subscription_id TEXT UNIQUE,
                    tier_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_period_start TIMESTAMP,
                    current_period_end TIMESTAMP,
                    cancel_at_period_end BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Usage tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    api_calls INTEGER DEFAULT 0,
                    predictions INTEGER DEFAULT 0,
                    portfolios_count INTEGER DEFAULT 0,
                    storage_used_mb REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, date)
                )
            ''')
            
            # Billing history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS billing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_invoice_id TEXT UNIQUE,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    status TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
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
    def get_user_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = ?"
        results = db_manager.execute_query(query, (user_id,))
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
        """Deactivate a user account."""
        query = "UPDATE users SET is_active = 0 WHERE username = ?"
        db_manager.execute_update(query, (username,))
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """Get all users from the database."""
        return db_manager.execute_query("SELECT * FROM users ORDER BY created_at DESC")
    
    @staticmethod
    def get_user_count() -> int:
        """Get total number of users in the database."""
        result = db_manager.execute_query("SELECT COUNT(*) as count FROM users")
        return result[0]['count'] if result else 0
    
    @staticmethod
    def update_stripe_customer_id(user_id: int, stripe_customer_id: str):
        """Update user's Stripe customer ID."""
        query = "UPDATE users SET stripe_customer_id = ? WHERE id = ?"
        db_manager.execute_update(query, (stripe_customer_id, user_id))

class SubscriptionRepository:
    """Repository for subscription-related database operations."""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def create_subscription(self, user_id: int, stripe_subscription_id: str, 
                          tier_name: str, status: str, current_period_start: datetime,
                          current_period_end: datetime, cancel_at_period_end: bool = False) -> Dict:
        """Create a new subscription."""
        query = '''
            INSERT INTO subscriptions 
            (user_id, stripe_subscription_id, tier_name, status, current_period_start, 
             current_period_end, cancel_at_period_end)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        db_manager.execute_update(query, (
            user_id, stripe_subscription_id, tier_name, status, 
            current_period_start, current_period_end, cancel_at_period_end
        ))
        
        # Return the created subscription
        return self.get_subscription_by_stripe_id(stripe_subscription_id)
    
    def get_active_subscription(self, user_id: int) -> Optional[Dict]:
        """Get user's active subscription."""
        query = '''
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        '''
        results = db_manager.execute_query(query, (user_id,))
        return results[0] if results else None
    
    def get_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict]:
        """Get subscription by Stripe subscription ID."""
        query = "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?"
        results = db_manager.execute_query(query, (stripe_subscription_id,))
        return results[0] if results else None
    
    def update_subscription(self, subscription_id: int, **kwargs) -> bool:
        """Update subscription fields."""
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        params.append(subscription_id)
        
        query = f"UPDATE subscriptions SET {', '.join(set_clauses)} WHERE id = ?"
        return db_manager.execute_update(query, tuple(params)) > 0
    
    def update_subscription_from_stripe(self, stripe_subscription: Dict) -> bool:
        """Update subscription from Stripe webhook data."""
        subscription = self.get_subscription_by_stripe_id(stripe_subscription["id"])
        if not subscription:
            return False
        
        return self.update_subscription(
            subscription["id"],
            status=stripe_subscription["status"],
            current_period_start=datetime.fromtimestamp(stripe_subscription["current_period_start"]),
            current_period_end=datetime.fromtimestamp(stripe_subscription["current_period_end"]),
            cancel_at_period_end=stripe_subscription.get("cancel_at_period_end", False)
        )
    
    def cancel_subscription(self, stripe_subscription_id: str) -> bool:
        """Cancel a subscription."""
        return self.update_subscription_from_stripe({
            "id": stripe_subscription_id,
            "status": "canceled",
            "current_period_start": int(datetime.now().timestamp()),
            "current_period_end": int(datetime.now().timestamp()),
            "cancel_at_period_end": True
        })
    
    def get_all_subscriptions(self) -> List[Dict]:
        """Get all subscriptions."""
        query = "SELECT * FROM subscriptions ORDER BY created_at DESC"
        return db_manager.execute_query(query)
    
    def get_usage_stats(self, user_id: int) -> Dict:
        """Get user's usage statistics."""
        today = datetime.now().date()
        month_start = datetime.now().replace(day=1).date()
        
        # Get today's usage
        today_query = "SELECT * FROM usage_tracking WHERE user_id = ? AND date = ?"
        today_results = db_manager.execute_query(today_query, (user_id, today))
        today_usage = today_results[0] if today_results else {
            "api_calls": 0,
            "predictions": 0,
            "portfolios_count": 0,
            "storage_used_mb": 0
        }
        
        # Get this month's usage
        month_query = '''
            SELECT 
                SUM(api_calls) as api_calls,
                SUM(predictions) as predictions,
                MAX(portfolios_count) as portfolios_count,
                MAX(storage_used_mb) as storage_used_mb
            FROM usage_tracking 
            WHERE user_id = ? AND date >= ?
        '''
        month_results = db_manager.execute_query(month_query, (user_id, month_start))
        month_usage = month_results[0] if month_results else {
            "api_calls": 0,
            "predictions": 0,
            "portfolios_count": 0,
            "storage_used_mb": 0
        }
        
        return {
            "api_calls_today": today_usage.get("api_calls", 0),
            "api_calls_this_month": month_usage.get("api_calls", 0),
            "predictions_today": today_usage.get("predictions", 0),
            "predictions_this_month": month_usage.get("predictions", 0),
            "portfolios_count": today_usage.get("portfolios_count", 0),
            "storage_used_mb": today_usage.get("storage_used_mb", 0)
        }
    
    def increment_usage(self, user_id: int, usage_type: str, amount: int = 1):
        """Increment usage statistics for a user."""
        today = datetime.now().date()
        
        # Insert or update today's usage
        query = '''
            INSERT INTO usage_tracking (user_id, date, api_calls, predictions, portfolios_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                api_calls = api_calls + ?,
                predictions = predictions + ?,
                portfolios_count = portfolios_count + ?
        '''
        
        if usage_type == "api_calls":
            db_manager.execute_update(query, (user_id, today, amount, 0, 0, amount, 0, 0))
        elif usage_type == "predictions":
            db_manager.execute_update(query, (user_id, today, 0, amount, 0, 0, amount, 0))
        elif usage_type == "portfolios":
            db_manager.execute_update(query, (user_id, today, 0, 0, amount, 0, 0, amount))
    
    def handle_successful_payment(self, invoice: Dict):
        """Handle successful payment from Stripe webhook."""
        user_id = self._get_user_id_from_invoice(invoice)
        if not user_id:
            return
        
        query = '''
            INSERT INTO billing_history 
            (user_id, stripe_invoice_id, amount, currency, status, description)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        db_manager.execute_update(query, (
            user_id,
            invoice["id"],
            invoice["amount_paid"] / 100,  # Convert from cents
            invoice["currency"].upper(),
            invoice["status"],
            invoice.get("description", f"Invoice for {invoice.get('period_start')}")
        ))
    
    def handle_failed_payment(self, invoice: Dict):
        """Handle failed payment from Stripe webhook."""
        user_id = self._get_user_id_from_invoice(invoice)
        if not user_id:
            return
        
        # Log failed payment
        query = '''
            INSERT INTO billing_history 
            (user_id, stripe_invoice_id, amount, currency, status, description)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        db_manager.execute_update(query, (
            user_id,
            invoice["id"],
            invoice["amount_due"] / 100,  # Convert from cents
            invoice["currency"].upper(),
            "failed",
            f"Failed payment: {invoice.get('last_payment_error', {}).get('message', 'Unknown error')}"
        ))
    
    def _get_user_id_from_invoice(self, invoice: Dict) -> Optional[int]:
        """Extract user ID from Stripe invoice."""
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return None
        
        subscription = self.get_subscription_by_stripe_id(subscription_id)
        return subscription["user_id"] if subscription else None
    
    def get_subscription_stats(self) -> Dict:
        """Get subscription statistics for admin dashboard."""
        # Total subscriptions
        total_query = "SELECT COUNT(*) as count FROM subscriptions"
        total_results = db_manager.execute_query(total_query)
        total_subscriptions = total_results[0]["count"] if total_results else 0
        
        # Active subscriptions
        active_query = "SELECT COUNT(*) as count FROM subscriptions WHERE status = 'active'"
        active_results = db_manager.execute_query(active_query)
        active_subscriptions = active_results[0]["count"] if active_results else 0
        
        # Subscriptions by tier
        tier_query = '''
            SELECT tier_name, COUNT(*) as count 
            FROM subscriptions 
            WHERE status = 'active' 
            GROUP BY tier_name
        '''
        tier_results = db_manager.execute_query(tier_query)
        subscriptions_by_tier = {row["tier_name"]: row["count"] for row in tier_results}
        
        # Calculate churn rate (simplified)
        churn_query = '''
            SELECT COUNT(*) as count 
            FROM subscriptions 
            WHERE status = 'canceled' 
            AND updated_at >= datetime('now', '-30 days')
        '''
        churn_results = db_manager.execute_query(churn_query)
        churned_subscriptions = churn_results[0]["count"] if churn_results else 0
        
        churn_rate = (churned_subscriptions / max(active_subscriptions, 1)) * 100
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "monthly_revenue": 0,  # Would need to calculate from billing history
            "subscriptions_by_tier": subscriptions_by_tier,
            "churn_rate": churn_rate,
            "average_revenue_per_user": 0  # Would need to calculate from billing history
        }

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

def get_db():
    """Dependency for FastAPI to provide a database manager instance."""
    try:
        yield db_manager
    finally:
        pass  # No explicit close needed for db_manager 