"""Orchestrator agent for coordinating agent workflows.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

Orchestrator Responsibilities:
- Receives user input (financial_state, user_intent, optional proposal)
- Classifies user intent (extracted from UserIntent type)
- Calls guardrail agent FIRST for validation
- Routes request based on guardrail decision
- Aggregates agent responses into final output

Hard Constraints:
- MUST NOT give financial advice
- MUST NOT explain stocks, markets, or investing concepts
- MUST NOT recommend securities or strategies
- MUST NOT override or second-guess guardrail decisions
- Acts as a traffic controller, not a reasoning agent
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
    
    This agent acts as a traffic controller that:
    1. Receives user input (financial_state, user_intent, optional proposal)
    2. Classifies user intent from UserIntent type
    3. Calls guardrail agent FIRST for validation
    4. Routes request based on guardrail decision:
       - BLOCK -> REJECT decision
       - WARN -> MODIFY decision (if proposal provided)
       - ALLOW -> APPROVE decision (if proposal provided)
       - Missing proposal -> REQUEST_INFO decision
    5. Aggregates agent responses into final output
    
    This agent does NOT:
    - Give financial advice
    - Explain stocks, markets, or investing concepts
    - Recommend securities or strategies
    - Override guardrail decisions
    - Create portfolio proposals
    
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
        Route request and aggregate agent responses into final decision.
        
        Routing Logic:
        1. Classify user intent (from UserIntent.type)
        2. Call guardrail agent FIRST for validation
        3. Route based on guardrail decision:
           - BLOCK -> REJECT (no proposal, override confirmations)
           - WARN + proposal -> MODIFY (proposal with warnings)
           - WARN_AND_EDUCATE + proposal -> MODIFY (intent-related warnings, requires education)
           - ALLOW + proposal -> APPROVE (proposal approved)
           - ALLOW/WARN/WARN_AND_EDUCATE + no proposal -> REQUEST_INFO (proposal needed)
        
        Args:
            financial_state: User's current financial state
            user_intent: User's intent or request (intent classification extracted from type)
            proposal: Optional portfolio proposal from model/service (NOT created here)
            
        Returns:
            AdvisorDecision with routing result, aggregated from guardrail and other agents
            
        Note:
            This method does NOT:
            - Create portfolio proposals (returns REQUEST_INFO if missing)
            - Give financial advice
            - Override guardrail decisions
            - Call Alpaca, DB, or LLM services directly
        """
        # Step 1: Classify user intent (extracted from UserIntent.type)
        # Intent is already classified in the UserIntent object, no additional classification needed
        
        # Step 2: Call guardrail agent FIRST (hard requirement)
        guardrail_result = await self.guardrail_agent.validate(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=proposal
        )
        
        # Step 3: Route based on guardrail decision
        # Route: BLOCK -> REJECT
        if guardrail_result.status == GuardrailStatus.BLOCK:
            return self._route_block(guardrail_result, financial_state, user_intent)
        
        # Route: Missing proposal -> REQUEST_INFO
        if proposal is None:
            return self._route_request_info(guardrail_result, financial_state, user_intent)
        
        # Route: ALLOW/WARN/WARN_AND_EDUCATE with proposal -> APPROVE/MODIFY
        return self._route_allow_or_warn(guardrail_result, financial_state, user_intent, proposal)
    
    def _route_block(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> AdvisorDecision:
        """
        Route BLOCK guardrail result to REJECT decision.
        
        This routing path returns a REJECT decision with no proposal,
        override confirmations, and explanation inputs for the tutor agent.
        
        Args:
            guardrail_result: Guardrail validation result with BLOCK status
            financial_state: User's financial state
            user_intent: User's intent
            
        Returns:
            AdvisorDecision with REJECT decision type
        """
        explanation_inputs = self._build_explanation_inputs_from_guardrails(
            guardrail_result,
            financial_state,
            user_intent
        )
        
        override_confirmations = self._build_confirmations_from_guardrails(guardrail_result)
        
        return AdvisorDecision(
            decision=AdvisorDecisionType.REJECT,
            proposal=None,  # No proposal when blocked
            required_confirmations=override_confirmations,
            explanation_inputs=explanation_inputs,
            reasoning="Request blocked by guardrails. Override confirmations required to proceed.",
            metadata={
                "guardrail_status": guardrail_result.status.value,
                "guardrail_reasons": [r.code for r in guardrail_result.reasons]
            }
        )
    
    def _route_request_info(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> AdvisorDecision:
        """
        Route missing proposal to REQUEST_INFO decision.
        
        This routing path is used when guardrails allow but no proposal
        is provided. The orchestrator does NOT create proposals (that's
        financial advice). Instead, it requests that a proposal be generated
        by the appropriate service/agent.
        
        Args:
            guardrail_result: Guardrail validation result (ALLOW, WARN, or WARN_AND_EDUCATE)
            financial_state: User's financial state
            user_intent: User's intent
            
        Returns:
            AdvisorDecision with REQUEST_INFO decision type
        """
        explanation_inputs = self._build_explanation_inputs_from_guardrails(
            guardrail_result,
            financial_state,
            user_intent
        )
        
        return AdvisorDecision(
            decision=AdvisorDecisionType.REQUEST_INFO,
            proposal=None,  # No proposal available
            required_confirmations=[],  # No confirmations needed yet
            explanation_inputs=explanation_inputs,
            reasoning="Portfolio proposal is required but not provided. Please generate proposal first.",
            metadata={
                "guardrail_status": guardrail_result.status.value,
                "guardrail_reasons": [r.code for r in guardrail_result.reasons],
                "computed_values": guardrail_result.computed_values
            }
        )
    
    def _route_allow_or_warn(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent,
        proposal: PortfolioProposal
    ) -> AdvisorDecision:
        """
        Route ALLOW/WARN/WARN_AND_EDUCATE guardrail result with proposal to APPROVE/MODIFY decision.
        
        This routing path aggregates the guardrail result with the provided
        proposal to create an APPROVE (ALLOW) or MODIFY (WARN/WARN_AND_EDUCATE) decision.
        
        Args:
            guardrail_result: Guardrail validation result (ALLOW, WARN, or WARN_AND_EDUCATE)
            financial_state: User's financial state
            user_intent: User's intent
            proposal: Portfolio proposal (provided by service/agent, not created here)
            
        Returns:
            AdvisorDecision with APPROVE (ALLOW) or MODIFY (WARN/WARN_AND_EDUCATE) decision type
        """
        explanation_inputs = self._build_explanation_inputs(
            guardrail_result,
            financial_state,
            user_intent,
            proposal
        )
        
        required_confirmations = self._build_confirmations_from_guardrails(guardrail_result)
        
        # Route: WARN/WARN_AND_EDUCATE -> MODIFY, ALLOW -> APPROVE
        # WARN: Proposal/output validation warnings
        # WARN_AND_EDUCATE: User intent evaluation warnings (requires education)
        if guardrail_result.status in [GuardrailStatus.WARN, GuardrailStatus.WARN_AND_EDUCATE]:
            decision_type = AdvisorDecisionType.MODIFY
            if guardrail_result.status == GuardrailStatus.WARN_AND_EDUCATE:
                reasoning = "Proposal has intent-related warnings requiring education. Review guardrail results before proceeding."
            else:
                reasoning = "Proposal has warnings. Review guardrail results before proceeding."
        else:
            decision_type = AdvisorDecisionType.APPROVE
            reasoning = "Proposal passes all guardrails."
        
        return AdvisorDecision(
            decision=decision_type,
            proposal=proposal,  # Pass through proposal from service/agent
            required_confirmations=required_confirmations,
            explanation_inputs=explanation_inputs,
            reasoning=reasoning,
            metadata={
                "guardrail_status": guardrail_result.status.value,
                "guardrail_reasons": [r.code for r in guardrail_result.reasons],
                "computed_values": guardrail_result.computed_values
            }
        )
    
    def _build_explanation_inputs_from_guardrails(
        self,
        guardrail_result: GuardrailResult,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> List[ExplanationInput]:
        """
        Aggregate explanation inputs from guardrail results (for BLOCK/REQUEST_INFO cases).
        
        This method only translates/aggregates existing data into explanation inputs.
        It does NOT provide financial advice or explanations.
        """
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
        """
        Aggregate explanation inputs for ALLOW/WARN/WARN_AND_EDUCATE cases.
        
        This method only translates/aggregates existing data (guardrail results,
        financial state, user intent, proposal) into explanation inputs for the
        tutor agent. It does NOT provide financial advice or explanations.
        """
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
        """
        Aggregate required confirmations from guardrail results.
        
        This method translates guardrail warnings/blocks into confirmation
        requirements. It does NOT provide financial advice.
        
        Routing rules:
        - WARN → require user confirmation checkbox text (proposal validation warnings)
        - WARN_AND_EDUCATE → require user confirmation checkbox text (intent evaluation warnings)
        - BLOCK → require explicit override acknowledgement text
        """
        confirmations = []
        
        if guardrail_result.status == GuardrailStatus.BLOCK:
            # BLOCK requires explicit override acknowledgement
            for reason in guardrail_result.reasons:
                if reason.severity == "error":
                    confirmation_type = self._get_confirmation_type_from_reason(reason.code)
                    override_text = self._get_override_acknowledgement_text(reason.code, reason.message)
                    confirmations.append(RequiredConfirmation(
                        confirmation_id=f"conf_{reason.code.lower()}",
                        type=confirmation_type,
                        message=reason.message,
                        required=True,
                        confirmation_text=None,  # BLOCK doesn't use checkbox
                        override_acknowledgement=override_text
                    ))
        elif guardrail_result.status in [GuardrailStatus.WARN, GuardrailStatus.WARN_AND_EDUCATE]:
            # WARN/WARN_AND_EDUCATE requires checkbox confirmation
            # WARN: Proposal validation warnings
            # WARN_AND_EDUCATE: Intent evaluation warnings (requires education)
            for reason in guardrail_result.reasons:
                if reason.severity == "warning":
                    confirmation_type = self._get_confirmation_type_from_reason(reason.code)
                    checkbox_text = self._get_confirmation_checkbox_text(reason.code, reason.message)
                    confirmations.append(RequiredConfirmation(
                        confirmation_id=f"conf_{reason.code.lower()}",
                        type=confirmation_type,
                        message=reason.message,
                        required=True,
                        confirmation_text=checkbox_text,
                        override_acknowledgement=None  # WARN/WARN_AND_EDUCATE doesn't use override
                    ))
        
        return confirmations
    
    def _get_confirmation_type_from_reason(self, reason_code: str) -> str:
        """
        Map guardrail reason code to confirmation type.
        
        This is a pure routing/translation function with no financial advice.
        """
        mapping = {
            "LOW_EMERGENCY_FUND_RISK_INCREASE": "risk_acknowledgment",
            "LOW_EMERGENCY_FUND_INVESTMENT": "emergency_fund_acknowledgment",
            "LOW_EMERGENCY_FUND_LARGE_INVESTMENT": "emergency_fund_acknowledgment",
            "HIGH_INTEREST_DEBT_LUMP_SUM": "debt_acknowledgment",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "goal_timeframe_acknowledgment",
            "NEGATIVE_CASHFLOW_INVEST": "cashflow_acknowledgment",
        }
        return mapping.get(reason_code, "general_acknowledgment")
    
    def _get_confirmation_checkbox_text(self, reason_code: str, reason_message: str) -> str:
        """
        Get checkbox text for WARN confirmations.
        
        This method translates guardrail reason codes into user-facing
        confirmation text. It does NOT provide financial advice.
        """
        # Generate checkbox text based on reason
        checkbox_texts = {
            "LOW_EMERGENCY_FUND_RISK_INCREASE": "I understand my emergency fund is below recommended levels and want to proceed",
            "LOW_EMERGENCY_FUND_INVESTMENT": "I understand my emergency fund is below recommended levels and want to proceed",
            "HIGH_INTEREST_DEBT_LUMP_SUM": "I understand I have high-interest debt and want to proceed with this investment",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "I understand the risks of equity-heavy allocation for short-term goals and want to proceed",
        }
        return checkbox_texts.get(reason_code, f"I understand: {reason_message}")
    
    def _get_override_acknowledgement_text(self, reason_code: str, reason_message: str) -> str:
        """
        Get explicit override acknowledgement text for BLOCK confirmations.
        
        This method translates guardrail reason codes into user-facing
        override acknowledgement text. It does NOT provide financial advice.
        """
        # Generate override text that user must explicitly acknowledge
        override_texts = {
            "NEGATIVE_CASHFLOW_INVEST": "I acknowledge that I have negative cash flow and explicitly override the safety guardrail to proceed with this investment",
            "LOW_EMERGENCY_FUND_LARGE_INVESTMENT": "I acknowledge that my emergency fund is insufficient and explicitly override the safety guardrail to proceed with this large investment",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "I acknowledge the risk to my short-term goals and explicitly override the safety guardrail to proceed with this equity-heavy allocation",
        }
        return override_texts.get(reason_code, f"I explicitly acknowledge and override: {reason_message}")
    
    async def orchestrate(self, request: AgentRequest) -> AgentResponse:
        """
        Orchestrate agent workflow (general purpose routing).
        
        This method provides a general-purpose orchestration entry point.
        For decision-making flows, use decide() instead.
        
        Args:
            request: Agent request with context
            
        Returns:
            AgentResponse with orchestration result
            
        Note:
            This method routes requests but does NOT provide financial advice.
        """
        # TODO: Implement orchestration logic for general agent workflows
        # This would route to appropriate agents based on request type
        return AgentResponse(
            success=False,
            message="Orchestrator not yet implemented",
            data=None
        )

