"""Chat service for coordinating user requests through orchestrator.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

Service Constraints:
- MUST call orchestrator (cannot bypass)
- MUST NOT directly call recommendation_service
- MUST NOT duplicate guardrail logic
- Coordinates execution, does not make decisions
"""

from typing import Optional, Dict, Any
import json
from app.agents.orchestrator import OrchestratorAgent
from app.agents.tutor_agent import TutorAgent
from app.agents.schemas import (
    AdvisorDecision,
    FinancialState,
    UserIntent,
    UserIntentType,
    GuardrailStatus,
)
from app.repositories import profiles_repo, snapshots_repo, recommendations_repo
from app.models.errors import NotFoundError, ExternalServiceError


class ChatService:
    """
    Service for coordinating user requests through orchestrator.
    
    This service coordinates execution flow:
    1. Receives user input
    2. Calls orchestrator (which calls guardrail agent FIRST)
    3. Routes based on guardrail decision:
       - BLOCK → return refusal + safe educational alternative
       - WARN → call tutor_agent only (for education, proposal validation warnings)
       - WARN_AND_EDUCATE → call tutor_agent only (for education, intent evaluation warnings)
       - ALLOW → optionally call recommendation_service
    
    This service does NOT:
    - Bypass the orchestrator
    - Directly call recommendation_service
    - Duplicate guardrail logic
    - Make decisions (only coordinates)
    """
    
    def __init__(
        self,
        orchestrator: Optional[OrchestratorAgent] = None,
        tutor_agent: Optional[TutorAgent] = None
    ):
        """
        Initialize chat service.
        
        Args:
            orchestrator: Optional orchestrator agent (creates new if not provided)
            tutor_agent: Optional tutor agent (creates new if not provided)
        """
        self.orchestrator = orchestrator or OrchestratorAgent()
        self.tutor_agent = tutor_agent or TutorAgent()
    
    async def handle_user_request(
        self,
        user_id: str,
        user_intent_data: Dict[str, Any],
        financial_state: Optional[FinancialState] = None
    ) -> Dict[str, Any]:
        """
        Handle user request by coordinating through orchestrator.
        
        Execution Flow:
        1. Receive user input (user_intent_data, optional financial_state)
        2. Build FinancialState if not provided
        3. Build UserIntent
        4. Call orchestrator (which calls guardrail agent FIRST)
        5. Route based on guardrail decision:
           - BLOCK → return refusal + safe educational alternative
           - WARN → call tutor_agent only (proposal validation warnings)
           - WARN_AND_EDUCATE → call tutor_agent only (intent evaluation warnings)
           - ALLOW → optionally call recommendation_service
        
        Args:
            user_id: User ID
            user_intent_data: User intent data dictionary
            financial_state: Optional financial state (will load from DB if not provided)
            
        Returns:
            Response dictionary with explanation and metadata
            
        Raises:
            NotFoundError: If profile or snapshot not found
            ExternalServiceError: If coordination fails
        """
        # Step 1: Build FinancialState if not provided
        if financial_state is None:
            financial_state = await self._load_financial_state(user_id)
        
        # Step 2: Build UserIntent
        user_intent = self._build_user_intent(user_intent_data)
        
        # Step 3: Call orchestrator (which calls guardrail agent FIRST)
        # Orchestrator internally calls guardrail.validate() FIRST
        decision = await self.orchestrator.decide(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=None  # No proposal yet, orchestrator will route based on guardrail
        )
        
        # Step 4: Route based on guardrail decision from orchestrator
        guardrail_status = decision.metadata.get("guardrail_status")
        
        if guardrail_status == GuardrailStatus.BLOCK.value:
            # BLOCK → return refusal + safe educational alternative
            return await self._handle_block(decision, financial_state)
        elif guardrail_status in [GuardrailStatus.WARN.value, GuardrailStatus.WARN_AND_EDUCATE.value]:
            # WARN/WARN_AND_EDUCATE → call tutor_agent only (for education)
            # WARN: Proposal validation warnings
            # WARN_AND_EDUCATE: Intent evaluation warnings
            return await self._handle_warn(decision, financial_state, guardrail_status)
        elif guardrail_status == GuardrailStatus.ALLOW.value:
            # ALLOW → optionally call recommendation_service
            return await self._handle_allow(decision, financial_state, user_intent, user_id)
        else:
            # Unknown status, return decision as-is
            explanation = await self.tutor_agent.explain_decision(decision, financial_state)
            return {
                "explanation": explanation.explanation_text,
                "decision": decision.decision.value,
                "guardrail_status": guardrail_status,
                "metadata": decision.metadata
            }
    
    async def _handle_block(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState
    ) -> Dict[str, Any]:
        """
        Handle BLOCK guardrail decision.
        
        Returns refusal + safe educational alternative.
        
        Args:
            decision: Advisor decision with BLOCK status
            financial_state: User's financial state
            
        Returns:
            Response dictionary with refusal and safe alternative
        """
        # Get explanation from tutor agent
        explanation = await self.tutor_agent.explain_decision(decision, financial_state)
        
        # Extract safe alternative from guardrail reasons or use default
        safe_alternative = self._extract_safe_alternative(decision)
        
        return {
            "explanation": explanation.explanation_text,
            "decision": decision.decision.value,
            "guardrail_status": GuardrailStatus.BLOCK.value,
            "refusal": True,
            "safe_alternative": safe_alternative,
            "metadata": decision.metadata
        }
    
    async def _handle_warn(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState,
        guardrail_status: str = GuardrailStatus.WARN.value
    ) -> Dict[str, Any]:
        """
        Handle WARN or WARN_AND_EDUCATE guardrail decision.
        
        Calls tutor_agent only for educational purposes.
        
        Args:
            decision: Advisor decision with WARN or WARN_AND_EDUCATE status
            financial_state: User's financial state
            guardrail_status: Guardrail status (WARN or WARN_AND_EDUCATE)
            
        Returns:
            Response dictionary with educational explanation
        """
        # Call tutor_agent only (for education)
        # WARN: Proposal validation warnings
        # WARN_AND_EDUCATE: Intent evaluation warnings (requires education)
        explanation = await self.tutor_agent.explain_decision(decision, financial_state)
        
        return {
            "explanation": explanation.explanation_text,
            "decision": decision.decision.value,
            "guardrail_status": guardrail_status,
            "teaching_points": [
                {
                    "topic": tp.topic,
                    "explanation": tp.explanation,
                    "relevance": tp.relevance
                }
                for tp in explanation.teaching_points
            ],
            "metadata": decision.metadata
        }
    
    async def _handle_allow(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState,
        user_intent: UserIntent,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle ALLOW guardrail decision.
        
        Optionally calls recommendation_service if user explicitly requests recommendations.
        
        Args:
            decision: Advisor decision with ALLOW status
            financial_state: User's financial state
            user_intent: User's intent
            user_id: User ID
            
        Returns:
            Response dictionary with explanation and optional recommendation
        """
        # Check if user explicitly requests recommendations
        if self._should_call_recommendation_service(user_intent):
            # Optionally call recommendation_service
            # Note: recommendation_service has its own defensive checks
            from app.services.recommendation_service import RecommendationService
            
            try:
                rec_service = RecommendationService()
                recommendation = await rec_service.generate_recommendation(
                    user_id=user_id,
                    user_intent_data=user_intent.model_dump()
                )
                
                # Get explanation for the recommendation
                explanation = await self.tutor_agent.explain_decision(decision, financial_state)
                
                return {
                    "explanation": explanation.explanation_text,
                    "decision": decision.decision.value,
                    "guardrail_status": GuardrailStatus.ALLOW.value,
                    "recommendation_id": recommendation.get("id"),
                    "metadata": decision.metadata
                }
            except ExternalServiceError as e:
                # Recommendation service blocked the request (e.g., guardrail not ALLOW)
                # Return explanation without recommendation
                explanation = await self.tutor_agent.explain_decision(decision, financial_state)
                return {
                    "explanation": explanation.explanation_text,
                    "decision": decision.decision.value,
                    "guardrail_status": GuardrailStatus.ALLOW.value,
                    "recommendation_error": str(e),
                    "metadata": decision.metadata
                }
        else:
            # User didn't explicitly request recommendations, just return explanation
            explanation = await self.tutor_agent.explain_decision(decision, financial_state)
            return {
                "explanation": explanation.explanation_text,
                "decision": decision.decision.value,
                "guardrail_status": GuardrailStatus.ALLOW.value,
                "metadata": decision.metadata
            }
    
    def _should_call_recommendation_service(self, user_intent: UserIntent) -> bool:
        """
        Check if recommendation_service should be called.
        
        Only calls if user explicitly requests recommendations.
        
        Args:
            user_intent: User's intent
            
        Returns:
            True if recommendation_service should be called, False otherwise
        """
        # Only call if user explicitly requests recommendations
        return user_intent.type in [UserIntentType.GET_ADVICE, UserIntentType.INVEST]
    
    def _extract_safe_alternative(self, decision: AdvisorDecision) -> str:
        """
        Extract safe educational alternative from decision.
        
        Args:
            decision: Advisor decision
            
        Returns:
            Safe alternative text
        """
        # Try to extract from required_confirmations
        if decision.required_confirmations:
            for conf in decision.required_confirmations:
                if conf.override_acknowledgement:
                    return conf.override_acknowledgement
        
        # Default safe alternative
        return "Consider speaking with a licensed financial advisor about your goals and risk tolerance before making investment decisions."
    
    async def _load_financial_state(self, user_id: str) -> FinancialState:
        """
        Load financial state from database.
        
        Args:
            user_id: User ID
            
        Returns:
            FinancialState object
            
        Raises:
            NotFoundError: If profile or snapshot not found
        """
        profile = profiles_repo.get_profile(user_id)
        if not profile:
            raise NotFoundError("User profile not found", "PROFILE_NOT_FOUND")
        
        snapshot = snapshots_repo.get_latest_snapshot(user_id)
        if not snapshot:
            raise NotFoundError("Portfolio snapshot not found", "SNAPSHOT_NOT_FOUND")
        
        # Build FinancialState (reuse logic from recommendation_service)
        from app.services.recommendation_service import RecommendationService
        temp_service = RecommendationService()
        return temp_service._build_financial_state(profile, snapshot)
    
    def _build_user_intent(self, intent_data: Dict[str, Any]) -> UserIntent:
        """
        Build UserIntent from intent data.
        
        Args:
            intent_data: Intent data dictionary
            
        Returns:
            UserIntent object
        """
        intent_type_str = intent_data.get("type", "other")
        try:
            intent_type = UserIntentType(intent_type_str)
        except ValueError:
            intent_type = UserIntentType.OTHER
        
        return UserIntent(
            type=intent_type,
            amount=intent_data.get("amount"),
            risk_change=intent_data.get("risk_change"),
            target=intent_data.get("target"),
            timeframe=intent_data.get("timeframe"),
            metadata=intent_data.get("metadata", {})
        )
    
    async def explain_recommendation(
        self,
        user_id: str,
        recommendation_id: Optional[str] = None
    ) -> str:
        """
        Get explanation for an existing recommendation.
        
        This method is kept for backward compatibility with existing chat endpoint.
        It explains already-generated recommendations, not new user requests.
        
        Args:
            user_id: User ID
            recommendation_id: Optional recommendation ID (uses latest if not provided)
            
        Returns:
            Explanation text only
            
        Raises:
            NotFoundError: If recommendation not found
            ExternalServiceError: If data parsing fails
        """
        # Load recommendation
        if recommendation_id:
            recommendation = recommendations_repo.get_recommendation(recommendation_id)
            if not recommendation:
                raise NotFoundError(
                    f"Recommendation {recommendation_id} not found",
                    "RECOMMENDATION_NOT_FOUND"
                )
            # Verify it belongs to user
            if recommendation.get("user_id") != user_id:
                raise NotFoundError(
                    "Recommendation not found",
                    "RECOMMENDATION_NOT_FOUND"
                )
        else:
            recommendation = recommendations_repo.get_latest_recommendation(user_id)
            if not recommendation:
                raise NotFoundError(
                    "No recommendations found",
                    "NO_RECOMMENDATIONS_FOUND"
                )
        
        # Parse decision from recommendation
        decision_json_str = recommendation.get("decision_json")
        if not decision_json_str:
            raise ExternalServiceError(
                "Recommendation missing decision_json",
                "INVALID_RECOMMENDATION_DATA"
            )
        
        try:
            decision_data = json.loads(decision_json_str)
            decision = AdvisorDecision(**decision_data)
        except (json.JSONDecodeError, Exception) as e:
            raise ExternalServiceError(
                f"Failed to parse decision_json: {str(e)}",
                "INVALID_RECOMMENDATION_DATA"
            )
        
        # Parse financial state from recommendation
        financial_state_json_str = recommendation.get("financial_state_json")
        if not financial_state_json_str:
            raise ExternalServiceError(
                "Recommendation missing financial_state_json",
                "INVALID_RECOMMENDATION_DATA"
            )
        
        try:
            financial_state_data = json.loads(financial_state_json_str)
            financial_state = FinancialState(**financial_state_data)
        except (json.JSONDecodeError, Exception) as e:
            raise ExternalServiceError(
                f"Failed to parse financial_state_json: {str(e)}",
                "INVALID_RECOMMENDATION_DATA"
            )
        
        # Get explanation from tutor agent
        explanation = await self.tutor_agent.explain_decision(decision, financial_state)
        
        # Return only explanation text
        return explanation.explanation_text

