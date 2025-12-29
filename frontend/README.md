# Financial Advisor Frontend

A simple, modern frontend for the Financial Advisor API.

## Features

- 🔐 Token-based authentication
- 👤 User profile display
- 📊 Generate and view recommendations
- 💬 Get explanations for recommendations
- ✅ Approve recommendations

## Setup

1. Make sure your backend is running on `http://localhost:8000`

2. Open `index.html` in your browser, or serve it with a simple HTTP server:

   ```bash
   # Using Python
   cd frontend
   python3 -m http.server 3000
   
   # Then open http://localhost:3000 in your browser
   ```

   Or:

   ```bash
   # Using Node.js (if you have it)
   npx serve frontend
   ```

## Usage

1. **Get a token**: Use the backend's `generate_test_token.py` script:
   ```bash
   cd backend
   source venv/bin/activate
   python generate_test_token.py test-user-123 test@example.com
   ```

2. **Set token**: Paste the token in the "Enter your Bearer token" field and click "Set Token"

3. **Check auth**: Click "Check Auth" to verify your token works

4. **Use features**:
   - Click "Load Profile" to see your user info
   - Click "Generate Recommendation" to create a new recommendation
   - Click "Get Latest" to view your most recent recommendation
   - Click "Explain Latest Recommendation" to get an explanation
   - Enter a recommendation ID and click "Approve" to approve it

## API Endpoints Used

- `GET /me` - Get user profile
- `POST /recommendations/generate` - Generate recommendation
- `GET /recommendations/latest` - Get latest recommendation
- `POST /chat` - Get explanation
- `POST /recommendations/{id}/approve` - Approve recommendation

## Notes

- Token is stored in browser localStorage
- All API calls include the Bearer token in the Authorization header
- The frontend assumes the backend is running on `http://localhost:8000`
- To change the API URL, edit `API_BASE_URL` in `app.js`

