# JWKS Migration Summary

## What Changed

We've updated the authentication system to use **JWKS (JSON Web Key Set)** instead of the legacy JWT secret. This is Supabase's new, more secure token verification system.

## Key Changes

### 1. **Token Verification Method**
- **Old**: Used a shared HS256 secret (`SUPABASE_JWT_SECRET`)
- **New**: Automatically fetches public keys from Supabase's JWKS endpoint
- **Fallback**: Still supports legacy tokens if `SUPABASE_JWT_SECRET` is configured

### 2. **Files Updated**

#### `backend/app/auth.py`
- Added `PyJWKClient` for fetching JWKS keys
- Updated `verify_supabase_jwt()` to:
  1. Try JWKS first (for new ECC P-256 tokens)
  2. Fall back to legacy HS256 secret if JWKS fails
  3. Support both ES256/RS256 (new) and HS256 (legacy) algorithms

#### `backend/app/config.py`
- Updated comments to reflect new key names:
  - `SUPABASE_KEY`: Now refers to "Secret key" (not "service_role")
  - `SUPABASE_ANON_KEY`: Now refers to "Publishable key" (not "anon public")
  - `SUPABASE_JWT_SECRET`: Marked as optional (for legacy token support only)

#### Documentation
- Updated `AUTH_SETUP_GUIDE.md` with new key locations
- Updated `QUICK_START_AUTH.md` with simplified instructions

## Benefits

1. **More Secure**: Uses public key cryptography (ECC P-256) instead of shared secrets
2. **Automatic Key Rotation**: JWKS automatically handles key rotation
3. **Future-Proof**: Aligns with Supabase's new authentication system
4. **Backward Compatible**: Still supports legacy tokens if needed

## Environment Variables

### Required
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=sb_secret_...  # Secret key
SUPABASE_ANON_KEY=sb_publishable_...  # Publishable key
```

### Optional (Legacy Support)
```bash
SUPABASE_JWT_SECRET=legacy-secret  # Only if you have old tokens
```

## How It Works

1. **New Token Flow**:
   - Token contains `kid` (key ID) in header
   - System fetches public key from `{SUPABASE_URL}/.well-known/jwks.json`
   - Verifies token signature using public key
   - Supports ES256 (ECC) and RS256 (RSA) algorithms

2. **Legacy Token Flow** (if `SUPABASE_JWT_SECRET` is set):
   - Token uses HS256 algorithm
   - Verifies using shared secret
   - Falls back to this if JWKS fails

## Testing

The system automatically:
- Detects token type (new vs legacy)
- Uses appropriate verification method
- Handles key rotation transparently
- Caches JWKS keys for performance

## Migration Notes

- **No breaking changes**: Existing code continues to work
- **No action required**: JWKS is automatic if `SUPABASE_URL` is set
- **Legacy support**: Old tokens still work if `SUPABASE_JWT_SECRET` is configured
- **New tokens**: Automatically use JWKS (no configuration needed)

## Troubleshooting

**"Token verification failed"**
- Check `SUPABASE_URL` is correct
- Ensure Supabase project is active
- Verify network can reach `{SUPABASE_URL}/.well-known/jwks.json`

**"JWKS verification failed"**
- System will fall back to legacy secret if configured
- Check token is from the correct Supabase project
- Verify token hasn't expired

