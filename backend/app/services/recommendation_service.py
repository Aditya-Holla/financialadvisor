"""Recommendation service for generating portfolio allocation examples.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories

Service Constraints:
- ONLY executes when user explicitly requests recommendations
- ONLY executes when guardrail has already returned ALLOW (enforced by ChatService + Orchestrator)
- All outputs framed as examples, educational illustrations, trade-offs
- Avoids imperative or directive language
- Does NOT present outputs as personalized financial advice

This service trusts ChatService + Orchestrator to enforce safety.
Its responsibility starts ONLY after guardrail approval.
"""

from typing import Optional, Dict, Any
from app.agents.orchestrator import OrchestratorAgent
from app.agents.schemas import (
    FinancialState,
    UserIntent,
    UserIntentType,
    PortfolioProposal,
    AdvisorDecision,
)
from app.repositories import profiles_repo, snapshots_repo, recommendations_repo
from app.models.errors import NotFoundError, ExternalServiceError


class RecommendationService:
    """
    Service for generating portfolio allocation examples and educational illustrations.
    
    This service provides educational portfolio allocation examples that:
    - Are only generated when user explicitly requests recommendations
    - Are only generated when guardrail has already returned ALLOW (enforced upstream)
    - Are framed as examples, educational illustrations, and trade-offs
    - Avoid imperative or directive language
    - Do NOT present as personalized financial advice
    
    This service trusts ChatService + Orchestrator to enforce safety.
    It assumes guardrail has already returned ALLOW before this service is called.
    Its responsibility starts ONLY after guardrail approval.
    
    Flow:
    1. Validates user intent explicitly requests recommendations
    2. Loads user profile and latest portfolio snapshot
    3. Builds FinancialState and UserIntent
    4. Calls model to get PortfolioProposal (as example)
    5. Calls orchestrator.decide() (orchestrator will validate with guardrail)
    6. Stores result in database (framed as educational example)
    """
    
    def __init__(
        self,
        orchestrator: Optional[OrchestratorAgent] = None
    ):
        """
        Initialize recommendation service.
        
        Args:
            orchestrator: Optional orchestrator agent (creates new if not provided)
        """
        self.orchestrator = orchestrator or OrchestratorAgent()
    
    async def generate_recommendation(
        self,
        user_id: str,
        user_intent_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a portfolio allocation example for educational purposes.
        
        This method assumes:
        1. User explicitly requests recommendations (GET_ADVICE or INVEST intent)
        2. Guardrail has already returned ALLOW (enforced by ChatService + Orchestrator)
        
        This service trusts ChatService + Orchestrator to enforce safety.
        It does NOT perform its own guardrail checks.
        
        All outputs are framed as examples, educational illustrations, and trade-offs.
        They are NOT personalized financial advice.
        
        Args:
            user_id: User ID
            user_intent_data: Optional user intent data (must explicitly request recommendations)
            
        Returns:
            Recommendation data dictionary (framed as educational example)
            
        Raises:
            NotFoundError: If profile or snapshot not found
            ExternalServiceError: If database or service operations fail
        """
        # Step 1: Build UserIntent to check if user explicitly requests recommendations
        user_intent = self._build_user_intent(user_intent_data or {})
        
        # Defensive check: User must explicitly request recommendations
        if not self._is_explicit_recommendation_request(user_intent):
            raise ExternalServiceError(
                "This service only generates examples when user explicitly requests recommendations. "
                "Use appropriate intent type (GET_ADVICE or INVEST).",
                "INTENT_NOT_RECOMMENDATION_REQUEST"
            )
        
        # Step 2: Load profile and latest snapshot
        profile = profiles_repo.get_profile(user_id)
        if not profile:
            raise NotFoundError("User profile not found", "PROFILE_NOT_FOUND")
        
        snapshot = snapshots_repo.get_latest_snapshot(user_id)
        if not snapshot:
            raise NotFoundError("Portfolio snapshot not found", "SNAPSHOT_NOT_FOUND")
        
        # Step 3: Build FinancialState
        # Capture timestamp at decision time for deterministic replay
        from datetime import datetime, timezone
        decision_timestamp = datetime.now(timezone.utc).isoformat()
        financial_state = self._build_financial_state(profile, snapshot)
        # Override timestamp to ensure deterministic replay
        financial_state.timestamp = decision_timestamp
        
        # Step 4: Call model to get PortfolioProposal (as educational example)
        # Note: Guardrail validation is handled by Orchestrator (called in Step 5)
        proposal = await self._get_model_proposal(financial_state, user_intent, profile)
        
        # Step 5: Call orchestrator.decide()
        # Orchestrator will call guardrail agent FIRST to validate
        # This service trusts that ChatService only calls it when guardrail returns ALLOW
        decision = await self.orchestrator.decide(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=proposal
        )
        
        # Step 6: Store recommendation (framed as educational example)
        rec_data = self._build_recommendation_data(decision, financial_state, user_intent)
        stored_rec = recommendations_repo.create_recommendation(user_id, rec_data)
        
        return stored_rec
    
    def _is_explicit_recommendation_request(self, user_intent: UserIntent) -> bool:
        """
        Check if user intent explicitly requests recommendations.
        
        This is a defensive check to ensure the service is only called
        when user explicitly requests recommendations.
        
        Args:
            user_intent: User intent to check
            
        Returns:
            True if intent explicitly requests recommendations, False otherwise
        """
        # Only GET_ADVICE and INVEST intents are considered explicit recommendation requests
        return user_intent.type in [UserIntentType.GET_ADVICE, UserIntentType.INVEST]
    
    def _build_financial_state(
        self,
        profile: Dict[str, Any],
        snapshot: Dict[str, Any]
    ) -> FinancialState:
        """
        Build FinancialState from profile and snapshot data.
        
        Args:
            profile: Profile dictionary from database
            snapshot: Snapshot dictionary from database
            
        Returns:
            FinancialState object
        """
        from app.agents.schemas import (
            Cashflow,
            DebtSummary,
            PortfolioSummary,
            FinancialGoal,
        )
        
        # Build cashflow from profile
        cashflow = Cashflow(
            monthly_income=profile.get("monthly_income", 0.0),
            monthly_expenses=profile.get("monthly_expenses", 0.0),
            net_cashflow=profile.get("monthly_income", 0.0) - profile.get("monthly_expenses", 0.0)
        )
        
        # Calculate emergency fund months
        cash_balance = snapshot.get("cash", 0.0)
        monthly_expenses = profile.get("monthly_expenses", 0.0)
        emergency_fund_months = cash_balance / monthly_expenses if monthly_expenses > 0 else 0.0
        
        # Build debt summary from profile
        debt_summary = DebtSummary(
            total_debt=profile.get("total_debt", 0.0),
            credit_card_debt=profile.get("credit_card_debt", 0.0),
            mortgage_debt=profile.get("mortgage_debt", 0.0),
            student_loan_debt=profile.get("student_loan_debt", 0.0),
            other_debt=profile.get("other_debt", 0.0),
            monthly_debt_payments=profile.get("monthly_debt_payments", 0.0)
        )
        
        # Build portfolio summary from snapshot
        positions = snapshot.get("positions_json", [])
        if isinstance(positions, str):
            import json
            positions = json.loads(positions) if positions else []
        
        invested_value = sum(pos.get("value", 0.0) for pos in positions) if positions else 0.0
        total_value = cash_balance + invested_value
        
        portfolio_summary = PortfolioSummary(
            total_value=total_value,
            cash_balance=cash_balance,
            invested_value=invested_value,
            positions_count=len(positions),
            positions=positions
        )
        
        # Build goals from profile
        goals_data = profile.get("goals", [])
        if isinstance(goals_data, str):
            import json
            goals_data = json.loads(goals_data) if goals_data else []
        
        goals = []
        for goal_data in goals_data:
            goals.append(FinancialGoal(
                goal_id=goal_data.get("goal_id", ""),
                name=goal_data.get("name", ""),
                target_amount=goal_data.get("target_amount", 0.0),
                current_progress=goal_data.get("current_progress", 0.0),
                target_date=goal_data.get("target_date"),
                priority=goal_data.get("priority", 1)
            ))
        
        # Build metadata (e.g., credit card APR)
        metadata = {}
        if "credit_card_apr" in profile:
            metadata["credit_card_apr"] = profile["credit_card_apr"]
        
        return FinancialState(
            cashflow=cashflow,
            emergency_fund_months=emergency_fund_months,
            debt_summary=debt_summary,
            portfolio_summary=portfolio_summary,
            goals=goals,
            metadata=metadata
        )
    
    def _build_user_intent(self, intent_data: Dict[str, Any]) -> UserIntent:
        """
        Build UserIntent from intent data.
        
        Args:
            intent_data: Intent data dictionary
            
        Returns:
            UserIntent object
        """
        intent_type_str = intent_data.get("type", "invest")
        try:
            intent_type = UserIntentType(intent_type_str)
        except ValueError:
            intent_type = UserIntentType.INVEST
        
        return UserIntent(
            type=intent_type,
            amount=intent_data.get("amount"),
            risk_change=intent_data.get("risk_change"),
            target=intent_data.get("target"),
            timeframe=intent_data.get("timeframe", "immediate"),
            metadata=intent_data.get("metadata", {})
        )
    
    async def _get_model_proposal(
        self,
        financial_state: FinancialState,
        user_intent: UserIntent,
        profile: Dict[str, Any]
    ) -> Optional[PortfolioProposal]:
        """
        Get portfolio allocation example from model.
        
        This generates an educational example of portfolio allocation,
        not a personalized recommendation. The output is framed as an
        illustration of allocation concepts.
        
        Args:
            financial_state: User's financial state (for context only)
            user_intent: User's intent
            profile: User profile (for context only)
            
        Returns:
            PortfolioProposal as educational example, or None if model unavailable
            
        Note:
            This is a placeholder. In production, this would call the actual
            model (LLM or other) to generate an educational example.
            The model should be instructed to frame outputs as examples,
            not personalized advice.
        """
        # TODO: Implement actual model call with educational framing
        # Model should be instructed to:
        # - Frame outputs as examples and illustrations
        # - Explain trade-offs and considerations
        # - Avoid imperative or directive language
        # - Not present as personalized financial advice
        # For now, return None to let orchestrator handle missing proposal
        return None
    
    def _build_recommendation_data(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> Dict[str, Any]:
        """
        Build recommendation data dictionary for storage.
        
        This data is stored as an educational example, not personalized advice.
        All outputs are framed as examples, illustrations, and trade-offs.
        
        Args:
            decision: Advisor decision (framed as educational example)
            financial_state: Financial state used (for context)
            user_intent: User intent used
            
        Returns:
            Recommendation data dictionary (educational example)
        """
        import json
        import uuid
        from datetime import datetime, timezone
        
        rec_data = {
            "id": str(uuid.uuid4()),  # Generate unique ID
            "decision": decision.decision.value,
            "decision_json": json.dumps(decision.model_dump()),
            "proposal_json": json.dumps(decision.proposal.model_dump()) if decision.proposal else None,
            "financial_state_json": json.dumps(financial_state.model_dump()),
            "user_intent_json": json.dumps(user_intent.model_dump()),
            "guardrail_status": decision.metadata.get("guardrail_status"),
            "guardrail_reasons": json.dumps(decision.metadata.get("guardrail_reasons", [])),
            "computed_values_json": json.dumps(decision.metadata.get("computed_values", {})),
            "status": "pending",  # pending, approved, rejected
            "created_at": datetime.now(timezone.utc).isoformat(),
            # Store evaluation timestamp for deterministic replay
            "evaluation_timestamp": financial_state.timestamp,
            # Educational framing metadata
            "is_educational_example": True,
            "framing": "example_illustration_tradeoffs",
        }
        
        return rec_data

