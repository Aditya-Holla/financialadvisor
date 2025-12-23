#!/usr/bin/env python3
"""Quick test script to verify the backend setup."""

import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(path, expected_status=200):
    """Test an endpoint and return True if successful."""
    try:
        response = requests.get(f"{BASE_URL}{path}", timeout=2)
        if response.status_code == expected_status:
            print(f"✓ {path} - Status: {response.status_code}")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ {path} - Expected {expected_status}, got {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ {path} - Could not connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"✗ {path} - Error: {e}")
        return False

def main():
    print("Testing Financial Advisor Backend...")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    # Test endpoints
    results = []
    results.append(test_endpoint("/health"))
    results.append(test_endpoint("/me"))
    results.append(test_endpoint("/profile"))
    results.append(test_endpoint("/portfolio/latest"))
    results.append(test_endpoint("/recommendations/latest"))
    
    print("=" * 50)
    if all(results):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("⚠ Some tests failed. Make sure the server is running.")
        print("  Start server with: python -m uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

if __name__ == "__main__":
    main()

