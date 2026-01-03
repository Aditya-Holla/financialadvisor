# Architectural & Compliance Audit Report

## Executive Summary

This audit evaluates the financial advisor application's alignment with its stated educational philosophy: teaching users how to think about investing, not what to buy, while maintaining user agency and prioritizing safety over optimization.

---

## 1. OVERARCHING INTENT (Inferred from Codebase)

### What Problem Is the App Trying to Solve?
The app helps users understand portfolio allocation concepts and investment decision-making through:
- Educational explanations of financial concepts
- Safety-validated portfolio allocation examples
- Risk awareness and reasoning tools
- Structured decision-making frameworks

### What Is It Explicitly NOT Trying to Do?
- Provide personalized financial advice
- Make investment decisions for users
- Guarantee returns or predict performance
- Replace licensed financial advisors
- Optimize for alpha or performance chasing

### What User Behavior Is It Trying to Encourage?
- **Learning-first approach**: Understanding concepts before taking action
- **Risk awareness**: Recognizing safety considerations before investing
- **Informed decision-making**: Using educational tools to make choices
- **Agency**: Users retain control; system provides information, not commands

### Where Does Responsibility Lie?
- **User**: Makes final investment decisions, understands risks, consults licensed advisors for personalized advice
- **System**: Provides educational content, validates safety, presents examples (not prescriptions), blocks unsafe requests

---

## 2. DIMENSION-BY-DIMENSION EVALUATION

### 2.1 SYSTEM ARCHITECTURE

#### ✅ WELL ALIGNED: Orchestrator as Router
**Files**: `backend/app/agents/orchestrator.py`
- Orchestrator acts purely as a traffic controller
- Calls guardrail agent FIRST (line 115)
- Routes based on guardrail decisions without second-guessing
- Does not create proposals or give advice
- **Alignment**: Perfect - acts as pure router, no business logic

#### ✅ WELL ALIGNED: Guardrail Agent as Sole Safety Authority
**Files**: `backend/app/agents/guardrail_agent.py`
- Deterministic validation rules (no LLM decisions)
- Blocks high-risk patterns (lines 74-87)
- Returns structured decisions (ALLOW/WARN_AND_EDUCATE/BLOCK)
- Provides educational alternatives, not recommendations
- **Alignment**: Perfect - sole safety authority, deterministic, educational alternatives

#### ✅ WELL ALIGNED: Tutor Agent as Purely Educational
**Files**: `backend/app/agents/tutor_agent.py`, `backend/app/integrations/llm.py`
- Explains concepts without recommendations (lines 225-315)
- Uses neutral, explanatory language
- LLM safety constraints prevent advisory language (lines 129-149, 261-306)
- No "buy", "sell", "invest", "you should" language
- **Alignment**: Excellent - strictly educational, strong safety filters

#### ⚠️ PARTIAL ALIGNMENT: Recommendation Service Gating
**Files**: `backend/app/services/recommendation_service.py`
- **Well-aligned aspects**:
  - Trusts upstream safety (no redundant guardrail calls)
  - Frames outputs as examples (lines 355-356)
  - Only executes when guardrail returns ALLOW
- **Concern**: Model proposal generation returns `None` (line 314)
  - When model fails, orchestrator receives `None` → returns `REQUEST_INFO`
  - This is safe but may not provide educational fallback
- **Alignment**: Good, but failure mode needs clarification

#### ✅ WELL ALIGNED: No Bypass Paths
**Files**: `backend/app/routers/recommendations.py`, `backend/app/services/chat_service.py`
- All requests route through ChatService → Orchestrator → Guardrail
- No direct calls to recommendation service from routers
- Guardrail is always called FIRST
- **Alignment**: Perfect - no bypass paths detected

---

### 2.2 USER EXPERIENCE & LANGUAGE

#### ❌ MISALIGNMENT: Default Intent Assumes Recommendation Request
**Concept Violated**: Education precedes examples; opt-in, not opt-out
**Files**: `backend/app/routers/recommendations.py`
**Lines**: 109-110
**Severity**: **HIGH**

