"""Service for handling recommendation approvals.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from typing import Optional, Dict, Any, List
import json
from app.repositories import recommendations_repo
from app.agents.schemas import AdvisorDecision, RequiredConfirmation
from app.models.errors import NotFoundError, ValidationError, ExternalServiceError


class ApprovalService:
    """
    Service for handling recommendation approvals.
    
    This service validates confirmations before allowing approval.
    """
    
    def validate_confirmations(
        self,
        recommendation: Dict[str, Any],
        provided_confirmations: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Validate that all required confirmations are provided.
        
        Args:
            recommendation: Recommendation dictionary from database
            provided_confirmations: Dictionary mapping confirmation_id to confirmation text/acknowledgement
            
        Raises:
            ValidationError: If confirmations are missing or invalid
            NotFoundError: If recommendation data is invalid
        """
        # Parse decision from recommendation
        decision_json_str = recommendation.get("decision_json")
        if not decision_json_str:
            raise NotFoundError(
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
        
        # Check if there are required confirmations
        if not decision.required_confirmations:
            # No confirmations required, approval is valid
            return
        
        # If confirmations are required but none provided
        if not provided_confirmations:
            raise ValidationError(
                "Required confirmations not provided",
                "MISSING_CONFIRMATIONS"
            )
        
        # Validate each required confirmation
        for required_conf in decision.required_confirmations:
            if not required_conf.required:
                continue  # Skip non-required confirmations
            
            confirmation_id = required_conf.confirmation_id
            
            # Check if confirmation was provided
            if confirmation_id not in provided_confirmations:
                raise ValidationError(
                    f"Missing required confirmation: {confirmation_id}",
                    "MISSING_CONFIRMATION"
                )
            
            provided_text = provided_confirmations[confirmation_id]
            
            # Validate based on confirmation type
            if required_conf.override_acknowledgement:
                # BLOCK case: Must match override acknowledgement exactly
                if provided_text != required_conf.override_acknowledgement:
                    raise ValidationError(
                        f"Override acknowledgement for {confirmation_id} does not match required text",
                        "INVALID_OVERRIDE_ACKNOWLEDGEMENT"
                    )
            elif required_conf.confirmation_text:
                # WARN case: Must match confirmation text exactly
                if provided_text != required_conf.confirmation_text:
                    raise ValidationError(
                        f"Confirmation text for {confirmation_id} does not match required text",
                        "INVALID_CONFIRMATION_TEXT"
                    )
            else:
                # Generic confirmation - just check it's provided
                if not provided_text or len(provided_text.strip()) == 0:
                    raise ValidationError(
                        f"Confirmation {confirmation_id} is empty",
                        "EMPTY_CONFIRMATION"
                    )
    
    def approve_recommendation(
        self,
        user_id: str,
        recommendation_id: str,
        confirmations: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Approve a recommendation after validating confirmations.
        
        Args:
            user_id: User ID
            recommendation_id: Recommendation ID
            confirmations: Optional confirmations dictionary
            
        Returns:
            Updated recommendation dictionary
            
        Raises:
            NotFoundError: If recommendation not found
            ValidationError: If confirmations are invalid
        """
        # Load recommendation
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
        
        # Validate confirmations
        self.validate_confirmations(recommendation, confirmations)
        
        # TODO: Execute trades via Alpaca integration
        # For now, just update status
        
        # Update recommendation status
        # Note: This would typically be done via repository update method
        # For now, we'll return the recommendation with updated status
        recommendation["status"] = "approved"
        
        return recommendation

