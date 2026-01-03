# Backend Safety Scan Report

## Scan Date
Generated after refactoring to remove redundant guardrail calls

## 1. RecommendationService Guardrail Imports/Calls

### Status: ✅ PASS
- **Zero guardrail imports**: No `GuardrailAgent` or `GuardrailStatus` imports found
- **Zero guardrail method calls**: No calls to `guardrail_agent.validate()` or `guardrail_agent.evaluate_intent()`
- **Only comments**: References to guardrail exist only in docstrings/comments (acceptable)
- **Trusts upstream**: Service correctly trusts ChatService + Orchestrator to enforce safety

### Evidence:
- File: `backend/app/services/recommendation_service.py`
- Imports: Only `OrchestratorAgent`, no guardrail imports
- Method calls: Only `orchestrator.decide()`, no direct guardrail calls
- Comments: References guardrail in docstrings but performs no validation

---

## 2. Guardrail Intent Evaluation Return Types

### Status: ✅ PASS
- **Correct return type**: `evaluate_intent()` returns `IntentDecision` with `IntentDecisionType`
- **Correct enum values**: `IntentDecisionType` has exactly: `ALLOW`, `WARN_AND_EDUCATE`, `BLOCK`
- **Correct implementation**: Method returns these three values appropriately

### Evidence:
- File: `backend/app/agents/guardrail_agent.py`
- Method: `async def evaluate_intent(...) -> IntentDecision`
- Return type: `IntentDecision` with `decision: IntentDecisionType`
- Enum: `IntentDecisionType` (lines 213-218 in schemas.py)
  - `ALLOW = "ALLOW"`
  - `WARN_AND_EDUCATE = "WARN_AND_EDUCATE"`
  - `BLOCK = "BLOCK"`
- Implementation: Returns `BLOCK` for high-risk patterns, `WARN_AND_EDUCATE` for recommendation requests, `ALLOW` otherwise

---

## 3. Redundant Safety Checks in Services

### Status: ✅ PASS (with minor documentation issue)

#### RecommendationService: ✅ NO REDUNDANT CHECKS
- No guardrail validation calls
- Only validates intent type (GET_ADVICE or INVEST) - this is appropriate defensive check
- Trusts upstream safety enforcement

#### ChatService: ✅ NO REDUNDANT CHECKS
- Only reads `guardrail_status` from orchestrator decision metadata
- Does not call guardrail agent directly
- Routes based on orchestrator's guardrail result (not redundant)

#### ApprovalService: ✅ NO REDUNDANT CHECKS
- No guardrail imports or calls
- Only validates confirmations (appropriate for approval flow)

---

## Minor Issues Found

### 1. Documentation Inconsistency (Non-functional)
- **File**: `backend/app/agents/schemas.py`
- **Line**: 258
- **Issue**: `GuardrailResult.status` field description says "ALLOW, WARN, or BLOCK" but should include "WARN_AND_EDUCATE"
- **Impact**: Documentation only, no functional impact
- **Fix**: Update docstring to: "Validation status: ALLOW, WARN, WARN_AND_EDUCATE, or BLOCK"

---

## Summary

✅ **All critical requirements met:**
1. RecommendationService has zero guardrail imports or calls
2. Guardrail intent evaluation returns ALLOW / WARN_AND_EDUCATE / BLOCK
3. No services perform redundant safety checks

⚠️ **Minor documentation issue:**
- GuardrailResult schema docstring should mention WARN_AND_EDUCATE

---

## Architecture Compliance

The backend correctly implements the separation of concerns:
- **RecommendationService**: Trusts upstream, no guardrail calls
- **ChatService**: Coordinates through orchestrator, reads guardrail status from decision
- **Orchestrator**: Calls guardrail FIRST, routes based on result
- **GuardrailAgent**: Performs all validation, returns structured decisions

No violations of the safety architecture found.

