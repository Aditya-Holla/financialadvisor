# Testing Guide

This guide covers how to test the financial advisor backend.

## Prerequisites

Install test dependencies:

```bash
cd backend
pip install pytest pytest-asyncio httpx
```

## Running Existing Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test Files
```bash
# Test guardrails
pytest tests/test_guardrails.py -v

# Test orchestrator
pytest tests/test_orchestrator.py -v

# Test recommendation service (when created)
pytest tests/test_recommendation_service.py -v
```

### Run with Coverage
```bash
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

## Testing the API Endpoint

### 1. Start the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Generate Test Token

```bash
python generate_test_token.py <user_id> <email>
# Example:
python generate_test_token.py test-user-123 test@example.com
```

This will output a Bearer token you can use for authentication.

### 3. Test with curl

```bash
# Set your token
TOKEN="Bearer <token_from_generate_test_token.py>"

# Test health check (no auth required)
curl http://localhost:8000/health

# Test /me endpoint
curl -H "Authorization: $TOKEN" http://localhost:8000/me

# Test recommendation generation (requires profile and snapshot in DB)
curl -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "invest", "amount": 1000.0}' \
  http://localhost:8000/recommendations/generate
```

### 4. Test with FastAPI Docs

1. Start the server
2. Open http://localhost:8000/docs
3. Click "Authorize" button
4. Paste your Bearer token (without "Bearer " prefix)
5. Click "Authorize"
6. Test endpoints interactively

### 5. Test with Python requests

```python
import requests

token = "Bearer <your_token>"
headers = {"Authorization": token}

# Generate recommendation
response = requests.post(
    "http://localhost:8000/recommendations/generate",
    headers=headers,
    json={"type": "invest", "amount": 1000.0}
)
print(response.json())
```

## Setting Up Test Data

Before testing the recommendation endpoint, you need:

1. **User Profile** in `profiles` table:
```sql
INSERT INTO profiles (user_id, monthly_income, monthly_expenses, total_debt, credit_card_debt, monthly_debt_payments)
VALUES ('test-user-123', 5000.0, 3000.0, 0.0, 0.0, 0.0);
```

2. **Portfolio Snapshot** in `snapshots` table:
```sql
INSERT INTO snapshots (user_id, cash, positions_json, as_of)
VALUES (
  'test-user-123',
  10000.0,
  '[]',
  NOW()
);
```

## Writing New Tests

### Example: Testing Recommendation Service

```python
import pytest
from unittest.mock import Mock, patch
from app.services.recommendation_service import RecommendationService
from app.models.errors import NotFoundError

class TestRecommendationService:
    @pytest.fixture
    def service(self):
        return RecommendationService()
    
    @pytest.fixture
    def mock_profile(self):
        return {
            "user_id": "test-user",
            "monthly_income": 5000.0,
            "monthly_expenses": 3000.0,
            "total_debt": 0.0,
            "credit_card_debt": 0.0,
            "monthly_debt_payments": 0.0
        }
    
    @pytest.fixture
    def mock_snapshot(self):
        return {
            "user_id": "test-user",
            "cash": 10000.0,
            "positions_json": "[]",
            "as_of": "2024-01-01T00:00:00"
        }
    
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    @patch('app.services.recommendation_service.snapshots_repo.get_latest_snapshot')
    @patch('app.services.recommendation_service.recommendations_repo.create_recommendation')
    async def test_generate_recommendation_success(
        self, mock_create, mock_snapshot, mock_profile, service, mock_profile, mock_snapshot
    ):
        mock_profile.return_value = mock_profile
        mock_snapshot.return_value = mock_snapshot
        mock_create.return_value = {"id": "rec-123", "decision": "approve", "status": "pending"}
        
        result = await service.generate_recommendation("test-user")
        
        assert result["id"] == "rec-123"
        assert result["decision"] == "approve"
    
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    async def test_generate_recommendation_no_profile(self, mock_profile, service):
        mock_profile.return_value = None
        
        with pytest.raises(NotFoundError):
            await service.generate_recommendation("test-user")
```

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies (DB, APIs)
- Fast execution
- Examples: `test_guardrails.py`, `test_orchestrator.py`

### Integration Tests
- Test component interactions
- Use test database or mocks
- Examples: `test_recommendation_service.py`

### API Tests
- Test full HTTP request/response cycle
- Use TestClient from FastAPI
- Examples: `test_recommendations_api.py`

## Common Issues

### Import Errors
Make sure you're running from the `backend` directory:
```bash
cd backend
pytest tests/
```

### Database Connection Errors
Tests should mock database calls. If testing against real DB:
1. Set up test database
2. Use environment variables for test DB credentials
3. Clean up test data after tests

### Async Test Issues
Use `pytest-asyncio` and mark async tests:
```python
@pytest.mark.asyncio
async def test_async_function():
    ...
```

## Continuous Integration

For CI/CD, add to your workflow:

```yaml
- name: Run tests
  run: |
    cd backend
    pip install pytest pytest-asyncio
    pytest tests/ -v
```

