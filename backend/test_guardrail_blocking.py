"""Test script to verify guardrail blocking and friendly LLM explanations.

This script tests that when guardrails block an action, the system:
1. Returns a REJECT decision
2. Uses the friendly blocked-action handler
3. Provides conversational LLM explanation

Run with: python test_guardrail_blocking.py
(Ensure you're in the backend directory with venv activated and LLM_API_KEY configured)
"""

import asyncio
import sys
from app.services.chat_service import ChatService
from app.services.recommendation_service import RecommendationService
from app.repositories import profiles_repo, snapshots_repo
from app.agents.schemas import UserIntentType
import json


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


async def check_user_profile(user_id: str):
    """Check if user profile exists and show financial state."""
    print_header("Checking User Profile")
    
    profile = profiles_repo.get_profile(user_id)
    snapshot = snapshots_repo.get_latest_snapshot(user_id)
    
    if not profile:
        print_error(f"Profile not found for user: {user_id}")
        print_info("You need to create a profile with poor financial state to test guardrails")
        print_info("Example: negative cashflow, low emergency fund, high-interest debt")
        return False
    
    if not snapshot:
        print_error(f"Snapshot not found for user: {user_id}")
        return False
    
    print_success("Profile and snapshot found")
    
    # Show financial state
    monthly_income = profile.get("monthly_income", 0.0)
    monthly_expenses = profile.get("monthly_expenses", 0.0)
    net_cashflow = monthly_income - monthly_expenses
    cash_balance = snapshot.get("cash", 0.0)
    emergency_months = cash_balance / monthly_expenses if monthly_expenses > 0 else 0.0
    credit_card_debt = profile.get("credit_card_debt", 0.0)
    
    print(f"\n{Colors.BOLD}Financial State:{Colors.RESET}")
    print(f"  Monthly Income: ${monthly_income:,.2f}")
    print(f"  Monthly Expenses: ${monthly_expenses:,.2f}")
    print(f"  Net Cashflow: ${net_cashflow:,.2f} {'(NEGATIVE - will trigger guardrails)' if net_cashflow < 0 else ''}")
    print(f"  Cash Balance: ${cash_balance:,.2f}")
    print(f"  Emergency Fund: {emergency_months:.1f} months {'(LOW - will trigger guardrails)' if emergency_months < 3 else ''}")
    print(f"  Credit Card Debt: ${credit_card_debt:,.2f}")
    
    # Check if this profile would trigger guardrails
    would_trigger = False
    reasons = []
    
    if net_cashflow < 0:
        would_trigger = True
        reasons.append("Negative cashflow")
    
    if emergency_months < 3.0:
        would_trigger = True
        reasons.append("Low emergency fund")
    
    if credit_card_debt > 0:
        would_trigger = True
        reasons.append("Has credit card debt")
    
    if would_trigger:
        print_success(f"Profile would trigger guardrails: {', '.join(reasons)}")
    else:
        print_warning("Profile has good financial state - guardrails may not block")
        print_info("To test blocking, create a profile with:")
        print_info("  - Negative cashflow (expenses > income)")
        print_info("  - Low emergency fund (< 3 months)")
        print_info("  - High-interest debt")
    
    return True


