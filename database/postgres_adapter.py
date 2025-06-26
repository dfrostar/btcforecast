"""
PostgreSQL Database Adapter
Provides PostgreSQL database models and operations with connection pooling.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection
import logging
from config import get_config

logger = logging.getLogger(__name__)

class PostgreSQLManager:
    """PostgreSQL database manager with connection pooling"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql://btcforecast_user:btcforecast_password@localhost:5432/btcforecast')
        self.pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the connection pool"""
        if self.pool is None:
            async with self._lock:
                if self.pool is None:
                    try:
                        self.pool = await asyncpg.create_pool(
                            self.database_url,
                            min_size=5,
                            max_size=20,
                            command_timeout=60,
                            server_settings={
                                'application_name': 'btcforecast',
                                'timezone': 'UTC'
                            }
                        )
                        logger.info("PostgreSQL connection pool initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize PostgreSQL pool: {e}")
                        raise
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            await self.initialize()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute a SELECT query and return results as list of dicts"""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_update(self, query: str, *args) -> str:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        async with self.get_connection() as conn:
            result = await conn.execute(query, *args)
            return result
    
    async def execute_insert(self, query: str, *args) -> int:
        """Execute an INSERT query and return the inserted ID"""
        async with self.get_connection() as conn:
            result = await conn.fetchval(query, *args)
            return result

# Global PostgreSQL manager instance
postgres_manager = PostgreSQLManager()

