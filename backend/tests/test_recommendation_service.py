"""Tests for recommendation service.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.recommendation_service import RecommendationService
from app.models.errors import NotFoundError
from app.agents.schemas import AdvisorDecisionType


class TestRecommendationService:
    """Test suite for RecommendationService."""
    
    @pytest.fixture
    def service(self):
        """Create recommendation service instance."""
        return RecommendationService()
    
    @pytest.fixture
    def mock_profile(self):
        """Mock user profile."""
        return {
            "user_id": "test-user-123",
            "monthly_income": 5000.0,
            "monthly_expenses": 3000.0,
            "total_debt": 0.0,
            "credit_card_debt": 0.0,
            "mortgage_debt": 0.0,
            "student_loan_debt": 0.0,
            "other_debt": 0.0,
            "monthly_debt_payments": 0.0,
            "goals": "[]"
        }
    
    @pytest.fixture
    def mock_snapshot(self):
        """Mock portfolio snapshot."""
        return {
            "user_id": "test-user-123",
            "cash": 10000.0,
            "positions_json": "[]",
            "as_of": "2024-01-01T00:00:00"
        }
    
    @pytest.fixture
    def mock_recommendation(self):
        """Mock stored recommendation."""
        return {
            "id": "rec-123",
            "user_id": "test-user-123",
            "decision": "approve",
            "status": "pending",
            "created_at": "2024-01-01T00:00:00"
        }
    
    @patch('app.services.recommendation_service.recommendations_repo.create_recommendation')
    @patch('app.services.recommendation_service.OrchestratorAgent')
    @patch('app.services.recommendation_service.snapshots_repo.get_latest_snapshot')
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    @pytest.mark.asyncio
    async def test_generate_recommendation_success(
        self,
        mock_get_profile,
        mock_get_snapshot,
        mock_orchestrator_class,
        mock_create_rec,
        service,
        mock_profile,
        mock_snapshot,
        mock_recommendation
    ):
        """Test successful recommendation generation."""
        # Setup mocks
        mock_get_profile.return_value = mock_profile
        mock_get_snapshot.return_value = mock_snapshot
        
        # Mock orchestrator
        mock_orchestrator = AsyncMock()
        mock_decision = Mock(
            decision=AdvisorDecisionType.APPROVE,
            proposal=None,
            metadata={"guardrail_status": "ALLOW"}
        )
        # Configure model_dump() to return a serializable dictionary
        mock_decision.model_dump.return_value = {
            "decision": "approve",
            "proposal": None,
            "required_confirmations": [],
            "explanation_inputs": [],
            "reasoning": None,
            "metadata": {"guardrail_status": "ALLOW"}
        }
        mock_orchestrator.decide.return_value = mock_decision
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Replace the service's orchestrator with the mock
        service.orchestrator = mock_orchestrator
        
        mock_create_rec.return_value = mock_recommendation
        
        # Execute
        result = await service.generate_recommendation("test-user-123")
        
        # Verify
        assert result["id"] == "rec-123"
        assert result["decision"] == "approve"
        mock_get_profile.assert_called_once_with("test-user-123")
        mock_get_snapshot.assert_called_once_with("test-user-123")
        mock_orchestrator.decide.assert_called_once()
        mock_create_rec.assert_called_once()
    
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    @pytest.mark.asyncio
    async def test_generate_recommendation_no_profile(self, mock_get_profile, service):
        """Test that missing profile raises NotFoundError."""
        mock_get_profile.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            await service.generate_recommendation("test-user-123")
        
        assert "profile" in exc_info.value.message.lower()
    
    @patch('app.services.recommendation_service.snapshots_repo.get_latest_snapshot')
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    @pytest.mark.asyncio
    async def test_generate_recommendation_no_snapshot(
        self, mock_get_profile, mock_get_snapshot, service, mock_profile
    ):
        """Test that missing snapshot raises NotFoundError."""
        mock_get_profile.return_value = mock_profile
        mock_get_snapshot.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            await service.generate_recommendation("test-user-123")
        
        assert "snapshot" in exc_info.value.message.lower()
    
    @patch('app.services.recommendation_service.recommendations_repo.create_recommendation')
    @patch('app.services.recommendation_service.OrchestratorAgent')
    @patch('app.services.recommendation_service.snapshots_repo.get_latest_snapshot')
    @patch('app.services.recommendation_service.profiles_repo.get_profile')
    @pytest.mark.asyncio
    async def test_generate_recommendation_with_intent_data(
        self,
        mock_get_profile,
        mock_get_snapshot,
        mock_orchestrator_class,
        mock_create_rec,
        service,
        mock_profile,
        mock_snapshot,
        mock_recommendation
    ):
        """Test recommendation generation with custom intent data."""
        mock_get_profile.return_value = mock_profile
        mock_get_snapshot.return_value = mock_snapshot
        
        mock_orchestrator = AsyncMock()
        mock_decision = Mock(
            decision=AdvisorDecisionType.APPROVE,
            proposal=None,
            metadata={"guardrail_status": "ALLOW"}
        )
        # Configure model_dump() to return a serializable dictionary
        mock_decision.model_dump.return_value = {
            "decision": "approve",
            "proposal": None,
            "required_confirmations": [],
            "explanation_inputs": [],
            "reasoning": None,
            "metadata": {"guardrail_status": "ALLOW"}
        }
        mock_orchestrator.decide.return_value = mock_decision
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Replace the service's orchestrator with the mock
        service.orchestrator = mock_orchestrator
        
        mock_create_rec.return_value = mock_recommendation
        
        intent_data = {
            "type": "invest",
            "amount": 5000.0,
            "timeframe": "immediate"
        }
        
        result = await service.generate_recommendation("test-user-123", intent_data)
        
        assert result["id"] == "rec-123"
        # Verify orchestrator was called with correct intent
        call_args = mock_orchestrator.decide.call_args
        assert call_args is not None
        user_intent = call_args.kwargs.get("user_intent")
        assert user_intent is not None
        assert user_intent.type.value == "invest"
        assert user_intent.amount == 5000.0
    
    def test_build_financial_state(self, service, mock_profile, mock_snapshot):
        """Test building FinancialState from profile and snapshot."""
        financial_state = service._build_financial_state(mock_profile, mock_snapshot)
        
        assert financial_state.cashflow.monthly_income == 5000.0
        assert financial_state.cashflow.monthly_expenses == 3000.0
        assert financial_state.cashflow.net_cashflow == 2000.0
        assert financial_state.emergency_fund_months > 0
        assert financial_state.portfolio_summary.cash_balance == 10000.0
    
    def test_build_user_intent_default(self, service):
        """Test building UserIntent with default values."""
        intent = service._build_user_intent({})
        
        assert intent.type.value == "invest"
        assert intent.timeframe == "immediate"
    
    def test_build_user_intent_custom(self, service):
        """Test building UserIntent with custom data."""
        intent_data = {
            "type": "rebalance",
            "amount": 1000.0,
            "risk_change": 0.1,
            "target": "AAPL",
            "timeframe": "1 month"
        }
        
        intent = service._build_user_intent(intent_data)
        
        assert intent.type.value == "rebalance"
        assert intent.amount == 1000.0
        assert intent.risk_change == 0.1
        assert intent.target == "AAPL"
        assert intent.timeframe == "1 month"

