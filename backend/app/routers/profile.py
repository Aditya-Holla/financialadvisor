"""Profile management endpoints.

Rules of Engagement:
- Agents are separate from FastAPI routers and services
- Business logic lives in services, agents orchestrate and coordinate
- LLM agents must never change numbers or decide trades
- Guardrails must be deterministic code, not LLM decisions
- All model outputs must be structured JSON (Pydantic models)
- Agents coordinate between integrations, services, and repositories
"""

from fastapi import APIRouter, Depends, Body
from app.auth import get_current_user
from app.models.user import UserContext
from app.models.profile import ProfileResponse, ProfileUpdateRequest
from app.models.errors import NotFoundError
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: UserContext = Depends(get_current_user)
):
    """
    Get user profile with full FinancialState representation.
    
    Returns all FinancialState components:
    - Cashflow (income, expenses, net cashflow)
    - Emergency fund months
    - Debt summary (all types with APRs)
    - Financial goals (with target dates)
    - Risk level and investment horizon
    - Additional metadata
    
    Requires: Authorization: Bearer <token>
    
    Response Contract:
    - cashflow: Cashflow object (monthly_income, monthly_expenses, net_cashflow)
    - emergency_fund_months: float (emergency fund coverage in months)
    - debt_summary: DebtSummary object (all debt types and monthly payments)
    - goals: List[FinancialGoal] (goals with target amounts and dates)
    - risk_level: Optional[str] (conservative, moderate, aggressive)
    - investment_horizon: Optional[str] (short, medium, long)
    - metadata: Dict[str, Any] (additional metadata like credit_card_apr)
    
    Example Response:
    {
      "cashflow": {
        "monthly_income": 5000.0,
        "monthly_expenses": 3000.0,
        "net_cashflow": 2000.0
      },
      "emergency_fund_months": 6.0,
      "debt_summary": {
        "total_debt": 10000.0,
        "credit_card_debt": 5000.0,
        "mortgage_debt": 0.0,
        "student_loan_debt": 5000.0,
        "other_debt": 0.0,
        "monthly_debt_payments": 500.0
      },
      "goals": [
        {
          "goal_id": "goal-1",
          "name": "Emergency Fund",
          "target_amount": 20000.0,
          "current_progress": 10000.0,
          "target_date": null,
          "priority": 1
        }
      ],
      "risk_level": "moderate",
      "investment_horizon": "long",
      "metadata": {
        "credit_card_apr": 20.0
      }
    }
    
    Error Responses:
    - 404 NotFoundError: Profile not found
      {
        "code": "PROFILE_NOT_FOUND",
        "message": "User profile not found",
        "details": null
      }
    """
    service = ProfileService()
    return service.get_profile(user.user_id)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    user: UserContext = Depends(get_current_user),
    update_request: ProfileUpdateRequest = Body(...)
):
    """
    Create or update user profile with FinancialState components.
    
    Updates profile with any provided fields:
    - Cashflow (income, expenses)
    - Emergency fund months
    - Debt summary (all types with APRs)
    - Financial goals (with target dates)
    - Risk level and investment horizon
    - Additional metadata
    
    All fields are optional - only provided fields will be updated.
    Missing fields will be preserved from existing profile or set to defaults.
    
    Requires: Authorization: Bearer <token>
    
    Request Body (all fields optional):
    {
      "cashflow": {
        "monthly_income": 5000.0,
        "monthly_expenses": 3000.0
      },
      "emergency_fund_months": 6.0,
      "debt_summary": {
        "total_debt": 10000.0,
        "credit_card_debt": 5000.0,
        "mortgage_debt": 0.0,
        "student_loan_debt": 5000.0,
        "other_debt": 0.0,
        "monthly_debt_payments": 500.0
      },
      "goals": [
        {
          "goal_id": "goal-1",
          "name": "Emergency Fund",
          "target_amount": 20000.0,
          "current_progress": 10000.0,
          "target_date": "2025-12-31",
          "priority": 1
        }
      ],
      "risk_level": "moderate",
      "investment_horizon": "long",
      "metadata": {
        "credit_card_apr": 20.0
      }
    }
    
    Response Contract:
    - Same as GET /profile - returns updated ProfileResponse
    
    Example Response:
    {
      "cashflow": {
        "monthly_income": 5000.0,
        "monthly_expenses": 3000.0,
        "net_cashflow": 2000.0
      },
      "emergency_fund_months": 6.0,
      "debt_summary": { ... },
      "goals": [ ... ],
      "risk_level": "moderate",
      "investment_horizon": "long",
      "metadata": { ... }
    }
    
    Error Responses:
    - 500 ExternalServiceError: Database operation failed
      {
        "code": "PROFILE_UPSERT_ERROR",
        "message": "Failed to upsert profile: ...",
        "details": null
      }
    """
    service = ProfileService()
    return service.update_profile(user.user_id, update_request)

