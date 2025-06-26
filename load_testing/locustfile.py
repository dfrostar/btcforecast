"""
Load Testing Script for BTC Forecast API
Uses Locust to simulate realistic user behavior and test performance.
"""

import time
import random
import json
from locust import HttpUser, task, between, events
from typing import Dict, Any

class BTCForecastUser(HttpUser):
    """Simulates a user interacting with the BTC Forecast application"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Initialize user session"""
        self.user_data = {
            "username": f"testuser_{random.randint(1000, 9999)}",
            "email": f"testuser_{random.randint(1000, 9999)}@example.com",
            "password": "testpassword123"
        }
        self.token = None
        self.user_id = None
        
        # Register user
        try:
            response = self.client.post("/auth/register", json=self.user_data)
            if response.status_code == 200:
                print(f"Registered user: {self.user_data['username']}")
            else:
                print(f"Failed to register user: {response.status_code}")
        except Exception as e:
            print(f"Error registering user: {e}")
        
        # Login user
        try:
            login_data = {
                "username": self.user_data["username"],
                "password": self.user_data["password"]
            }
            response = self.client.post("/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")
                print(f"Logged in user: {self.user_data['username']}")
            else:
                print(f"Failed to login user: {response.status_code}")
        except Exception as e:
            print(f"Error logging in user: {e}")
    
    @task(3)
    def get_health(self):
        """Check API health"""
        self.client.get("/health")
    
    @task(2)
    def get_status(self):
        """Get system status"""
        self.client.get("/status")
    
    @task(1)
    def get_predictions(self):
        """Get BTC predictions"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/predictions", headers=headers)
        else:
            self.client.get("/predictions")
    
    @task(1)
    def get_market_data(self):
        """Get market data"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/market-data", headers=headers)
        else:
            self.client.get("/market-data")
    
    @task(1)
    def get_portfolio(self):
        """Get user portfolio"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/portfolio", headers=headers)
    
    @task(1)
    def create_prediction(self):
        """Create a new prediction"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            prediction_data = {
                "symbol": "BTC-USD",
                "timeframe": "1d",
                "horizon": 7
            }
            self.client.post("/predictions", json=prediction_data, headers=headers)
    
    @task(1)
    def get_user_profile(self):
        """Get user profile"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/user/profile", headers=headers)
    
    @task(1)
    def update_user_profile(self):
        """Update user profile"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            profile_data = {
                "email": f"updated_{self.user_data['email']}",
                "preferences": {
                    "default_timeframe": "1d",
                    "default_horizon": 7
                }
            }
            self.client.put("/user/profile", json=profile_data, headers=headers)

class AdminUser(HttpUser):
    """Simulates an admin user with elevated privileges"""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight for admin users
    
    def on_start(self):
        """Initialize admin session"""
        self.admin_data = {
            "username": "admin",
            "password": "admin123"
        }
        self.token = None
        
        # Login as admin
        try:
            response = self.client.post("/auth/login", json=self.admin_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print("Logged in as admin")
            else:
                print(f"Failed to login as admin: {response.status_code}")
        except Exception as e:
            print(f"Error logging in as admin: {e}")
    
    @task(2)
    def get_system_metrics(self):
        """Get system metrics"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/admin/metrics", headers=headers)
    
    @task(1)
    def get_all_users(self):
        """Get all users"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/admin/users", headers=headers)
    
    @task(1)
    def get_audit_log(self):
        """Get audit log"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/admin/audit-log", headers=headers)
    
    @task(1)
    def get_system_status(self):
        """Get detailed system status"""
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/admin/system-status", headers=headers)

# Event handlers for monitoring
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Log request details for monitoring"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    else:
        print(f"Request: {name} - {response_time}ms - {response.status_code}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Load test starting...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("Load test completed.")

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "response_time_p95": 500,  # 95th percentile should be under 500ms
    "response_time_p99": 1000,  # 99th percentile should be under 1s
    "error_rate": 0.01,  # Error rate should be under 1%
    "throughput": 100,  # Should handle at least 100 requests/second
}

def validate_performance(stats):
    """Validate performance against thresholds"""
    results = {}
    
    # Check response time percentiles
    if stats.get("response_time_p95", 0) > PERFORMANCE_THRESHOLDS["response_time_p95"]:
        results["response_time_p95"] = "FAIL"
    else:
        results["response_time_p95"] = "PASS"
    
    if stats.get("response_time_p99", 0) > PERFORMANCE_THRESHOLDS["response_time_p99"]:
        results["response_time_p99"] = "FAIL"
    else:
        results["response_time_p99"] = "PASS"
    
    # Check error rate
    error_rate = stats.get("error_rate", 0)
    if error_rate > PERFORMANCE_THRESHOLDS["error_rate"]:
        results["error_rate"] = "FAIL"
    else:
        results["error_rate"] = "PASS"
    
    # Check throughput
    throughput = stats.get("throughput", 0)
    if throughput < PERFORMANCE_THRESHOLDS["throughput"]:
        results["throughput"] = "FAIL"
    else:
        results["throughput"] = "PASS"
    
    return results 