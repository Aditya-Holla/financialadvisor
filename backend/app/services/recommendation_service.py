"""Recommendation service for generating investment recommendations.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
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
from app.services.mystockdna_service import MyStockDNAService


class RecommendationService:
    """
    Service for generating investment recommendations.
    
    This service orchestrates the recommendation generation flow per the vision:
    1. Loads user profile and latest portfolio snapshot
    2. Builds FinancialState (canonical user financial state)
    3. Builds UserIntent from request
    4. Applies guardrails (pre-check: "Is investing appropriate?")
    5. Calls myStockDNA service for PortfolioProposal (Phase 2 - currently stub)
    6. Calls OrchestratorAgent.decide() to evaluate and make final decision
    7. Stores recommendation in database
    
    The OrchestratorAgent (Boss Agent) coordinates guardrails, model proposals,
    and generates explanations. This service handles the business logic of
    loading data and coordinating the flow.
    """
    
    def __init__(self, orchestrator: Optional[OrchestratorAgent] = None):
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
        Generate a recommendation for the user.
        
        Args:
            user_id: User ID
            user_intent_data: Optional user intent data (defaults to INVEST intent)
            
        Returns:
            Recommendation data dictionary
            
        Raises:
            NotFoundError: If profile or snapshot not found
            ExternalServiceError: If database or service operations fail
        """
        # Step 1: Load profile and latest snapshot
        profile = profiles_repo.get_profile(user_id)
        if not profile:
            raise NotFoundError("User profile not found", "PROFILE_NOT_FOUND")
        
        snapshot = snapshots_repo.get_latest_snapshot(user_id)
        if not snapshot:
            raise NotFoundError("Portfolio snapshot not found", "SNAPSHOT_NOT_FOUND")
        
        # Step 2: Build FinancialState
        # Capture timestamp at decision time for deterministic replay
        from datetime import datetime, timezone
        decision_timestamp = datetime.now(timezone.utc).isoformat()
        financial_state = self._build_financial_state(profile, snapshot)
        # Override timestamp to ensure deterministic replay
        financial_state.timestamp = decision_timestamp
        
        # Step 3: Build UserIntent
        user_intent = self._build_user_intent(user_intent_data or {})
        
        # Step 4: Pre-check guardrails (early exit if investing is inappropriate)
        # Note: Full guardrail check happens in orchestrator, but we could add
        # a quick pre-check here if needed for performance
        
        # Step 5: Call myStockDNA service to get PortfolioProposal
        # TODO (Phase 2): Replace with actual myStockDNA service call
        # For now, returns None and orchestrator creates stub proposal
        proposal = await self._get_model_proposal(financial_state, user_intent, profile)
        
        # Step 6: Call OrchestratorAgent.decide() (Boss Agent)
        # Orchestrator evaluates guardrails, re-applies constraints to proposal,
        # and makes final decision with required confirmations
        decision = await self.orchestrator.decide(
            financial_state=financial_state,
            user_intent=user_intent,
            proposal=proposal
        )
        
        # Step 7: Store recommendation
        rec_data = self._build_recommendation_data(decision, financial_state, user_intent)
        stored_rec = recommendations_repo.create_recommendation(user_id, rec_data)
        
        return stored_rec
    
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
        Get portfolio proposal from myStockDNA model.
        
        Args:
            financial_state: User's financial state
            user_intent: User's intent
            profile: User profile
            
        Returns:
            PortfolioProposal from myStockDNA service, or None if service unavailable
            
        Note:
            Phase 2: Calls myStockDNA service to generate proposals.
            myStockDNA models are responsible for:
            - Portfolio optimization
            - Allocation targets
            - Rebalance proposals
            - Trade generation
            
            They operate independently of user interaction and do NOT:
            - Communicate with users
            - Enforce personal finance constraints
            - Execute trades autonomously
        """
        try:
            service = MyStockDNAService()
            proposal = await service.generate_proposal(financial_state, user_intent, profile)
            return proposal
        except ExternalServiceError:
            # If myStockDNA service fails, return None and let orchestrator create stub
            # This provides fallback behavior
            return None
        except Exception as e:
            # Log unexpected errors but still return None for fallback
            # In production, might want to log this
            return None
    
    def _build_recommendation_data(
        self,
        decision: AdvisorDecision,
        financial_state: FinancialState,
        user_intent: UserIntent
    ) -> Dict[str, Any]:
        """
        Build recommendation data dictionary for storage.
        
        Args:
            decision: Advisor decision
            financial_state: Financial state used
            user_intent: User intent used
            
        Returns:
            Recommendation data dictionary
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
        }
        
        return rec_data

