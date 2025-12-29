# Frontend-Facing API Response Contracts

This document defines the response contracts for frontend-facing endpoints. These contracts are locked and should not change without frontend coordination.

## GET /me

**Authentication:** Required (Bearer token)

**Response:** `MeResponse`

```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "broker_linked": true,
  "last_sync": "2024-01-15T10:30:00"
}
```

**Fields:**
- `user_id`: string (required) - User's unique identifier
- `email`: string | null - User's email address
- `broker_linked`: boolean (required) - Whether broker account is linked
- `last_sync`: ISO datetime string | null - Last portfolio sync timestamp

**Example:**
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "broker_linked": true,
  "last_sync": "2024-01-15T10:30:00"
}
```

---

## GET /recommendations/latest

**Authentication:** Required (Bearer token)

**Response:** `LatestRecommendationResponse`

```json
{
  "recommendation_id": "rec-123",
  "decision": "approve",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "guardrail_status": "ALLOW",
  "has_proposal": true
}
```

**Fields:**
- `recommendation_id`: string (required) - Unique recommendation identifier
- `decision`: string (required) - Decision type: "approve", "modify", "reject", "request_info", "defer"
- `status`: string (required) - Recommendation status: "pending", "approved", "rejected"
- `created_at`: ISO datetime string (required) - When recommendation was created
- `guardrail_status`: string | null - Guardrail result: "ALLOW", "WARN", "BLOCK", or null
- `has_proposal`: boolean (required) - Whether recommendation includes a portfolio proposal

**Example (with proposal):**
```json
{
  "recommendation_id": "rec-123",
  "decision": "approve",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "guardrail_status": "ALLOW",
  "has_proposal": true
}
```

**Example (blocked):**
```json
{
  "recommendation_id": "rec-456",
  "decision": "reject",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "guardrail_status": "BLOCK",
  "has_proposal": false
}
```

**Error Responses:**
- `404 NotFoundError`: No recommendations found
  ```json
  {
    "code": "NO_RECOMMENDATIONS_FOUND",
    "message": "No recommendations found",
    "details": null
  }
  ```

---

## POST /chat

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "recommendation_id": "rec-123"  // Optional: specific recommendation ID
}
```
If `recommendation_id` is null/omitted, uses latest recommendation.

**Response:** `ChatResponse`

```json
{
  "explanation": "This recommendation has been approved and is ready for your review. The proposed portfolio allocation is: 60.0% stocks, 30.0% bonds, 10.0% cash. This involves 1 trade(s) to achieve this allocation."
}
```

**Fields:**
- `explanation`: string (required) - Human-readable explanation text

**Example (approved):**
```json
{
  "explanation": "This recommendation has been approved and is ready for your review. The proposed portfolio allocation is: 60.0% stocks, 30.0% bonds, 10.0% cash. This involves 1 trade(s) to achieve this allocation."
}
```

**Example (with warnings):**
```json
{
  "explanation": "This recommendation has been modified with additional considerations. Please review the changes carefully. This recommendation has warnings that require your attention. Reasons: Your emergency fund (2.0 months) is below recommended minimum. Consider building emergency fund first. The proposed portfolio allocation is: 60.0% stocks, 30.0% bonds, 10.0% cash."
}
```

**Example (blocked):**
```json
{
  "explanation": "This recommendation has been rejected based on safety guardrails. See below for details. This recommendation was blocked by safety guardrails. Reasons: You have negative cash flow, so investing now is not recommended."
}
```

**Error Responses:**
- `404 NotFoundError`: No recommendations found or recommendation not found
  ```json
  {
    "code": "NO_RECOMMENDATIONS_FOUND",
    "message": "No recommendations found",
    "details": null
  }
  ```

---

## POST /recommendations/{recommendation_id}/approve

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "confirmations": {
    "conf_low_emergency_fund_investment": "I understand my emergency fund is below recommended levels and want to proceed"
  }
}
```

**Response:** `ApprovalResponse`

```json
{
  "recommendation_id": "rec-123",
  "status": "approved",
  "message": "Recommendation approved successfully"
}
```

**Fields:**
- `recommendation_id`: string (required) - Recommendation identifier
- `status`: string (required) - Updated status: "approved"
- `message`: string (required) - Success message

**Confirmation Requirements:**
- **WARN**: Requires checkbox confirmations (`confirmation_text` must match exactly)
- **BLOCK**: Requires explicit override acknowledgements (`override_acknowledgement` must match exactly)
- **ALLOW**: No confirmations required

**Example (success):**
```json
{
  "recommendation_id": "rec-123",
  "status": "approved",
  "message": "Recommendation approved successfully"
}
```

**Error Responses:**
- `400 ValidationError`: Missing or invalid confirmations
  ```json
  {
    "code": "MISSING_CONFIRMATIONS",
    "message": "Required confirmations not provided",
    "details": null
  }
  ```
  
  ```json
  {
    "code": "INVALID_CONFIRMATION_TEXT",
    "message": "Confirmation text for conf_low_emergency_fund_investment does not match required text",
    "details": null
  }
  ```
  
  ```json
  {
    "code": "INVALID_OVERRIDE_ACKNOWLEDGEMENT",
    "message": "Override acknowledgement for conf_negative_cashflow_invest does not match required text",
    "details": null
  }
  ```

- `404 NotFoundError`: Recommendation not found
  ```json
  {
    "code": "RECOMMENDATION_NOT_FOUND",
    "message": "Recommendation rec-123 not found",
    "details": null
  }
  ```

---

## Standard Error Response Format

All endpoints use the same error response format:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": "Additional details (only in development mode)"
}
```

**HTTP Status Codes:**
- `400` - ValidationError (bad request)
- `401` - AuthError (unauthorized)
- `404` - NotFoundError (not found)
- `500` - AppError (internal server error)
- `502` - ExternalServiceError (bad gateway)

---

## Notes

- All datetime fields use ISO 8601 format (e.g., "2024-01-15T10:30:00")
- All string fields are UTF-8 encoded
- All numeric fields use standard JSON number format
- Response contracts are locked - changes require frontend coordination

