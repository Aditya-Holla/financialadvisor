"""Intent extraction service for parsing natural language into structured UserIntent.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

This service uses LLMIntegration to extract UserIntent from natural language.
The LLM only extracts intent - it never makes decisions or changes numbers.
"""

from typing import Optional, Dict, Any
import json
import logging
from app.agents.schemas import UserIntent, UserIntentType
from app.integrations.llm import LLMIntegration
from app.models.errors import ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)


class IntentService:
    """
    Service for extracting UserIntent from natural language input.
    
    Uses LLMIntegration to parse conversational input and extract structured intent.
    The LLM only extracts - it never decides or changes numbers.
    """
    
    def __init__(self, llm_integration: Optional[LLMIntegration] = None):
        """
        Initialize intent service.
        
        Args:
            llm_integration: Optional LLM integration (creates new if not provided)
        """
        self.llm = llm_integration or LLMIntegration()
    
    async def extract_intent(self, user_message: str) -> UserIntent:
        """
        Extract UserIntent from natural language message.
        
        Args:
            user_message: Natural language message from user
            
        Returns:
            UserIntent object with extracted information
            
        Raises:
            ValidationError: If intent cannot be extracted or is invalid
            ExternalServiceError: If LLM service fails
        """
        if not user_message or not user_message.strip():
            raise ValidationError("User message cannot be empty", "EMPTY_MESSAGE")
        
        # Try LLM extraction first
        if self.llm.is_available():
            try:
                intent = await self._extract_with_llm(user_message)
                if intent:
                    logger.info(f"Extracted intent via LLM: {intent.type.value}")
                    return intent
            except Exception as e:
                logger.warning(f"LLM intent extraction failed: {str(e)}, falling back to keyword matching")
        
        # Fallback to keyword matching if LLM unavailable or fails
        return self._extract_with_keywords(user_message)
    
    async def _extract_with_llm(self, user_message: str) -> Optional[UserIntent]:
        """
        Extract intent using LLM.
        
        Args:
            user_message: User's natural language message
            
        Returns:
            UserIntent if extraction successful, None otherwise
        """
        if not self.llm.client:
            return None
        
        try:
            # Build prompt for intent extraction
            system_prompt = self._get_intent_extraction_prompt()
            user_prompt = f"Extract the investment intent from this user message:\n\n{user_message}\n\nInclude the original message in metadata as 'original_message' for percentage-based detection."
            
            logger.info(f"Calling LLM for intent extraction with model: {self.llm.settings.LLM_MODEL}")
            
            # Build request parameters
            request_params = {
                "model": self.llm.settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,  # Lower temperature for more consistent extraction
                "max_tokens": 200
            }
            
            # Add JSON mode if supported (gpt-3.5-turbo and gpt-4 support it)
            if "gpt" in self.llm.settings.LLM_MODEL.lower():
                try:
                    request_params["response_format"] = {"type": "json_object"}
                except Exception:
                    # If JSON mode not supported, continue without it
                    pass
            
            # Call LLM with structured output request
            response = await self.llm.client.chat.completions.create(**request_params)
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"LLM intent extraction response: {response_text[:100]}...")
            
            # Parse JSON response
            intent_data = json.loads(response_text)
            
            # Store original message for percentage-based detection
            if "metadata" not in intent_data:
                intent_data["metadata"] = {}
            intent_data["metadata"]["original_message"] = user_message
            
            # Validate and convert to UserIntent
            return self._parse_intent_data(intent_data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"LLM intent extraction error: {str(e)}", exc_info=True)
            return None
    
    def _extract_with_keywords(self, user_message: str) -> UserIntent:
        """
        Extract intent using keyword matching (fallback).
        
        Args:
            user_message: User's natural language message
            
        Returns:
            UserIntent extracted from keywords
        """
        message_lower = user_message.lower()
        
        # FIRST: Check for question/advice patterns (prioritize these)
        question_words = ["what", "how", "why", "when", "where", "explain", "tell me", "describe", "help me understand"]
        advice_patterns = ["what should", "what is", "what are", "how do", "how can", "tell me about", "explain", "help with"]
        
        is_question = any(word in message_lower for word in question_words) or \
                     any(pattern in message_lower for pattern in advice_patterns)
        
        # Determine intent type from keywords
        intent_type = UserIntentType.INVEST  # Default
        
        # If it's a question, default to GET_ADVICE unless it's clearly an action
        if is_question:
            # But check if it's a question about a specific action
            if any(word in message_lower for word in ["withdraw", "take out", "sell", "cash out"]):
                intent_type = UserIntentType.WITHDRAW
            elif any(word in message_lower for word in ["rebalance", "re-balance", "reallocate"]):
                intent_type = UserIntentType.REBALANCE
            elif any(word in message_lower for word in ["change risk", "increase risk", "decrease risk", "more risk", "less risk"]):
                intent_type = UserIntentType.CHANGE_RISK
            elif any(word in message_lower for word in ["invest", "buy", "purchase", "put money"]):
                intent_type = UserIntentType.INVEST
            else:
                # It's a general question - treat as GET_ADVICE
                intent_type = UserIntentType.GET_ADVICE
        else:
            # Not a question - check for action keywords
            if any(word in message_lower for word in ["withdraw", "take out", "sell", "cash out"]):
                intent_type = UserIntentType.WITHDRAW
            elif any(word in message_lower for word in ["rebalance", "re-balance", "reallocate"]):
                intent_type = UserIntentType.REBALANCE
            elif any(word in message_lower for word in ["change risk", "increase risk", "decrease risk", "more risk", "less risk"]):
                intent_type = UserIntentType.CHANGE_RISK
            elif any(word in message_lower for word in ["invest", "buy", "purchase", "put money"]):
                intent_type = UserIntentType.INVEST
        
        # Extract amount (look for dollar amounts)
        import re
        amount = None
        metadata_extra = {}
        
        # Check for "all", "everything", "100%" first (will be handled by guardrails)
        if any(word in message_lower for word in ["all", "everything", "100%", "entire"]):
            # Set amount to None - guardrails will handle percentage-based investments
            amount = None
            # Store in metadata for guardrail processing
            metadata_extra = {"percentage_based": True, "amount_type": "all"}
        else:
            amount_patterns = [
                r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $1,000.00 or $1000
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 1000 dollars
                r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$',  # 1000 $
            ]
            for pattern in amount_patterns:
                matches = re.findall(pattern, user_message, re.IGNORECASE)
                if matches:
                    # Take the first match and clean it
                    amount_str = matches[0].replace(',', '')
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
        
        # Extract risk change (look for "increase risk", "decrease risk", etc.)
        risk_change = None
        if "increase risk" in message_lower or "more risk" in message_lower:
            risk_change = 0.1  # Default increase
        elif "decrease risk" in message_lower or "less risk" in message_lower:
            risk_change = -0.1  # Default decrease
        
        # Extract timeframe
        timeframe = None
        if any(word in message_lower for word in ["now", "immediate", "asap", "right away"]):
            timeframe = "immediate"
        elif any(word in message_lower for word in ["soon", "short term"]):
            timeframe = "short"
        elif any(word in message_lower for word in ["long term", "years"]):
            timeframe = "long"
        
        # Extract target (symbol or goal name)
        target = None
        # Look for stock symbols (uppercase 1-5 letter codes)
        symbol_pattern = r'\b([A-Z]{1,5})\b'
        symbols = re.findall(symbol_pattern, user_message)
        if symbols:
            # Filter out common words that might match
            common_words = {"I", "A", "THE", "AN", "TO", "FOR", "IN", "ON", "AT", "BY"}
            valid_symbols = [s for s in symbols if s not in common_words]
            if valid_symbols:
                target = valid_symbols[0]
        
        metadata = {"extraction_method": "keyword_matching"}
        metadata.update(metadata_extra)
        
        return UserIntent(
            type=intent_type,
            amount=amount,
            risk_change=risk_change,
            target=target,
            timeframe=timeframe,
            metadata=metadata
        )
    
    def _get_intent_extraction_prompt(self) -> str:
        """Get system prompt for intent extraction."""
        return """You are an intent extraction assistant. Your role is to parse user messages and extract structured investment intent information.

IMPORTANT: Distinguish between QUESTIONS and ACTIONS:
- QUESTIONS (use "get_advice"): "Should I invest?", "What about crypto?", "Is it good to invest?", "Should I invest in crypto?", "What do you think about...?"
- ACTIONS (use "invest"/"withdraw"/etc.): "I want to invest $1000", "Invest $500", "Let's invest now", "I'd like to invest"

If the message is a QUESTION asking for advice or opinion, use "get_advice" NOT "invest".

Extract the following information from the user's message:
- intent_type: One of "invest", "withdraw", "rebalance", "change_risk", "get_advice", or "other"
- amount: Dollar amount if mentioned (as a number, no currency symbols). If user says "all", "everything", or "100%", set to null (will be handled separately)
- risk_change: If user wants to change risk, provide a number between -1.0 and 1.0 (positive = more risk, negative = less risk)
- target: Stock symbol (e.g., "AAPL") or goal name if mentioned
- timeframe: "immediate", "short", "medium", "long", or null

Return ONLY valid JSON in this exact format:
{
  "intent_type": "invest",
  "amount": 1000.0,
  "risk_change": null,
  "target": null,
  "timeframe": "immediate"
}

Rules:
- If amount is not mentioned, set to null
- If user says "all", "everything", or "100%", set amount to null and include "percentage_based": true in metadata
- If risk_change is not mentioned, set to null
- If target is not mentioned, set to null
- If timeframe is not mentioned, set to null
- Use null (not "null" string) for missing values
- Only extract what is explicitly stated - do not infer or assume"""
    
    def _parse_intent_data(self, intent_data: Dict[str, Any]) -> UserIntent:
        """
        Parse intent data dictionary into UserIntent.
        
        Args:
            intent_data: Intent data from LLM or keyword matching
            
        Returns:
            UserIntent object
            
        Raises:
            ValidationError: If intent data is invalid
        """
        # Extract intent type
        intent_type_str = intent_data.get("intent_type", "invest")
        try:
            intent_type = UserIntentType(intent_type_str)
        except ValueError:
            # Default to INVEST if invalid
            intent_type = UserIntentType.INVEST
        
        # Extract amount (handle null, None, or numeric)
        amount = intent_data.get("amount")
        if amount is None or amount == "null":
            amount = None
        else:
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = None
        
        # Extract risk_change
        risk_change = intent_data.get("risk_change")
        if risk_change is None or risk_change == "null":
            risk_change = None
        else:
            try:
                risk_change = float(risk_change)
                # Clamp to valid range
                risk_change = max(-1.0, min(1.0, risk_change))
            except (ValueError, TypeError):
                risk_change = None
        
        # Extract target
        target = intent_data.get("target")
        if target is None or target == "null" or target == "":
            target = None
        
        # Extract timeframe
        timeframe = intent_data.get("timeframe")
        if timeframe is None or timeframe == "null" or timeframe == "":
            timeframe = None
        
        # Extract metadata
        metadata = intent_data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["extraction_method"] = "llm"
        
        # Check if amount is percentage-based ("all", "everything", "100%")
        if amount is None:
            # Check if user said "all", "everything", or "100%"
            user_message_lower = str(intent_data.get("original_message", "")).lower()
            if any(word in user_message_lower for word in ["all", "everything", "100%", "entire"]):
                metadata["percentage_based"] = True
                metadata["amount_type"] = "all"
        
        return UserIntent(
            type=intent_type,
            amount=amount,
            risk_change=risk_change,
            target=target,
            timeframe=timeframe,
            metadata=metadata
        )

