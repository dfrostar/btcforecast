#!/usr/bin/env python3
"""
Direct API test for registration and login
"""

import requests
import json
import time

def test_registration():
    """Test user registration directly."""
    url = "http://127.0.0.1:8001/auth/register"
    
    test_user = {
        "username": f"testuser_{int(time.time())}",
        "email": f"testuser_{int(time.time())}@example.com",
        "password": "testpassword123",
        "role": "free"
    }
    
    print(f"Testing registration for: {test_user['username']}")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(test_user, indent=2)}")
    
    try:
        response = requests.post(url, json=test_user, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Registration successful!")
            return test_user
        else:
            print("❌ Registration failed!")
            return None
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

def test_login(username, password):
    """Test user login directly."""
    url = "http://127.0.0.1:8001/auth/login"
    
    login_data = {
        "username": username,
        "password": password
    }
    
    print(f"\nTesting login for: {username}")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(login_data, indent=2)}")
    
    try:
        response = requests.post(url, json=login_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            return response.json()
        else:
            print("❌ Login failed!")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def main():
    """Run the tests."""
    print("🔍 Direct API Test")
    print("=" * 50)
    
    # Test registration
    test_user = test_registration()
    
    if test_user:
        # Test login
        token_data = test_login(test_user["username"], test_user["password"])
        
        if token_data:
            print("\n🎉 Both registration and login are working!")
        else:
            print("\n⚠️ Registration worked but login failed.")
    else:
        print("\n❌ Registration failed.")

if __name__ == "__main__":
    main() 