**Issue**:
```python
if not user_intent_data.get("type"):
    user_intent_data["type"] = "invest"  # Default to invest intent
```

**Problem**: 
- Defaulting to "invest" intent assumes user wants recommendations
- Violates "education precedes examples" principle
- Should default to educational mode, not recommendation mode
- User must explicitly opt-in to recommendations

**Recommendation**:
- Default to `UserIntentType.OTHER` or require explicit intent
- If no intent provided, route to educational flow (tutor agent)
- Only generate recommendations when user explicitly requests (GET_ADVICE or INVEST with clear indication)

#### ✅ WELL ALIGNED: Language Constraints in Tutor Agent
**Files**: `backend/app/agents/tutor_agent.py`, `backend/app/integrations/llm.py`
- Explicit constraints against "buy", "sell", "invest", "you should" (lines 18, 135)
- Neutral, explanatory tone throughout
- Educational framing in all explanations
- **Alignment**: Excellent - strong language constraints

#### ✅ WELL ALIGNED: Clear Educational Framing
**Files**: `backend/app/services/recommendation_service.py`
- Metadata explicitly marks as educational example (lines 355-356)
- Framing: "example_illustration_tradeoffs"
- Docstrings emphasize educational nature
- **Alignment**: Good - clear framing in storage

#### ⚠️ PARTIAL ALIGNMENT: Distinction Between Education and Examples
**Files**: `backend/app/services/chat_service.py`
- WARN/WARN_AND_EDUCATE routes to tutor_agent (education) - ✅ Good
- ALLOW routes to recommendation_service (examples) - ✅ Good
- **Concern**: When recommendation service fails, does it default to education?
  - Line 254-264: Catches ExternalServiceError and returns explanation
  - This is safe but may not clearly distinguish "education" vs "example failed"
- **Alignment**: Good, but could be more explicit about education-first fallback

#### ✅ WELL ALIGNED: Intentional Friction for Risk
**Files**: `backend/app/agents/orchestrator.py`, `backend/app/agents/guardrail_agent.py`
- BLOCK requires explicit override acknowledgements (lines 160, 406-419)
- WARN requires checkbox confirmations (lines 420-433)
- High-risk patterns trigger BLOCK (lines 130-135)
- **Alignment**: Excellent - friction increases with risk

---

### 2.3 DATA & LOGIC BOUNDARIES

#### ✅ WELL ALIGNED: No Fiduciary Responsibility Implied
**Files**: `backend/app/services/recommendation_service.py`
- All outputs marked as "educational example" (line 355)
- No personalized advice language
- Framing as "examples, illustrations, trade-offs"
- **Alignment**: Good - clear boundaries

#### ✅ WELL ALIGNED: No Predictions or Guarantees
**Files**: `backend/app/agents/tutor_agent.py`, `backend/app/integrations/llm.py`
- Explicit prohibition of predictions (lines 20, 137, 286-288)
- Language emphasizes "may", "potentially", "does not guarantee"
- No performance guarantees in explanations
- **Alignment**: Excellent - strong constraints against predictions

#### ✅ WELL ALIGNED: No Hidden Recommendation Logic in Education
**Files**: `backend/app/agents/tutor_agent.py`
- Educational explanations are separate from recommendations
- Concept explanations (diversification, risk, asset allocation) are pure education
- No embedded "you should" logic
- **Alignment**: Perfect - clean separation

---

### 2.4 FAILURE MODES

#### ⚠️ PARTIAL ALIGNMENT: Guardrail Failure Handling
**Files**: `backend/app/agents/orchestrator.py`, `backend/app/services/chat_service.py`
- **Current behavior**: If guardrail fails (exception), orchestrator would raise error
- **Issue**: No explicit fallback to "safe default" (education-only mode)
- **Recommendation**: Add try-catch in orchestrator.decide() to default to REJECT with educational explanation if guardrail fails

