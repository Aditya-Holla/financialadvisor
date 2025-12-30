# Phase 0: Testing Existing Deployment

## Goal
Test the existing frontend/backend deployment to understand what the co-builder has built before making changes.

## Prerequisites

1. **Backend Environment Setup:**
   ```bash
   cd backend
   source venv/bin/activate  # Activate virtual environment
   ```

2. **Environment Variables:**
   - Copy `backend/env.example` to `backend/.env`
   - Fill in required values (at minimum, you'll need test values for MVP testing)

3. **Dependencies:**
   - Should already be installed in `venv/`
   - If not: `pip install -r requirements.txt`

## Testing Steps

### 1. Start Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Expected:** Server starts on http://localhost:8000

**Verify:**
- No import errors
- Server responds to requests
- Check http://localhost:8000/docs for FastAPI docs

### 2. Test Backend Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```
**Expected:** `{"status": "ok"}`

#### Authentication Test
```bash
# Generate a test token first
cd backend
python generate_test_token.py

# Use the token (replace <token> with output)
curl -H "Authorization: Bearer <token>" http://localhost:8000/me
```
**Expected:** Returns user info with `user_id` and `email`

#### Profile Endpoint
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/profile
```
**Expected:** Either returns profile data or "Not implemented yet"

#### Recommendations
```bash
# Generate recommendation
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/recommendations/generate

# Get latest
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/recommendations/latest
```

#### Chat/Explanation
```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/chat
```

### 3. Test Frontend

1. Open `frontend/index.html` in a browser (or serve it)
2. Enter a test token in the "Enter Bearer token" field
3. Click "Set Token" then "Verify"
4. Test each section:
   - Dashboard: Check stats display
   - Recommendations: Generate and view latest
   - Explanations: Get explanation for recommendation
   - Profile: Load profile info

### 4. Document Findings

Create a checklist of what works and what's stubbed:

#### Working Endpoints
- [ ] `/health` - Status check
- [ ] `/me` - User identity
- [ ] `/profile` - Profile management
- [ ] `/recommendations/generate` - Generate recommendations
- [ ] `/recommendations/latest` - Get latest recommendation
- [ ] `/chat` - Get explanations

#### Stubbed/Not Implemented
- [ ] Profile endpoints (GET/PUT)
- [ ] Portfolio endpoints
- [ ] Trade execution
- [ ] myStockDNA integration (stub or real?)
- [ ] Market data integration

#### Issues Found
- [ ] Any errors or exceptions
- [ ] Missing dependencies
- [ ] Configuration problems
- [ ] Database connection issues

## Test Results Template

```
## Phase 0 Test Results - [Date]

### Backend Status
- Server starts: ✅ / ❌
- Port: 8000
- FastAPI docs accessible: ✅ / ❌

### Endpoint Status
- /health: ✅ / ❌ / ⚠️ (works but stubbed)
- /me: ✅ / ❌ / ⚠️
- /profile: ✅ / ❌ / ⚠️
- /recommendations/generate: ✅ / ❌ / ⚠️
- /recommendations/latest: ✅ / ❌ / ⚠️
- /chat: ✅ / ❌ / ⚠️

### Frontend Status
- Loads: ✅ / ❌
- Connects to backend: ✅ / ❌
- Authentication works: ✅ / ❌
- All sections functional: ✅ / ❌

### Key Findings
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

### Next Steps
- [ ] Fix any blocking issues
- [ ] Document what needs implementation
- [ ] Proceed to Phase 1
```

## Notes

- If backend fails to start, check:
  - Virtual environment is activated
  - Dependencies are installed
  - Environment variables are set
  - Port 8000 is not in use

- If frontend can't connect:
  - Check CORS settings in backend
  - Verify backend is running
  - Check browser console for errors