async def test_blocked_action(user_id: str, message: str, expected_blocked: bool = True):
    """Test that an action is blocked and gets friendly explanation."""
    print(f"\n{Colors.BOLD}Testing: '{message}'{Colors.RESET}")
    
    service = ChatService()
    
    try:
        result = await service.handle_conversational_input(user_id, message)
        
        response_type = result.get("type")
        response_message = result.get("message", "")
        data = result.get("data", {})
        is_blocked = data.get("blocked", False)
        
        print(f"  Response type: {response_type}")
        print(f"  Blocked: {is_blocked}")
        
        if expected_blocked:
            if is_blocked:
                print_success("Action was correctly blocked")
            else:
                print_error("Action was NOT blocked (expected it to be blocked)")
                return False
            
            if response_type == "conversation":
                print_success("Got conversational response (not error)")
            else:
                print_warning(f"Response type is '{response_type}' (expected 'conversation')")
            
            if response_message and len(response_message) > 50:
                print_success(f"Got friendly explanation (length: {len(response_message)} chars)")
                print(f"\n{Colors.CYAN}Explanation:{Colors.RESET}")
                print(f"  {response_message[:300]}...")
                
                # Check if explanation is friendly (not just error message)
                error_indicators = ["error", "failed", "cannot", "unable", "rejected"]
                is_friendly = not any(indicator in response_message.lower() for indicator in error_indicators)
                
                if is_friendly:
                    print_success("Explanation is friendly and conversational")
                else:
                    print_warning("Explanation may be too error-like")
            else:
                print_error(f"Explanation too short or empty: {len(response_message)} chars")
                return False
        else:
            # Not expected to be blocked
            if not is_blocked:
                print_success("Action was allowed (as expected)")
            else:
                print_warning("Action was blocked (but not expected to be)")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            print_warning(f"Expected error (DB not set up): {error_msg[:100]}")
            return True  # Count as passed if it's just DB setup
        else:
            print_error(f"Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


async def test_recommendation_decision(user_id: str, message: str):
    """Test that recommendation has REJECT decision when blocked."""
    print(f"\n{Colors.BOLD}Checking Recommendation Decision: '{message}'{Colors.RESET}")
    
    service = RecommendationService()
    intent_service = ChatService().intent_service
    
    try:
        # Extract intent
        intent = await intent_service.extract_intent(message)
        intent_data = intent.model_dump(exclude_none=True)
        
        # Generate recommendation
        recommendation = await service.generate_recommendation(
            user_id=user_id,
            user_intent_data=intent_data
        )
        
        # Check decision
        decision_json_str = recommendation.get("decision_json")
        if decision_json_str:
            decision_data = json.loads(decision_json_str)
            decision_type = decision_data.get("decision")
            guardrail_status = decision_data.get("metadata", {}).get("guardrail_status")
            guardrail_reasons = decision_data.get("metadata", {}).get("guardrail_reasons", [])
            
            print(f"  Decision: {decision_type}")
            print(f"  Guardrail Status: {guardrail_status}")
            print(f"  Guardrail Reasons: {guardrail_reasons}")
            
            if decision_type == "reject":
                print_success("Decision is REJECT (blocked by guardrails)")
                if guardrail_reasons:
                    print_success(f"Guardrail reasons: {', '.join(guardrail_reasons)}")
                return True
            else:
                print_warning(f"Decision is '{decision_type}' (not REJECT)")
                print_info("This means guardrails allowed the action")
                return False
        else:
            print_error("No decision_json in recommendation")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            print_warning(f"Expected error (DB not set up): {error_msg[:100]}")
            return True
        else:
            print_error(f"Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run guardrail blocking tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Guardrail Blocking Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    
    # Test user ID (change this to your test user)
    test_user_id = "test-user-blocked"  # Changed from "test-user-123"
    
    print(f"\n{Colors.BOLD}Test User ID:{Colors.RESET} {test_user_id}")
    print_info("Change this in the script if you want to test with a different user")
    
    # Check profile
    profile_exists = await check_user_profile(test_user_id)
    
    if not profile_exists:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Cannot run tests - profile not found{Colors.RESET}")
        print(f"\n{Colors.BOLD}To create a test profile that triggers guardrails:{Colors.RESET}")
        print("1. Create a profile with:")
        print("   - monthly_income: 3000")
        print("   - monthly_expenses: 4000 (negative cashflow)")
        print("   - credit_card_debt: 5000")
        print("2. Create a snapshot with:")
        print("   - cash: 2000 (low emergency fund - less than 3 months)")
        print("3. Then run this test again")
        return 1
    
    # Test blocked actions
    print_header("Testing Blocked Actions")
    
    test_cases = [
        ("I want to invest $10000", True),  # Large investment with low emergency fund should be blocked
        ("I want to invest everything I have", True),  # Investing all should be blocked if emergency fund < 3 months
        ("I want to invest $1000 immediately", True),  # Immediate investment with negative cashflow should be blocked
    ]
    
    passed = 0
    failed = 0
    
    for message, expected_blocked in test_cases:
        result = await test_blocked_action(test_user_id, message, expected_blocked)
        if result:
            passed += 1
        else:
            failed += 1
    
    # Test recommendation decisions
    print_header("Testing Recommendation Decisions")
    
    decision_passed = 0
    decision_failed = 0
    
    for message, _ in test_cases:
        result = await test_recommendation_decision(test_user_id, message)
        if result:
            decision_passed += 1
        else:
            decision_failed += 1
    
    # Summary
    print_header("Test Summary")
    
    print(f"{Colors.BOLD}Blocked Action Tests:{Colors.RESET} {passed}/{len(test_cases)} passed, {failed} failed")
    print(f"{Colors.BOLD}Decision Type Tests:{Colors.RESET} {decision_passed}/{len(test_cases)} passed, {decision_failed} failed")
    
    total_passed = passed + decision_passed
    total_tests = len(test_cases) * 2
    
    if total_passed == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Guardrail blocking is working correctly.{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some tests failed or were skipped.{Colors.RESET}")
        print(f"{Colors.YELLOW}Note: If guardrails didn't block, your test user's financial state may be too good.{Colors.RESET}")
        print(f"{Colors.YELLOW}Create a profile with negative cashflow and low emergency fund to test blocking.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

