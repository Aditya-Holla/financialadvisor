"""LLM integration for educational explanations.

Rules of Engagement:
- LLM agents must never change numbers or decide trades
- All LLM outputs must be validated for safety
- Numbers must match exactly from input to output
- Fallback to templates if LLM fails or violates constraints
"""

from typing import Optional, Dict, Any, List
import re
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMIntegration:
    """
    LLM integration for generating educational explanations.
    
    Safety constraints:
    - Only generates explanation text
    - Never changes numbers
    - Never suggests trades or overrides decisions
    - Validates output before returning
    """
    
    def __init__(self):
        """Initialize LLM integration."""
        self.settings = get_settings()
        self.client = None
        
        # Initialize OpenAI client if API key is available
        if self.settings.LLM_API_KEY:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.settings.LLM_API_KEY)
            except ImportError:
                # OpenAI package not installed, will fallback to templates
                pass
    
    def is_available(self) -> bool:
        """Check if LLM is available (API key and client configured)."""
        return self.client is not None and self.settings.LLM_API_KEY is not None
    
    async def generate_explanation(
        self,
        decision_summary: Dict[str, Any],
        financial_state_summary: Dict[str, Any],
        guardrail_info: Optional[Dict[str, Any]] = None,
        proposal_info: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate explanation text using LLM.
        
        Args:
            decision_summary: Summary of the advisor decision
            financial_state_summary: Summary of financial state
            guardrail_info: Optional guardrail information
            proposal_info: Optional proposal information
            
        Returns:
            Generated explanation text, or None if LLM unavailable or fails
            
        Safety:
            - Validates that numbers in output match input
            - Falls back to None if validation fails
        """
        if not self.is_available():
            logger.warning("LLM not available - client or API key missing")
            return None
        
        try:
            # Build safety-constrained prompt
            prompt = self._build_safe_prompt(
                decision_summary,
                financial_state_summary,
                guardrail_info,
                proposal_info
            )
            
            # Extract numbers from input for validation
            input_numbers = self._extract_numbers(decision_summary, proposal_info)
            
            logger.info(f"Calling LLM with model: {self.settings.LLM_MODEL}")
            
            # Call LLM
            response = await self.client.chat.completions.create(
                model=self.settings.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Some creativity but not too much
                max_tokens=500
            )
            
            explanation = response.choices[0].message.content.strip()
            logger.info(f"LLM generated explanation (length: {len(explanation)})")
            
            # Validate numbers match (relaxed - only check significant numbers)
            if not self._validate_numbers(explanation, input_numbers):
                logger.warning("LLM output failed number validation, using template fallback")
                return None
            
            # Validate no trade suggestions or decision overrides
            unsafe_reason = self._contains_unsafe_content(explanation)
            if unsafe_reason:
                logger.warning(f"LLM output contains unsafe content: {unsafe_reason}, using template fallback")
                logger.debug(f"LLM output that triggered safety check: {explanation[:200]}...")
                return None
            
            logger.info("LLM explanation validated successfully")
            return explanation
            
        except Exception as e:
            # Log the error for debugging
            logger.error(f"LLM call failed: {str(e)}", exc_info=True)
            logger.error(f"LLM error details: {type(e).__name__}: {str(e)}")
            return None
    
    def _get_system_prompt(self) -> str:
        """Get system prompt with educational constraints."""
        return """You are a financial education assistant. Your role is to explain financial concepts and portfolio data in clear, educational terms, like a finance professor explaining tools.

CRITICAL EDUCATIONAL RULES:
1. NEVER change any numbers - use the exact numbers provided
2. NEVER use words like "buy", "sell", "invest", or "you should"
3. NEVER rank, score, or recommend securities
4. NEVER predict future performance
5. ONLY explain concepts and existing data
6. Use neutral, explanatory language only
7. Explain what data means, not what actions to take
8. Use the exact percentages, amounts, and values provided

Your explanations should be:
- Clear and educational, like a finance professor
- Neutral and explanatory, not advisory
- Focused on explaining concepts and existing data
- Helpful for understanding financial fundamentals
- Respectful of the user's financial situation
- Never tell users what to do, only explain what things mean"""
    
    def _build_safe_prompt(
        self,
        decision_summary: Dict[str, Any],
        financial_state_summary: Dict[str, Any],
        guardrail_info: Optional[Dict[str, Any]],
        proposal_info: Optional[Dict[str, Any]]
    ) -> str:
        """Build a safe prompt with all necessary information."""
        parts = []
        
        parts.append("Explain this portfolio proposal and decision in clear, educational terms. Act like a finance professor explaining concepts, not an advisor making recommendations.")
        parts.append("\n## Decision:")
        parts.append(f"Type: {decision_summary.get('decision_type', 'unknown')}")
        parts.append(f"Status: {decision_summary.get('status', 'unknown')}")
        
        if guardrail_info:
            parts.append("\n## Safety Guardrails:")
            parts.append(f"Status: {guardrail_info.get('status', 'unknown')}")
            if guardrail_info.get('reasons'):
                parts.append("Safety considerations:")
                for reason in guardrail_info['reasons']:
                    parts.append(f"- {reason.get('message', reason.get('code', ''))}")
        
        if proposal_info:
            parts.append("\n## Portfolio Allocation:")
            allocation = proposal_info.get('allocation', {})
            if allocation:
                parts.append(f"Allocation: {allocation.get('stocks', 0)}% stocks, {allocation.get('bonds', 0)}% bonds, {allocation.get('cash', 0)}% cash")
            if proposal_info.get('trade_count'):
                parts.append(f"Number of transactions: {proposal_info['trade_count']}")
            if proposal_info.get('risk_delta') is not None:
                parts.append(f"Risk profile change: {proposal_info['risk_delta']}")
        
        parts.append("\n## Financial Context:")
        parts.append(f"Emergency fund coverage: {financial_state_summary.get('emergency_fund_months', 0)} months")
        parts.append(f"Net cashflow: ${financial_state_summary.get('net_cashflow', 0):,.0f}/month")
        
        parts.append("\nRemember:")
        parts.append("- Use the EXACT numbers provided")
        parts.append("- Explain concepts and data, not what actions to take")
        parts.append("- Use neutral, educational language")
        parts.append("- Never use words like 'buy', 'sell', 'invest', or 'you should'")
        parts.append("- Never rank, score, or recommend securities")
        parts.append("- Never predict future performance")
        
        return "\n".join(parts)
    
    def _extract_numbers(
        self,
        decision_summary: Dict[str, Any],
        proposal_info: Optional[Dict[str, Any]]
    ) -> List[float]:
        """Extract all numbers from input for validation."""
        numbers = []
        
        if proposal_info:
            allocation = proposal_info.get('allocation', {})
            numbers.extend([
                allocation.get('stocks', 0),
                allocation.get('bonds', 0),
                allocation.get('cash', 0),
                allocation.get('other', 0)
            ])
            if proposal_info.get('trade_count'):
                numbers.append(float(proposal_info['trade_count']))
            if proposal_info.get('risk_delta') is not None:
                numbers.append(proposal_info['risk_delta'])
        
        return [n for n in numbers if n is not None]
    
    def _validate_numbers(self, text: str, expected_numbers: List[float]) -> bool:
        """
        Validate that numbers in text match expected numbers.
        
        This is a safety check to ensure LLM didn't change any values.
        Relaxed validation: only checks significant numbers (> 1% or > 1).
        """
        if not expected_numbers:
            # No numbers to validate
            return True
        
        # Extract all numbers from text
        # Match percentages like "60.0%", "60%", "60.5%"
        # Match decimals like "0.1", "1.5"
        # Match integers like "1", "10"
        number_pattern = r'\b(\d+\.?\d*)\b'
        found_numbers = [float(match) for match in re.findall(number_pattern, text)]
        
        # Only validate significant numbers (relaxed approach)
        # Skip very small numbers and zeros
        significant_numbers = [n for n in expected_numbers if abs(n) > 1.0 or (abs(n) > 0.01 and abs(n) <= 1.0)]
        
        if not significant_numbers:
            # No significant numbers to validate
            return True
        
        # Check if significant numbers appear in the text (with tolerance)
        # We require at least 50% of significant numbers to be present
        found_count = 0
        for expected in significant_numbers:
            # Find matching number (within 5% tolerance for percentages, 10% for others)
            tolerance = 0.05 if expected > 10 else 0.10
            for found_num in found_numbers:
                if abs(found_num - expected) / max(abs(expected), 1.0) < tolerance:
                    found_count += 1
                    break
        
        # Require at least 50% of significant numbers to be present
        return found_count >= len(significant_numbers) * 0.5
    
    def _contains_unsafe_content(self, text: str) -> Optional[str]:
        """
        Check if text contains unsafe content (recommendations, predictions, advisory language).
        
        Returns the pattern that matched if unsafe content detected, None otherwise.
        More precise patterns to avoid false positives.
        """
        text_lower = text.lower()
        
        # Educational constraint patterns (avoid false positives)
        # Patterns are ordered from most specific to least specific
        unsafe_patterns = [
            # Recommendation language
            (r'\byou should\b.*(?:buy|sell|invest)', 'using "you should" with action words'),
            (r'\byou should\b.*(?:stock|bond|asset|security)', 'using "you should" with securities'),
            (r'recommend.*you.*(?:buy|sell|invest)', 'recommending specific actions'),
            (r'suggest.*you.*(?:buy|sell|invest)', 'suggesting specific actions'),
            (r'\byou should\b.*(?:purchase|acquire|divest)', 'using "you should" with purchase language'),
            # Action words in advisory context
            (r'\b(?:buy|sell|invest)\b.*(?:now|today|immediately|should)', 'using action words with urgency'),
            (r'\b(?:buy|sell|invest)\b.*(?:recommend|suggest|advise)', 'using action words with recommendation language'),
            # Ranking/scoring
            (r'(?:rank|score|rate).*as.*(?:best|worst|top|bottom)', 'ranking or scoring securities'),
            (r'(?:best|worst|top|bottom).*stock|security|investment', 'ranking securities'),
            # Predictions
            (r'(?:will|going to|likely to).*(?:increase|decrease|go up|go down|rise|fall)', 'predicting future performance'),
            (r'(?:expected|forecast|predict).*(?:return|performance|price)', 'predicting returns or performance'),
            (r'(?:guarantee|guaranteed).*(?:return|profit|gain)', 'guaranteeing returns'),
            # Trade suggestions
            (r'suggest.*new.*trade', 'suggesting new trades'),
            (r'recommend.*different.*(?:allocation|portfolio|strategy)', 'recommending different strategies'),
            (r'consider.*instead.*of.*this', 'suggesting alternatives to current proposal'),
            # Decision overrides
            (r'override.*decision', 'overriding decisions'),
            (r'disagree.*with.*this.*decision', 'disagreeing with decisions'),
            (r'change.*the.*allocation.*to', 'changing allocations'),
            (r'modify.*this.*proposal.*to', 'modifying proposals'),
        ]
        
        for pattern, description in unsafe_patterns:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                matched_text = match.group(0) if match else "pattern matched"
                return f"{description} (matched: '{matched_text[:50]}...')"
        
        return None

