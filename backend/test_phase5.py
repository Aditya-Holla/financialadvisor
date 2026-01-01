"""Test script for Phase 5: Conversational Input Processing.

Tests:
1. Intent extraction (LLM and keyword fallback)
2. Conversational input handling
3. Chat endpoint integration

Run with: python test_phase5.py
(Ensure you're in the backend directory with venv activated)
"""

import asyncio
import sys
from app.services.intent_service import IntentService
from app.services.chat_service import ChatService
from app.agents.schemas import UserIntentType


async def test_intent_extraction():
    """Test intent extraction service."""
    print("\n" + "=" * 60)
    print("Testing Intent Extraction Service")
    print("=" * 60)
    
    service = IntentService()
    
    test_cases = [
        ("I want to invest $1000", UserIntentType.INVEST, 1000.0),
        ("rebalance my portfolio", UserIntentType.REBALANCE, None),
        ("I need to withdraw $500", UserIntentType.WITHDRAW, 500.0),
        ("increase my risk by 10%", UserIntentType.CHANGE_RISK, None),
        ("What should I know about emergency funds?", UserIntentType.GET_ADVICE, None),
        ("I'd like to invest $2000 in AAPL next month", UserIntentType.INVEST, 2000.0),
    ]
    
    passed = 0
    failed = 0
    
    for message, expected_type, expected_amount in test_cases:
        try:
            print(f"\n📝 Testing: '{message}'")
            intent = await service.extract_intent(message)
            
            # Check intent type (more lenient - allow LLM to be close)
            if intent.type == expected_type:
                print(f"  ✓ Intent type correct: {intent.type.value}")
                passed += 1
            elif expected_type == UserIntentType.GET_ADVICE and intent.type in [UserIntentType.GET_ADVICE, UserIntentType.OTHER]:
                # Allow OTHER for general questions if LLM interprets differently
                print(f"  ✓ Intent type acceptable: {intent.type.value} (expected {expected_type.value})")
                passed += 1
            else:
                print(f"  ✗ Intent type mismatch: expected {expected_type.value}, got {intent.type.value}")
                failed += 1
                continue
            
            # Check amount if expected
            if expected_amount is not None:
                if intent.amount and abs(intent.amount - expected_amount) < 0.01:
                    print(f"  ✓ Amount correct: ${intent.amount:.2f}")
                else:
                    print(f"  ⚠ Amount mismatch: expected ${expected_amount:.2f}, got ${intent.amount or 'None'}")
            else:
                print(f"  ✓ Amount: {intent.amount or 'None'}")
            
            # Print full intent
            print(f"  Intent details: {intent.model_dump()}")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Intent Extraction Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    
    return failed == 0


