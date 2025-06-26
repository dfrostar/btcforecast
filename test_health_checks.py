#!/usr/bin/env python3
"""
Test script for health check endpoints
"""

import requests
import json
import time

def test_health_endpoints():
    """Test all health check endpoints."""
    base_url = "http://127.0.0.1:8001"
    
    print("🏥 Testing Health Check Endpoints")
    print("=" * 50)
    
    # Test simple health check
    print("\n1. Testing simple health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test detailed health check
    print("\n2. Testing detailed health check...")
    try:
        response = requests.get(f"{base_url}/health/detailed", timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Detailed health check passed")
            print(f"Overall status: {data.get('status', 'unknown')}")
            print(f"Uptime: {data.get('uptime', 0):.2f} seconds")
            print(f"Number of checks: {len(data.get('checks', []))}")
            
            # Show individual check results
            for check in data.get('checks', []):
                status_emoji = "✅" if check['status'] == 'healthy' else "⚠️" if check['status'] == 'degraded' else "❌"
                print(f"  {status_emoji} {check['name']}: {check['status']} - {check['message']}")
        else:
            print(f"❌ Detailed health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Detailed health check error: {e}")
    
    # Test system status
    print("\n3. Testing system status...")
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System status: {data.get('status', 'unknown')}")
            if 'system' in data:
                system = data['system']
                print(f"  CPU: {system.get('cpu_percent', 0):.1f}%")
                print(f"  Memory: {system.get('memory_percent', 0):.1f}%")
                print(f"  Disk: {system.get('disk_percent', 0):.1f}%")
            if 'database' in data:
                db = data['database']
                print(f"  Database: {db.get('status', 'unknown')}")
                print(f"  Users: {db.get('user_count', 0)}")
        else:
            print(f"❌ System status failed: {response.text}")
    except Exception as e:
        print(f"❌ System status error: {e}")
    
    # Test root endpoint
    print("\n4. Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint: {data.get('message', 'unknown')}")
            print(f"Version: {data.get('version', 'unknown')}")
            print(f"Status: {data.get('status', 'unknown')}")
        else:
            print(f"❌ Root endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")

if __name__ == "__main__":
    test_health_endpoints() 