"""Chat service for conversational interactions and explanations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, Dict, Any
import json
from app.agents.tutor_agent import TutorAgent
from app.agents.schemas import AdvisorDecision, FinancialState, UserIntent, UserIntentType
from app.services.intent_service import IntentService
from app.services.recommendation_service import RecommendationService
from app.repositories import recommendations_repo
from app.models.errors import NotFoundError, ExternalServiceError, ValidationError


class ChatService:
    """
    Service for chat/explanation functionality and conversational input.
    
    This service handles:
    - Explaining recommendations (using TutorAgent)
    - Processing conversational input (using IntentService)
    - Routing between explanation and recommendation generation
    """
    
    def __init__(
        self,
        tutor_agent: Optional[TutorAgent] = None,
        intent_service: Optional[IntentService] = None,
        recommendation_service: Optional[RecommendationService] = None
    ):
        """
        Initialize chat service.
        
        Args:
            tutor_agent: Optional tutor agent (creates new if not provided)
            intent_service: Optional intent service (creates new if not provided)
            recommendation_service: Optional recommendation service (creates new if not provided)
        """
        self.tutor_agent = tutor_agent or TutorAgent()
        self.intent_service = intent_service or IntentService()
        self.recommendation_service = recommendation_service or RecommendationService()
    
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
    
    async def handle_conversational_input(
        self,
        user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Handle conversational input from user.
        
        ALL interactions go through LLM for smooth conversation.
        Guardrails only block recommendation generation, not LLM responses.
        
        Flow:
        1. LLM processes message (conversational response)
        2. Extract intent in parallel
        3. If action request → Check guardrails → Generate recommendation if allowed
        4. If question → LLM answers directly (smooth conversation)
        
        Args:
            user_id: User ID
            message: User's conversational message
            
        Returns:
            Dictionary with response type and data:
            {
                "type": "explanation" | "recommendation" | "conversation",
                "message": str,  # LLM-generated response message
                "recommendation_id": Optional[str],  # If recommendation was generated
                "data": Optional[Dict]  # Additional data
            }
            
        Raises:
            ValidationError: If message is invalid
            ExternalServiceError: If service operations fail
        """
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty", "EMPTY_MESSAGE")
        
        # Step 1: Extract intent (for routing decisions)
        intent = None
        try:
            intent = await self.intent_service.extract_intent(message)
        except Exception as e:
            # If intent extraction fails, continue anyway - LLM will handle it
            pass
        
        # Step 2: Check if this is an action request
        is_action_request = intent and intent.type in [
            UserIntentType.INVEST,
            UserIntentType.WITHDRAW,
            UserIntentType.REBALANCE,
            UserIntentType.CHANGE_RISK
        ]
        
        if is_action_request:
            # Action request - try to generate recommendation
            # Guardrails will block if inappropriate, but we still respond conversationally
            try:
                return await self._handle_action_request_with_llm(user_id, message, intent)
            except Exception as e:
                # If recommendation generation fails (e.g., guardrails block),
                # still provide conversational LLM response explaining why
                return await self._handle_blocked_action_with_llm(user_id, message, intent, str(e))
        else:
            # Question or general conversation - LLM handles directly
            return await self._handle_conversational_question(user_id, message, intent)
    
    async def _handle_conversational_question(
        self,
        user_id: str,
        message: str,
        intent: Optional[UserIntent]
    ) -> Dict[str, Any]:
        """Handle conversational questions using LLM."""
        from app.integrations.llm import LLMIntegration
        import logging
        
        logger = logging.getLogger(__name__)
        
        llm = LLMIntegration()
        
        # Debug: Check why LLM might not be available
        if not llm.is_available():
            logger.warning(f"LLM not available - client: {llm.client is not None}, API key: {llm.settings.LLM_API_KEY is not None}")
            if llm.settings.LLM_API_KEY:
                logger.warning(f"API key exists but client is None - check OpenAI package installation")
            else:
                logger.warning("LLM_API_KEY not found in settings - check .env file")
        
        # Try to get context (latest recommendation) for better answers
        recommendation = recommendations_repo.get_latest_recommendation(user_id)
        recommendation_context = ""
        
        if recommendation:
            try:
                # Get brief summary of latest recommendation for context
                decision_json = recommendation.get("decision_json")
                if decision_json:
                    import json
                    decision_data = json.loads(decision_json)
                    decision_type = decision_data.get("decision", "unknown")
                    recommendation_context = f"\n\nContext: You have a recent recommendation with decision '{decision_type}'. The user may be asking about it."
            except Exception:
                pass
        
        if llm.is_available():
            try:
                # Use LLM for conversational response
                system_prompt = """You are a friendly financial advisor AI assistant. Answer user questions about personal finance, investing, and financial planning in a clear, conversational, and educational way. 

Keep responses:
- Concise (2-4 sentences for simple questions, up to 6 for complex ones)
- Friendly and approachable
- Educational and helpful
- Focused on the user's question

If the user asks about their recommendation, reference it naturally. If they ask general questions, provide helpful financial education."""
                
                user_prompt = message
                if recommendation_context:
                    user_prompt += recommendation_context
                
                logger.info(f"Calling LLM for conversational question: {message[:50]}...")
                response = await llm.client.chat.completions.create(
                    model=llm.settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                llm_response = response.choices[0].message.content.strip()
                logger.info(f"LLM generated response (length: {len(llm_response)})")
                
                return {
                    "type": "conversation",
                    "message": llm_response,
                    "recommendation_id": recommendation.get("id") if recommendation else None,
                    "data": {
                        "intent": intent.model_dump() if intent else None,
                        "has_recommendation_context": bool(recommendation)
                    }
                }
            except Exception as e:
                # LLM failed - log and fallback
                logger.error(f"LLM call failed: {str(e)}", exc_info=True)
                pass
        
        # Fallback if LLM unavailable or fails
        # IMPORTANT: Only explain recommendation if user is asking about it
        # Otherwise, provide general response
        user_asking_about_recommendation = (
            recommendation and 
            intent and
            any(word in message.lower() for word in ["recommendation", "suggestion", "advice you gave", "what you said", "that"])
        )
        
        if user_asking_about_recommendation and recommendation:
            # User is asking about their recommendation - explain it
            try:
                explanation = await self.explain_recommendation(user_id, recommendation.get("id"))
                return {
                    "type": "explanation",
                    "message": explanation,
                    "recommendation_id": recommendation.get("id"),
                    "data": {"intent": intent.model_dump() if intent else None}
                }
            except Exception:
                pass
        
        # Final fallback - general response (not recommendation explanation)
        return {
            "type": "conversation",
            "message": "I'd be happy to help! To get started, you can ask me to generate an investment recommendation, or ask me questions about investing. For example, you could say 'I want to invest $1000' or 'What should I know about emergency funds?'",
            "recommendation_id": None,
            "data": {
                "intent": intent.model_dump() if intent else None,
                "fallback_used": True,
                "llm_available": llm.is_available()
            }
        }
    
    async def _handle_action_request_with_llm(
        self,
        user_id: str,
        message: str,
        intent: UserIntent
    ) -> Dict[str, Any]:
        """Handle action request with LLM conversational response."""
        from app.integrations.llm import LLMIntegration
        from app.agents.schemas import AdvisorDecisionType
        import json
        
        # Convert intent to recommendation service format
        intent_data = intent.model_dump(exclude_none=True)
        
        # Generate recommendation (guardrails will block if inappropriate)
        recommendation = await self.recommendation_service.generate_recommendation(
            user_id=user_id,
            user_intent_data=intent_data
        )
        
        # Check if decision is REJECT (blocked by guardrails)
        decision_json_str = recommendation.get("decision_json")
        if decision_json_str:
            try:
                decision_data = json.loads(decision_json_str)
                decision_type = decision_data.get("decision")
                
                if decision_type == "reject":
                    # Guardrails blocked - use friendly LLM explanation
                    guardrail_reasons = decision_data.get("metadata", {}).get("guardrail_reasons", [])
                    reasoning = decision_data.get("reasoning", "Request blocked by guardrails")
                    
                    # Build friendly error message from guardrail reasons
                    # Get human-readable messages from guardrail reasons if available
                    error_parts = []
                    if guardrail_reasons:
                        # Map reason codes to friendly messages
                        reason_messages = {
                            "NEGATIVE_CASHFLOW_INVEST": "You have negative cash flow, which means your expenses exceed your income. Investing right now could worsen your financial situation.",
                            "LOW_EMERGENCY_FUND_LARGE_INVESTMENT": "Your emergency fund is below the recommended 3 months of expenses. Large investments aren't recommended until you build up your emergency fund.",
                            "LOW_EMERGENCY_FUND_INVEST_ALL": "Investing all your available cash would leave you without an adequate emergency fund.",
                            "HIGH_INTEREST_DEBT_LUMP_SUM": "You have high-interest debt. It's usually better to pay down high-interest debt before making large investments.",
                            "SHORT_TERM_GOAL_EQUITY_HEAVY": "You have short-term financial goals (less than 12 months away). Equity-heavy investments are risky for short-term goals.",
                        }
                        
                        for reason_code in guardrail_reasons:
                            if reason_code in reason_messages:
                                error_parts.append(reason_messages[reason_code])
                            else:
                                error_parts.append(f"Safety check: {reason_code}")
                        
                        if error_parts:
                            error_message = " ".join(error_parts)
                        else:
                            error_message = f"Guardrails blocked this request: {', '.join(guardrail_reasons)}. {reasoning}"
                    else:
                        error_message = reasoning
                    
                    # Use blocked-action handler for friendly LLM explanation
                    return await self._handle_blocked_action_with_llm(user_id, message, intent, error_message)
            except (json.JSONDecodeError, KeyError, Exception) as e:
                # If parsing fails, log and continue with normal flow
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse decision_json for REJECT check: {str(e)}")
        
        # Normal flow: decision is APPROVE or MODIFY
        # Get explanation using LLM for conversational response
        explanation = await self.explain_recommendation(
            user_id=user_id,
            recommendation_id=recommendation.get("id")
        )
        
        # Enhance with LLM for more conversational tone if available
        llm = LLMIntegration()
        if llm.is_available():
            try:
                # Make the explanation more conversational
                # Note: This enhancement step is for tone/style only, not for generating new recommendations
                # So we skip safety validation here (it's just rephrasing)
                conversational_prompt = f"""The user said: "{message}"

I've generated this recommendation explanation:
"{explanation}"

Please rephrase this in a more conversational, friendly way while keeping all the important details. Make it sound like you're talking directly to the user. DO NOT suggest different allocations, trades, or changes - just rephrase what's already there."""
                
                response = await llm.client.chat.completions.create(
                    model=llm.settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a friendly financial advisor. Rephrase explanations to be more conversational while keeping all details accurate. Never suggest changes to allocations or trades - only rephrase existing information."},
                        {"role": "user", "content": conversational_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=400
                )
                
                enhanced_explanation = response.choices[0].message.content.strip()
                
                # Skip safety check for enhancement (it's just rephrasing, not generating new content)
                # The original explanation already passed safety checks
                explanation = enhanced_explanation
            except Exception:
                # If LLM enhancement fails, use original explanation
                pass
        
        return {
            "type": "recommendation",
            "message": explanation,
            "recommendation_id": recommendation.get("id"),
            "data": {
                "recommendation": {
                    "id": recommendation.get("id"),
                    "decision": recommendation.get("decision"),
                    "status": recommendation.get("status"),
                    "created_at": recommendation.get("created_at")
                },
                "intent": intent.model_dump()
            }
        }
    
    async def _handle_blocked_action_with_llm(
        self,
        user_id: str,
        message: str,
        intent: UserIntent,
        error_message: str
    ) -> Dict[str, Any]:
        """Handle blocked action with conversational LLM response explaining why."""
        from app.integrations.llm import LLMIntegration
        
        llm = LLMIntegration()
        
        if llm.is_available():
            try:
                # Use LLM to explain why the action was blocked in a friendly way
                system_prompt = """You are a friendly financial advisor. When a user's investment request is blocked by safety guardrails, explain why in a helpful, educational, and supportive way. Don't be preachy - be understanding and offer alternatives."""
                
                user_prompt = f"""The user requested: "{message}"

The system blocked this request because: {error_message}

Please explain this to the user in a friendly, conversational way. Help them understand why and suggest what they could do instead."""
                
                response = await llm.client.chat.completions.create(
                    model=llm.settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                llm_response = response.choices[0].message.content.strip()
                
                return {
                    "type": "conversation",
                    "message": llm_response,
                    "recommendation_id": None,
                    "data": {
                        "intent": intent.model_dump(),
                        "blocked": True,
                        "block_reason": error_message
                    }
                }
            except Exception:
                pass
        
        # Fallback if LLM unavailable
        return {
            "type": "conversation",
            "message": f"I understand you'd like to {intent.type.value}, but I can't proceed with that right now. {error_message}. Would you like to discuss alternatives or ask me questions about your financial situation?",
            "recommendation_id": None,
            "data": {
                "intent": intent.model_dump(),
                "blocked": True,
                "block_reason": error_message
            }
        }