#### ✅ WELL ALIGNED: Recommender Failure Defaults to Education
**Files**: `backend/app/services/chat_service.py`
**Lines**: 254-264
- When recommendation_service fails (ExternalServiceError), returns explanation without recommendation
- Falls back to tutor_agent explanation
- **Alignment**: Good - defaults to education

#### ✅ WELL ALIGNED: Unsafe Requests Safely Refused
**Files**: `backend/app/agents/guardrail_agent.py`, `backend/app/services/chat_service.py`
- High-risk patterns → BLOCK (lines 130-135)
- BLOCK → REJECT decision with safe alternative (lines 139-165)
- Safe alternatives provided (line 134, 142)
- **Alignment**: Excellent - unsafe requests blocked with educational alternatives

#### ⚠️ PARTIAL ALIGNMENT: Model Proposal Failure
**Files**: `backend/app/services/recommendation_service.py`
**Lines**: 280-314
- `_get_model_proposal()` returns `None` (stub implementation)
- When `None`, orchestrator returns `REQUEST_INFO` (line 128-129)
- **Issue**: `REQUEST_INFO` may not provide educational value
- **Recommendation**: When proposal is None, consider providing educational content about portfolio allocation concepts instead of just requesting info

---

## 3. SUMMARY OF FINDINGS

### Critical Misalignments (HIGH Severity)

1. **Default Intent Assumes Recommendation Request**
   - **File**: `backend/app/routers/recommendations.py:109-110`
   - **Issue**: Defaults to "invest" intent, violating opt-in principle
   - **Fix**: Default to educational mode, require explicit recommendation request

### Moderate Concerns (MEDIUM Severity)

2. **Model Proposal Failure Handling**
   - **File**: `backend/app/services/recommendation_service.py:314`
   - **Issue**: Returns None → REQUEST_INFO, may not provide educational value
   - **Fix**: Provide educational content when model unavailable

3. **Guardrail Failure Fallback**
   - **File**: `backend/app/agents/orchestrator.py:114-120`
   - **Issue**: No explicit safe default if guardrail raises exception
   - **Fix**: Add try-catch to default to REJECT with education

### Well-Aligned Components

✅ **Orchestrator**: Pure router, no business logic
✅ **Guardrail Agent**: Sole safety authority, deterministic
✅ **Tutor Agent**: Strictly educational, strong language constraints
✅ **Language Constraints**: No advisory language, neutral tone
✅ **Safety Friction**: Intentional friction increases with risk
✅ **No Predictions**: Strong constraints against guarantees/predictions
✅ **No Hidden Logic**: Clean separation of education and examples

---

## 4. RECOMMENDATIONS PRIORITY

### Priority 1 (Critical - Address Immediately)
1. **Change default intent behavior** in `recommendations.py`:
   - Remove default to "invest"
   - Default to educational mode or require explicit intent
   - Ensure education precedes examples

### Priority 2 (Important - Address Soon)
2. **Enhance model failure handling**:
   - When proposal is None, provide educational content about allocation concepts
   - Don't just return REQUEST_INFO

3. **Add guardrail failure fallback**:
   - Wrap guardrail call in try-catch
   - Default to REJECT with educational explanation if guardrail fails

### Priority 3 (Enhancement - Consider for Future)
4. **Clarify education vs example distinction**:
   - Make it more explicit when system is in "education mode" vs "example mode"
   - Consider separate endpoints or clearer response metadata

---

## 5. OVERALL ASSESSMENT

**Alignment Score**: 85/100

**Strengths**:
- Excellent architectural separation
- Strong safety constraints
- Educational language well-enforced
- No bypass paths
- Good failure handling in most cases

**Weaknesses**:
- Default intent violates opt-in principle
- Some failure modes could be more educational
- Model stub needs better fallback

**Conclusion**: The codebase is **largely well-aligned** with the stated philosophy. The primary concern is the default intent behavior, which should be addressed to fully align with the "education precedes examples" principle. The architecture is sound, safety is prioritized, and language constraints are strong.