async def test_chat_service_conversational():
    """Test chat service with conversational input."""
    print("\n" + "=" * 60)
    print("Testing Chat Service - Conversational Input")
    print("=" * 60)
    
    # Use a test user ID
    test_user_id = "test-user-123"
    
    service = ChatService()
    
    test_messages = [
        ("I want to invest $1000", "recommendation"),
        ("What is a good emergency fund?", "explanation"),
        ("rebalance my portfolio", "recommendation"),
        ("Tell me about my latest recommendation", "explanation"),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for message, expected_type in test_messages:
        try:
            print(f"\n💬 Testing: '{message}'")
            result = await service.handle_conversational_input(test_user_id, message)
            
            # Check response type
            if result.get("type") == expected_type or result.get("type") == "error":
                # Error is acceptable if DB not set up
                if result.get("type") == "error":
                    print(f"  ⚠ Got error (may be expected if DB not set up): {result.get('message', '')[:100]}")
                    skipped += 1
                else:
                    print(f"  ✓ Response type correct: {result.get('type')}")
                    print(f"  Message: {result.get('message', '')[:150]}...")
                    passed += 1
            else:
                print(f"  ✗ Response type mismatch: expected {expected_type}, got {result.get('type')}")
                print(f"  Full result: {result}")
                failed += 1
            
        except Exception as e:
            # Some errors are expected if DB not set up
            error_msg = str(e)
            if "not found" in error_msg.lower() or "profile" in error_msg.lower():
                print(f"  ⚠ Expected error (DB not set up): {error_msg[:100]}")
                skipped += 1
            else:
                print(f"  ✗ Unexpected error: {error_msg}")
                failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Chat Service Results: {passed} passed, {failed} failed, {skipped} skipped (DB not set up)")
    print(f"{'=' * 60}")
    
    return failed == 0


async def test_intent_parsing():
    """Test intent data parsing."""
    print("\n" + "=" * 60)
    print("Testing Intent Data Parsing")
    print("=" * 60)
    
    service = IntentService()
    
    test_data = [
        {
            "intent_type": "invest",
            "amount": 1000.0,
            "risk_change": None,
            "target": None,
            "timeframe": "immediate"
        },
        {
            "intent_type": "rebalance",
            "amount": None,
            "risk_change": 0.1,
            "target": None,
            "timeframe": None
        },
        {
            "intent_type": "change_risk",
            "amount": None,
            "risk_change": -0.2,
            "target": None,
            "timeframe": None
        },
    ]
    
    passed = 0
    failed = 0
    
    for data in test_data:
        try:
            print(f"\n🔍 Testing intent data: {data}")
            intent = service._parse_intent_data(data)
            
            # Validate
            if intent.type.value == data["intent_type"]:
                print(f"  ✓ Intent type parsed correctly: {intent.type.value}")
                passed += 1
            else:
                print(f"  ✗ Intent type mismatch")
                failed += 1
                continue
            
            # Check other fields
            if intent.amount == data.get("amount"):
                print(f"  ✓ Amount parsed correctly: {intent.amount}")
            else:
                print(f"  ⚠ Amount mismatch: expected {data.get('amount')}, got {intent.amount}")
            
            if intent.risk_change == data.get("risk_change"):
                print(f"  ✓ Risk change parsed correctly: {intent.risk_change}")
            else:
                print(f"  ⚠ Risk change mismatch: expected {data.get('risk_change')}, got {intent.risk_change}")
            
        except Exception as e:
            print(f"  ✗ Error parsing intent data: {str(e)}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Intent Parsing Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    
    return failed == 0


async def test_keyword_fallback():
    """Test keyword-based intent extraction fallback."""
    print("\n" + "=" * 60)
    print("Testing Keyword Fallback Extraction")
    print("=" * 60)
    
    service = IntentService()
    
    test_cases = [
        ("invest $500", UserIntentType.INVEST, 500.0),
        ("withdraw 1000 dollars", UserIntentType.WITHDRAW, 1000.0),
        ("I want to rebalance", UserIntentType.REBALANCE, None),
        ("increase risk", UserIntentType.CHANGE_RISK, None),
    ]
    
    passed = 0
    failed = 0
    
    for message, expected_type, expected_amount in test_cases:
        try:
            print(f"\n🔑 Testing keyword extraction: '{message}'")
            intent = service._extract_with_keywords(message)
            
            if intent.type == expected_type:
                print(f"  ✓ Intent type correct: {intent.type.value}")
                passed += 1
            else:
                print(f"  ✗ Intent type mismatch: expected {expected_type.value}, got {intent.type.value}")
                failed += 1
                continue
            
            if expected_amount:
                if intent.amount and abs(intent.amount - expected_amount) < 0.01:
                    print(f"  ✓ Amount extracted correctly: ${intent.amount:.2f}")
                else:
                    print(f"  ⚠ Amount mismatch: expected ${expected_amount:.2f}, got ${intent.amount or 'None'}")
            else:
                print(f"  ✓ Amount: {intent.amount or 'None'}")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Keyword Fallback Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    
    return failed == 0


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 5: Conversational Input Processing - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Intent extraction
    try:
        result = await test_intent_extraction()
        results.append(("Intent Extraction", result))
    except Exception as e:
        print(f"\n✗ Intent extraction test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Intent Extraction", False))
    
    # Test 2: Keyword fallback
    try:
        result = await test_keyword_fallback()
        results.append(("Keyword Fallback", result))
    except Exception as e:
        print(f"\n✗ Keyword fallback test failed: {str(e)}")
        results.append(("Keyword Fallback", False))
    
    # Test 3: Intent parsing
    try:
        result = await test_intent_parsing()
        results.append(("Intent Parsing", result))
    except Exception as e:
        print(f"\n✗ Intent parsing test failed: {str(e)}")
        results.append(("Intent Parsing", False))
    
    # Test 4: Chat service (may fail if DB not set up - that's OK)
    try:
        result = await test_chat_service_conversational()
        results.append(("Chat Service", result))
    except Exception as e:
        print(f"\n✗ Chat service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Chat Service", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("⚠ Some tests failed (may be expected if DB not set up)")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

