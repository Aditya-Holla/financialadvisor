"""Guardrail agent for deterministic validation and safety checks.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

Guardrail Agent Responsibilities:
- Evaluates user intent explicitly
- Returns structured decisions: ALLOW, WARN_AND_EDUCATE, BLOCK
- Blocks high-risk instructions
- Provides educational alternatives (not recommendations)

Hard Constraints:
- MUST NOT recommend stocks, portfolios, or actions
- MUST NOT explain market fundamentals in depth
- MUST NOT provide financial advice
- Acts as a compliance and safety filter, not a conversational assistant
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
    IntentDecision,
    IntentDecisionType,
)


class GuardrailAgent:
    """
    Guardrail agent for deterministic validation and intent evaluation.
    
    This agent acts as a compliance and safety filter that:
    1. Evaluates user intent explicitly
    2. Returns structured decisions: ALLOW, WARN_AND_EDUCATE, BLOCK
    3. Blocks high-risk instructions
    4. Provides educational alternatives (not recommendations)
    
    This agent does NOT:
    - Recommend stocks, portfolios, or actions
    - Explain market fundamentals in depth
    - Provide financial advice
    - Act as a conversational assistant
    
    All validation logic is deterministic code. No LLM decisions about
    numbers or trades are made here.
    
    Guardrail Rules (for validate method):
    - Negative cash flow => BLOCK for "invest now" intents
    - Emergency fund months < 3 => WARN_AND_EDUCATE for risk increase (intent-related), WARN/BLOCK for investing large amount
    - High-interest debt APR >= 15% and balance > 0 => WARN_AND_EDUCATE for investing lump sum (intent-related)
    - Goal timeframe < 12 months => WARN/BLOCK for equity-heavy recommendations (proposal validation - uses WARN)
    
    Note:
    - WARN_AND_EDUCATE: Used for user intent evaluation warnings (intent-related concerns)
    - WARN: Reserved for proposal/output validation warnings (proposal-specific issues)
    """
    
    # Thresholds
    EMERGENCY_FUND_MIN_MONTHS = 3.0
    HIGH_INTEREST_DEBT_APR_THRESHOLD = 15.0
    SHORT_TERM_GOAL_MONTHS = 12
    LARGE_INVESTMENT_THRESHOLD = 10000.0  # $10k considered large
    EQUITY_HEAVY_THRESHOLD = 60.0  # >60% stocks considered equity-heavy
    
    # High-risk patterns for intent evaluation
    HIGH_RISK_PATTERNS = [
        "invest all",
        "all my money",
        "everything i have",
        "guaranteed returns",
        "guaranteed profit",
        "risk-free",
        "what should i buy",
        "what to buy right now",
        "what stock should i",
        "best stock to buy",
        "sure thing",
        "can't lose",
    ]
    
    def __init__(self):
        """Initialize the guardrail agent."""
        pass
    
    async def evaluate_intent(
        self,
        user_intent: UserIntent,
        financial_state: Optional[FinancialState] = None
    ) -> IntentDecision:
        """
        Evaluate user intent and return explicit structured decision.
        
        This method evaluates the user's intent for safety and compliance.
        It checks for high-risk patterns and recommendation requests.
        
        Decision Logic:
        - High-risk instructions (e.g., "invest all my money", "guaranteed returns")
          -> BLOCK
        - Requests for recommendations (GET_ADVICE intent or recommendation language)
          -> WARN_AND_EDUCATE (by default)
        - Safe, specific requests -> ALLOW
        
        Args:
            user_intent: User's intent or request
            financial_state: Optional financial state for context
            
        Returns:
            IntentDecision with decision, reason, and safe_alternative
            
        Note:
            This method does NOT recommend stocks, portfolios, or actions.
            safe_alternative provides educational guidance only.
        """
        # Extract intent text from metadata if available
        intent_text = user_intent.metadata.get("text", "").lower() if user_intent.metadata else ""
        
        # Check for high-risk patterns in intent
        if self._contains_high_risk_pattern(intent_text, user_intent, financial_state):
            return IntentDecision(
                decision=IntentDecisionType.BLOCK,
                reason="This request contains high-risk language that could lead to financial harm. We cannot proceed with requests that promise guaranteed returns or suggest investing all available funds.",
                safe_alternative="Consider speaking with a licensed financial advisor about your goals and risk tolerance before making investment decisions."
            )
        
        # Check for recommendation requests
        if self._is_recommendation_request(user_intent, intent_text):
            return IntentDecision(
                decision=IntentDecisionType.WARN_AND_EDUCATE,
                reason="This appears to be a request for investment recommendations. We provide educational information and portfolio analysis, but cannot provide specific investment advice.",
                safe_alternative="You can review your portfolio allocation, understand your risk profile, and learn about diversification principles. For specific investment recommendations, consult a licensed financial advisor."
            )
        
        # Default: ALLOW for specific, safe requests
        return IntentDecision(
            decision=IntentDecisionType.ALLOW,
            reason="This request appears safe to proceed.",
            safe_alternative=None
        )
    
    def _contains_high_risk_pattern(
        self,
        intent_text: str,
        user_intent: UserIntent,
        financial_state: Optional[FinancialState] = None
    ) -> bool:
        """
        Check if intent contains high-risk patterns.
        
        Args:
            intent_text: Lowercase text from intent metadata
            user_intent: User intent object
            financial_state: Optional financial state for context
            
        Returns:
            True if high-risk pattern detected
        """
        # Check text patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if pattern in intent_text:
                return True
        
        # Check for "invest all" via amount comparison
        if user_intent.type == UserIntentType.INVEST and user_intent.amount:
            # If amount is very large relative to portfolio, could be "all money"
            # This is a heuristic - actual check would need portfolio value
            if financial_state and hasattr(financial_state, 'portfolio_summary'):
                portfolio_value = financial_state.portfolio_summary.total_value
                if portfolio_value > 0 and user_intent.amount >= portfolio_value * 0.95:
                    return True
        
        return False
    
    def _is_recommendation_request(self, user_intent: UserIntent, intent_text: str) -> bool:
        """
        Check if intent is a request for recommendations.
        
        Args:
            user_intent: User intent object
            intent_text: Lowercase text from intent metadata
            
        Returns:
            True if this is a recommendation request
        """
        # Check intent type
        if user_intent.type == UserIntentType.GET_ADVICE:
            return True
        
        # Check for recommendation language patterns
        recommendation_patterns = [
            "what should i",
            "what do you recommend",
            "what would you",
            "recommend",
            "suggest",
            "advice",
            "what to invest",
            "should i buy",
        ]
        
        for pattern in recommendation_patterns:
            if pattern in intent_text:
                return True
        
        return False
    
    async def validate(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        proposal: Optional[PortfolioProposal] = None
    ) -> GuardrailResult:
        """
        Perform deterministic guardrail validation.
        
        This method validates financial state and proposals against safety rules.
        For intent evaluation, use evaluate_intent() instead.
        
        Args:
            financial_state: User's current financial state
            user_intent: User's intent or request
            proposal: Optional portfolio proposal to validate
            
        Returns:
            GuardrailResult with validation outcome, reasons, and computed values
            
        Note:
            This method uses deterministic code only. No LLM decisions
            about numbers or trades are made here.
            This method does NOT recommend stocks, portfolios, or actions.
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
        
        # Rule 2: Emergency fund months < 3 => WARN_AND_EDUCATE for risk increase (intent-related), WARN/BLOCK for investing large amount
        emergency_months = financial_state.emergency_fund_months
        computed_values["emergency_fund_months"] = emergency_months
        
        if emergency_months < self.EMERGENCY_FUND_MIN_MONTHS:
            # WARN_AND_EDUCATE for risk increase (intent-related warning)
            if user_intent.risk_change is not None and user_intent.risk_change > 0:
                reasons.append(GuardrailReason(
                    code="LOW_EMERGENCY_FUND_RISK_INCREASE",
                    message=f"Emergency fund ({emergency_months:.1f} months) is below recommended minimum (3 months). Increasing risk is not recommended.",
                    severity="warning"
                ))
                if highest_severity == GuardrailStatus.ALLOW:
                    highest_severity = GuardrailStatus.WARN_AND_EDUCATE
            
            # WARN/BLOCK for investing large amount
            if user_intent.type == UserIntentType.INVEST and user_intent.amount is not None:
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
        
        # Rule 3: High-interest debt APR >= 15% and balance > 0 => WARN_AND_EDUCATE for investing lump sum (intent-related)
        # Assume credit card debt is high-interest (typically 15%+)
        credit_card_debt = financial_state.debt_summary.credit_card_debt
        computed_values["credit_card_debt"] = credit_card_debt
        
        # Check if there's high-interest debt (credit cards typically have high APR)
        # Check metadata for explicit APR if available, otherwise assume credit cards are high-interest
        debt_apr = financial_state.metadata.get("credit_card_apr", 20.0)  # Default to 20% if not specified
        computed_values["debt_apr"] = debt_apr
        
        if debt_apr >= self.HIGH_INTEREST_DEBT_APR_THRESHOLD and credit_card_debt > 0:
            if user_intent.type == UserIntentType.INVEST and user_intent.amount is not None:
                if user_intent.amount >= self.LARGE_INVESTMENT_THRESHOLD:
                    reasons.append(GuardrailReason(
                        code="HIGH_INTEREST_DEBT_LUMP_SUM",
                        message=f"High-interest debt (${credit_card_debt:,.0f} at {debt_apr:.1f}% APR) detected. Consider paying down debt before investing large amounts.",
                        severity="warning"
                    ))
                    # WARN_AND_EDUCATE for intent-related warning (user wants to invest large amount)
                    if highest_severity == GuardrailStatus.ALLOW:
                        highest_severity = GuardrailStatus.WARN_AND_EDUCATE
        
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
                    # WARN for proposal validation (proposal-specific issue, not intent-related)
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

