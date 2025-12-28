"""Orchestrator agent for coordinating agent workflows.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, List
from app.agents.schemas import (
    AgentRequest,
    AgentResponse,
    FinancialState,
    UserIntent,
    PortfolioProposal,
    AdvisorDecision,
    AdvisorDecisionType,
    GuardrailResult,
    GuardrailStatus,
    ExplanationInput,
    RequiredConfirmation,
)
from app.agents.guardrail_agent import GuardrailAgent


class OrchestratorAgent:
    """
    Orchestrator agent that coordinates workflow between specialized agents.
    
    This agent manages the flow of information between guardrail_agent,
    tutor_agent, and other components without containing business logic.
    
    Note: This agent does NOT call Alpaca, DB, or LLM services.
    It only orchestrates between agents using deterministic logic.
    """
    
    def __init__(self, guardrail_agent: Optional[GuardrailAgent] = None):
        """
        Initialize the orchestrator agent.
        
        Args:
            guardrail_agent: Optional guardrail agent instance (creates new if not provided)
        """
        self.guardrail_agent = guardrail_agent or GuardrailAgent()
    
    async def decide(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        proposal: Optional[PortfolioProposal] = None
    ) -> AdvisorDecision:
        """
        Make an advisor decision based on financial state, user intent, and proposal.
        
        Flow:
        1. Evaluate guardrails
        2. If BLOCK -> return REJECT decision with explanation_inputs only
        3. If ALLOW/WARN -> accept proposal (stub if needed) and return decision
        
        Args:
            financial_state: User's current financial state
            user_intent: User's intent or request
            proposal: Optional portfolio proposal from model (will create stub if needed)
            
        Returns:
            AdvisorDecision with decision, proposal (if allowed), and explanation inputs
            
        Note:
            This method does NOT call Alpaca, DB, or LLM services.
            It only orchestrates deterministic guardrail checks.
        """
        # Step 1: Evaluate guardrails
        guardrail_result = await self.guardrail_agent.validate(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=proposal
        )
        
        # Step 2: If BLOCK -> return REJECT decision with explanation_inputs only
        if guardrail_result.status == GuardrailStatus.BLOCK:
            explanation_inputs = self._build_explanation_inputs_from_guardrails(
                guardrail_result,
                financial_state,
                user_intent
            )
            
            return AdvisorDecision(
                decision=AdvisorDecisionType.REJECT,
                proposal=None,  # No proposal when blocked
                required_confirmations=[],
                explanation_inputs=explanation_inputs,
                reasoning="Request blocked by guardrails. See explanation inputs for details.",
                metadata={
                    "guardrail_status": guardrail_result.status.value,
                    "guardrail_reasons": [r.code for r in guardrail_result.reasons]
                }
            )
        
        # Step 3: If ALLOW/WARN -> accept proposal (stub if needed) and return decision
        # Create stub proposal if none provided
        if proposal is None:
            proposal = self._create_stub_proposal(user_intent, financial_state)
        
        # Build explanation inputs
        explanation_inputs = self._build_explanation_inputs(
            guardrail_result,
            financial_state,
            user_intent,
            proposal
        )
        
        # Build required confirmations based on warnings
        required_confirmations = self._build_confirmations_from_guardrails(guardrail_result)
        
        # Determine decision type
        if guardrail_result.status == GuardrailStatus.WARN:
            decision_type = AdvisorDecisionType.MODIFY
            reasoning = "Proposal has warnings. Review guardrail results before proceeding."
        else:
            decision_type = AdvisorDecisionType.APPROVE
            reasoning = "Proposal passes all guardrails."
        
        return AdvisorDecision(
            decision=decision_type,
            proposal=proposal,
            required_confirmations=required_confirmations,
            explanation_inputs=explanation_inputs,
            reasoning=reasoning,
            metadata={
                "guardrail_status": guardrail_result.status.value,
                "guardrail_reasons": [r.code for r in guardrail_result.reasons],
                "computed_values": guardrail_result.computed_values
            }
        )
    
    def _create_stub_proposal(
        self,
        user_intent: UserIntent,
        financial_state: FinancialState
    ) -> PortfolioProposal:
        """
        Create a stub portfolio proposal when none is provided.
        
        This is a placeholder that should be replaced by actual model output
        in production.
        
        Args:
            user_intent: User's intent
            financial_state: Financial state
            
        Returns:
            Stub PortfolioProposal
        """
        from app.agents.schemas import AssetAllocation, Trade
        
        # Default allocation (can be improved based on intent)
        allocation = AssetAllocation(stocks=60.0, bonds=30.0, cash=10.0, other=0.0)
        
        # Create stub trades if amount is specified
        trades = []
        if user_intent.amount and user_intent.amount > 0:
            # Stub trade - in production this would come from model
            trades.append(Trade(
                symbol="SPY",  # Default to broad market ETF
                action="BUY",
                quantity=1,  # Placeholder
                estimated_price=user_intent.amount,
                estimated_total=user_intent.amount
            ))
        
        return PortfolioProposal(
            target_allocation=allocation,
            trades=trades,
            reason_codes=["STUB_PROPOSAL"],
            risk_delta=0.0,
            estimated_cost=user_intent.amount or 0.0,
            metadata={"is_stub": True}
        )
    
    def _build_explanation_inputs_from_guardrails(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> List[ExplanationInput]:
        """Build explanation inputs from guardrail results (for BLOCK case)."""
        inputs = []
        
        # Add guardrail status
        inputs.append(ExplanationInput(
            key="guardrail_status",
            value=guardrail_result.status.value,
            description="Guardrail validation status"
        ))
        
        # Add guardrail reasons
        inputs.append(ExplanationInput(
            key="guardrail_reasons",
            value=[r.code for r in guardrail_result.reasons],
            description="List of guardrail violation codes"
        ))
        
        # Add key financial metrics
        inputs.append(ExplanationInput(
            key="net_cashflow",
            value=financial_state.cashflow.net_cashflow,
            description="Monthly net cashflow"
        ))
        
        inputs.append(ExplanationInput(
            key="emergency_fund_months",
            value=financial_state.emergency_fund_months,
            description="Emergency fund coverage in months"
        ))
        
        # Add computed values from guardrails
        for key, value in guardrail_result.computed_values.items():
            inputs.append(ExplanationInput(
                key=f"computed_{key}",
                value=value,
                description=f"Computed value: {key}"
            ))
        
        return inputs
    
    def _build_explanation_inputs(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent,
        proposal: PortfolioProposal
    ) -> List[ExplanationInput]:
        """Build explanation inputs for ALLOW/WARN cases."""
        inputs = []
        
        # Add guardrail status
        inputs.append(ExplanationInput(
            key="guardrail_status",
            value=guardrail_result.status.value,
            description="Guardrail validation status"
        ))
        
        # Add proposal details
        inputs.append(ExplanationInput(
            key="equity_allocation",
            value=proposal.target_allocation.stocks,
            description="Proposed equity allocation percentage"
        ))
        
        inputs.append(ExplanationInput(
            key="risk_delta",
            value=proposal.risk_delta,
            description="Change in risk score"
        ))
        
        inputs.append(ExplanationInput(
            key="estimated_cost",
            value=proposal.estimated_cost or 0.0,
            description="Estimated cost of proposal"
        ))
        
        # Add user intent
        inputs.append(ExplanationInput(
            key="intent_type",
            value=user_intent.type.value,
            description="User intent type"
        ))
        
        if user_intent.amount:
            inputs.append(ExplanationInput(
                key="intent_amount",
                value=user_intent.amount,
                description="User requested amount"
            ))
        
        # Add key financial metrics
        inputs.append(ExplanationInput(
            key="portfolio_value",
            value=financial_state.portfolio_summary.total_value,
            description="Total portfolio value"
        ))
        
        # Add computed values from guardrails
        for key, value in guardrail_result.computed_values.items():
            inputs.append(ExplanationInput(
                key=f"computed_{key}",
                value=value,
                description=f"Computed value: {key}"
            ))
        
        return inputs
    
    def _build_confirmations_from_guardrails(
        self,
        guardrail_result: GuardrailResult
    ) -> List[RequiredConfirmation]:
        """Build required confirmations based on guardrail warnings."""
        confirmations = []
        
        for reason in guardrail_result.reasons:
            if reason.severity == "warning":
                # Create confirmation for each warning
                confirmation_type = self._get_confirmation_type_from_reason(reason.code)
                confirmations.append(RequiredConfirmation(
                    confirmation_id=f"conf_{reason.code.lower()}",
                    type=confirmation_type,
                    message=reason.message,
                    required=True
                ))
        
        return confirmations
    
    def _get_confirmation_type_from_reason(self, reason_code: str) -> str:
        """Map guardrail reason code to confirmation type."""
        mapping = {
            "LOW_EMERGENCY_FUND_RISK_INCREASE": "risk_acknowledgment",
            "LOW_EMERGENCY_FUND_INVESTMENT": "emergency_fund_acknowledgment",
            "HIGH_INTEREST_DEBT_LUMP_SUM": "debt_acknowledgment",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "goal_timeframe_acknowledgment",
        }
        return mapping.get(reason_code, "general_acknowledgment")
    
    async def orchestrate(self, request: AgentRequest) -> AgentResponse:
        """
        Orchestrate agent workflow.
        
        Args:
            request: Agent request with context
            
        Returns:
            AgentResponse with orchestration result
        """
        # TODO: Implement orchestration logic
        return AgentResponse(
            success=False,
            message="Orchestrator not yet implemented",
            data=None
        )

