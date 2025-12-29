"""Schemas for agent layer communication.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone


class AgentContext(BaseModel):
    """Context passed between agents."""
    
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class AgentRequest(BaseModel):
    """Base request model for agents."""
    
    context: AgentContext = Field(..., description="Agent context")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Request timestamp")


class AgentResponse(BaseModel):
    """Base response model for agents."""
    
    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Response timestamp")


class TutorMessage(BaseModel):
    """Message for tutor agent interaction."""
    
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Message timestamp")


# Canonical Financial Schemas

class Cashflow(BaseModel):
    """Monthly cashflow summary."""
    
    monthly_income: float = Field(0.0, ge=0.0, description="Monthly income in dollars")
    monthly_expenses: float = Field(0.0, ge=0.0, description="Monthly expenses in dollars")
    net_cashflow: float = Field(0.0, description="Net monthly cashflow (income - expenses)")
    
    @classmethod
    def default(cls) -> "Cashflow":
        """Unit-testable default."""
        return cls(monthly_income=5000.0, monthly_expenses=3000.0, net_cashflow=2000.0)


class DebtSummary(BaseModel):
    """Summary of user's debt obligations."""
    
    total_debt: float = Field(0.0, ge=0.0, description="Total debt in dollars")
    credit_card_debt: float = Field(0.0, ge=0.0, description="Credit card debt in dollars")
    mortgage_debt: float = Field(0.0, ge=0.0, description="Mortgage debt in dollars")
    student_loan_debt: float = Field(0.0, ge=0.0, description="Student loan debt in dollars")
    other_debt: float = Field(0.0, ge=0.0, description="Other debt in dollars")
    monthly_debt_payments: float = Field(0.0, ge=0.0, description="Monthly debt payments in dollars")
    
    @classmethod
    def default(cls) -> "DebtSummary":
        """Unit-testable default."""
        return cls(
            total_debt=10000.0,
            credit_card_debt=5000.0,
            mortgage_debt=0.0,
            student_loan_debt=5000.0,
            other_debt=0.0,
            monthly_debt_payments=500.0
        )


class PortfolioSummary(BaseModel):
    """Summary of user's investment portfolio."""
    
    total_value: float = Field(0.0, ge=0.0, description="Total portfolio value in dollars")
    cash_balance: float = Field(0.0, ge=0.0, description="Cash balance in dollars")
    invested_value: float = Field(0.0, ge=0.0, description="Invested value in dollars")
    positions_count: int = Field(0, ge=0, description="Number of positions")
    positions: List[Dict[str, Any]] = Field(default_factory=list, description="List of position details")
    
    @classmethod
    def default(cls) -> "PortfolioSummary":
        """Unit-testable default."""
        return cls(
            total_value=50000.0,
            cash_balance=10000.0,
            invested_value=40000.0,
            positions_count=5,
            positions=[
                {"symbol": "AAPL", "quantity": 10, "value": 15000.0},
                {"symbol": "MSFT", "quantity": 5, "value": 15000.0},
                {"symbol": "GOOGL", "quantity": 10, "value": 10000.0}
            ]
        )


class FinancialGoal(BaseModel):
    """A financial goal."""
    
    goal_id: str = Field(..., description="Unique goal identifier")
    name: str = Field(..., description="Goal name")
    target_amount: float = Field(0.0, ge=0.0, description="Target amount in dollars")
    current_progress: float = Field(0.0, ge=0.0, description="Current progress toward goal in dollars")
    target_date: Optional[str] = Field(None, description="Target date (ISO format)")
    priority: int = Field(1, ge=1, le=5, description="Priority level (1-5)")
    
    @classmethod
    def default(cls) -> "FinancialGoal":
        """Unit-testable default."""
        return cls(
            goal_id="goal-1",
            name="Emergency Fund",
            target_amount=20000.0,
            current_progress=10000.0,
            target_date=None,
            priority=1
        )


class FinancialState(BaseModel):
    """Complete financial state of the user."""
    
    cashflow: Cashflow = Field(default_factory=Cashflow.default, description="Monthly cashflow")
    emergency_fund_months: float = Field(0.0, ge=0.0, description="Emergency fund coverage in months")
    debt_summary: DebtSummary = Field(default_factory=DebtSummary.default, description="Debt obligations")
    portfolio_summary: PortfolioSummary = Field(default_factory=PortfolioSummary.default, description="Investment portfolio")
    goals: List[FinancialGoal] = Field(default_factory=list, description="Financial goals")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="State timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (e.g., credit_card_apr)")
    
    @classmethod
    def default(cls) -> "FinancialState":
        """Unit-testable default."""
        return cls(
            cashflow=Cashflow.default(),
            emergency_fund_months=6.0,
            debt_summary=DebtSummary.default(),
            portfolio_summary=PortfolioSummary.default(),
            goals=[FinancialGoal.default()],
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={}
        )


