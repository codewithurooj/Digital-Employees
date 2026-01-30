# MCP Tool Architecture - Template Output

> This is an example of what the MCP Builder subagent generates. Use this as a reference for expected output format.

---

## MCP Tool Architecture

### Overview
This MCP server provides task management capabilities for the Todo AI Chatbot. It exposes 5 tools that enable the AI agent to perform all CRUD operations on user tasks. All tools enforce user isolation and are designed for stateless operation.

### Tool Catalog

| Tool Name | Purpose | Modifies Data | Auth Required | Idempotent |
|-----------|---------|---------------|---------------|------------|
| add_task | Create new task | Yes | Yes | No |
| list_tasks | Retrieve user's tasks | No | Yes | Yes |
| update_task | Modify existing task | Yes | Yes | No |
| delete_task | Remove task permanently | Yes | Yes | Yes |
| complete_task | Mark task as done | Yes | Yes | Yes |

---

### Tool: add_task

**Purpose:** Create a new task for the authenticated user

**Parameters:**
- `user_id` (string, required) - User identifier from JWT token for authorization
- `title` (string, required, 1-200 chars) - Task title displayed in task list
- `description` (string, optional, max 1000 chars) - Optional detailed description of the task

**Returns:**
- `task_id` (integer) - Unique identifier for the created task
- `status` (string: "created") - Operation status
- `title` (string) - Echo of the task title for confirmation
- `description` (string|null) - Echo of description if provided
- `completed` (boolean) - Always false for new tasks
- `created_at` (ISO 8601 datetime) - Timestamp of creation

**Validation Rules:**
- Title must not be empty or whitespace-only
- Title length: 1-200 characters (UI displays first 50 chars before truncation)
- Description length: 0-1000 characters (stored in TEXT field)
- user_id must exist in users table (foreign key constraint)
- Title and description must be sanitized to prevent XSS

**Error Cases:**
- **ValidationError** (400): When title is empty, too long, or contains only whitespace
- **AuthorizationError** (401): When user_id doesn't match authenticated user from JWT
- **DatabaseError** (500): When database is unavailable (safe to retry)
- **RateLimitError** (429): When user exceeds 100 tasks per hour

**Example:**
```json
// Input
{
  "user_id": "user_abc123",
  "title": "Buy groceries",
  "description": "Milk, eggs, bread from Whole Foods"
}

// Output (Success)
{
  "task_id": 42,
  "status": "created",
  "title": "Buy groceries",
  "description": "Milk, eggs, bread from Whole Foods",
  "completed": false,
  "created_at": "2025-12-18T10:30:00Z"
}

// Output (Error - Validation)
{
  "error": "ValidationError",
  "message": "Title cannot be empty or whitespace-only",
  "field": "title"
}
```

**Security Notes:**
- Verify user_id from request matches JWT token user_id (must be done at API gateway/middleware level)
- Sanitize title and description to prevent XSS attacks (escape HTML entities)
- Rate limit: Max 100 task creations per user per hour
- Do not allow setting user_id to arbitrary values (derive from authenticated session)

**Idempotency:** No - calling twice with same inputs creates duplicate tasks. Consider adding optional idempotency_key parameter if duplicate prevention is needed.

---

### Tool: list_tasks

**Purpose:** Retrieve all tasks for the authenticated user with optional filtering

**Parameters:**
- `user_id` (string, required) - User identifier from JWT token
- `status` (string, optional, enum: "all" | "pending" | "completed") - Filter by completion status (default: "all")
- `limit` (integer, optional, 1-100) - Maximum number of tasks to return (default: 50)
- `offset` (integer, optional, min 0) - Number of tasks to skip for pagination (default: 0)
- `sort_by` (string, optional, enum: "created_at" | "updated_at" | "title") - Sort field (default: "created_at")
- `sort_order` (string, optional, enum: "asc" | "desc") - Sort direction (default: "desc")

**Returns:**
- `tasks` (array of Task objects) - List of tasks matching filters
  - Each Task contains: `task_id`, `title`, `description`, `completed`, `created_at`, `updated_at`
- `total_count` (integer) - Total number of tasks matching filter (ignoring pagination)
- `limit` (integer) - Echo of limit parameter used
- `offset` (integer) - Echo of offset parameter used
- `has_more` (boolean) - True if there are more results beyond current page

**Validation Rules:**
- user_id must be valid and authenticated
- status must be one of: "all", "pending", "completed"
- limit must be between 1 and 100 (prevents excessive data transfer)
- offset must be >= 0
- sort_by must be one of the allowed fields
- sort_order must be "asc" or "desc"

**Error Cases:**
- **ValidationError** (400): When parameters are out of range or invalid enum values
- **AuthorizationError** (401): When user_id doesn't match authenticated user
- **DatabaseError** (500): When database query fails (safe to retry)

