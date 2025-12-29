"""Chat service for explaining recommendations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional
import json
from app.agents.tutor_agent import TutorAgent
from app.agents.schemas import AdvisorDecision, FinancialState
from app.repositories import recommendations_repo
from app.models.errors import NotFoundError, ExternalServiceError


class ChatService:
    """
    Service for chat/explanation functionality.
    
    This service loads recommendations and uses TutorAgent to explain them.
    """
    
    def __init__(self, tutor_agent: Optional[TutorAgent] = None):
        """
        Initialize chat service.
        
        Args:
            tutor_agent: Optional tutor agent (creates new if not provided)
        """
        self.tutor_agent = tutor_agent or TutorAgent()
    
    async def explain_recommendation(
        self,
        user_id: str,
        recommendation_id: Optional[str] = None
    ) -> str:
        """
        Get explanation for a recommendation.
        
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

