---
name: MVP Consolidation Plan
overview: "Consolidate and restructure the existing codebase to align with the new conversational financial advisor vision, ensuring all components work together to deliver the full end-to-end flow: user input → FinancialState → guardrails → myStockDNA → Orchestrator Agent decision → explanation → approval → execution."
todos:
  - id: test_existing_deployment
    content: Test existing frontend/backend deployment to understand what co-builder has built
    status: pending
  - id: orchestrator_verification
    content: Verify OrchestratorAgent matches vision document role (keep name as-is, ensure flow is correct)
    status: pending
  - id: mystockdna_service
    content: Create myStockDNA service that generates PortfolioProposal objects (use sophisticated stub for MVP)
    status: pending
  - id: recommendation_flow_update
    content: "Update recommendation service flow to: Load FinancialState → Pre-check guardrails → Call myStockDNA → Re-apply guardrails → Orchestrator Agent decision"
    status: pending
    dependencies:
      - orchestrator_verification
      - mystockdna_service
  - id: market_data_service
    content: Create market data service with Alpaca integration for real-time prices, ETF holdings, and fundamentals (Alpaca only, no Polygon/Finnhub)
    status: pending
  - id: profile_endpoints
    content: Implement GET/PUT /profile endpoints to capture and return full FinancialState (cashflow, debt, goals, portfolio constraints)
    status: pending
  - id: intent_service
    content: Create intent extraction service to parse natural language input into UserIntent using existing LLMIntegration (ChatGPT API)
    status: pending
  - id: trade_execution
    content: Implement Alpaca trade execution service and integrate with approval flow
    status: pending
    dependencies:
      - market_data_service
  - id: chat_enhancement
    content: Enhance chat endpoint to handle conversational input using existing LLMIntegration and route to intent extraction or explanation
    status: pending
    dependencies:
      - intent_service
  - id: livekit_integration
    content: Create LiveKit integration for voice/avatar layer (real-time audio/video streaming)
    status: pending
  - id: end_to_end_tests
    content: Create integration tests for full end-to-end flow scenarios
    status: pending
    dependencies:
      - recommendation_flow_update
      - trade_execution
  - id: documentation_update
    content: Update ARCHITECTURE.md and create VISION_ALIGNMENT.md to document how code matches vision
    status: pending
    dependencies:
      - orchestrator_verification
  - id: code_cleanup
    content: Remove unused code, ensure consistent terminology, update all docstrings to reference vision
    status: pending
    dependencies:
      - orchestrator_verification
---

# MVP Consolidation and Alignment Plan

## Overview

The codebase has solid foundations (agents, guardrails, services) but needs consolidation to match the new vision. The system should follow: **User Request → Load FinancialState → Apply Guardrails → Call myStockDNA → Orchestrator Agent Evaluates → Generate Explanation → Request Confirmation → Execute Trades**.**Note:** Keep "Orchestrator Agent" naming (as implemented by co-builder). The vision document's "Boss Agent" concept aligns with Orchestrator Agent's role.

## Current State Analysis

### ✅ What's Already Good

- **FinancialState schema** - Matches vision perfectly (cashflow, debt, portfolio, goals)
- **Guardrail system** - Deterministic rules implemented correctly
- **Agent architecture** - Separation of concerns is solid
- **Repository pattern** - Database abstraction in place
- **LLM integration** - Explanation generation ready

### 🔄 What Needs Refactoring

- **Orchestrator Agent verification** - Keep name as-is, ensure it matches vision's "Boss Agent" role (Orchestrator Agent = Boss Agent in vision)
- **myStockDNA integration** - Currently stub, needs proper integration point (even if mocked for MVP)
- **Profile endpoints** - Stubs need implementation to capture full FinancialState
- **Market data** - Need real-time integration (Alpaca only - sufficient for MVP)
- **Flow alignment** - Ensure exact flow matches vision document
- **LLM integration** - Use existing LLMIntegration code (ChatGPT API already configured)

### ❌ What's Missing

- **Conversational input parsing** - Extract UserIntent from natural language (use existing LLMIntegration)
- **Trade execution** - Alpaca integration for actual order placement
- **Voice/avatar layer** - LiveKit integration for real-time voice/avatar delivery

---

## Phase 0: Test Existing Deployment

### 0.1 Test Current Frontend/Backend

**Actions:**

- Start backend server and verify it runs
- Test frontend UI and verify it connects to backend
- Test existing endpoints:
- `/health`
- `/me`
- `/profile` (if implemented)
- `/recommendations/generate`
- `/recommendations/latest`
- `/chat`
- Document what works and what's stubbed
- Identify any issues or missing pieces

**Goal:** Understand current state before making changes---

## Phase 1: Core Architecture Alignment

### 1.1 Verify Orchestrator Agent Role

**Files to review:**

- `backend/app/agents/orchestrator.py`
- Ensure it matches vision's "Boss Agent" role (keep name as OrchestratorAgent)

**Changes:**