**Example:**
```json
// Input
{
  "user_id": "user_abc123",
  "status": "pending",
  "limit": 10,
  "offset": 0,
  "sort_by": "created_at",
  "sort_order": "desc"
}

// Output
{
  "tasks": [
    {
      "task_id": 42,
      "title": "Buy groceries",
      "description": "Milk, eggs, bread from Whole Foods",
      "completed": false,
      "created_at": "2025-12-18T10:30:00Z",
      "updated_at": "2025-12-18T10:30:00Z"
    },
    {
      "task_id": 41,
      "title": "Call dentist",
      "description": null,
      "completed": false,
      "created_at": "2025-12-18T09:15:00Z",
      "updated_at": "2025-12-18T09:15:00Z"
    }
  ],
  "total_count": 2,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

**Security Notes:**
- ALWAYS filter by user_id to prevent data leakage between users
- Validate user_id matches authenticated session before executing query
- Consider rate limiting to prevent enumeration attacks (max 100 requests per minute)
- Do not expose task_id generation patterns that could reveal user activity

**Idempotency:** Yes - calling multiple times with same parameters returns consistent results (assuming no concurrent modifications)

---

### Tool: update_task

**Purpose:** Modify title and/or description of an existing task

**Parameters:**
- `user_id` (string, required) - User identifier from JWT token
- `task_id` (integer, required) - Unique identifier of task to update
- `title` (string, optional, 1-200 chars) - New task title (if provided, replaces existing)
- `description` (string, optional, 0-1000 chars) - New description (if provided, replaces existing; empty string clears it)

**Returns:**
- `task_id` (integer) - ID of updated task
- `status` (string: "updated") - Operation status
- `title` (string) - Current title after update
- `description` (string|null) - Current description after update
- `completed` (boolean) - Completion status (unchanged by this operation)
- `updated_at` (ISO 8601 datetime) - New update timestamp

**Validation Rules:**
- user_id must own the task (authorization check)
- task_id must exist in database
- At least one of title or description must be provided
- Title (if provided) must be 1-200 characters, not whitespace-only
- Description (if provided) must be 0-1000 characters
- Cannot change user_id or task_id (security constraint)
- Cannot change completed status (use complete_task tool instead)

**Error Cases:**
- **ValidationError** (400): When no fields provided, or validation fails
- **NotFoundError** (404): When task_id doesn't exist
- **AuthorizationError** (403): When user_id doesn't own the task
- **DatabaseError** (500): When update operation fails (safe to retry)

**Example:**
```json
// Input (Update title only)
{
  "user_id": "user_abc123",
  "task_id": 42,
  "title": "Buy groceries and cook dinner"
}

// Output
{
  "task_id": 42,
  "status": "updated",
  "title": "Buy groceries and cook dinner",
  "description": "Milk, eggs, bread from Whole Foods",
  "completed": false,
  "updated_at": "2025-12-18T11:45:00Z"
}

// Input (Clear description)
{
  "user_id": "user_abc123",
  "task_id": 42,
  "description": ""
}

// Output
{
  "task_id": 42,
  "status": "updated",
  "title": "Buy groceries and cook dinner",
  "description": null,
  "completed": false,
  "updated_at": "2025-12-18T11:50:00Z"
}

// Error (Not Found)
{
  "error": "NotFoundError",
  "message": "Task with ID 999 not found",
  "task_id": 999
}

// Error (Authorization)
{
  "error": "AuthorizationError",
  "message": "User does not have permission to update this task",
  "task_id": 42
}
```

**Security Notes:**
- MUST verify user_id owns the task before allowing update
- Do not allow changing user_id field (would enable task theft)
- Do not allow changing task_id (would enable overwriting other tasks)
- Sanitize title and description to prevent XSS
- Log updates for audit trail (user_id, task_id, timestamp)

**Idempotency:** No - calling twice updates the updated_at timestamp each time. However, the final state is the same, so it's "idempotent in effect" if same values provided.

---

### Tool: delete_task

**Purpose:** Permanently remove a task from the database (hard delete)

**Parameters:**
- `user_id` (string, required) - User identifier from JWT token
- `task_id` (integer, required) - Unique identifier of task to delete

**Returns:**
- `task_id` (integer) - ID of deleted task
- `status` (string: "deleted") - Operation status
- `deleted_at` (ISO 8601 datetime) - Timestamp of deletion

**Validation Rules:**
- user_id must own the task (authorization check)
- task_id must exist in database (at time of deletion)
- Deletion is permanent and cannot be undone

**Error Cases:**
- **NotFoundError** (404): When task_id doesn't exist or already deleted
- **AuthorizationError** (403): When user_id doesn't own the task
- **DatabaseError** (500): When delete operation fails (safe to retry)

**Example:**
```json
// Input
{
  "user_id": "user_abc123",
  "task_id": 42
}

