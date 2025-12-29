"""Tests for recommendations API endpoints.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import UserContext


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock user context."""
    return UserContext(user_id="test-user-123", email="test@example.com")


@pytest.fixture
def mock_token():
    """Generate mock token."""
    import base64
    import json
    payload = {'sub': 'test-user-123', 'email': 'test@example.com'}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    header_b64 = base64.urlsafe_b64encode(json.dumps({'typ': 'JWT', 'alg': 'HS256'}).encode()).decode().rstrip('=')
    return f'{header_b64}.{payload_b64}.fake_signature'


class TestRecommendationsAPI:
    """Test suite for recommendations API endpoints."""
    
    @patch('app.routers.recommendations.get_current_user')
    @patch('app.routers.recommendations.RecommendationService')
    def test_generate_recommendation_success(
        self, mock_service_class, mock_get_user, client, mock_user, mock_token
    ):
        """Test successful recommendation generation."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.generate_recommendation.return_value = {
            "id": "rec-123",
            "decision": "approve",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_service_class.return_value = mock_service
        
        # Make request
        response = client.post(
            "/recommendations/generate",
            headers={"Authorization": f"Bearer {mock_token}"},
            json={"type": "invest", "amount": 1000.0}
        )
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_id"] == "rec-123"
        assert data["decision"] == "approve"
        assert data["status"] == "pending"
    
    def test_generate_recommendation_no_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.post("/recommendations/generate", json={})
        
        assert response.status_code == 401  # Unauthorized
    
    @patch('app.routers.recommendations.get_current_user')
    @patch('app.routers.recommendations.RecommendationService')
    def test_generate_recommendation_without_intent_data(
        self, mock_service_class, mock_get_user, client, mock_user, mock_token
    ):
        """Test recommendation generation without intent data (uses defaults)."""
        mock_get_user.return_value = mock_user
        
        mock_service = AsyncMock()
        mock_service.generate_recommendation.return_value = {
            "id": "rec-456",
            "decision": "approve",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00"
        }
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/recommendations/generate",
            headers={"Authorization": f"Bearer {mock_token}"}
        )
        
        assert response.status_code == 200
        # Verify service was called with None intent_data
        mock_service.generate_recommendation.assert_called_once_with(
            user_id="test-user-123",
            user_intent_data=None
        )

