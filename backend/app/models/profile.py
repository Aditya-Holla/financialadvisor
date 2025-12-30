"""Profile request and response models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.agents.schemas import (
    Cashflow,
    DebtSummary,
    FinancialGoal,
    FinancialState,
)


class ProfileResponse(BaseModel):
    """Profile response matching FinancialState schema."""
    
    cashflow: Cashflow = Field(..., description="Monthly cashflow")
    emergency_fund_months: float = Field(0.0, ge=0.0, description="Emergency fund coverage in months")
    debt_summary: DebtSummary = Field(..., description="Debt obligations")
    goals: List[FinancialGoal] = Field(default_factory=list, description="Financial goals")
    risk_level: Optional[str] = Field(None, description="Risk tolerance level (conservative, moderate, aggressive)")
    investment_horizon: Optional[str] = Field(None, description="Investment horizon (short, medium, long)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (e.g., credit_card_apr)")
    
    @classmethod
    def from_financial_state(cls, financial_state: FinancialState, risk_level: Optional[str] = None, investment_horizon: Optional[str] = None) -> "ProfileResponse":
        """Create ProfileResponse from FinancialState."""
        return cls(
            cashflow=financial_state.cashflow,
            emergency_fund_months=financial_state.emergency_fund_months,
            debt_summary=financial_state.debt_summary,
            goals=financial_state.goals,
            risk_level=risk_level,
            investment_horizon=investment_horizon,
            metadata=financial_state.metadata
        )


class ProfileUpdateRequest(BaseModel):
    """Request model for updating profile."""
    
    cashflow: Optional[Cashflow] = Field(None, description="Monthly cashflow")
    emergency_fund_months: Optional[float] = Field(None, ge=0.0, description="Emergency fund coverage in months")
    debt_summary: Optional[DebtSummary] = Field(None, description="Debt obligations")
    goals: Optional[List[FinancialGoal]] = Field(None, description="Financial goals")
    risk_level: Optional[str] = Field(None, description="Risk tolerance level (conservative, moderate, aggressive)")
    investment_horizon: Optional[str] = Field(None, description="Investment horizon (short, medium, long)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (e.g., credit_card_apr)")

