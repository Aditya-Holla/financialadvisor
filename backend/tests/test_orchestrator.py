"""Tests for orchestrator agent decision making.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

import pytest
from datetime import datetime, timedelta
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
    Trade,
    AdvisorDecisionType,
    GuardrailStatus,
)


class TestOrchestratorDecide:
    """Test suite for OrchestratorAgent.decide()."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator agent instance."""
        return OrchestratorAgent()
    
    @pytest.fixture
    def healthy_financial_state(self):
        """Healthy financial state for testing."""
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
            goals=[]
        )
    
    @pytest.fixture
    def sample_proposal(self):
        """Sample portfolio proposal."""
        return PortfolioProposal(
            target_allocation=AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0),
            trades=[
                Trade(
                    symbol="AAPL",
                    action="BUY",
                    quantity=10,
                    estimated_price=150.0,
                    estimated_total=1500.0
                )
            ],
            reason_codes=["REBALANCE"],
            risk_delta=0.1,
            estimated_cost=1500.0
        )
    
    async def test_block_returns_reject_decision(self, orchestrator):
        """Test that BLOCK guardrail result returns REJECT decision."""
        # Financial state with negative cash flow
        financial_state = FinancialState(
            cashflow=Cashflow(
                monthly_income=2000.0,
                monthly_expenses=3000.0,
                net_cashflow=-1000.0
            ),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
        
        decision = await orchestrator.decide(financial_state, user_intent)
        
        assert decision.decision == AdvisorDecisionType.REJECT
        assert decision.proposal is None
        assert len(decision.explanation_inputs) > 0
        assert any(inp.key == "guardrail_status" for inp in decision.explanation_inputs)
        assert decision.metadata["guardrail_status"] == GuardrailStatus.BLOCK.value
    
    async def test_block_includes_explanation_inputs(self, orchestrator):
        """Test that BLOCK decision includes proper explanation inputs."""
        financial_state = FinancialState(
            cashflow=Cashflow(
                monthly_income=2000.0,
                monthly_expenses=3000.0,
                net_cashflow=-1000.0
            ),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
        
        decision = await orchestrator.decide(financial_state, user_intent)
        
        # Check for key explanation inputs
        input_keys = [inp.key for inp in decision.explanation_inputs]
        assert "guardrail_status" in input_keys
        assert "guardrail_reasons" in input_keys
        assert "net_cashflow" in input_keys
        assert "emergency_fund_months" in input_keys
    
    async def test_allow_returns_approve_decision(self, orchestrator, healthy_financial_state, sample_proposal):
        """Test that ALLOW guardrail result returns APPROVE decision."""
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        decision = await orchestrator.decide(healthy_financial_state, user_intent, sample_proposal)
        
        assert decision.decision == AdvisorDecisionType.APPROVE
        assert decision.proposal is not None
        assert decision.proposal == sample_proposal
        assert len(decision.explanation_inputs) > 0
        assert decision.metadata["guardrail_status"] == GuardrailStatus.ALLOW.value
    
    async def test_warn_returns_modify_decision(self, orchestrator):
        """Test that WARN guardrail result returns MODIFY decision."""
        # Financial state with low emergency fund
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=2.0,  # Below 3 months
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.CHANGE_RISK,
            risk_change=0.2
        )
        
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=70.0, bonds=20.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["RISK_ADJUSTMENT"],
            risk_delta=0.2
        )
        
        decision = await orchestrator.decide(financial_state, user_intent, proposal)
        
        assert decision.decision == AdvisorDecisionType.MODIFY
        assert decision.proposal is not None
        assert len(decision.required_confirmations) > 0
        assert decision.metadata["guardrail_status"] == GuardrailStatus.WARN.value
    
    async def test_warn_includes_required_confirmations(self, orchestrator):
        """Test that WARN decision includes required confirmations."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=2.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["INVESTMENT"],
            risk_delta=0.0
        )
        
        decision = await orchestrator.decide(financial_state, user_intent, proposal)
        
        assert len(decision.required_confirmations) > 0
        assert all(conf.required for conf in decision.required_confirmations)
        assert all(conf.message for conf in decision.required_confirmations)
    
    async def test_allow_includes_explanation_inputs(self, orchestrator, healthy_financial_state, sample_proposal):
        """Test that ALLOW decision includes proper explanation inputs."""
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        decision = await orchestrator.decide(healthy_financial_state, user_intent, sample_proposal)
        
        input_keys = [inp.key for inp in decision.explanation_inputs]
        assert "guardrail_status" in input_keys
        assert "equity_allocation" in input_keys
        assert "risk_delta" in input_keys
        assert "intent_type" in input_keys
        assert "portfolio_value" in input_keys
    
    async def test_stub_proposal_created_when_none_provided(self, orchestrator, healthy_financial_state):
        """Test that stub proposal is created when none is provided."""
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        decision = await orchestrator.decide(healthy_financial_state, user_intent, proposal=None)
        
        assert decision.proposal is not None
        assert decision.proposal.metadata.get("is_stub") is True
        assert "STUB_PROPOSAL" in decision.proposal.reason_codes
    
    async def test_stub_proposal_uses_intent_amount(self, orchestrator, healthy_financial_state):
        """Test that stub proposal uses intent amount."""
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=5000.0
        )
        
        decision = await orchestrator.decide(healthy_financial_state, user_intent, proposal=None)
        
        assert decision.proposal is not None
        assert decision.proposal.estimated_cost == 5000.0
    
    async def test_decision_includes_guardrail_reasons_in_metadata(self, orchestrator):
        """Test that decision includes guardrail reasons in metadata."""
        financial_state = FinancialState(
            cashflow=Cashflow(
                monthly_income=2000.0,
                monthly_expenses=3000.0,
                net_cashflow=-1000.0
            ),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
        
        decision = await orchestrator.decide(financial_state, user_intent)
        
        assert "guardrail_reasons" in decision.metadata
        assert len(decision.metadata["guardrail_reasons"]) > 0
        assert isinstance(decision.metadata["guardrail_reasons"], list)
    
    async def test_decision_includes_computed_values_for_allow(self, orchestrator, healthy_financial_state, sample_proposal):
        """Test that ALLOW decision includes computed values in metadata."""
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        decision = await orchestrator.decide(healthy_financial_state, user_intent, sample_proposal)
        
        assert "computed_values" in decision.metadata
        assert isinstance(decision.metadata["computed_values"], dict)
    
    async def test_short_term_goal_creates_appropriate_decision(self, orchestrator):
        """Test that short-term goals create appropriate decision."""
        goal_date = (datetime.now() + timedelta(days=180)).isoformat()
        
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
            ]
        )
        
        # Equity-heavy proposal
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=85.0, bonds=10.0, cash=5.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.2
        )
        
        user_intent = UserIntent(
            type=UserIntentType.REBALANCE
        )
        
        decision = await orchestrator.decide(financial_state, user_intent, proposal)
        
        # Should be BLOCK or MODIFY depending on equity allocation
        assert decision.decision in [AdvisorDecisionType.REJECT, AdvisorDecisionType.MODIFY]
        if decision.decision == AdvisorDecisionType.REJECT:
            assert decision.proposal is None
        else:
            assert decision.proposal is not None
    
    async def test_no_proposal_when_blocked(self, orchestrator):
        """Test that no proposal is included when decision is REJECT."""
        financial_state = FinancialState(
            cashflow=Cashflow(
                monthly_income=2000.0,
                monthly_expenses=3000.0,
                net_cashflow=-1000.0
            ),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
        
        # Even if proposal is provided, it should be None when blocked
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["INVESTMENT"],
            risk_delta=0.0
        )
        
        decision = await orchestrator.decide(financial_state, user_intent, proposal)
        
        assert decision.decision == AdvisorDecisionType.REJECT
        assert decision.proposal is None

