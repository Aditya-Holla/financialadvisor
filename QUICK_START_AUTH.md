# Quick Start: Email/Password Authentication

## 🚀 Quick Setup (5 minutes)

### 1. Backend `.env` - Add these lines:
```bash
# Required
SUPABASE_ANON_KEY=sb_publishable_...  # From "Publishable key" section
SUPABASE_KEY=sb_secret_...  # From "Secret keys" section (if not already set)

# Optional (only for legacy token support)
# SUPABASE_JWT_SECRET=legacy-jwt-secret  # From "Legacy JWT Secret" tab
```

**Note:** The system now uses JWKS (automatic key fetching) - you don't need the JWT secret unless you have old tokens!

### 2. Frontend `config.js` - Create this file:
```bash
cd frontend
cp config.example.js config.js
# Edit config.js and add your Supabase URL and anon key
```

### 3. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### 4. Create test users in Supabase:
- Go to Supabase Dashboard > Authentication > Users
- Click "Add user" > Create:
  - `test@approved.com` / `test123456`
  - `test@blocked.com` / `test123456`

### 5. Run SQL script:
- Go to Supabase SQL Editor
- Copy/paste `backend/setup_test_users.sql`
- Run it

### 6. Test it:
- Open `frontend/login.html`
- Sign in with `test@approved.com` / `test123456`
- You should see the chat interface!

## 📝 Where to Find Supabase Keys

1. Go to your Supabase project dashboard
2. Click **Settings** (gear icon) > **API**
3. You'll see:
   - **Project URL** → `SUPABASE_URL` (already set)
   - **Publishable key** (sb_publishable_...) → `SUPABASE_ANON_KEY` (frontend)
   - **Secret key** (sb_secret_...) → `SUPABASE_KEY` (backend)
   - **Legacy JWT Secret** (optional) → `SUPABASE_JWT_SECRET` (only if needed for old tokens)

**New System:** The app uses JWKS (automatic key fetching) - no JWT secret needed for new tokens!

## ✅ What Changed

- ✅ Login page with email/password
- ✅ Sign up functionality
- ✅ Automatic session management
- ✅ Easy user switching (logout/login)
- ✅ Secure JWT verification
- ✅ Test user quick buttons

## 🎯 Test Users

| Email | Password | Status |
|-------|----------|--------|
| `test@approved.com` | `test123456` | ✅ Approved (good financial state) |
| `test@blocked.com` | `test123456` | ⚠️ Blocked (triggers guardrails) |

## 🔄 User Flow

```
Landing Page → Login Page → Product Page (Chat)
                      ↓
              (Sign up or Sign in)
                      ↓
              (Supabase Auth)
                      ↓
              (Session stored)
                      ↓
              (Access Chat)
```

## 🐛 Common Issues

**"Authentication service not configured"**
→ Create `frontend/config.js` with Supabase credentials

**"Token verification failed"**
→ Check `SUPABASE_URL` is correct in `backend/.env`
→ JWKS automatically fetches keys - ensure URL is right

**Users can't sign in**
→ Make sure users exist in Supabase Auth dashboard

**Profile not found**
→ Run `backend/setup_test_users.sql` in Supabase SQL Editor

## 📚 Full Documentation

See `AUTH_SETUP_GUIDE.md` for detailed instructions.

