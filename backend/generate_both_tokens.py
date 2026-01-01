#!/usr/bin/env python3
"""Generate test JWT tokens for both approved and blocked users."""

import base64
import json
import sys

def generate_token(user_id: str, email: str):
    """Generate a test JWT token."""
    payload = {'sub': user_id, 'email': email}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    header_b64 = base64.urlsafe_b64encode(json.dumps({'typ': 'JWT', 'alg': 'HS256'}).encode()).decode().rstrip('=')
    token = f'{header_b64}.{payload_b64}.fake_signature'
    return token

if __name__ == "__main__":
    print("=" * 60)
    print("Test User Tokens Generator")
    print("=" * 60)
    print()
    
    # Generate approved user token
    approved_user_id = "test-user-123"
    approved_email = "test@example.com"
    approved_token = generate_token(approved_user_id, approved_email)
    
    print("✅ APPROVED USER (test-user-123)")
    print("-" * 60)
    print(f"Token: {approved_token}")
    print(f"User ID: {approved_user_id}")
    print(f"Email: {approved_email}")
    print()
    
    # Generate blocked user token
    blocked_user_id = "test-user-blocked"
    blocked_email = "test@blocked.com"
    blocked_token = generate_token(blocked_user_id, blocked_email)
    
    print("🚫 BLOCKED USER (test-user-blocked)")
    print("-" * 60)
    print(f"Token: {blocked_token}")
    print(f"User ID: {blocked_user_id}")
    print(f"Email: {blocked_email}")
    print()
    
    print("=" * 60)
    print("How to Use:")
    print("=" * 60)
    print("1. Copy the token for the user you want to test")
    print("2. In the product page, click the 🔄 (Switch User) button")
    print("3. Paste the token in the auth modal")
    print("4. Start chatting!")
    print()
    print("💡 Tip: Keep both tokens handy for quick switching")
    print("=" * 60)

