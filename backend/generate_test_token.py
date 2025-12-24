#!/usr/bin/env python3
"""Generate a test JWT token for authentication testing."""

import base64
import json
import sys

def generate_token(user_id: str = "test-user-123", email: str = "test@example.com"):
    """Generate a test JWT token."""
    payload = {'sub': user_id, 'email': email}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    header_b64 = base64.urlsafe_b64encode(json.dumps({'typ': 'JWT', 'alg': 'HS256'}).encode()).decode().rstrip('=')
    token = f'{header_b64}.{payload_b64}.fake_signature'
    return token

if __name__ == "__main__":
    # Allow custom user_id and email from command line
    user_id = sys.argv[1] if len(sys.argv) > 1 else "test-user-123"
    email = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
    
    token = generate_token(user_id, email)
    print(f"Bearer {token}")
    print()
    print("Copy the token above and use it in:")
    print("  1. FastAPI docs: Click 'Authorize' → Paste token → Click 'Authorize'")
    print("  2. curl: curl -H \"Authorization: Bearer {token}\" http://localhost:8000/me")
    print()
    print(f"Token contains: user_id='{user_id}', email='{email}'")