class UserIntentType(str, Enum):
    """Types of user intents."""
    
    INVEST = "invest"
    WITHDRAW = "withdraw"
    REBALANCE = "rebalance"
    CHANGE_RISK = "change_risk"
    SET_GOAL = "set_goal"
    UPDATE_PROFILE = "update_profile"
    GET_ADVICE = "get_advice"
    OTHER = "other"


class UserIntent(BaseModel):
    """User's intent or request."""
    
    type: UserIntentType = Field(..., description="Type of intent")
    amount: Optional[float] = Field(None, ge=0.0, description="Amount in dollars (for transactions)")
    risk_change: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Risk change (-1.0 to 1.0)")
    target: Optional[str] = Field(None, description="Target symbol, goal, or other identifier")
    timeframe: Optional[str] = Field(None, description="Timeframe for the intent (e.g., '1 year', 'immediate')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional intent metadata")
    
    @classmethod
    def default(cls) -> "UserIntent":
        """Unit-testable default."""
        return cls(
            type=UserIntentType.INVEST,
            amount=1000.0,
            risk_change=None,
            target=None,
            timeframe="immediate",
            metadata={}
        )


class GuardrailStatus(str, Enum):
    """Guardrail validation status."""
    
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


class GuardrailReason(BaseModel):
    """A reason for guardrail validation result."""
    
    code: str = Field(..., description="Reason code (e.g., 'INSUFFICIENT_CASH', 'RISK_TOO_HIGH')")
    message: str = Field(..., description="Human-readable reason message")
    severity: str = Field(..., description="Severity: 'info', 'warning', or 'error'")
    
    @classmethod
    def default(cls) -> "GuardrailReason":
        """Unit-testable default."""
        return cls(
            code="NO_VIOLATION",
            message="No violations detected",
            severity="info"
        )


class GuardrailResult(BaseModel):
    """Result from guardrail validation with status, reasons, and computed values."""
    
    status: GuardrailStatus = Field(..., description="Validation status: ALLOW, WARN, or BLOCK")
    reasons: List[GuardrailReason] = Field(default_factory=list, description="List of reason codes and messages")
    computed_values: Dict[str, Any] = Field(default_factory=dict, description="Computed values used in validation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")
    
    @classmethod
    def default_allow(cls) -> "GuardrailResult":
        """Unit-testable default - ALLOW status."""
        return cls(
            status=GuardrailStatus.ALLOW,
            reasons=[GuardrailReason.default()],
            computed_values={"risk_score": 0.5, "cash_available": 10000.0},
            metadata={}
        )
    
    @classmethod
    def default_warn(cls) -> "GuardrailResult":
        """Unit-testable default - WARN status."""
        return cls(
            status=GuardrailStatus.WARN,
            reasons=[
                GuardrailReason(
                    code="HIGH_RISK_ALLOCATION",
                    message="Proposed allocation has higher risk than user profile",
                    severity="warning"
                )
            ],
            computed_values={"risk_score": 0.7, "profile_risk": 0.5},
            metadata={}
        )
    
    @classmethod
    def default_block(cls) -> "GuardrailResult":
        """Unit-testable default - BLOCK status."""
        return cls(
            status=GuardrailStatus.BLOCK,
            reasons=[
                GuardrailReason(
                    code="INSUFFICIENT_CASH",
                    message="Insufficient cash to execute trade",
                    severity="error"
                )
            ],
            computed_values={"cash_available": 500.0, "required": 1000.0},
            metadata={}
        )


class Trade(BaseModel):
    """A single trade to execute."""
    
    symbol: str = Field(..., description="Stock ticker symbol")
    action: str = Field(..., description="Trade action: 'BUY' or 'SELL'")
    quantity: int = Field(..., ge=1, description="Number of shares")
    estimated_price: Optional[float] = Field(None, ge=0.0, description="Estimated price per share")
    estimated_total: Optional[float] = Field(None, ge=0.0, description="Estimated total value")
    
    @classmethod
    def default(cls) -> "Trade":
        """Unit-testable default."""
        return cls(
            symbol="AAPL",
            action="BUY",
            quantity=10,
            estimated_price=150.0,
            estimated_total=1500.0
        )


class AssetAllocation(BaseModel):
    """Target asset allocation percentages."""
    
    stocks: float = Field(0.0, ge=0.0, le=100.0, description="Stocks allocation percentage")
    bonds: float = Field(0.0, ge=0.0, le=100.0, description="Bonds allocation percentage")
    cash: float = Field(0.0, ge=0.0, le=100.0, description="Cash allocation percentage")
    other: float = Field(0.0, ge=0.0, le=100.0, description="Other assets allocation percentage")
    
    @model_validator(mode='after')
    def validate_allocation_sum(self) -> "AssetAllocation":
        """Validate that allocations sum to approximately 100%."""
        total = self.stocks + self.bonds + self.cash + self.other
        if abs(total - 100.0) > 0.01:  # Allow small floating point differences
            raise ValueError(f"Asset allocations must sum to 100%, got {total}%")
        return self
    
    @classmethod
    def default(cls) -> "AssetAllocation":
        """Unit-testable default."""
        return cls(stocks=70.0, bonds=20.0, cash=10.0, other=0.0)


