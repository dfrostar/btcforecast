#!/usr/bin/env python3
"""
Simple API test to isolate startup issues
"""

import requests
import json

def test_basic_endpoints():
    """Test basic API endpoints without authentication."""
    base_url = "http://127.0.0.1:8000"
    
    print("🔍 Testing Basic API Endpoints")
    print("=" * 40)
    
    # Test root endpoint
    try:
        print("Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Root endpoint working")
            print(f"Response: {response.text[:200]}...")
        else:
            print(f"❌ Root endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        print("\nTesting health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            print(f"Response: {response.text}")
        else:
            print(f"❌ Health endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test docs endpoint
    try:
        print("\nTesting docs endpoint...")
        response = requests.get(f"{base_url}/docs", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Docs endpoint working")
        else:
            print(f"❌ Docs endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Docs endpoint error: {e}")

def test_auth_endpoints():
    """Test authentication endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    print("\n🔐 Testing Authentication Endpoints")
    print("=" * 40)
    
    # Test registration endpoint (should return 422 for missing data)
    try:
        print("Testing registration endpoint...")
        response = requests.post(f"{base_url}/auth/register", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            print("✅ Registration endpoint working (expected validation error)")
        elif response.status_code == 200:
            print("✅ Registration endpoint working")
        else:
            print(f"❌ Registration endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Registration endpoint error: {e}")
    
    # Test login endpoint (should return 422 for missing data)
    try:
        print("\nTesting login endpoint...")
        response = requests.post(f"{base_url}/auth/login", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 422:
            print("✅ Login endpoint working (expected validation error)")
        elif response.status_code == 200:
            print("✅ Login endpoint working")
        else:
            print(f"❌ Login endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Login endpoint error: {e}")

def main():
    """Run all tests."""
    print("🚀 Simple API Test")
    print("=" * 60)
    
    test_basic_endpoints()
    test_auth_endpoints()
    
    print("\n" + "=" * 60)
    print("📊 Test Complete")

if __name__ == "__main__":
    main() 