"""Tests for guardrail agent deterministic validation.

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
from app.agents.guardrail_agent import GuardrailAgent
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
    GuardrailStatus,
)


class TestGuardrailAgent:
    """Test suite for GuardrailAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create guardrail agent instance."""
        return GuardrailAgent()
    
    @pytest.fixture
    def default_financial_state(self):
        """Default financial state for testing."""
        return FinancialState.default()
    
    @pytest.fixture
    def default_user_intent(self):
        """Default user intent for testing."""
        return UserIntent.default()
    
    async def test_negative_cashflow_blocks_invest_now(self, agent, default_user_intent):
        """Test that negative cash flow blocks 'invest now' intents."""
        # Create financial state with negative cash flow
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
        
        # Intent to invest immediately
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="immediate"
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        assert result.status == GuardrailStatus.BLOCK
        assert any(r.code == "NEGATIVE_CASHFLOW_INVEST" for r in result.reasons)
        assert result.computed_values["net_cashflow"] == -1000.0
    
    async def test_negative_cashflow_allows_future_invest(self, agent):
        """Test that negative cash flow allows future investment intents."""
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
        
        # Intent to invest in the future
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0,
            timeframe="6 months"
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        # Should not block (though may have other warnings)
        assert result.status != GuardrailStatus.BLOCK or not any(
            r.code == "NEGATIVE_CASHFLOW_INVEST" for r in result.reasons
        )
    
    async def test_low_emergency_fund_warns_risk_increase(self, agent, default_user_intent):
        """Test that low emergency fund warns on risk increase."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=2.0,  # Below 3 months
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.CHANGE_RISK,
            risk_change=0.2  # Increasing risk
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        assert result.status == GuardrailStatus.WARN
        assert any(r.code == "LOW_EMERGENCY_FUND_RISK_INCREASE" for r in result.reasons)
        assert result.computed_values["emergency_fund_months"] == 2.0
    
    async def test_low_emergency_fund_blocks_large_investment(self, agent):
        """Test that low emergency fund blocks large investments."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=2.0,  # Below 3 months
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=15000.0  # Large investment (> $10k)
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        assert result.status == GuardrailStatus.BLOCK
        assert any(r.code == "LOW_EMERGENCY_FUND_LARGE_INVESTMENT" for r in result.reasons)
    
    async def test_low_emergency_fund_warns_small_investment(self, agent):
        """Test that low emergency fund warns on small investments."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=2.0,  # Below 3 months
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0  # Small investment
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        assert result.status == GuardrailStatus.WARN
        assert any(r.code == "LOW_EMERGENCY_FUND_INVESTMENT" for r in result.reasons)
    
    async def test_high_interest_debt_warns_lump_sum(self, agent):
        """Test that high-interest debt warns on lump sum investments."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary(
                total_debt=5000.0,
                credit_card_debt=5000.0,  # High-interest debt
                mortgage_debt=0.0,
                student_loan_debt=0.0,
                other_debt=0.0,
                monthly_debt_payments=200.0
            ),
            portfolio_summary=PortfolioSummary.default(),
            goals=[],
            metadata={"credit_card_apr": 18.0}  # 18% APR >= 15%
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=15000.0  # Large lump sum
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        assert result.status == GuardrailStatus.WARN
        assert any(r.code == "HIGH_INTEREST_DEBT_LUMP_SUM" for r in result.reasons)
        assert result.computed_values["credit_card_debt"] == 5000.0
        assert result.computed_values["debt_apr"] == 18.0
    
    async def test_high_interest_debt_allows_small_investment(self, agent):
        """Test that high-interest debt allows small investments."""
        financial_state = FinancialState(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary(
                total_debt=5000.0,
                credit_card_debt=5000.0,
                mortgage_debt=0.0,
                student_loan_debt=0.0,
                other_debt=0.0,
                monthly_debt_payments=200.0
            ),
            portfolio_summary=PortfolioSummary.default(),
            goals=[],
            metadata={"credit_card_apr": 18.0}
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0  # Small investment
        )
        
        result = await agent.validate(financial_state, user_intent)
        
        # Should not warn for small investments
        assert not any(r.code == "HIGH_INTEREST_DEBT_LUMP_SUM" for r in result.reasons)
    
    async def test_short_term_goal_blocks_equity_heavy(self, agent):
        """Test that short-term goals block very equity-heavy proposals."""
        # Goal within 6 months
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
        
        # Very equity-heavy proposal (>80% stocks)
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=85.0, bonds=10.0, cash=5.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.2
        )
        
        user_intent = UserIntent(
            type=UserIntentType.REBALANCE
        )
        
        result = await agent.validate(financial_state, user_intent, proposal)
        
        assert result.status == GuardrailStatus.BLOCK
        assert any(r.code == "SHORT_TERM_GOAL_EQUITY_HEAVY" for r in result.reasons)
        assert result.computed_values["equity_allocation"] == 85.0
    
    async def test_short_term_goal_warns_moderate_equity(self, agent):
        """Test that short-term goals warn on moderately equity-heavy proposals."""
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
        
        # Moderately equity-heavy (60-80% stocks)
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=70.0, bonds=20.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.1
        )
        
        user_intent = UserIntent(
            type=UserIntentType.REBALANCE
        )
        
        result = await agent.validate(financial_state, user_intent, proposal)
        
        assert result.status == GuardrailStatus.WARN
        assert any(r.code == "SHORT_TERM_GOAL_EQUITY_HEAVY" for r in result.reasons)
    
    async def test_short_term_goal_allows_conservative_allocation(self, agent):
        """Test that short-term goals allow conservative allocations."""
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
        
        # Conservative allocation (<60% stocks)
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=40.0, bonds=40.0, cash=20.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.0
        )
        
        user_intent = UserIntent(
            type=UserIntentType.REBALANCE
        )
        
        result = await agent.validate(financial_state, user_intent, proposal)
        
        # Should not warn/block for conservative allocation
        assert not any(r.code == "SHORT_TERM_GOAL_EQUITY_HEAVY" for r in result.reasons)
    
    async def test_all_guardrails_pass(self, agent):
        """Test that all guardrails pass with healthy financial state."""
        financial_state = FinancialState(
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
            goals=[
                FinancialGoal(
                    goal_id="goal-1",
                    name="Retirement",
                    target_amount=1000000.0,
                    current_progress=100000.0,
                    target_date=(datetime.now() + timedelta(days=3650)).isoformat(),  # 10 years away
                    priority=1
                )
            ]
        )
        
        user_intent = UserIntent(
            type=UserIntentType.INVEST,
            amount=1000.0
        )
        
        proposal = PortfolioProposal(
            target_allocation=AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0),
            trades=[],
            reason_codes=["REBALANCE"],
            risk_delta=0.0
        )
        
        result = await agent.validate(financial_state, user_intent, proposal)
        
        assert result.status == GuardrailStatus.ALLOW
        assert any(r.code == "NO_VIOLATIONS" for r in result.reasons)
    
    async def test_computed_values_included(self, agent):
        """Test that computed values are included in result."""
        financial_state = FinancialState.default()
        user_intent = UserIntent.default()
        
        result = await agent.validate(financial_state, user_intent)
        
        assert "net_cashflow" in result.computed_values
        assert "emergency_fund_months" in result.computed_values
        assert "credit_card_debt" in result.computed_values

