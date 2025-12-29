"""Tests for deterministic and replayable recommendations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

These tests verify that:
- Same inputs produce same outputs
- No randomness or time-dependent logic affects decisions
- Recommendations can be replayed with stored inputs
"""

import pytest
from unittest.mock import Mock, patch
import json
from app.agents.orchestrator import OrchestratorAgent
from app.agents.schemas import (
    FinancialState,
    Cashflow,
    DebtSummary,
    PortfolioSummary,
    FinancialGoal,
    UserIntent,
    UserIntentType,
    PortfolioProposal,
    AssetAllocation,
    AdvisorDecision,
    AdvisorDecisionType,
)


class TestDeterministicRecommendations:
    """Test suite for deterministic recommendation generation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator agent instance."""
        return OrchestratorAgent()
    
    @pytest.fixture
    def fixed_financial_state(self):
        """Financial state with fixed timestamp for deterministic testing."""
        from datetime import datetime
        return FinancialState(
            cashflow=Cashflow(
                monthly_income=5000.0,
                monthly_expenses=3000.0,
                net_cashflow=2000.0
            ),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary(
                total_debt=0.0,
                credit_card_debt=0.0,
                mortgage_debt=0.0,
                student_loan_debt=0.0,
                other_debt=0.0,
                monthly_debt_payments=0.0
            ),
            portfolio_summary=PortfolioSummary.default(),
            goals=[],
            timestamp="2024-01-15T10:00:00"  # Fixed timestamp
        )
    
    @pytest.fixture
    def fixed_user_intent(self):
        """Fixed user intent for deterministic testing."""
        return UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
    
    @pytest.mark.asyncio
    async def test_same_inputs_produce_same_output(self, orchestrator, fixed_financial_state, fixed_user_intent):
        """Test that same inputs produce identical outputs."""
        # Run decision twice with same inputs
        decision1 = await orchestrator.decide(
            financial_state=fixed_financial_state,
            user_intent=fixed_user_intent,
            proposal=None
        )
        
        decision2 = await orchestrator.decide(
            financial_state=fixed_financial_state,
            user_intent=fixed_user_intent,
            proposal=None
        )
        
        # Compare decisions (excluding metadata timestamps if any)
        assert decision1.decision == decision2.decision
        assert decision1.reasoning == decision2.reasoning
        
        # Compare proposals if present
        if decision1.proposal and decision2.proposal:
            assert decision1.proposal.target_allocation.stocks == decision2.proposal.target_allocation.stocks
            assert decision1.proposal.target_allocation.bonds == decision2.proposal.target_allocation.bonds
            assert decision1.proposal.risk_delta == decision2.proposal.risk_delta
            assert len(decision1.proposal.trades) == len(decision2.proposal.trades)
        
        # Compare confirmations
        assert len(decision1.required_confirmations) == len(decision2.required_confirmations)
        for conf1, conf2 in zip(decision1.required_confirmations, decision2.required_confirmations):
            assert conf1.confirmation_id == conf2.confirmation_id
            assert conf1.message == conf2.message
            assert conf1.confirmation_text == conf2.confirmation_text
            assert conf1.override_acknowledgement == conf2.override_acknowledgement
        
        # Compare guardrail status
        assert decision1.metadata.get("guardrail_status") == decision2.metadata.get("guardrail_status")
        assert decision1.metadata.get("guardrail_reasons") == decision2.metadata.get("guardrail_reasons")
    
    @pytest.mark.asyncio
    async def test_replay_from_stored_inputs(self, orchestrator):
        """Test that recommendations can be replayed from stored inputs."""
        from datetime import datetime, timedelta
        
        # Create financial state with goal
        goal_date = (datetime(2024, 1, 15) + timedelta(days=180)).isoformat()
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[
                FinancialGoal(
                    goal_id="goal-1",
                    name="Vacation",
                    target_amount=5000.0,
                    current_progress=2000.0,
                    target_date=goal_date,
                    priority=1
                )
            ],
            timestamp="2024-01-15T10:00:00"  # Fixed timestamp
        )
        
        user_intent = UserIntent(
            type=UserIntentType.REBALANCE
        )
        
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=70.0, bonds=20.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.1
        )
        
        # Generate original decision
        original_decision = await orchestrator.decide(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=proposal
        )
        
        # Store inputs (simulating database storage)
        stored_financial_state_json = json.dumps(financial_state.model_dump())
        stored_user_intent_json = json.dumps(user_intent.model_dump())
        stored_proposal_json = json.dumps(proposal.model_dump())
        
        # Replay from stored inputs
        replayed_financial_state = FinancialState(**json.loads(stored_financial_state_json))
        replayed_user_intent = UserIntent(**json.loads(stored_user_intent_json))
        replayed_proposal = PortfolioProposal(**json.loads(stored_proposal_json))
        
        replayed_decision = await orchestrator.decide(
            financial_state=replayed_financial_state,
            user_intent=replayed_user_intent,
            proposal=replayed_proposal
        )
        
        # Verify decisions match
        assert original_decision.decision == replayed_decision.decision
        assert original_decision.metadata.get("guardrail_status") == replayed_decision.metadata.get("guardrail_status")
        assert original_decision.metadata.get("guardrail_reasons") == replayed_decision.metadata.get("guardrail_reasons")
        
        # Verify computed values match (including goal months_away)
        original_computed = original_decision.metadata.get("computed_values", {})
        replayed_computed = replayed_decision.metadata.get("computed_values", {})
        
        # Check goal months_away is deterministic
        if "goal_goal-1_months_away" in original_computed:
            assert original_computed["goal_goal-1_months_away"] == replayed_computed.get("goal_goal-1_months_away")
    
    @pytest.mark.asyncio
    async def test_time_independent_goal_calculation(self, orchestrator):
        """Test that goal date calculations are time-independent when timestamp is fixed."""
        from datetime import datetime, timedelta
        
        # Create goal 6 months from fixed timestamp
        fixed_timestamp = "2024-01-15T10:00:00"
        goal_date = (datetime(2024, 1, 15) + timedelta(days=180)).isoformat()
        
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[
                FinancialGoal(
                    goal_id="goal-1",
                    name="Vacation",
                    target_amount=5000.0,
                    current_progress=2000.0,
                    target_date=goal_date,
                    priority=1
                )
            ],
            timestamp=fixed_timestamp
        )
        
        user_intent = UserIntent(type=UserIntentType.REBALANCE)
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=85.0, bonds=10.0, cash=5.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.2
        )
        
        # Run decision multiple times - should produce same result
        decision1 = await orchestrator.decide(financial_state, user_intent, proposal)
        decision2 = await orchestrator.decide(financial_state, user_intent, proposal)
        
        # Computed values should match
        computed1 = decision1.metadata.get("computed_values", {})
        computed2 = decision2.metadata.get("computed_values", {})
        
        if "goal_goal-1_months_away" in computed1:
            assert computed1["goal_goal-1_months_away"] == computed2.get("goal_goal-1_months_away")
        
        # Guardrail status should match
        assert decision1.metadata.get("guardrail_status") == decision2.metadata.get("guardrail_status")
    
    @pytest.mark.asyncio
    async def test_all_inputs_stored(self):
        """Test that all decision inputs are stored in recommendation data."""
        from app.services.recommendation_service import RecommendationService
        from unittest.mock import Mock, patch
        
        service = RecommendationService()
        
        # Create test data
        financial_state = FinancialState.default()
        user_intent = UserIntent.default()
        decision = AdvisorDecision.default()
        
        # Build recommendation data
        rec_data = service._build_recommendation_data(decision, financial_state, user_intent)
        
        # Verify all inputs are stored
        assert "financial_state_json" in rec_data
        assert "user_intent_json" in rec_data
        assert "decision_json" in rec_data
        
        # Verify stored data can be parsed
        stored_financial_state = FinancialState(**json.loads(rec_data["financial_state_json"]))
        stored_user_intent = UserIntent(**json.loads(rec_data["user_intent_json"]))
        stored_decision = AdvisorDecision(**json.loads(rec_data["decision_json"]))
        
        # Verify data matches
        assert stored_financial_state.emergency_fund_months == financial_state.emergency_fund_months
        assert stored_user_intent.type == user_intent.type
        assert stored_decision.decision == decision.decision
        
        # Verify evaluation timestamp is stored
        assert "evaluation_timestamp" in rec_data
        assert rec_data["evaluation_timestamp"] == financial_state.timestamp
    
    @pytest.mark.asyncio
    async def test_no_randomness_in_decisions(self, orchestrator, fixed_financial_state, fixed_user_intent):
        """Test that decisions contain no random elements."""
        # Run decision multiple times
        decisions = []
        for _ in range(5):
            decision = await orchestrator.decide(
                financial_state=fixed_financial_state,
                user_intent=fixed_user_intent,
                proposal=None
            )
            decisions.append(decision)
        
        # All decisions should be identical
        first_decision = decisions[0]
        for decision in decisions[1:]:
            assert decision.decision == first_decision.decision
            assert decision.metadata.get("guardrail_status") == first_decision.metadata.get("guardrail_status")
            
            # Proposals should be identical
            if decision.proposal and first_decision.proposal:
                assert decision.proposal.target_allocation.stocks == first_decision.proposal.target_allocation.stocks
                assert decision.proposal.risk_delta == first_decision.proposal.risk_delta
    
    @pytest.mark.asyncio
    async def test_deterministic_with_short_term_goals(self, orchestrator):
        """Test deterministic behavior with short-term goals."""
        from datetime import datetime, timedelta
        
        # Goal 3 months from fixed timestamp
        fixed_timestamp = "2024-01-15T10:00:00"
        goal_date = (datetime(2024, 1, 15) + timedelta(days=90)).isoformat()
        
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[
                FinancialGoal(
                    goal_id="goal-1",
                    name="Short-term goal",
                    target_amount=5000.0,
                    current_progress=2000.0,
                    target_date=goal_date,
                    priority=1
                )
            ],
            timestamp=fixed_timestamp
        )
        
        user_intent = UserIntent(type=UserIntentType.REBALANCE)
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=85.0, bonds=10.0, cash=5.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.2
        )
        
        # Run multiple times
        decision1 = await orchestrator.decide(financial_state, user_intent, proposal)
        decision2 = await orchestrator.decide(financial_state, user_intent, proposal)
        
        # Should produce same result
        assert decision1.decision == decision2.decision
        assert decision1.metadata.get("guardrail_status") == decision2.metadata.get("guardrail_status")
        
        # Computed months_away should be identical
        computed1 = decision1.metadata.get("computed_values", {})
        computed2 = decision2.metadata.get("computed_values", {})
        if "goal_goal-1_months_away" in computed1:
            assert computed1["goal_goal-1_months_away"] == computed2.get("goal_goal-1_months_away")