class PortfolioProposal(BaseModel):
    """Proposed portfolio changes."""
    
    target_allocation: AssetAllocation = Field(..., description="Target asset allocation")
    trades: List[Trade] = Field(default_factory=list, description="List of trades to execute")
    reason_codes: List[str] = Field(default_factory=list, description="Reason codes for the proposal")
    risk_delta: float = Field(0.0, description="Change in risk score (-1.0 to 1.0)")
    estimated_cost: Optional[float] = Field(None, ge=0.0, description="Estimated total cost in dollars")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional proposal metadata")
    
    @classmethod
    def default(cls) -> "PortfolioProposal":
        """Unit-testable default."""
        return cls(
            target_allocation=AssetAllocation.default(),
            trades=[Trade.default()],
            reason_codes=["REBALANCE", "RISK_ADJUSTMENT"],
            risk_delta=0.1,
            estimated_cost=1500.0,
            metadata={}
        )


class AdvisorDecisionType(str, Enum):
    """Types of advisor decisions."""
    
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    REQUEST_INFO = "request_info"
    DEFER = "defer"


class RequiredConfirmation(BaseModel):
    """A confirmation required from the user."""
    
    confirmation_id: str = Field(..., description="Unique confirmation identifier")
    type: str = Field(..., description="Confirmation type (e.g., 'risk_acknowledgment', 'amount_verification')")
    message: str = Field(..., description="Message to display to user")
    required: bool = Field(True, description="Whether confirmation is required")
    confirmation_text: Optional[str] = Field(None, description="Checkbox text for WARN confirmations")
    override_acknowledgement: Optional[str] = Field(None, description="Explicit override text for BLOCK confirmations")
    
    @classmethod
    def default(cls) -> "RequiredConfirmation":
        """Unit-testable default."""
        return cls(
            confirmation_id="conf-1",
            type="risk_acknowledgment",
            message="This proposal increases your risk exposure. Do you want to proceed?",
            required=True,
            confirmation_text="I understand the risks and want to proceed",
            override_acknowledgement=None
        )


class ExplanationInput(BaseModel):
    """Input data for generating explanations."""
    
    key: str = Field(..., description="Input key (e.g., 'risk_score', 'allocation_change')")
    value: Any = Field(..., description="Input value")
    description: Optional[str] = Field(None, description="Description of the input")
    
    @classmethod
    def default(cls) -> "ExplanationInput":
        """Unit-testable default."""
        return cls(
            key="risk_score",
            value=0.6,
            description="Current portfolio risk score"
        )


class AdvisorDecision(BaseModel):
    """Advisor's decision on a user request."""
    
    decision: AdvisorDecisionType = Field(..., description="The decision made")
    proposal: Optional[PortfolioProposal] = Field(None, description="Optional portfolio proposal")
    required_confirmations: List[RequiredConfirmation] = Field(default_factory=list, description="Required user confirmations")
    explanation_inputs: List[ExplanationInput] = Field(default_factory=list, description="Inputs for explanation generation")
    reasoning: Optional[str] = Field(None, description="Reasoning for the decision")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")
    
    @classmethod
    def default(cls) -> "AdvisorDecision":
        """Unit-testable default."""
        return cls(
            decision=AdvisorDecisionType.APPROVE,
            proposal=PortfolioProposal.default(),
            required_confirmations=[RequiredConfirmation.default()],
            explanation_inputs=[ExplanationInput.default()],
            reasoning="Proposal aligns with user profile and financial goals",
            metadata={}
        )


class TeachingPoint(BaseModel):
    """A teaching point in the explanation."""
    
    topic: str = Field(..., description="Topic of the teaching point")
    explanation: str = Field(..., description="Educational explanation")
    relevance: str = Field(..., description="Why this is relevant to the decision")


class TutorExplanation(BaseModel):
    """Tutor agent explanation of an advisor decision."""
    
    explanation_text: str = Field(..., description="Main explanation text")
    teaching_points: List[TeachingPoint] = Field(default_factory=list, description="Educational teaching points")
    guardrail_references: List[str] = Field(default_factory=list, description="Guardrail reason codes referenced")
    proposal_referenced: bool = Field(False, description="Whether portfolio proposal is referenced")
    
    @classmethod
    def default(cls) -> "TutorExplanation":
        """Unit-testable default."""
        return cls(
            explanation_text="This recommendation has been reviewed and approved.",
            teaching_points=[
                TeachingPoint(
                    topic="Portfolio Diversification",
                    explanation="Diversification helps reduce risk by spreading investments across different assets.",
                    relevance="This proposal maintains a balanced allocation."
                )
            ],
            guardrail_references=[],
            proposal_referenced=True
        )

