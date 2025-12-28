# Visual Flow Diagram

## Simple Overview

```
User Request
    ↓
API Endpoint (Router)
    ↓
Service Layer
    ↓
Agent Layer (Orchestrator + Guardrails)
    ↓
Decision Made
    ↓
Stored in Database
    ↓
Response to User
```

## Detailed Flow

```
┌─────────────────────────────────────────────────────────────┐
│  USER SENDS REQUEST                                         │
│  POST /recommendations/generate                             │
│  { "type": "invest", "amount": 1000 }                       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  ROUTER (recommendations.py)                                │
│  - Authenticates user (gets user_id from JWT)              │
│  - Calls RecommendationService                             │
│  - Returns RecommendationResponse                           │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  SERVICE (recommendation_service.py)                        │
│                                                             │
│  1. Load Profile from DB                                    │
│     └─> profiles_repo.get_profile(user_id)                  │
│                                                             │
│  2. Load Snapshot from DB                                   │
│     └─> snapshots_repo.get_latest_snapshot(user_id)        │
│                                                             │
│  3. Build FinancialState                                    │
│     ├─ Cashflow (income - expenses)                        │
│     ├─ Emergency fund months                                │
│     ├─ Debt summary                                         │
│     ├─ Portfolio summary                                    │
│     └─ Goals                                                │
│                                                             │
│  4. Build UserIntent                                        │
│     └─ From request data (or default to INVEST)            │
│                                                             │
│  5. Get PortfolioProposal                                   │
│     └─> Model call (stub for now)                             │
│                                                             │
│  6. Call Orchestrator                                       │
│     └─> orchestrator.decide(...)                           │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (orchestrator.py)                             │
│                                                             │
│  1. Call GuardrailAgent                                     │
│     └─> guardrail_agent.validate(...)                      │
│                                                             │
│  2. Get GuardrailResult                                     │
│     ├─ Status: ALLOW / WARN / BLOCK                        │
│     ├─ Reasons: List of violation codes                   │
│     └─ Computed values: risk scores, etc.                 │
│                                                             │
│  3. Make Decision                                           │
│     ├─ If BLOCK → REJECT (no proposal)                    │
│     ├─ If ALLOW → APPROVE (with proposal)                 │
│     └─ If WARN → MODIFY (with proposal + confirmations)  │
│                                                             │
│  4. Return AdvisorDecision                                   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  GUARDRAIL AGENT (guardrail_agent.py)                      │
│                                                             │
│  Checks 4 Rules:                                           │
│                                                             │
│  Rule 1: Negative Cash Flow?                               │
│    If net_cashflow < 0 AND invest_now → BLOCK             │
│                                                             │
│  Rule 2: Low Emergency Fund?                               │
│    If emergency_fund < 3 months → WARN/BLOCK              │
│                                                             │
│  Rule 3: High-Interest Debt?                               │
│    If debt_apr >= 15% AND large_investment → WARN         │
│                                                             │
│  Rule 4: Short-Term Goals?                                 │
│    If goal < 12 months AND equity_heavy → WARN/BLOCK     │
│                                                             │
│  Returns: GuardrailResult with status + reasons            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  BACK TO SERVICE                                           │
│                                                             │
│  7. Store Recommendation                                    │
│     └─> recommendations_repo.create_recommendation(...)     │
│         Stores:                                             │
│         - Decision JSON                                     │
│         - Proposal JSON                                     │
│         - Guardrail results                                 │
│         - Financial state                                   │
│                                                             │
│  8. Return Recommendation Data                              │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  ROUTER RETURNS RESPONSE                                    │
│  {                                                          │
│    "recommendation_id": "rec-123",                         │
│    "decision": "approve",                                   │
│    "status": "pending",                                     │
│    "created_at": "2024-01-01T00:00:00"                     │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Router (`recommendations.py`)
- ✅ Handle HTTP request/response
- ✅ Authenticate user
- ✅ Call service
- ❌ NO business logic

### Service (`recommendation_service.py`)
- ✅ Load data from database
- ✅ Build data structures
- ✅ Call orchestrator
- ✅ Store results
- ❌ NO HTTP handling

### Orchestrator (`orchestrator.py`)
- ✅ Coordinate guardrail checks
- ✅ Make final decision
- ✅ Build explanation inputs
- ❌ NO database calls
- ❌ NO external API calls

### Guardrail Agent (`guardrail_agent.py`)
- ✅ Run safety checks
- ✅ Return validation results
- ❌ NO decision making (just validation)

## Data Flow

```
Database (Profile + Snapshot)
    ↓
FinancialState (Pydantic Model)
    ↓
UserIntent (Pydantic Model)
    ↓
PortfolioProposal (Pydantic Model) [from model]
    ↓
GuardrailResult (Pydantic Model) [from guardrails]
    ↓
AdvisorDecision (Pydantic Model) [from orchestrator]
    ↓
Database (Stored Recommendation)
    ↓
RecommendationResponse (Pydantic Model) [to user]
```

## Key Points

1. **Everything is typed** - Pydantic models ensure data structure
2. **Guardrails are deterministic** - No AI making safety decisions
3. **Separation of concerns** - Each layer has one job
4. **Testable** - Each component can be tested independently

