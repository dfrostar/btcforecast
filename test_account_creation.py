#!/usr/bin/env python3
"""
Test script for account creation functionality
"""

import requests
import json
import time

def test_api_health():
    """Test if the API is running and healthy."""
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and healthy")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API is not running (ConnectionError)")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_account_registration():
    """Test account registration functionality."""
    try:
        # Test data
        test_user = {
            "username": f"testuser_{int(time.time())}",
            "email": f"testuser_{int(time.time())}@example.com",
            "password": "testpassword123",
            "role": "free"
        }
        
        print(f"Testing registration for user: {test_user['username']}")
        
        response = requests.post(
            "http://127.0.0.1:8001/auth/register",
            json=test_user,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Account created successfully!")
            print(f"   Username: {user_data.get('username')}")
            print(f"   Email: {user_data.get('email')}")
            print(f"   Role: {user_data.get('role')}")
            return True, test_user
        else:
            print(f"❌ Registration failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API for registration test")
        return False, None
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
        return False, None

def test_account_login(username, password):
    """Test account login functionality."""
    try:
        print(f"Testing login for user: {username}")
        
        login_data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(
            "http://127.0.0.1:8001/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Login successful!")
            print(f"   Access token: {token_data.get('access_token', 'N/A')[:20]}...")
            print(f"   Token type: {token_data.get('token_type')}")
            return True, token_data
        else:
            print(f"❌ Login failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API for login test")
        return False, None
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False, None

def test_user_profile(access_token):
    """Test getting user profile with access token."""
    try:
        print("Testing user profile retrieval...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "http://127.0.0.1:8001/auth/profile",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            profile_data = response.json()
            print(f"✅ Profile retrieved successfully!")
            print(f"   Username: {profile_data.get('username')}")
            print(f"   Email: {profile_data.get('email')}")
            print(f"   Role: {profile_data.get('role')}")
            return True
        else:
            print(f"❌ Profile retrieval failed with status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API for profile test")
        return False
    except Exception as e:
        print(f"❌ Profile test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing BTC Forecast Account Creation Functionality")
    print("=" * 60)
    
    # Test 1: API Health
    print("\n1. Testing API Health...")
    api_healthy = test_api_health()
    
    if not api_healthy:
        print("\n⚠️  API is not running. Please start the backend API first:")
        print("   uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload")
        return
    
    # Test 2: Account Registration
    print("\n2. Testing Account Registration...")
    registration_success, test_user = test_account_registration()
    
    if not registration_success:
        print("\n❌ Account registration test failed. Stopping tests.")
        return
    
    # Test 3: Account Login
    print("\n3. Testing Account Login...")
    login_success, token_data = test_account_login(
        test_user["username"], 
        test_user["password"]
    )
    
    if not login_success:
        print("\n❌ Account login test failed. Stopping tests.")
        return
    
    # Test 4: User Profile
    print("\n4. Testing User Profile Retrieval...")
    profile_success = test_user_profile(token_data["access_token"])
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   API Health: {'✅ PASS' if api_healthy else '❌ FAIL'}")
    print(f"   Registration: {'✅ PASS' if registration_success else '❌ FAIL'}")
    print(f"   Login: {'✅ PASS' if login_success else '❌ FAIL'}")
    print(f"   Profile: {'✅ PASS' if profile_success else '❌ FAIL'}")
    
    if all([api_healthy, registration_success, login_success, profile_success]):
        print("\n🎉 All tests passed! Account creation functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the API configuration.")

if __name__ == "__main__":
    main() 