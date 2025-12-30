"""Profile service for managing user financial profiles.

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
from app.agents.schemas import (
    FinancialState,
    Cashflow,
    DebtSummary,
    PortfolioSummary,
    FinancialGoal,
)
from app.models.profile import ProfileResponse, ProfileUpdateRequest
from app.repositories import profiles_repo
from app.models.errors import NotFoundError, ExternalServiceError


class ProfileService:
    """
    Service for managing user financial profiles.
    
    This service handles conversion between FinancialState (canonical model)
    and database representation (profile table).
    """
    
    def get_profile(self, user_id: str) -> ProfileResponse:
        """
        Get user profile as FinancialState representation.
        
        Args:
            user_id: User ID
            
        Returns:
            ProfileResponse with full FinancialState components
            
        Raises:
            NotFoundError: If profile not found
            ExternalServiceError: If database operation fails
        """
        profile = profiles_repo.get_profile(user_id)
        if not profile:
            raise NotFoundError("User profile not found", "PROFILE_NOT_FOUND")
        
        # Convert database profile to FinancialState
        financial_state = self._profile_to_financial_state(profile)
        
        # Extract additional profile fields
        risk_level = profile.get("risk_level")
        investment_horizon = profile.get("investment_horizon")
        
        # Convert to ProfileResponse
        return ProfileResponse.from_financial_state(
            financial_state,
            risk_level=risk_level,
            investment_horizon=investment_horizon
        )
    
    def update_profile(
        self,
        user_id: str,
        update_request: ProfileUpdateRequest
    ) -> ProfileResponse:
        """
        Update user profile with FinancialState components.
        
        Args:
            user_id: User ID
            update_request: Profile update request with FinancialState components
            
        Returns:
            Updated ProfileResponse
            
        Raises:
            ExternalServiceError: If database operation fails
        """
        # Get existing profile or create defaults
        existing_profile = profiles_repo.get_profile(user_id)
        
        # Build profile data from update request
        profile_data = self._update_request_to_profile_data(
            user_id=user_id,
            existing_profile=existing_profile,
            update_request=update_request
        )
        
        # Upsert profile
        updated_profile = profiles_repo.upsert_profile(user_id, profile_data)
        
        # Convert back to FinancialState and return
        financial_state = self._profile_to_financial_state(updated_profile)
        
        risk_level = updated_profile.get("risk_level")
        investment_horizon = updated_profile.get("investment_horizon")
        
        return ProfileResponse.from_financial_state(
            financial_state,
            risk_level=risk_level,
            investment_horizon=investment_horizon
        )
    
    def _profile_to_financial_state(self, profile: Dict[str, Any]) -> FinancialState:
        """
        Convert database profile to FinancialState.
        
        Args:
            profile: Profile dictionary from database
            
        Returns:
            FinancialState object
        """
        # Build cashflow
        cashflow = Cashflow(
            monthly_income=profile.get("monthly_income", 0.0),
            monthly_expenses=profile.get("monthly_expenses", 0.0),
            net_cashflow=profile.get("monthly_income", 0.0) - profile.get("monthly_expenses", 0.0)
        )
        
        # Get emergency fund months (stored directly or calculated)
        emergency_fund_months = profile.get("emergency_fund_months", 0.0)
        
        # Build debt summary
        debt_summary = DebtSummary(
            total_debt=profile.get("total_debt", 0.0),
            credit_card_debt=profile.get("credit_card_debt", 0.0),
            mortgage_debt=profile.get("mortgage_debt", 0.0),
            student_loan_debt=profile.get("student_loan_debt", 0.0),
            other_debt=profile.get("other_debt", 0.0),
            monthly_debt_payments=profile.get("monthly_debt_payments", 0.0)
        )
        
        # Portfolio summary is not stored in profile (comes from snapshots)
        # For profile endpoint, we'll use empty portfolio
        portfolio_summary = PortfolioSummary(
            total_value=0.0,
            cash_balance=0.0,
            invested_value=0.0,
            positions_count=0,
            positions=[]
        )
        
        # Build goals from JSON
        goals_data = profile.get("goals", [])
        if isinstance(goals_data, str):
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
        
        # Build metadata
        metadata = {}
        if "credit_card_apr" in profile:
            metadata["credit_card_apr"] = profile["credit_card_apr"]
        if "other_metadata" in profile:
            other_meta = profile.get("other_metadata")
            if isinstance(other_meta, str):
                other_meta = json.loads(other_meta) if other_meta else {}
            metadata.update(other_meta)
        
        return FinancialState(
            cashflow=cashflow,
            emergency_fund_months=emergency_fund_months,
            debt_summary=debt_summary,
            portfolio_summary=portfolio_summary,
            goals=goals,
            metadata=metadata
        )
    
    def _update_request_to_profile_data(
        self,
        user_id: str,
        existing_profile: Optional[Dict[str, Any]],
        update_request: ProfileUpdateRequest
    ) -> Dict[str, Any]:
        """
        Convert ProfileUpdateRequest to database profile format.
        
        Args:
            user_id: User ID
            existing_profile: Existing profile data (if any)
            update_request: Update request
            
        Returns:
            Profile data dictionary for database
        """
        # Start with existing profile or defaults
        profile_data = existing_profile.copy() if existing_profile else {}
        profile_data["user_id"] = user_id
        
        # Update cashflow
        if update_request.cashflow:
            profile_data["monthly_income"] = update_request.cashflow.monthly_income
            profile_data["monthly_expenses"] = update_request.cashflow.monthly_expenses
        
        # Update emergency fund months
        if update_request.emergency_fund_months is not None:
            profile_data["emergency_fund_months"] = update_request.emergency_fund_months
        
        # Update debt summary
        if update_request.debt_summary:
            profile_data["total_debt"] = update_request.debt_summary.total_debt
            profile_data["credit_card_debt"] = update_request.debt_summary.credit_card_debt
            profile_data["mortgage_debt"] = update_request.debt_summary.mortgage_debt
            profile_data["student_loan_debt"] = update_request.debt_summary.student_loan_debt
            profile_data["other_debt"] = update_request.debt_summary.other_debt
            profile_data["monthly_debt_payments"] = update_request.debt_summary.monthly_debt_payments
        
        # Update goals (store as JSON)
        if update_request.goals is not None:
            goals_list = [goal.model_dump() for goal in update_request.goals]
            profile_data["goals"] = json.dumps(goals_list)
        
        # Update risk level and investment horizon
        if update_request.risk_level is not None:
            profile_data["risk_level"] = update_request.risk_level
        if update_request.investment_horizon is not None:
            profile_data["investment_horizon"] = update_request.investment_horizon
        
        # Update metadata
        if update_request.metadata is not None:
            # Extract credit_card_apr if present
            if "credit_card_apr" in update_request.metadata:
                profile_data["credit_card_apr"] = update_request.metadata["credit_card_apr"]
            
            # Store other metadata as JSON
            other_metadata = {k: v for k, v in update_request.metadata.items() if k != "credit_card_apr"}
            if other_metadata:
                profile_data["other_metadata"] = json.dumps(other_metadata)
        
        return profile_data

