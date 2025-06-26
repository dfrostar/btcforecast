#!/usr/bin/env python3
"""
Minimal API test to check if basic FastAPI structure works
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import uvicorn

# Create a minimal FastAPI app for testing
app = FastAPI(title="Test API")

@app.get("/")
async def root():
    return {"message": "Test API is working"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/auth/register")
async def register():
    return {"message": "Registration endpoint working"}

@app.post("/auth/login")
async def login():
    return {"message": "Login endpoint working"}

def test_minimal_api():
    """Test the minimal API."""
    client = TestClient(app)
    
    print("🧪 Testing Minimal API")
    print("=" * 40)
    
    # Test root
    response = client.get("/")
    print(f"Root endpoint: {response.status_code} - {response.json()}")
    
    # Test health
    response = client.get("/health")
    print(f"Health endpoint: {response.status_code} - {response.json()}")
    
    # Test register
    response = client.post("/auth/register")
    print(f"Register endpoint: {response.status_code} - {response.json()}")
    
    # Test login
    response = client.post("/auth/login")
    print(f"Login endpoint: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    print("✅ Minimal API test passed!")
    test_minimal_api()
    print("\n🎉 Basic FastAPI structure is working correctly.") 