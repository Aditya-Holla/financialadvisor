"""Tutor agent for user education and guidance.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, List, Dict, Any
from app.agents.schemas import (
    AdvisorDecision,
    FinancialState,
    TutorExplanation,
    TeachingPoint,
    GuardrailReason,
    GuardrailStatus,
)
from app.integrations.llm import LLMIntegration


class TutorAgent:
    """
    Tutor agent for providing educational guidance to users.
    
    This agent explains AdvisorDecisions in educational terms. It:
    - Explains guardrail reasons
    - Describes portfolio proposals
    - Provides teaching points
    
    Safety constraints:
    - NEVER suggests new trades
    - NEVER overrides decisions
    - NEVER changes numbers
    - ONLY explains what already exists
    """
    
    def __init__(self, llm_integration: Optional[LLMIntegration] = None):
        """
        Initialize the tutor agent.
        
        Args:
            llm_integration: Optional LLM integration (creates new if not provided)
        """
        self.llm = llm_integration or LLMIntegration()
    
    async def explain_decision(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> TutorExplanation:
        """
        Explain an AdvisorDecision in educational terms.
        
        Tries LLM first (if available), falls back to template-based explanation.
        
        Args:
            decision: The advisor decision to explain
            financial_state: User's financial state (for context)
            
        Returns:
            TutorExplanation with explanation text and teaching points
            
        Safety guarantees:
        - Numbers are preserved exactly as in decision
        - No new recommendations are introduced
        - No decisions are overridden
        - Only explains existing decision and proposal
        """
        # Try LLM first (if available)
        llm_explanation = await self._try_llm_explanation(decision, financial_state)
        
        if llm_explanation:
            # LLM generated valid explanation, use it
            # Still generate teaching points from templates (they're safe)
            teaching_points = []
            guardrail_references = []
            proposal_referenced = False
            
            guardrail_status = decision.metadata.get("guardrail_status")
            guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
            
            if guardrail_status and guardrail_status != GuardrailStatus.ALLOW.value:
                guardrail_references.extend(guardrail_reasons)
                for reason_code in guardrail_reasons:
                    teaching_point = self._create_guardrail_teaching_point(reason_code)
                    if teaching_point:
                        teaching_points.append(teaching_point)
            
            if decision.proposal:
                proposal_referenced = True
                proposal_teaching = self._create_proposal_teaching_points(decision.proposal)
                teaching_points.extend(proposal_teaching)
            
            general_teaching = self._create_general_teaching_points(financial_state, decision)
            teaching_points.extend(general_teaching)
            
            return TutorExplanation(
                explanation_text=llm_explanation,
                teaching_points=teaching_points,
                guardrail_references=guardrail_references,
                proposal_referenced=proposal_referenced
            )
        
        # Fallback to template-based explanation
        return await self._explain_with_templates(decision, financial_state)
    
    async def _try_llm_explanation(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> Optional[str]:
        """
        Try to generate explanation using LLM.
        
        Returns explanation text if successful, None if LLM unavailable or fails validation.
        """
        if not self.llm.is_available():
            return None
        
        # Build summaries for LLM
        decision_summary = {
            "decision_type": decision.decision.value,
            "status": "approved" if decision.decision.value == "approve" else decision.decision.value
        }
        
        financial_state_summary = {
            "emergency_fund_months": financial_state.emergency_fund_months,
            "net_cashflow": financial_state.cashflow.net_cashflow
        }
        
        guardrail_info = None
        guardrail_status = decision.metadata.get("guardrail_status")
        guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
        if guardrail_status and guardrail_reasons:
            guardrail_info = {
                "status": guardrail_status,
                "reasons": [
                    {"code": code, "message": self._get_reason_description(code)}
                    for code in guardrail_reasons
                ]
            }
        
        proposal_info = None
        if decision.proposal:
            proposal_info = {
                "allocation": {
                    "stocks": decision.proposal.target_allocation.stocks,
                    "bonds": decision.proposal.target_allocation.bonds,
                    "cash": decision.proposal.target_allocation.cash,
                    "other": decision.proposal.target_allocation.other
                },
                "trade_count": len(decision.proposal.trades) if decision.proposal.trades else 0,
                "risk_delta": decision.proposal.risk_delta
            }
        
        # Try LLM generation
        return await self.llm.generate_explanation(
            decision_summary=decision_summary,
            financial_state_summary=financial_state_summary,
            guardrail_info=guardrail_info,
            proposal_info=proposal_info
        )
    
    async def _explain_with_templates(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> TutorExplanation:
        """
        Generate explanation using template-based approach (fallback).
        
        This is the original template-based implementation.
        """
        explanation_parts = []
        teaching_points = []
        guardrail_references = []
        proposal_referenced = False
        
        # Start with decision explanation
        decision_explanation = self._explain_decision_type(decision.decision)
        explanation_parts.append(decision_explanation)
        
        # Explain guardrail reasons if present
        guardrail_status = decision.metadata.get("guardrail_status")
        guardrail_reasons = decision.metadata.get("guardrail_reasons", [])
        
        if guardrail_status and guardrail_status != GuardrailStatus.ALLOW.value:
            guardrail_explanation = self._explain_guardrails(
                guardrail_status,
                guardrail_reasons,
                decision.explanation_inputs
            )
            explanation_parts.append(guardrail_explanation)
            guardrail_references.extend(guardrail_reasons)
            
            # Add teaching points for guardrail reasons
            for reason_code in guardrail_reasons:
                teaching_point = self._create_guardrail_teaching_point(reason_code)
                if teaching_point:
                    teaching_points.append(teaching_point)
        
        # Explain portfolio proposal if present
        if decision.proposal:
            proposal_explanation = self._explain_proposal(decision.proposal)
            explanation_parts.append(proposal_explanation)
            proposal_referenced = True
            
            # Add teaching points for proposal
            proposal_teaching = self._create_proposal_teaching_points(decision.proposal)
            teaching_points.extend(proposal_teaching)
        
        # Add general financial education teaching points
        general_teaching = self._create_general_teaching_points(financial_state, decision)
        teaching_points.extend(general_teaching)
        
        # Combine explanation parts
        explanation_text = " ".join(explanation_parts)
        
        return TutorExplanation(
            explanation_text=explanation_text,
            teaching_points=teaching_points,
            guardrail_references=guardrail_references,
            proposal_referenced=proposal_referenced
        )
    
    def _explain_decision_type(self, decision_type) -> str:
        """Explain the decision type."""
        explanations = {
            "approve": "This recommendation has been approved and is ready for your review.",
            "modify": "This recommendation has been modified with additional considerations. Please review the changes carefully.",
            "reject": "This recommendation has been rejected based on safety guardrails. See below for details.",
            "request_info": "Additional information is needed before a recommendation can be made.",
            "defer": "This recommendation has been deferred. Please review your financial situation and try again later."
        }
        return explanations.get(decision_type.value, "A decision has been made on your recommendation.")
    
    def _explain_guardrails(
        self,
        status: str,
        reason_codes: List[str],
        explanation_inputs: List
    ) -> str:
        """Explain guardrail results."""
        if status == GuardrailStatus.BLOCK.value:
            explanation = "This recommendation was blocked by safety guardrails. "
        elif status == GuardrailStatus.WARN.value:
            explanation = "This recommendation has warnings that require your attention. "
        else:
            explanation = "Safety guardrails were checked. "
        
        # Add specific reasons
        if reason_codes:
            reason_descriptions = []
            for code in reason_codes:
                desc = self._get_reason_description(code)
                if desc:
                    reason_descriptions.append(desc)
            
            if reason_descriptions:
                explanation += "Reasons: " + "; ".join(reason_descriptions) + "."
        
        return explanation
    
    def _get_reason_description(self, reason_code: str) -> str:
        """Get human-readable description of guardrail reason code."""
        descriptions = {
            "NEGATIVE_CASHFLOW_INVEST": "You have negative cash flow, so investing now is not recommended",
            "LOW_EMERGENCY_FUND_RISK_INCREASE": "Your emergency fund is below the recommended 3 months",
            "LOW_EMERGENCY_FUND_INVESTMENT": "Your emergency fund is below recommended levels",
            "LOW_EMERGENCY_FUND_LARGE_INVESTMENT": "Your emergency fund is insufficient for large investments",
            "HIGH_INTEREST_DEBT_LUMP_SUM": "You have high-interest debt that should be prioritized",
            "SHORT_TERM_GOAL_EQUITY_HEAVY": "You have short-term goals that conflict with equity-heavy allocations",
            "NO_VIOLATIONS": "All safety checks passed"
        }
        return descriptions.get(reason_code, f"Guardrail check: {reason_code}")
    
    def _explain_proposal(self, proposal) -> str:
        """Explain the portfolio proposal."""
        explanation = "The proposed portfolio allocation is: "
        
        allocation = proposal.target_allocation
        parts = []
        if allocation.stocks > 0:
            parts.append(f"{allocation.stocks:.1f}% stocks")
        if allocation.bonds > 0:
            parts.append(f"{allocation.bonds:.1f}% bonds")
        if allocation.cash > 0:
            parts.append(f"{allocation.cash:.1f}% cash")
        if allocation.other > 0:
            parts.append(f"{allocation.other:.1f}% other")
        
        explanation += ", ".join(parts) + "."
        
        # Mention trades if present
        if proposal.trades:
            trade_count = len(proposal.trades)
            explanation += f" This involves {trade_count} trade(s) to achieve this allocation."
        
        # Mention risk change if significant
        if abs(proposal.risk_delta) > 0.05:
            direction = "increases" if proposal.risk_delta > 0 else "decreases"
            explanation += f" This {direction} your portfolio risk."
        
        return explanation
    
    def _create_guardrail_teaching_point(self, reason_code: str) -> Optional[TeachingPoint]:
        """Create a teaching point for a guardrail reason."""
        teaching_points = {
            "NEGATIVE_CASHFLOW_INVEST": TeachingPoint(
                topic="Cash Flow Management",
                explanation="Before investing, it's important to have positive cash flow. Negative cash flow means you're spending more than you earn, which can lead to financial stress.",
                relevance="This recommendation was blocked because your cash flow is negative."
            ),
            "LOW_EMERGENCY_FUND_RISK_INCREASE": TeachingPoint(
                topic="Emergency Fund Importance",
                explanation="Financial experts recommend having 3-6 months of expenses in an emergency fund. This provides a safety net for unexpected expenses or income loss.",
                relevance="Your emergency fund is below the recommended minimum."
            ),
            "HIGH_INTEREST_DEBT_LUMP_SUM": TeachingPoint(
                topic="Debt vs. Investment Priority",
                explanation="High-interest debt (typically 15%+ APR) should generally be paid off before making large investments. The guaranteed return from paying off debt often exceeds investment returns.",
                relevance="You have high-interest debt that should be prioritized."
            ),
            "SHORT_TERM_GOAL_EQUITY_HEAVY": TeachingPoint(
                topic="Investment Time Horizon",
                explanation="Stocks are volatile and best suited for long-term goals (5+ years). For short-term goals, more stable investments like bonds or cash are recommended.",
                relevance="You have short-term goals that require more stable investments."
            )
        }
        return teaching_points.get(reason_code)
    
    def _create_proposal_teaching_points(self, proposal) -> List[TeachingPoint]:
        """Create teaching points about the proposal."""
        points = []
        
        # Asset allocation teaching
        if proposal.target_allocation.stocks > 60:
            points.append(TeachingPoint(
                topic="Equity-Heavy Portfolios",
                explanation="Portfolios with more than 60% stocks are considered equity-heavy. They offer higher potential returns but also higher volatility and risk.",
                relevance="This proposal allocates a significant portion to stocks."
            ))
        
        # Diversification teaching
        if len(proposal.trades) > 1:
            points.append(TeachingPoint(
                topic="Portfolio Diversification",
                explanation="Diversification means spreading investments across different assets. This helps reduce risk because different investments may perform differently under various market conditions.",
                relevance="This proposal includes multiple trades to diversify your portfolio."
            ))
        
        return points
    
    def _create_general_teaching_points(
        self,
        financial_state: FinancialState,
        decision: AdvisorDecision
    ) -> List[TeachingPoint]:
        """Create general financial education teaching points."""
        points = []
        
        # Emergency fund teaching
        if financial_state.emergency_fund_months < 3:
            points.append(TeachingPoint(
                topic="Building an Emergency Fund",
                explanation="An emergency fund is money set aside to cover unexpected expenses. Aim for 3-6 months of expenses in a high-yield savings account.",
                relevance="Your emergency fund could be strengthened."
            ))
        
        # Debt management teaching
        if financial_state.debt_summary.total_debt > 0:
            points.append(TeachingPoint(
                topic="Debt Management",
                explanation="Managing debt effectively involves prioritizing high-interest debt, making consistent payments, and avoiding taking on new debt unnecessarily.",
                relevance="You have outstanding debt to consider."
            ))
        
        return points
    
    async def respond(self, request, messages: List) -> "AgentResponse":
        """
        Generate educational response to user query.
        
        This method is kept for backward compatibility but explain_decision()
        should be used for explaining AdvisorDecisions.
        """
        from app.agents.schemas import AgentRequest, AgentResponse
        return AgentResponse(
            success=False,
            message="Use explain_decision() method for explaining decisions",
            data=None
        )
    
    async def explain_recommendation(self, request, recommendation_data: Dict) -> "AgentResponse":
        """
        Explain a recommendation in educational terms.
        
        This method is kept for backward compatibility but explain_decision()
        should be used for explaining AdvisorDecisions.
        """
        from app.agents.schemas import AgentRequest, AgentResponse
        return AgentResponse(
            success=False,
            message="Use explain_decision() method for explaining decisions",
            data=None
        )