// Output (Success)
{
  "task_id": 42,
  "status": "deleted",
  "deleted_at": "2025-12-18T12:00:00Z"
}

// Output (Already Deleted - Idempotent)
{
  "task_id": 42,
  "status": "deleted",
  "deleted_at": "2025-12-18T12:00:00Z",
  "note": "Task was already deleted"
}

// Error (Authorization)
{
  "error": "AuthorizationError",
  "message": "User does not have permission to delete this task",
  "task_id": 42
}
```

**Security Notes:**
- MUST verify user_id owns the task before allowing deletion
- Consider implementing soft delete (mark as deleted instead of removing) for data recovery
- Log deletions for audit trail (user_id, task_id, timestamp)
- Rate limit to prevent abuse (max 100 deletions per user per hour)

**Idempotency:** Yes - deleting an already-deleted task returns success (not an error). This prevents errors in retry scenarios.

---

### Tool: complete_task

**Purpose:** Mark a task as completed (or toggle completion status)

**Parameters:**
- `user_id` (string, required) - User identifier from JWT token
- `task_id` (integer, required) - Unique identifier of task to complete
- `completed` (boolean, optional) - Set to true to mark complete, false to mark incomplete (default: true)

**Returns:**
- `task_id` (integer) - ID of updated task
- `status` (string: "completed" | "reopened") - Operation status
- `title` (string) - Task title for confirmation
- `completed` (boolean) - New completion status
- `updated_at` (ISO 8601 datetime) - New update timestamp

**Validation Rules:**
- user_id must own the task (authorization check)
- task_id must exist in database
- completed must be a boolean (true or false)

**Error Cases:**
- **NotFoundError** (404): When task_id doesn't exist
- **AuthorizationError** (403): When user_id doesn't own the task
- **DatabaseError** (500): When update operation fails (safe to retry)

**Example:**
```json
// Input (Mark complete)
{
  "user_id": "user_abc123",
  "task_id": 42,
  "completed": true
}

// Output
{
  "task_id": 42,
  "status": "completed",
  "title": "Buy groceries",
  "completed": true,
  "updated_at": "2025-12-18T14:30:00Z"
}

// Input (Reopen task)
{
  "user_id": "user_abc123",
  "task_id": 42,
  "completed": false
}

// Output
{
  "task_id": 42,
  "status": "reopened",
  "title": "Buy groceries",
  "completed": false,
  "updated_at": "2025-12-18T14:35:00Z"
}
```

**Security Notes:**
- MUST verify user_id owns the task before allowing status change
- Log status changes for audit trail (useful for productivity analytics)
- Consider adding completed_at timestamp field to track when task was marked done

**Idempotency:** Yes - marking an already-completed task as complete returns success with same state. This prevents errors in retry scenarios.

---

## Implementation Notes

### Database Schema Requirements
```sql
CREATE TABLE tasks (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_completed ON tasks(completed);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
```

### MCP Server Implementation (Python)
```python
from mcp.server import MCPServer
from mcp.types import Tool, TextContent

server = MCPServer("todo-mcp-server")

@server.tool("add_task")
async def add_task(user_id: str, title: str, description: str = None) -> dict:
    # Implementation
    pass

@server.tool("list_tasks")
async def list_tasks(
    user_id: str,
    status: str = "all",
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> dict:
    # Implementation
    pass

# ... other tools
```

### OpenAI Agent Integration
```python
from openai import OpenAI

client = OpenAI()
agent = client.beta.agents.create(
    model="gpt-4o",
    tools=[
        {"type": "mcp_server", "mcp_server": {"url": "http://localhost:8000/mcp"}}
    ]
)

# Agent will automatically call MCP tools based on user messages
response = agent.messages.create(
    agent_id=agent.id,
    messages=[{"role": "user", "content": "Add a task to buy groceries"}]
)
```

---

## Testing Checklist

- [ ] All tools validate user_id ownership
- [ ] Validation errors return 400 with descriptive messages
- [ ] Authorization errors return 403 (not 404 to prevent enumeration)
- [ ] Not found errors return 404
- [ ] Database errors return 500 and are safe to retry
- [ ] Idempotent operations can be safely retried
- [ ] All string inputs are sanitized for XSS
- [ ] Rate limiting is enforced
- [ ] Pagination works correctly with limit/offset
- [ ] Sorting works for all allowed fields
- [ ] Empty description is handled correctly (null vs empty string)
- [ ] Timestamps are ISO 8601 format with timezone

---

**This template serves as the expected output format for the MCP Builder subagent.**
