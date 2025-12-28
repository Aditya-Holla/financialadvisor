# Complete Architecture Overview

This document explains everything that was built in this session.

## 🎯 The Big Picture

We built a **financial advisor recommendation system** that:
1. Takes a user's financial situation
2. Generates investment recommendations
3. **Safely validates** them with guardrails
4. Returns safe, approved recommendations

Think of it like a financial advisor that:
- ✅ Never makes risky decisions (guardrails block dangerous trades)
- ✅ Always explains why (structured data for explanations)
- ✅ Separates concerns (agents, services, routers are separate)

---

## 📁 What We Built - File by File

### 1. **Agent Layer** (`app/agents/`)
This is the "brain" of the system - it makes decisions.

#### `schemas.py` - The Data Models
**What it does:** Defines all the data structures used by agents.

**Key Models:**
- `FinancialState` - Complete picture of user's finances (cashflow, debt, portfolio, goals)
- `UserIntent` - What the user wants to do (invest $1000, rebalance, etc.)
- `GuardrailResult` - Result of safety checks (ALLOW/WARN/BLOCK + reasons)
- `PortfolioProposal` - Suggested trades and allocations
- `AdvisorDecision` - Final decision (APPROVE/MODIFY/REJECT)

**Why it matters:** Everything is structured JSON (Pydantic models) - no loose dictionaries.

#### `guardrail_agent.py` - The Safety System
**What it does:** Validates recommendations using deterministic rules.

**Rules it enforces:**
1. ❌ **BLOCK** if user has negative cash flow and wants to invest immediately
2. ⚠️ **WARN** if emergency fund < 3 months and user wants to increase risk
3. ⚠️ **WARN** if high-interest debt (15%+ APR) and user wants to invest large amounts
4. ⚠️ **WARN/BLOCK** if short-term goals (<12 months) and equity-heavy proposal

**Key point:** This is **deterministic code** - no AI making decisions here. Just clear rules.

#### `orchestrator.py` - The Decision Maker
**What it does:** Coordinates the whole decision process.

**Flow:**
```
1. Takes FinancialState + UserIntent + PortfolioProposal
2. Calls guardrail_agent.validate() to check safety
3. If BLOCK → Returns REJECT decision (no proposal)
4. If ALLOW/WARN → Returns APPROVE/MODIFY decision (with proposal)
```

**Key point:** This is pure orchestration - no business logic, no external calls.

#### `tutor_agent.py` - Placeholder for Future
**What it does:** Currently a stub. Will provide educational explanations later.

---

### 2. **Service Layer** (`app/services/`)

#### `recommendation_service.py` - The Orchestrator
**What it does:** The main service that coordinates everything.

**Flow:**
```
1. Load user profile from database
2. Load latest portfolio snapshot from database
3. Build FinancialState object from profile + snapshot
4. Build UserIntent from request (or default to INVEST)
5. Call model to get PortfolioProposal (currently stub)
6. Call orchestrator.decide() to get AdvisorDecision
7. Store recommendation in database
8. Return recommendation
```

**Key point:** This is where business logic lives - routers just call this.

---

### 3. **Router Layer** (`app/routers/`)

#### `recommendations.py` - The API Endpoint
**What it does:** Thin HTTP endpoint that delegates to service.

**Endpoint:** `POST /recommendations/generate`

**What it does:**
1. Authenticates user (gets user_id from JWT token)
2. Calls `RecommendationService.generate_recommendation()`
3. Returns `RecommendationResponse` (maintains API shape)

**Key point:** Router is thin - no business logic here.

---

### 4. **Repository Layer** (`app/repositories/`)

#### `recommendations_repo.py`
- `create_recommendation()` - Stores recommendation in database

#### `snapshots_repo.py`
- `get_latest_snapshot()` - Gets most recent portfolio snapshot

#### `profiles_repo.py` (already existed)
- `get_profile()` - Gets user profile

**Key point:** These handle all database operations.

---

### 5. **Integration Layer** (`app/integrations/`)

#### `mystockdna.py` - Stock Analysis Integration
**What it does:** Placeholder for myStockDNA model integration.

**Returns:** Structured JSON with stock analysis (risk scores, recommendations, etc.)

**Key point:** Ready to be wired up to actual model.

---

### 6. **Models** (`app/models/`)

#### `common.py`
- Added `RecommendationResponse` - API response model

#### `mystockdna.py`
- `StockDNAAnalysis` - Structured output from stock analysis model
- `StockDNABatchResponse` - Batch analysis results

---

## 🔄 Complete Request Flow

Here's what happens when a user calls `POST /recommendations/generate`:

```
1. User sends request
   ↓
2. Router authenticates (gets user_id from JWT)
   ↓
3. Router calls RecommendationService.generate_recommendation()
   ↓
4. Service loads profile + snapshot from database
   ↓
5. Service builds FinancialState (cashflow, debt, portfolio, goals)
   ↓
6. Service builds UserIntent (what user wants to do)
   ↓
7. Service calls model to get PortfolioProposal (stub for now)
   ↓
8. Service calls OrchestratorAgent.decide()
   ↓
9. Orchestrator calls GuardrailAgent.validate()
   ↓
10. Guardrails check:
    - Negative cash flow? → BLOCK
    - Low emergency fund? → WARN/BLOCK
    - High-interest debt? → WARN
    - Short-term goals with risky proposal? → WARN/BLOCK
   ↓
11. Orchestrator makes decision:
    - BLOCK → REJECT (no proposal)
    - ALLOW → APPROVE (with proposal)
    - WARN → MODIFY (with proposal + confirmations)
   ↓
12. Service stores recommendation in database
   ↓
13. Service returns recommendation data
   ↓
14. Router returns RecommendationResponse to user
```

---

## 🛡️ Safety Features (Guardrails)

The guardrails prevent dangerous recommendations:

### Rule 1: Negative Cash Flow
- **If:** User has negative monthly cash flow
- **And:** Wants to invest immediately
- **Then:** BLOCK the recommendation
- **Why:** Can't invest money you don't have

### Rule 2: Low Emergency Fund
- **If:** Emergency fund < 3 months expenses
- **And:** User wants to increase risk or invest large amount
- **Then:** WARN or BLOCK
- **Why:** Need emergency fund before taking risks

### Rule 3: High-Interest Debt
- **If:** Credit card debt with 15%+ APR
- **And:** User wants to invest large lump sum
- **Then:** WARN
- **Why:** Pay off high-interest debt first

### Rule 4: Short-Term Goals
- **If:** Goal within 12 months
- **And:** Proposal is equity-heavy (>60% stocks)
- **Then:** WARN or BLOCK
- **Why:** Stocks are risky for short-term goals

---

## 📊 Data Structures

### FinancialState
Complete picture of user's finances:
```python
{
  "cashflow": {
    "monthly_income": 5000.0,
    "monthly_expenses": 3000.0,
    "net_cashflow": 2000.0
  },
  "emergency_fund_months": 6.0,
  "debt_summary": {
    "total_debt": 0.0,
    "credit_card_debt": 0.0,
    ...
  },
  "portfolio_summary": {
    "total_value": 50000.0,
    "cash_balance": 10000.0,
    "positions": [...]
  },
  "goals": [...]
}
```

### UserIntent
What the user wants:
```python
{
  "type": "invest",  # or "rebalance", "withdraw", etc.
  "amount": 1000.0,
  "timeframe": "immediate"
}
```

### AdvisorDecision
Final decision:
```python
{
  "decision": "APPROVE",  # or "MODIFY", "REJECT"
  "proposal": {...},  # PortfolioProposal if approved
  "required_confirmations": [...],  # If warnings exist
  "explanation_inputs": [...],  # Data for generating explanations
  "reasoning": "..."
}
```

---

## 🧪 Testing

We created comprehensive tests:

1. **`test_guardrails.py`** - Tests all guardrail rules
2. **`test_orchestrator.py`** - Tests decision-making logic
3. **`test_recommendation_service.py`** - Tests service layer
4. **`test_recommendations_api.py`** - Tests API endpoint

Run with: `pytest tests/ -v`

---

## 🎯 Key Design Principles

### 1. Separation of Concerns
- **Routers** = HTTP handling only
- **Services** = Business logic
- **Agents** = Decision-making
- **Repositories** = Database access

### 2. Deterministic Guardrails
- No AI making safety decisions
- Clear, testable rules
- Predictable behavior

### 3. Structured Data
- Everything is Pydantic models
- No loose dictionaries
- Type-safe

### 4. No External Calls in Agents
- Orchestrator doesn't call Alpaca, DB, or LLM
- Pure coordination logic
- Easy to test

---

## 🚀 What's Next (TODOs)

1. **Model Integration** - Replace stub in `_get_model_proposal()` with actual model call
2. **Tutor Agent** - Implement educational explanations
3. **Alpaca Integration** - Wire up trade execution
4. **More Guardrails** - Add additional safety rules as needed

---

## 📝 Summary

We built a **complete recommendation system** with:
- ✅ Agent layer for decision-making
- ✅ Guardrails for safety
- ✅ Service layer for orchestration
- ✅ API endpoint for users
- ✅ Database integration
- ✅ Comprehensive tests

The system is **safe** (guardrails), **structured** (Pydantic models), and **testable** (deterministic logic).