class AsyncUserRepository:
    """Async user repository for PostgreSQL"""
    
    @staticmethod
    async def create_user(username: str, email: str, hashed_password: str, role: str = "free") -> Dict:
        """Create a new user"""
        query = """
            INSERT INTO users (username, email, hashed_password, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id, username, email, role, is_active, created_at
        """
        try:
            user_id = await postgres_manager.execute_insert(query, username, email, hashed_password, role)
            return await AsyncUserRepository.get_user_by_id(user_id)
        except asyncpg.UniqueViolationError:
            raise ValueError("Username or email already exists")
    
    @staticmethod
    async def get_user_by_username(username: str) -> Optional[Dict]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = $1"
        results = await postgres_manager.execute_query(query, username)
        return results[0] if results else None
    
    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = $1"
        results = await postgres_manager.execute_query(query, email)
        return results[0] if results else None
    
    @staticmethod
    async def get_user_by_api_key(api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        query = "SELECT * FROM users WHERE api_key = $1"
        results = await postgres_manager.execute_query(query, api_key)
        return results[0] if results else None
    
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = $1"
        results = await postgres_manager.execute_query(query, user_id)
        return results[0] if results else None
    
    @staticmethod
    async def update_last_login(username: str):
        """Update user's last login timestamp"""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = $1"
        await postgres_manager.execute_update(query, username)
    
    @staticmethod
    async def update_api_key(username: str, api_key: str):
        """Update user's API key"""
        query = "UPDATE users SET api_key = $2 WHERE username = $1"
        await postgres_manager.execute_update(query, username, api_key)
    
    @staticmethod
    async def revoke_api_key(username: str):
        """Revoke user's API key"""
        query = "UPDATE users SET api_key = NULL WHERE username = $1"
        await postgres_manager.execute_update(query, username)
    
    @staticmethod
    async def update_user_role(username: str, role: str):
        """Update user's role"""
        query = "UPDATE users SET role = $2 WHERE username = $1"
        await postgres_manager.execute_update(query, username, role)
    
    @staticmethod
    async def deactivate_user(username: str):
        """Deactivate user"""
        query = "UPDATE users SET is_active = false WHERE username = $1"
        await postgres_manager.execute_update(query, username)
    
    @staticmethod
    async def get_all_users() -> List[Dict]:
        """Get all users"""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        return await postgres_manager.execute_query(query)
    
    @staticmethod
    async def get_user_count() -> int:
        """Get total user count"""
        query = "SELECT COUNT(*) as count FROM users"
        results = await postgres_manager.execute_query(query)
        return results[0]['count'] if results else 0

class AsyncSubscriptionRepository:
    """Async subscription repository for PostgreSQL"""
    
    @staticmethod
    async def create_subscription(user_id: int, stripe_subscription_id: str, 
                                tier_name: str, status: str, current_period_start: datetime,
                                current_period_end: datetime, cancel_at_period_end: bool = False) -> Dict:
        """Create a new subscription"""
        query = """
            INSERT INTO subscriptions (user_id, stripe_subscription_id, tier_name, status, 
                                     current_period_start, current_period_end, cancel_at_period_end)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        try:
            subscription_id = await postgres_manager.execute_insert(query, user_id, stripe_subscription_id, 
                                                                  tier_name, status, current_period_start, 
                                                                  current_period_end, cancel_at_period_end)
            return await AsyncSubscriptionRepository.get_subscription_by_id(subscription_id)
        except asyncpg.UniqueViolationError:
            raise ValueError("Subscription already exists")
    
    @staticmethod
    async def get_active_subscription(user_id: int) -> Optional[Dict]:
        """Get user's active subscription"""
        query = """
            SELECT * FROM subscriptions 
            WHERE user_id = $1 AND status = 'active' 
            ORDER BY created_at DESC LIMIT 1
        """
        results = await postgres_manager.execute_query(query, user_id)
        return results[0] if results else None
    
    @staticmethod
    async def get_subscription_by_stripe_id(stripe_subscription_id: str) -> Optional[Dict]:
        """Get subscription by Stripe ID"""
        query = "SELECT * FROM subscriptions WHERE stripe_subscription_id = $1"
        results = await postgres_manager.execute_query(query, stripe_subscription_id)
        return results[0] if results else None
    
    @staticmethod
    async def get_subscription_by_id(subscription_id: int) -> Optional[Dict]:
        """Get subscription by ID"""
        query = "SELECT * FROM subscriptions WHERE id = $1"
        results = await postgres_manager.execute_query(query, subscription_id)
        return results[0] if results else None
    
    @staticmethod
    async def update_subscription(subscription_id: int, **kwargs) -> bool:
        """Update subscription fields"""
        if not kwargs:
            return False
        
        set_clauses = []
        values = []
        param_count = 1
        
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = ${param_count}")
            values.append(value)
            param_count += 1
        
        query = f"UPDATE subscriptions SET {', '.join(set_clauses)} WHERE id = ${param_count}"
        values.append(subscription_id)
        
        result = await postgres_manager.execute_update(query, *values)
        return "UPDATE" in result

class AsyncAuditRepository:
    """Async audit repository for PostgreSQL"""
    
    @staticmethod
    async def log_api_request(user_id: Optional[int], endpoint: str, method: str, 
                             ip_address: str, user_agent: str, request_data: Dict,
                             response_status: int, response_time_ms: int):
        """Log API request"""
        query = """
            INSERT INTO api_audit_log (user_id, endpoint, method, ip_address, user_agent, 
                                     request_data, response_status, response_time_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        await postgres_manager.execute_update(query, user_id, endpoint, method, ip_address, 
                                            user_agent, json.dumps(request_data), response_status, response_time_ms)
    
    @staticmethod
    async def get_user_audit_log(user_id: int, limit: int = 100) -> List[Dict]:
        """Get user's audit log"""
        query = """
            SELECT * FROM api_audit_log 
            WHERE user_id = $1 
            ORDER BY timestamp DESC 
            LIMIT $2
        """
        return await postgres_manager.execute_query(query, user_id, limit)
    
    @staticmethod
    async def get_system_audit_log(limit: int = 1000) -> List[Dict]:
        """Get system audit log"""
        query = """
            SELECT * FROM api_audit_log 
            ORDER BY timestamp DESC 
            LIMIT $1
        """
        return await postgres_manager.execute_query(query, limit)

class AsyncMetricsRepository:
    """Async metrics repository for PostgreSQL"""
    
    @staticmethod
    async def log_system_metrics(cpu_usage: float, memory_usage: float, 
                                disk_usage: float, active_connections: int,
                                requests_per_minute: float):
        """Log system metrics"""
        query = """
            INSERT INTO system_metrics (cpu_usage, memory_usage, disk_usage, 
                                      active_connections, requests_per_minute)
            VALUES ($1, $2, $3, $4, $5)
        """
        await postgres_manager.execute_update(query, cpu_usage, memory_usage, disk_usage, 
                                            active_connections, requests_per_minute)
    
    @staticmethod
    async def get_recent_metrics(hours: int = 24) -> List[Dict]:
        """Get recent system metrics"""
        query = """
            SELECT * FROM system_metrics 
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour' * $1
            ORDER BY timestamp DESC
        """
        return await postgres_manager.execute_query(query, hours)
    
    @staticmethod
    async def get_metrics_summary(hours: int = 24) -> Dict:
        """Get metrics summary"""
        query = """
            SELECT 
                AVG(cpu_usage) as avg_cpu,
                AVG(memory_usage) as avg_memory,
                AVG(disk_usage) as avg_disk,
                MAX(active_connections) as max_connections,
                AVG(requests_per_minute) as avg_requests
            FROM system_metrics 
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour' * $1
        """
        results = await postgres_manager.execute_query(query, hours)
        return results[0] if results else {}

# Initialize database connection
async def init_database():
    """Initialize the database connection"""
    await postgres_manager.initialize()

# Cleanup database connection
async def cleanup_database():
    """Cleanup the database connection"""
    await postgres_manager.close()

# Get database manager
def get_postgres_manager() -> PostgreSQLManager:
    """Get the PostgreSQL manager instance"""
    return postgres_manager 