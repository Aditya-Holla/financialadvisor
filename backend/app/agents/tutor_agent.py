"""Tutor agent for user education and guidance.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, Dict, Any, List
from app.agents.schemas import AgentContext, AgentRequest, AgentResponse, TutorMessage


class TutorAgent:
    """
    Tutor agent for providing educational guidance to users.
    
    This agent can use LLM for educational content, but must never
    change numbers or decide trades. All trade decisions and number
    modifications are handled by deterministic guardrails.
    """
    
    def __init__(self):
        """Initialize the tutor agent."""
        pass
    
    async def respond(self, request: AgentRequest, messages: List[TutorMessage]) -> AgentResponse:
        """
        Generate educational response to user query.
        
        Args:
            request: Agent request with context
            messages: Conversation history
            
        Returns:
            AgentResponse with tutor's educational response
            
        Note:
            This agent can use LLM for educational purposes, but must
            never modify numbers or make trade decisions.
        """
        # TODO: Implement tutor agent logic
        return AgentResponse(
            success=False,
            message="Tutor agent not yet implemented",
            data=None
        )
    
    async def explain_recommendation(self, request: AgentRequest, recommendation_data: Dict[str, Any]) -> AgentResponse:
        """
        Explain a recommendation in educational terms.
        
        Args:
            request: Agent request with context
            recommendation_data: Recommendation data to explain
            
        Returns:
            AgentResponse with educational explanation
            
        Note:
            This method explains recommendations but does NOT modify
            numbers or make trade decisions.
        """
        # TODO: Implement recommendation explanation
        return AgentResponse(
            success=False,
            message="Recommendation explanation not yet implemented",
            data=None
        )