- Update docstrings to reference vision: "The Orchestrator Agent is the orchestrator and single voice of the system (equivalent to vision's 'Boss Agent')"
- Ensure it follows exact flow: Load FinancialState → Apply guardrails → Call myStockDNA → Re-apply constraints → Generate explanation plan → Ask for confirmation
- **Keep class name as `OrchestratorAgent`** (co-builder's naming)

### 1.2 Verify Service Layer Integration

**Files to review:**

- `backend/app/services/recommendation_service.py`
- Verify it uses `OrchestratorAgent` correctly
- Ensure flow matches vision exactly

### 1.3 Consolidate Agent Responsibilities

**Files to review:**

- `backend/app/agents/orchestrator.py`
- `backend/app/agents/guardrail_agent.py`
- `backend/app/agents/tutor_agent.py`

**Ensure:**

- Orchestrator Agent coordinates everything (matches vision's Boss Agent role)
- Guardrail Agent only does deterministic validation
- Tutor Agent only explains (never changes numbers)

---

## Phase 2: myStockDNA Integration

### 2.1 Create Proper myStockDNA Service

**Files to create/modify:**

- `backend/app/services/mystockdna_service.py` (new)
- `backend/app/integrations/mystockdna.py` (enhance existing)

**Responsibilities:**

- Generate portfolio proposals (allocations, rebalance suggestions, trade lists)
- Operate independently of user interaction
- Return structured `PortfolioProposal` objects
- For MVP: Use sophisticated stub that returns realistic proposals based on FinancialState

**Integration point:**

- Orchestrator Agent calls myStockDNA service after guardrails pass initial check
- myStockDNA returns proposal
- Orchestrator Agent re-applies guardrails to proposal
- Orchestrator Agent makes final decision

### 2.2 Update Recommendation Service Flow

**File:** `backend/app/services/recommendation_service.py`**New flow:**

1. Load FinancialState
2. Apply guardrails (pre-check: "Is investing appropriate?")
3. If BLOCK → Return REJECT decision immediately
4. If ALLOW/WARN → Call myStockDNA service for proposal
5. Re-apply guardrails to proposal
6. Orchestrator Agent makes final decision
7. Store recommendation

---

## Phase 3: Market Data Integration

### 3.1 Create Market Data Service

**Files to create:**

- `backend/app/services/market_data_service.py`
- `backend/app/integrations/alpaca_market.py` (for Alpaca market data)

**Responsibilities:**

- Fetch real-time prices via Alpaca
- Get ETF holdings via Alpaca
- Retrieve fundamentals via Alpaca
- Provide institutional ownership data (13F filings, contextual only) - if available via Alpaca
- **Critical:** LLMs never fetch data directly - all data comes through backend

**Note:** Alpaca provides sufficient market data for MVP. No need for Polygon or Finnhub.**Integration:**

- Market data service called by Orchestrator Agent when needed
- Data passed to LLM for explanation (never LLM fetching directly)

### 3.2 Update Config

**File:** `backend/app/config.py`

- Ensure `ALPACA_KEY` and `ALPACA_SECRET` are used for market data
- No need for Polygon or Finnhub API keys

---

## Phase 4: Profile and FinancialState Management

### 4.1 Implement Profile Endpoints

**File:** `backend/app/routers/profile.py`**Implement:**

- `GET /profile` - Returns full FinancialState representation
- `PUT /profile` - Updates profile with all FinancialState components:
- Cashflow (income, expenses)
- Emergency fund
- Debt (all types with APRs)
- Goals (with target dates)
- Portfolio constraints

**Response model:**

- Create `ProfileResponse` that matches `FinancialState` schema
- Ensure all fields from vision's "Canonical User Financial State" are captured

### 4.2 Update Profile Repository

**File:** `backend/app/repositories/profiles_repo.py`**Ensure:**

- Stores all FinancialState components
- Handles JSON serialization for complex fields (goals, metadata)
- Supports querying by user_id

---

## Phase 5: Conversational Input Processing

### 5.1 Create Intent Extraction Service

**Files to create:**

- `backend/app/services/intent_service.py`

**Responsibilities:**

- Parse natural language input (text or transcribed voice)
- Extract UserIntent from conversation using **existing LLMIntegration** (ChatGPT API)
- Map to structured `UserIntent` model:
- Type (invest, withdraw, rebalance, etc.)
- Amount
- Risk change
- Target
- Timeframe

**Integration:**

- Use existing `app/integrations/llm.py` LLMIntegration class
- Leverage ChatGPT API key already configured
- Intent extraction is separate from decision-making (LLM only extracts, never decides)

### 5.2 Update Chat Endpoint

**File:** `backend/app/routers/chat.py`**Enhance:**

- Accept conversational input
- Use intent service with LLMIntegration to extract intent if user is asking for action
- If asking for explanation, use existing tutor agent (which also uses LLMIntegration)
- If asking for action, route to recommendation generation

---

## Phase 6: Trade Execution

### 6.1 Implement Alpaca Trade Execution

**Files to create/modify:**

- `backend/app/integrations/alpaca_trading.py` (new)
- `backend/app/services/trade_execution_service.py` (new)

**Responsibilities:**

- Execute trades via Alpaca API
- Validate orders before execution
- Handle order status and confirmations
- Store executed orders in database

### 6.2 Update Approval Service

**File:** `backend/app/services/approval_service.py`**Enhance:**

- After validation, call trade execution service
- Execute trades from approved recommendation
- Update recommendation status to "executed"
- Store order IDs

### 6.3 Update Approval Endpoint

**File:** `backend/app/routers/recommendations.py`**Ensure:**

- `POST /recommendations/{id}/approve` triggers trade execution
- Returns execution status

---

## Phase 7: Voice and Avatar Layer

### 7.1 Create LiveKit Integration

**Files to create:**

- `backend/app/integrations/livekit.py` (real-time audio/video streaming)
- `backend/app/services/voice_service.py` (service layer for voice/avatar)

**Responsibilities:**

- Real-time audio/video streaming via LiveKit
- Low-latency delivery of advisor responses
- Support for talking avatar (avatar implementation may be frontend, but backend provides audio stream)

**Note:** LiveKit is planned for voice/avatar delivery. Architecture should support it.

### 7.2 Update Config

**File:** `backend/app/config.py`

- Add `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`
- Add `LIVEKIT_URL` (LiveKit server URL)

---

## Phase 8: End-to-End Flow Verification

### 8.1 Create Integration Tests

**Files to create:**

- `backend/tests/test_end_to_end_flow.py`

**Test scenarios:**

1. User with negative cashflow requests investment → BLOCK
2. User with low emergency fund requests risk increase → WARN
3. User with good finances requests investment → ALLOW → myStockDNA proposal → APPROVE
4. User approves recommendation → Trade execution

### 8.2 Update Documentation

**Files to update:**

- `ARCHITECTURE.md` - Reflect new vision
- `README.md` - Update with new flow
- Create `VISION_ALIGNMENT.md` - Document how code matches vision

---

## Phase 9: Code Cleanup and Consistency

### 9.1 Remove Unused Code

**Review and remove:**

- Any code that doesn't align with new vision
- Old test files that test deprecated patterns
- Unused models or schemas

### 9.2 Ensure Consistent Terminology

**Update all files to use:**

- "Orchestrator Agent" (keep co-builder's naming, matches vision's "Boss Agent" concept)
- "FinancialState" (canonical state)
- "myStockDNA" (model, not "recommendation model")
- "Guardrails" (not "safety checks")

### 9.3 Update All Docstrings

**Ensure:**

- All docstrings reference the vision document
- All agents have "Rules of Engagement" comments
- All services document their role in the flow

---

## Phase 10: Frontend Updates (If Needed)

### 10.1 Update Frontend to Match New Flow

**Files to review:**

- `frontend/app.js`
- `frontend/index.html`

**Ensure:**

- UI supports conversational input
- Displays FinancialState components
- Shows guardrail warnings/blocks clearly
- Displays myStockDNA proposals
- Handles approval flow with confirmations

---

## Implementation Order

1. **Phase 0** - Test existing deployment (understand current state)
2. **Phase 1** - Core architecture alignment (Orchestrator Agent verification, flow verification)
3. **Phase 2** - myStockDNA integration (even if stubbed)
4. **Phase 4** - Profile endpoints (needed for FinancialState)
5. **Phase 3** - Market data (Alpaca only, needed for real proposals)
6. **Phase 6** - Trade execution (needed for full flow)
7. **Phase 5** - Conversational input (using existing LLMIntegration)
8. **Phase 7** - LiveKit integration (voice/avatar layer)
9. **Phase 8** - Testing and verification
10. **Phase 9** - Cleanup
11. **Phase 10** - Frontend updates

---

## Key Principles to Maintain

1. **Rules before language** - Guardrails are code, not prompts
2. **Models decide, advisors explain** - myStockDNA generates, Orchestrator Agent judges
3. **LLM never changes numbers** - Only explains (use existing LLMIntegration)
4. **Deterministic guardrails** - No AI in safety decisions
5. **Structured data everywhere** - Pydantic models, no loose dicts
6. **Separation of concerns** - Agents, services, repositories are separate
7. **Leverage existing code** - Use LLMIntegration for explanations and intent extraction

---

## Success Criteria

- [ ] Existing deployment tested and understood
- [ ] Full end-to-end flow works: input → guardrails → myStockDNA → Orchestrator Agent → explanation → approval → execution
- [ ] All components use consistent terminology (keep Orchestrator Agent name)
- [ ] FinancialState is the single source of truth
- [ ] Guardrails prevent inappropriate actions
- [ ] myStockDNA generates proposals (even if stubbed)
- [ ] Orchestrator Agent coordinates everything (matches vision's Boss Agent role)
- [ ] LLM only explains, never decides (using existing LLMIntegration)
- [ ] Market data integration works (Alpaca only)
- [ ] Trade execution works (even if paper trading)