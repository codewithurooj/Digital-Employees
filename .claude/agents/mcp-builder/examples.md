# MCP Server Builder - Usage Examples

## Example 1: Basic Todo CRUD Operations

### Invocation
```bash
claude --agent mcp-builder "Design MCP tools for Phase 3 Todo chatbot based on specs/phase3/spec.md. Required operations: add_task, list_tasks, update_task, delete_task, complete_task"
```

### Input Context
- **Domain Model**: Task (user_id, id, title, description, completed, created_at, updated_at)
- **Operations**: CRUD + complete
- **Requirements**: Multi-user isolation, natural language friendly, stateless

### Expected Output
The subagent will generate a complete MCP Tool Architecture document with:
- Tool catalog table
- 5 tool specifications (add_task, list_tasks, update_task, delete_task, complete_task)
- Each tool with parameters, returns, validation rules, error cases, examples, security notes

---

## Example 2: Conversation Management Tools

### Invocation
```bash
claude --agent mcp-builder "Design MCP tools for conversation management. Operations: create_conversation, get_conversation_history, add_message"
```

### Input Context
- **Domain Models**:
  - Conversation (user_id, id, created_at, updated_at)
  - Message (user_id, id, conversation_id, role, content, created_at)
- **Operations**: Create, retrieve history, add message
- **Requirements**: Stateless retrieval, pagination for history

### Expected Output
3 tool specifications for managing conversations and messages

---

## Example 3: Custom Tool with Complex Validation

### Invocation
```bash
claude --agent mcp-builder "Design an MCP tool: search_tasks with filters (status, date_range, keyword) and pagination"
```

### Input Context
- **Single Operation**: search_tasks
- **Requirements**:
  - Filter by completed status
  - Filter by date range (created_at)
  - Text search in title/description
  - Paginated results (limit, offset)

### Expected Output
Single tool specification with:
- Complex parameter schema (filters object, pagination params)
- Return value with results array + pagination metadata
- Validation rules for date formats, limit ranges
- Examples showing different filter combinations

---

## Example 4: Batch Operations

### Invocation
```bash
claude --agent mcp-builder "Design MCP tool: complete_tasks_batch for marking multiple tasks as complete at once"
```

### Input Context
- **Operation**: Batch complete
- **Requirements**:
  - Accept array of task_ids
  - Max 50 tasks per batch
  - Partial success handling (some may fail)
  - Return success/failure status per task

### Expected Output
Tool specification with:
- Array parameter with length constraints
- Batch-specific validation rules
- Partial failure error handling documented
- Example showing mixed success/failure results

---

## Example 5: Integration with Existing Spec

### Invocation (Realistic Workflow)
```bash
# Step 1: Read the spec
claude "Read specs/phase3/spec.md and summarize the MCP tool requirements"

# Step 2: Invoke MCP Builder subagent
claude --agent mcp-builder "Based on specs/phase3/spec.md, design all MCP tools needed. Follow the constitution at .specify/memory/constitution.md"

# Step 3: Save output to plan
# (Agent will generate markdown, you copy to specs/phase3/plan.md)
```

---

## Tips for Effective Use

### 1. Provide Clear Context
**Good**: "Design MCP tools for user_id=123 to manage tasks with CRUD operations"
**Better**: "Design MCP tools for Phase 3 Todo chatbot (spec: specs/phase3/spec.md). User isolation required. Operations: add, list, update, delete, complete tasks"

### 2. Reference Existing Docs
- Always point to spec files if they exist
- Reference constitution for constraints
- Mention existing data models

### 3. Specify Constraints
- Max field lengths
- Pagination requirements
- Rate limits
- Security requirements

### 4. Request Specific Output
**Good**: "Design add_task tool"
**Better**: "Design add_task tool with validation for 200-char title limit and optional description (1000 chars max)"

---

## Integration with Other Subagents

### Planning Workflow
1. **Spec Created** → specs/phase3/spec.md written
2. **MCP Builder** → Generates tool architecture (this subagent)
3. **Database Schema Generator** → Generates SQLModel schemas
4. **Stateless API Designer** → Designs chat endpoint
5. **Output** → All goes into specs/phase3/plan.md

### Implementation Workflow
1. **Plan Complete** → specs/phase3/plan.md ready
2. **Tasks Broken Down** → specs/phase3/tasks.md created
3. **MCP Implementation Subagent** → Generates actual Python MCP server code
4. **Testing** → Natural Language Test Generator creates test cases

---

## Common Patterns

### Pattern 1: CRUD Tools (4 operations)
```bash
claude --agent mcp-builder "Design CRUD tools for [Entity]: create_[entity], list_[entity]s, update_[entity], delete_[entity]"
```

### Pattern 2: Status Transition Tools
```bash
claude --agent mcp-builder "Design status transition tool: mark_[entity]_[status] (e.g., mark_task_complete)"
```

### Pattern 3: Search/Filter Tools
```bash
claude --agent mcp-builder "Design search tool: search_[entity]s with filters [filter1, filter2] and pagination"
```

### Pattern 4: Batch Tools
```bash
claude --agent mcp-builder "Design batch tool: [action]_[entity]s_batch with max size [N] and partial failure handling"
```

---

## Validation Checklist (User)

After receiving output from MCP Builder, verify:
- [ ] All required operations are covered
- [ ] Parameter names match database schema (snake_case)
- [ ] user_id is required for all multi-user tools
- [ ] Examples are realistic and testable
- [ ] Error cases cover validation, auth, not found
- [ ] Security notes address data isolation
- [ ] Return values include enough data for natural language responses
- [ ] Tool names follow verb_noun convention

---

## Next Steps After MCP Builder

1. **Review Output**: Ensure all requirements met
2. **Add to Plan**: Copy markdown to specs/phase3/plan.md
3. **Get Approval**: Review with team/stakeholder
4. **Break into Tasks**: Use output to create tasks.md
5. **Implement**: Use MCP Implementation subagent or manual coding

---

## Troubleshooting

### Issue: Output too generic
**Solution**: Provide more specific constraints and examples in prompt

### Issue: Missing error cases
**Solution**: Mention specific error scenarios you need covered

### Issue: Validation rules unclear
**Solution**: Specify exact length limits, regex patterns, or enums

### Issue: Security considerations missing
**Solution**: Explicitly request "Include security analysis for multi-user isolation"
