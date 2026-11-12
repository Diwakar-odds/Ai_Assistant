# Chain of Actions API Documentation

The Chain of Actions feature orchestrates complex, multi-step tasks across the AI Assistant system. This document outlines the available REST APIs and WebSocket events for interacting with the Chain of Actions manager.

## Base URL
`/api/chains`

## Authentication
All endpoints require a valid JWT token via the `Authorization: Bearer <token>` header, unless otherwise specified.

---

## REST Endpoints

### 1. Create a Chain
`POST /create`

Parses a natural language command into a chain structure. The execution starts automatically in the background.

**Request Body:**
```json
{
  "command": "Analyze my recent project files and create a summary"
}
```

**Response (200 OK):**
```json
{
  "status": "started",
  "message": "Chain execution started",
  "chain_id": "chain_a1b2c3d4",
  "command": "Analyze my recent project files and create a summary"
}
```

### 2. Execute a Chain Manually
`POST /{chain_id}/execute`

Executes a previously created but unstarted chain.

**Response (200 OK):**
```json
{
  "status": "executing",
  "chain_id": "chain_a1b2c3d4",
  "message": "Chain execution started"
}
```

### 3. Cancel a Chain
`POST /{chain_id}/cancel`

Cancels a running chain.

**Response (200 OK):**
```json
{
  "status": "cancelled",
  "chain_id": "chain_a1b2c3d4"
}
```

### 4. Get Chain Status
`GET /{chain_id}`

Retrieves the full current state of a chain.

**Response (200 OK):**
```json
{
  "id": "chain_a1b2c3d4",
  "command": "Analyze my recent...",
  "status": "EXECUTING",
  "actions": [
    {
      "id": "action_1",
      "type": "FILE_READ",
      "status": "COMPLETED"
    }
  ]
}
```

### 5. Get Chain History
`GET /history`

Retrieves a summary of recently completed or cancelled chains.

**Response (200 OK):**
```json
{
  "history": [
    {
      "id": "chain_a1b2c3d4",
      "command": "Analyze my recent...",
      "status": "COMPLETED",
      "steps": 3
    }
  ]
}
```

### 6. Optimize Chain Plan
`POST /optimize`

Optimizes a proposed chain plan based on historical execution data.

**Request Body:**
```json
{
  "plan": [ { "type": "WEB_SEARCH" }, { "type": "LLM_SUMMARIZE" } ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "optimized_plan": [ { "type": "WEB_SEARCH_AND_SUMMARIZE" } ],
  "predicted_success_rate": 0.95
}
```

---

## Voice Integration

### Convert Voice to Chain
`POST /api/voice/chain`

Converts a voice command directly into a Chain of Actions and begins execution.

**Request Body:**
```json
{
  "command": "Deploy the backend server"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "chain_id": "chain_12345",
  "message": "Started chain execution for voice command: Deploy the backend server"
}
```

---

## WebSocket Events

Connect to the global socket endpoint and subscribe to specific chains.

### 1. Subscribe to a Chain
**Client Emits:** `subscribe_chain`
**Payload:** `{ "chain_id": "chain_12345" }`

**Server Responds:** `chain.subscribed`
**Payload:** `{ "chain_id": "chain_12345" }`

### 2. Unsubscribe from a Chain
**Client Emits:** `unsubscribe_chain`
**Payload:** `{ "chain_id": "chain_12345" }`

### 3. Server Progress Events

Once subscribed, the server will emit these events to the specific chain's room:

- **`chain.started`**: Emitted when decomposition and execution begin.
- **`chain.step_completed`**: Emitted when a single step finishes. Payload includes `step_id` and result data.
- **`chain.step_failed`**: Emitted when a step fails. Payload includes `error` details.
- **`chain.verification_completed`**: Emitted after the Advanced Verification System validates a step.
- **`chain.completed`**: Emitted when the entire chain finishes successfully.
