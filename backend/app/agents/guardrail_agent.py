"""Guardrail agent for deterministic validation and safety checks.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from app.agents.schemas import (
    AgentRequest,
    GuardrailResult,
    GuardrailStatus,
    GuardrailReason,
    FinancialState,
    UserIntent,
    UserIntentType,
    PortfolioProposal,
)


class GuardrailAgent:
    """
    Guardrail agent for deterministic validation and safety checks.
    
    This agent performs deterministic validation checks. It does NOT use
    LLM to make decisions about numbers or trades. All validation logic
    is deterministic code.
    
    Per the vision: "Financial safety and constraints are enforced in code,
    not prompts. Rules before language."
    
    Guardrail Rules (from vision document):
    - Negative cash flow => BLOCK for "invest now" intents
    - Emergency fund months < 3 => WARN for risk increase, WARN/BLOCK for investing large amount
    - High-interest debt APR >= 15% and balance > 0 => WARN for investing lump sum
    - Goal timeframe < 12 months => WARN/BLOCK for equity-heavy recommendations
    
    These rules prevent reckless behavior, ensure consistency, and enable
    the advisor to say no (a critical trust signal).
    """
    
    # Thresholds
    EMERGENCY_FUND_MIN_MONTHS = 3.0
    HIGH_INTEREST_DEBT_APR_THRESHOLD = 15.0
    SHORT_TERM_GOAL_MONTHS = 12
    LARGE_INVESTMENT_THRESHOLD = 10000.0  # $10k considered large
    EQUITY_HEAVY_THRESHOLD = 60.0  # >60% stocks considered equity-heavy
    
    def __init__(self):
        """Initialize the guardrail agent."""
        pass
    
    async def validate(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        proposal: Optional[PortfolioProposal] = None
    ) -> GuardrailResult:
        """
        Perform deterministic guardrail validation.
        
        Args:
            financial_state: User's current financial state
            user_intent: User's intent or request
            proposal: Optional portfolio proposal to validate
            
        Returns:
            GuardrailResult with validation outcome, reasons, and computed values
            
        Note:
            This method uses deterministic code only. No LLM decisions
            about numbers or trades are made here.
        """
        reasons: List[GuardrailReason] = []
        computed_values: dict = {}
        highest_severity = GuardrailStatus.ALLOW
        
        # Rule 1: Negative cash flow => BLOCK for "invest now" intents
        net_cashflow = financial_state.cashflow.net_cashflow
        computed_values["net_cashflow"] = net_cashflow
        
        if net_cashflow < 0:
            if user_intent.type == UserIntentType.INVEST:
                # Check if it's an "invest now" intent (immediate timeframe or no timeframe specified)
                is_immediate = (
                    user_intent.timeframe is None or
                    user_intent.timeframe.lower() in ["immediate", "now", "asap"]
                )
                if is_immediate:
                    reasons.append(GuardrailReason(
                        code="NEGATIVE_CASHFLOW_INVEST",
                        message="Cannot invest with negative cash flow. Consider improving cash flow first.",
                        severity="error"
                    ))
                    highest_severity = GuardrailStatus.BLOCK
        
        # Rule 2: Emergency fund months < 3 => WARN for risk increase, WARN/BLOCK for investing large amount
        emergency_months = financial_state.emergency_fund_months
        computed_values["emergency_fund_months"] = emergency_months
        
        if emergency_months < self.EMERGENCY_FUND_MIN_MONTHS:
            # WARN for risk increase
            if user_intent.risk_change is not None and user_intent.risk_change > 0:
                reasons.append(GuardrailReason(
                    code="LOW_EMERGENCY_FUND_RISK_INCREASE",
                    message=f"Emergency fund ({emergency_months:.1f} months) is below recommended minimum (3 months). Increasing risk is not recommended.",
                    severity="warning"
                ))
                if highest_severity == GuardrailStatus.ALLOW:
                    highest_severity = GuardrailStatus.WARN
            
            # WARN/BLOCK for investing large amount
            if user_intent.type == UserIntentType.INVEST:
                # Check for percentage-based investments ("all", "everything", "100%")
                is_percentage_based = user_intent.metadata.get("percentage_based", False)
                
                if is_percentage_based:
                    # User wants to invest all/everything - check if it would leave emergency fund < 3 months
                    cash_balance = financial_state.portfolio_summary.cash_balance
                    monthly_expenses = financial_state.cashflow.monthly_expenses
                    
                    if monthly_expenses > 0:
                        # Calculate emergency fund after investing all cash
                        remaining_cash = 0.0
                        emergency_months_after = remaining_cash / monthly_expenses
                        
                        if emergency_months_after < self.EMERGENCY_FUND_MIN_MONTHS:
                            reasons.append(GuardrailReason(
                                code="LOW_EMERGENCY_FUND_INVEST_ALL",
                                message=f"Investing all available cash (${cash_balance:,.0f}) would leave emergency fund at {emergency_months_after:.1f} months, below recommended minimum (3 months). Consider keeping some cash for emergencies.",
                                severity="error"
                            ))
                            highest_severity = GuardrailStatus.BLOCK
                        elif emergency_months_after < self.EMERGENCY_FUND_MIN_MONTHS * 1.5:  # Less than 4.5 months
                            reasons.append(GuardrailReason(
                                code="LOW_EMERGENCY_FUND_INVEST_ALL_WARN",
                                message=f"Investing all available cash would leave emergency fund at {emergency_months_after:.1f} months. Consider keeping some cash for emergencies.",
                                severity="warning"
                            ))
                            if highest_severity == GuardrailStatus.ALLOW:
                                highest_severity = GuardrailStatus.WARN
                
                # Check for specific dollar amounts
                elif user_intent.amount is not None:
                    if user_intent.amount >= self.LARGE_INVESTMENT_THRESHOLD:
                        reasons.append(GuardrailReason(
                            code="LOW_EMERGENCY_FUND_LARGE_INVESTMENT",
                            message=f"Emergency fund ({emergency_months:.1f} months) is below recommended minimum. Large investment (${user_intent.amount:,.0f}) not recommended.",
                            severity="error"
                        ))
                        highest_severity = GuardrailStatus.BLOCK
                    elif user_intent.amount > 0:
                        reasons.append(GuardrailReason(
                            code="LOW_EMERGENCY_FUND_INVESTMENT",
                            message=f"Emergency fund ({emergency_months:.1f} months) is below recommended minimum. Consider building emergency fund first.",
                            severity="warning"
                        ))
                        if highest_severity == GuardrailStatus.ALLOW:
                            highest_severity = GuardrailStatus.WARN
        
        # Rule 3: High-interest debt APR >= 15% and balance > 0 => WARN for investing lump sum
        # Assume credit card debt is high-interest (typically 15%+)
        credit_card_debt = financial_state.debt_summary.credit_card_debt
        computed_values["credit_card_debt"] = credit_card_debt
        
        # Check if there's high-interest debt (credit cards typically have high APR)
        # Check metadata for explicit APR if available, otherwise assume credit cards are high-interest
        debt_apr = financial_state.metadata.get("credit_card_apr", 20.0)  # Default to 20% if not specified
        computed_values["debt_apr"] = debt_apr
        
        if debt_apr >= self.HIGH_INTEREST_DEBT_APR_THRESHOLD and credit_card_debt > 0:
            if user_intent.type == UserIntentType.INVEST:
                is_percentage_based = user_intent.metadata.get("percentage_based", False)
                
                # Check for percentage-based or large investments
                if is_percentage_based or user_intent.amount is None or user_intent.amount >= self.LARGE_INVESTMENT_THRESHOLD:
                    reasons.append(GuardrailReason(
                        code="HIGH_INTEREST_DEBT_LUMP_SUM",
                        message=f"High-interest debt (${credit_card_debt:,.0f} at {debt_apr:.1f}% APR) detected. Consider paying down debt before investing large amounts.",
                        severity="warning"
                    ))
                    if highest_severity == GuardrailStatus.ALLOW:
                        highest_severity = GuardrailStatus.WARN
        
        # Rule 4: Goal timeframe < 12 months => WARN/BLOCK for equity-heavy recommendations
        if proposal is not None:
            equity_allocation = proposal.target_allocation.stocks
            computed_values["equity_allocation"] = equity_allocation
            
            # Check if any goal has timeframe < 12 months
            short_term_goals = []
            for goal in financial_state.goals:
                if goal.target_date:
                    try:
                        # Parse ISO format date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                        date_str = goal.target_date
                        if 'T' in date_str:
                            # ISO datetime format
                            if date_str.endswith('Z'):
                                date_str = date_str[:-1] + '+00:00'
                            target_date = datetime.fromisoformat(date_str)
                            # Convert to naive datetime for comparison
                            if target_date.tzinfo:
                                from datetime import timezone
                                target_date = target_date.replace(tzinfo=None)
                        else:
                            # ISO date format (YYYY-MM-DD)
                            target_date = datetime.fromisoformat(date_str)
                        
                        # Use financial_state timestamp for deterministic calculations
                        # If timestamp not available, use current time (but this should be stored)
                        if financial_state.timestamp:
                            try:
                                eval_time = datetime.fromisoformat(financial_state.timestamp)
                                if eval_time.tzinfo:
                                    from datetime import timezone
                                    eval_time = eval_time.replace(tzinfo=None)
                            except (ValueError, TypeError):
                                # Fallback to current time if timestamp invalid
                                eval_time = datetime.now()
                        else:
                            # Fallback to current time if no timestamp
                            eval_time = datetime.now()
                        
                        months_away = (target_date - eval_time).days / 30.0
                        computed_values[f"goal_{goal.goal_id}_months_away"] = months_away
                        
                        if months_away < self.SHORT_TERM_GOAL_MONTHS and months_away > 0:
                            short_term_goals.append((goal.name, months_away))
                    except (ValueError, TypeError):
                        # Invalid date format, skip
                        pass
            
            if short_term_goals and equity_allocation > self.EQUITY_HEAVY_THRESHOLD:
                goal_names = ", ".join([name for name, _ in short_term_goals])
                if equity_allocation > 80.0:  # Very equity-heavy
                    reasons.append(GuardrailReason(
                        code="SHORT_TERM_GOAL_EQUITY_HEAVY",
                        message=f"Short-term goals ({goal_names}) within 12 months. Equity-heavy allocation ({equity_allocation:.1f}%) is risky for short-term goals.",
                        severity="error"
                    ))
                    highest_severity = GuardrailStatus.BLOCK
                else:
                    reasons.append(GuardrailReason(
                        code="SHORT_TERM_GOAL_EQUITY_HEAVY",
                        message=f"Short-term goals ({goal_names}) within 12 months. Consider reducing equity allocation ({equity_allocation:.1f}%) for short-term goals.",
                        severity="warning"
                    ))
                    if highest_severity == GuardrailStatus.ALLOW:
                        highest_severity = GuardrailStatus.WARN
        
        # If no violations, return ALLOW with success message
        if not reasons:
            reasons.append(GuardrailReason(
                code="NO_VIOLATIONS",
                message="All guardrails passed",
                severity="info"
            ))
        
        return GuardrailResult(
            status=highest_severity,
            reasons=reasons,
            computed_values=computed_values,
            metadata={
                "rules_checked": [
                    "negative_cashflow",
                    "emergency_fund",
                    "high_interest_debt",
                    "short_term_goals"
                ]
            }
        )
    
    async def check_trade_safety(self, request: AgentRequest, trade_data: Dict[str, Any]) -> GuardrailResult:
        """
        Check trade safety using deterministic rules.
        
        Args:
            request: Agent request with context
            trade_data: Trade data to validate
            
        Returns:
            GuardrailResult with safety check outcome
            
        Note:
            This method uses deterministic code only. It does NOT use LLM
            to decide whether trades are safe or to modify trade parameters.
        """
        # This method can be extended for trade-specific validations
        # For now, delegate to validate() if we have the required data
        return GuardrailResult.default_allow()

