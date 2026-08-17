# Chain of Actions API Documentation

The Chain of Actions system allows the AI to perform multi-step complex tasks by decomposing them into executable steps, executing them across different agents/tools, and verifying the results.

## Base URL
`/api/chains`

## Authentication
All endpoints require a valid JWT token in the `Authorization` header:
`Authorization: Bearer <your_jwt_token>`

## Endpoints

### 1. Create & Execute Chain
Starts a new action chain execution based on a natural language command.

- **URL**: `/create`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "command": "Research the best budget 4k monitors and create a summary table"
  }
  ```
- **Response**:
  ```json
  {
    "status": "started",
    "message": "Chain execution started",
    "command": "Research the best budget 4k monitors..."
  }
  ```

### 2. Get Chain Status
Retrieve the current status, steps, and results of a specific chain.

- **URL**: `/<chain_id>`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "chain_id": "chain_20231027_123456",
    "status": "in_progress",
    "steps": [
      {
        "step_id": "step_1",
        "action_type": "web_search",
        "status": "completed",
        "result": {...}
      },
      ...
    ]
  }
  ```

### 3. Get Chain History
Retrieve a list of recently executed chains.

- **URL**: `/history`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "chains": [
      {
        "chain_id": "...",
        "status": "completed",
        "created_at": "..."
      },
      ...
    ]
  }
  ```

## WebSocket Events

Connect to the root namespace `/` to receive real-time updates.

### Event: `chain_progress`
Broadcasted whenever a step starts, completes, or fails in any active chain.

- **Payload**:
  ```json
  {
    "chain_id": "chain_...",
    "step_index": 1,
    "total_steps": 5,
    "status": "in_progress",
    "current_action": "Searching web for...",
    "message": "Found 5 results",
    "result": {...} // Only on completion
  }
  ```

## Testing

You can test the system using the provided script:
```bash
python test_chain_execution.py
```
