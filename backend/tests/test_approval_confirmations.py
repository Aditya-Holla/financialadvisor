"""Tests for approval confirmations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

These tests verify that:
- WARN recommendations require checkbox confirmations
- BLOCK recommendations require explicit override acknowledgements
- Approval endpoint rejects approval if confirmations not provided
- Confirmations must match exactly
"""

import pytest
from unittest.mock import Mock, patch
import json
from app.services.approval_service import ApprovalService
from app.agents.schemas import (
    AdvisorDecision,
    AdvisorDecisionType,
    RequiredConfirmation,
    PortfolioProposal,
    GuardrailStatus,
)
from app.models.errors import ValidationError, NotFoundError


class TestApprovalConfirmations:
    """Test suite for approval confirmations."""
    
    @pytest.fixture
    def approval_service(self):
        """Create approval service instance."""
        return ApprovalService()
    
    @pytest.fixture
    def warn_recommendation(self):
        """Recommendation with WARN guardrail status."""
        decision = AdvisorDecision(
            decision=AdvisorDecisionType.MODIFY,
            proposal=PortfolioProposal.default(),
            required_confirmations=[
                RequiredConfirmation(
                    confirmation_id="conf_low_emergency_fund_investment",
                    type="emergency_fund_acknowledgment",
                    message="Your emergency fund is below recommended levels",
                    required=True,
                    confirmation_text="I understand my emergency fund is below recommended levels and want to proceed",
                    override_acknowledgement=None
                )
            ],
            metadata={
                "guardrail_status": GuardrailStatus.WARN.value,
                "guardrail_reasons": ["LOW_EMERGENCY_FUND_INVESTMENT"]
            }
        )
        
        return {
            "id": "rec-123",
            "user_id": "test-user",
            "decision": "modify",
            "decision_json": json.dumps(decision.model_dump()),
            "status": "pending"
        }
    
    @pytest.fixture
    def block_recommendation(self):
        """Recommendation with BLOCK guardrail status."""
        decision = AdvisorDecision(
            decision=AdvisorDecisionType.REJECT,
            proposal=None,
            required_confirmations=[
                RequiredConfirmation(
                    confirmation_id="conf_negative_cashflow_invest",
                    type="cashflow_acknowledgment",
                    message="You have negative cash flow",
                    required=True,
                    confirmation_text=None,
                    override_acknowledgement="I acknowledge that I have negative cash flow and explicitly override the safety guardrail to proceed with this investment"
                )
            ],
            metadata={
                "guardrail_status": GuardrailStatus.BLOCK.value,
                "guardrail_reasons": ["NEGATIVE_CASHFLOW_INVEST"]
            }
        )
        
        return {
            "id": "rec-456",
            "user_id": "test-user",
            "decision": "reject",
            "decision_json": json.dumps(decision.model_dump()),
            "status": "pending"
        }
    
    @pytest.fixture
    def allow_recommendation(self):
        """Recommendation with ALLOW guardrail status (no confirmations)."""
        decision = AdvisorDecision(
            decision=AdvisorDecisionType.APPROVE,
            proposal=PortfolioProposal.default(),
            required_confirmations=[],  # No confirmations needed
            metadata={
                "guardrail_status": GuardrailStatus.ALLOW.value,
                "guardrail_reasons": []
            }
        )
        
        return {
            "id": "rec-789",
            "user_id": "test-user",
            "decision": "approve",
            "decision_json": json.dumps(decision.model_dump()),
            "status": "pending"
        }
    
    def test_warn_requires_checkbox_confirmation(self, approval_service, warn_recommendation):
        """Test that WARN recommendations require checkbox confirmation."""
        # Missing confirmations
        with pytest.raises(ValidationError) as exc_info:
            approval_service.validate_confirmations(warn_recommendation, None)
        
        assert "confirmations" in exc_info.value.message.lower()
        
        # Wrong confirmation text
        with pytest.raises(ValidationError) as exc_info:
            approval_service.validate_confirmations(
                warn_recommendation,
                {"conf_low_emergency_fund_investment": "wrong text"}
            )
        
        assert "match" in exc_info.value.message.lower() or "invalid" in exc_info.value.message.lower()
        
        # Correct confirmation text
        approval_service.validate_confirmations(
            warn_recommendation,
            {"conf_low_emergency_fund_investment": "I understand my emergency fund is below recommended levels and want to proceed"}
        )
        # Should not raise
    
    def test_block_requires_override_acknowledgement(self, approval_service, block_recommendation):
        """Test that BLOCK recommendations require explicit override acknowledgement."""
        # Missing confirmations
        with pytest.raises(ValidationError) as exc_info:
            approval_service.validate_confirmations(block_recommendation, None)
        
        assert "confirmations" in exc_info.value.message.lower()
        
        # Wrong override acknowledgement
        with pytest.raises(ValidationError) as exc_info:
            approval_service.validate_confirmations(
                block_recommendation,
                {"conf_negative_cashflow_invest": "wrong text"}
            )
        
        assert "override" in exc_info.value.message.lower() or "match" in exc_info.value.message.lower()
        
        # Correct override acknowledgement
        approval_service.validate_confirmations(
            block_recommendation,
            {"conf_negative_cashflow_invest": "I acknowledge that I have negative cash flow and explicitly override the safety guardrail to proceed with this investment"}
        )
        # Should not raise
    
    def test_allow_no_confirmations_required(self, approval_service, allow_recommendation):
        """Test that ALLOW recommendations don't require confirmations."""
        # No confirmations provided - should pass
        approval_service.validate_confirmations(allow_recommendation, None)
        
        # Empty confirmations - should pass
        approval_service.validate_confirmations(allow_recommendation, {})
    
    def test_approve_rejects_missing_confirmations(self, approval_service, warn_recommendation):
        """Test that approve_recommendation rejects if confirmations missing."""
        with patch('app.services.approval_service.recommendations_repo.get_recommendation') as mock_get:
            mock_get.return_value = warn_recommendation
            
            with pytest.raises(ValidationError):
                approval_service.approve_recommendation(
                    user_id="test-user",
                    recommendation_id="rec-123",
                    confirmations=None
                )
    
    def test_approve_rejects_invalid_confirmations(self, approval_service, warn_recommendation):
        """Test that approve_recommendation rejects if confirmations invalid."""
        with patch('app.services.approval_service.recommendations_repo.get_recommendation') as mock_get:
            mock_get.return_value = warn_recommendation
            
            with pytest.raises(ValidationError):
                approval_service.approve_recommendation(
                    user_id="test-user",
                    recommendation_id="rec-123",
                    confirmations={"conf_low_emergency_fund_investment": "wrong text"}
                )
    
    def test_approve_accepts_valid_confirmations(self, approval_service, warn_recommendation):
        """Test that approve_recommendation accepts valid confirmations."""
        with patch('app.services.approval_service.recommendations_repo.get_recommendation') as mock_get:
            mock_get.return_value = warn_recommendation
            
            result = approval_service.approve_recommendation(
                user_id="test-user",
                recommendation_id="rec-123",
                confirmations={
                    "conf_low_emergency_fund_investment": "I understand my emergency fund is below recommended levels and want to proceed"
                }
            )
            
            assert result["status"] == "approved"
    
    def test_approve_accepts_override_for_block(self, approval_service, block_recommendation):
        """Test that approve_recommendation accepts override for BLOCK."""
        with patch('app.services.approval_service.recommendations_repo.get_recommendation') as mock_get:
            mock_get.return_value = block_recommendation
            
            result = approval_service.approve_recommendation(
                user_id="test-user",
                recommendation_id="rec-456",
                confirmations={
                    "conf_negative_cashflow_invest": "I acknowledge that I have negative cash flow and explicitly override the safety guardrail to proceed with this investment"
                }
            )
            
            assert result["status"] == "approved"
    
    def test_multiple_confirmations_all_required(self, approval_service):
        """Test that all required confirmations must be provided."""
        decision = AdvisorDecision(
            decision=AdvisorDecisionType.MODIFY,
            proposal=PortfolioProposal.default(),
            required_confirmations=[
                RequiredConfirmation(
                    confirmation_id="conf_1",
                    type="risk_acknowledgment",
                    message="Risk increase",
                    required=True,
                    confirmation_text="I understand the risk",
                    override_acknowledgement=None
                ),
                RequiredConfirmation(
                    confirmation_id="conf_2",
                    type="debt_acknowledgment",
                    message="High debt",
                    required=True,
                    confirmation_text="I understand the debt",
                    override_acknowledgement=None
                )
            ],
            metadata={"guardrail_status": GuardrailStatus.WARN.value}
        )
        
        recommendation = {
            "id": "rec-multi",
            "user_id": "test-user",
            "decision_json": json.dumps(decision.model_dump()),
            "status": "pending"
        }
        
        # Missing one confirmation
        with pytest.raises(ValidationError):
            approval_service.validate_confirmations(
                recommendation,
                {"conf_1": "I understand the risk"}
            )
        
        # All confirmations provided
        approval_service.validate_confirmations(
            recommendation,
            {
                "conf_1": "I understand the risk",
                "conf_2": "I understand the debt"
            }
        )
    
    def test_non_required_confirmations_optional(self, approval_service):
        """Test that non-required confirmations are optional."""
        decision = AdvisorDecision(
            decision=AdvisorDecisionType.MODIFY,
            proposal=PortfolioProposal.default(),
            required_confirmations=[
                RequiredConfirmation(
                    confirmation_id="conf_required",
                    type="risk_acknowledgment",
                    message="Risk increase",
                    required=True,
                    confirmation_text="I understand the risk",
                    override_acknowledgement=None
                ),
                RequiredConfirmation(
                    confirmation_id="conf_optional",
                    type="info",
                    message="Optional info",
                    required=False,  # Not required
                    confirmation_text="Optional text",
                    override_acknowledgement=None
                )
            ],
            metadata={"guardrail_status": GuardrailStatus.WARN.value}
        )
        
        recommendation = {
            "id": "rec-optional",
            "user_id": "test-user",
            "decision_json": json.dumps(decision.model_dump()),
            "status": "pending"
        }
        
        # Only required confirmation provided - should pass
        approval_service.validate_confirmations(
            recommendation,
            {"conf_required": "I understand the risk"}
        )
    
    def test_approve_rejects_wrong_user(self, approval_service, warn_recommendation):
        """Test that approve_recommendation rejects if user doesn't own recommendation."""
        with patch('app.services.approval_service.recommendations_repo.get_recommendation') as mock_get:
            mock_get.return_value = warn_recommendation
            
            with pytest.raises(NotFoundError):
                approval_service.approve_recommendation(
                    user_id="different-user",
                    recommendation_id="rec-123",
                    confirmations={"conf_low_emergency_fund_investment": "I understand my emergency fund is below recommended levels and want to proceed"}
                )

