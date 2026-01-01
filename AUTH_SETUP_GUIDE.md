# Email/Password Authentication Setup Guide

This guide will help you set up email/password authentication using Supabase for the RoboAdvisor application.

## Overview

The application now uses Supabase Auth for email/password authentication instead of manual token entry. Users can:
- Sign up with email and password
- Sign in to access the advisor
- Switch between users easily by logging out and logging in with different credentials

## Setup Steps

### 1. Backend Configuration

#### Update `.env` file

Add the following variables to your `backend/.env` file:

```bash
# Supabase (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=sb_secret_...  # Secret key (from "Secret keys" section)
SUPABASE_ANON_KEY=sb_publishable_...  # Publishable key (from "Publishable key" section)

# Supabase Auth (optional - for legacy token support)
# SUPABASE_JWT_SECRET=legacy-jwt-secret  # Only needed if you have old tokens
```

**Where to find these values:**
- **SUPABASE_URL**: Your Supabase project URL (Settings > API)
- **SUPABASE_KEY**: Secret key (Settings > API > Secret keys) - keep this secret! Replaces old service_role key
- **SUPABASE_ANON_KEY**: Publishable key (Settings > API > Publishable key) - safe for frontend. Replaces old anon key
- **SUPABASE_JWT_SECRET**: Legacy JWT secret (Settings > API > JWT Keys > Legacy JWT Secret) - **Optional**, only needed for backward compatibility with old tokens

**Note:** The system now uses **JWKS (JSON Web Key Set)** for token verification, which automatically fetches public keys from Supabase. The legacy JWT secret is only used as a fallback for old tokens.

#### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install `PyJWT` and `cryptography` for JWT token verification.

### 2. Frontend Configuration

#### Create `config.js` file

1. Copy the example config:
   ```bash
   cd frontend
   cp config.example.js config.js
   ```

2. Edit `config.js` and add your Supabase credentials:
   ```javascript
   window.SUPABASE_URL = 'https://your-project.supabase.co';
   window.SUPABASE_ANON_KEY = 'your-anon-key-here';
   ```

3. **Important**: Add `config.js` to `.gitignore` to keep credentials private:
   ```bash
   echo "frontend/config.js" >> .gitignore
   ```

### 3. Supabase Dashboard Setup

#### Enable Email Authentication

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** > **Providers**
3. Ensure **Email** provider is enabled
4. For testing, you may want to disable **Confirm email** (Settings > Auth > Email Auth)

#### Create Test Users

**Option A: Via Supabase Dashboard**
1. Go to **Authentication** > **Users**
2. Click **Add user** > **Create new user**
3. Create two users:
   - **Email**: `test@approved.com`, **Password**: `test123456`
   - **Email**: `test@blocked.com`, **Password**: `test123456`

**Option B: Via Frontend Signup**
- Use the signup form on the login page to create users

### 4. Database Setup

After creating users, run the SQL script to set up their profiles:

1. Go to **SQL Editor** in Supabase dashboard
2. Open `backend/setup_test_users.sql`
3. Run the script to create profiles and snapshots for test users

The script will:
- Create profile for approved user (good financial state)
- Create profile for blocked user (bad financial state - triggers guardrails)
- Create snapshots for both users

### 5. Verify Setup

#### Test Backend

1. Start the backend server:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

2. Check that JWT verification is working:
   - The backend should now properly verify Supabase JWT tokens
   - Invalid/expired tokens will be rejected

#### Test Frontend

1. Open `frontend/login.html` in your browser
2. Try signing in with:
   - **Email**: `test@approved.com`
   - **Password**: `test123456`
3. You should be redirected to `product.html` (chat interface)
4. The user's email should appear in the chat header

#### Test User Switching

1. Click the **🔄 Switch User** button in the chat header
2. You'll be logged out and redirected to login
3. Sign in with a different user (e.g., `test@blocked.com`)
4. You should see different behavior based on the user's financial state

## File Structure

```
frontend/
├── login.html          # Login/signup page
├── login.css           # Login page styles
├── login.js            # Supabase auth logic
├── product.html        # Chat interface (updated)
├── product.js          # Chat logic (updated to use Supabase)
├── config.example.js   # Config template
└── config.js           # Your Supabase config (create this, add to .gitignore)

backend/
├── app/
│   ├── auth.py         # JWT verification (updated)
│   └── config.py       # Settings (updated with new vars)
├── setup_test_users.sql # SQL script for test users
└── requirements.txt    # Dependencies (updated)
```

## Troubleshooting

### "Authentication service not configured"
- Make sure you created `frontend/config.js` with your Supabase credentials
- Check that `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct

### "Token verification failed"
- Check that `SUPABASE_URL` is set correctly in `backend/.env`
- The system uses JWKS to automatically fetch public keys - ensure your Supabase URL is correct
- If using legacy tokens, ensure `SUPABASE_JWT_SECRET` is set (optional)

### "User not found" when accessing profile
- Run the `setup_test_users.sql` script to create profiles
- Make sure users exist in `auth.users` table

### Session expires quickly
- Supabase sessions typically last 1 hour
- Users will be redirected to login when session expires
- Sessions are automatically refreshed by Supabase client

### Test user buttons don't work
- Make sure users exist in Supabase Auth
- Check that email/password match what's in the database
- Verify `config.js` is loaded correctly

## Security Notes

1. **Never commit `config.js`** - It contains your Supabase anon key
2. **Never commit `.env`** - It contains your service role key and JWT secret
3. **Use environment variables** in production instead of `config.js`
4. **Enable email confirmation** in production for better security
5. **Use strong passwords** for production users

## Next Steps

- [ ] Set up email templates in Supabase for password reset
- [ ] Configure custom SMTP for production emails
- [ ] Add password strength requirements
- [ ] Implement "Remember me" functionality
- [ ] Add social login providers (Google, GitHub, etc.)

## Support

If you encounter issues:
1. Check browser console for JavaScript errors
2. Check backend logs for authentication errors
3. Verify all environment variables are set correctly
4. Ensure Supabase project is active and accessible

