# MCP Server Builder Subagent

> **Subagent Type:** Planning Subagent (📐)
> **Purpose:** Design MCP tool specifications from requirements
> **Output:** Documentation (not code)
> **Status:** Production Ready ✅

---

## Overview

The MCP Server Builder is a specialized planning subagent that designs Model Context Protocol (MCP) tool interfaces from user requirements. It generates comprehensive documentation that serves as the blueprint for implementing MCP servers that AI agents can interact with.

### What This Subagent Does

- **Input:** Feature specifications, user stories, domain models
- **Processing:** Analyzes requirements and designs clean tool interfaces
- **Output:** Detailed MCP tool architecture documentation with:
  - Tool schemas (parameters, returns, validation)
  - Error handling specifications
  - Security considerations
  - Concrete examples
  - Implementation guidance

### What This Subagent Does NOT Do

- Does not write actual code
- Does not implement the MCP server
- Does not test the tools
- Does not deploy anything

---

## When to Use This Subagent

### Use During Planning Phase (📐)

This subagent should be invoked DURING the planning stage, specifically:

1. **After** writing the feature specification (specs/phase3/spec.md)
2. **Before** breaking down into implementation tasks
3. **During** the architectural design process

### Workflow Position

```
Specification → [MCP Builder Subagent] → Plan Document → Tasks → Implementation
    (spec.md)                             (plan.md)      (tasks.md)    (code)
```

### Decision Criteria

Use this subagent when:
- ✅ You need to design MCP tools for an AI agent
- ✅ You have clear CRUD operations to expose
- ✅ You need structured API contracts between agent and backend
- ✅ You want consistent, well-documented tool interfaces

Don't use this subagent when:
- ❌ You're implementing the code (use implementation subagent instead)
- ❌ You don't have a spec yet (write spec first)
- ❌ You're designing REST APIs (not MCP tools)

---

## Installation

No installation required. This subagent is part of the `.claude/agents/` directory.

### File Structure

```
.claude/agents/mcp-builder/
├── agent.md           # Subagent definition (main file)
├── examples.md        # Usage examples and patterns
├── template-output.md # Expected output format reference
├── test-output.md     # Real example from Phase 3 spec
└── README.md          # This file
```

---

## Usage

### Basic Invocation

```bash
# From project root
claude --agent mcp-builder "Design MCP tool interfaces for Phase 3 Todo chatbot based on specs/phase3/spec.md"
```

### With Specific Operations

```bash
claude --agent mcp-builder "Design MCP tools for task management: add_task, list_tasks, update_task, delete_task, complete_task"
```

### With Constraints

```bash
claude --agent mcp-builder "Design MCP tools based on specs/phase3/spec.md. Follow constitution at .specify/memory/constitution.md. User isolation required."
```

---

## Input Requirements

### Minimum Inputs

The subagent needs at least ONE of the following:

1. **Specification File Path**
   - Example: `specs/phase3/spec.md`
   - Should contain: User stories, functional requirements, domain models

2. **Operation List**
   - Example: "add_task, list_tasks, complete_task"
   - Should specify: CRUD operations needed

3. **Domain Model**
   - Example: "Task (user_id, title, description, completed)"
   - Should include: Entity names and key fields

### Optional Inputs

- Constitution file path (for constraints and principles)
- Existing plan document (to add to or refactor)
- Specific validation rules or constraints
- Security requirements
- Performance requirements

---

## Output

### What You Get

The subagent generates a **markdown document** with:

#### 1. Tool Catalog Table
```markdown
| Tool Name | Purpose | Modifies Data | Auth Required | Idempotent |
|-----------|---------|---------------|---------------|------------|
| add_task  | Create new task | Yes | Yes | No |
```

#### 2. Detailed Tool Specifications

For each tool:
- **Purpose:** Clear one-line description
- **Parameters:** Full schema with types, constraints, descriptions
- **Returns:** Complete return value structure
- **Validation Rules:** All input validation requirements
- **Error Cases:** All possible errors with messages
- **Examples:** Concrete input/output examples (JSON)
- **Security Notes:** Security considerations and requirements
- **Idempotency:** Whether operation can be safely retried

#### 3. Implementation Guidance
- Database schema requirements
- Query patterns
- Performance considerations
- Testing checklist

### Output Format

See `template-output.md` for the complete output structure.

### Real Example

See `test-output.md` for actual output generated from Phase 3 spec.

---

## Examples

### Example 1: Todo CRUD Operations

**Input:**
```bash
claude --agent mcp-builder "Design MCP tools for Phase 3 Todo chatbot based on specs/phase3/spec.md. Required operations: add_task, list_tasks, update_task, delete_task, complete_task"
```

**Output:** Complete specification for 5 MCP tools (see `test-output.md`)

### Example 2: Conversation Management

**Input:**
```bash
claude --agent mcp-builder "Design MCP tools for conversation management. Operations: create_conversation, get_conversation_history, add_message. Domain: Conversation (user_id, id, created_at), Message (user_id, conversation_id, role, content)"
```

**Output:** 3 tool specifications for managing conversations

### Example 3: Custom Search Tool

**Input:**
```bash
claude --agent mcp-builder "Design MCP tool: search_tasks with filters (status, date_range, keyword) and pagination (limit, offset)"
```

**Output:** Single tool specification with complex parameters

---

## Best Practices

### 1. Provide Clear Context

**Good:**
```bash
"Design MCP tools for Phase 3 Todo chatbot (spec: specs/phase3/spec.md).
User isolation required. Operations: add, list, update, delete, complete tasks.
Title max 200 chars, description max 1000 chars."
```

**Bad:**
```bash
"Make task tools"
```

### 2. Reference Existing Documents

Always point to:
- Specification file (`specs/*/spec.md`)
- Constitution file (`.specify/memory/constitution.md`)
- Existing plan (if modifying)

### 3. Specify Constraints

Include:
- Field length limits
- Required vs optional parameters
- Security requirements (user isolation, rate limits)
- Performance requirements (response time, pagination)

### 4. Request Complete Output

Ask for:
- All required tools
- Error cases
- Examples
- Security notes

---

## Integration with Other Subagents

### Planning Phase Workflow

1. **Start:** Specification written (specs/phase3/spec.md)
2. **Step 1:** Run MCP Builder Subagent → generates tool architecture
3. **Step 2:** Run Database Schema Generator → generates SQLModel schemas
4. **Step 3:** Run Stateless API Designer → designs chat endpoint
5. **Output:** All combined into specs/phase3/plan.md
6. **Next:** Break plan into tasks (tasks.md)

### Using Output for Implementation

Once you have the MCP tool architecture:

1. **Copy to Plan:** Add output to `specs/phase3/plan.md`
2. **Review:** Verify all requirements covered
3. **Break into Tasks:** Create tasks.md based on tool specs
4. **Implement:** Use implementation subagent or manual coding

---

## Validation Checklist

After receiving output from MCP Builder, verify:

- [ ] All required operations are covered
- [ ] Parameter names match database schema (snake_case)
- [ ] user_id is required for all multi-user tools
- [ ] Examples are realistic and testable (not placeholders)
- [ ] Error cases cover: validation, auth, not found, database errors
- [ ] Security notes address data isolation and input sanitization
- [ ] Return values include enough data for natural language responses
- [ ] Tool names follow verb_noun convention (e.g., add_task, not createTask)
- [ ] Validation rules have clear rationale
- [ ] Idempotency is clearly documented for each tool

---

## Troubleshooting

### Issue: Output is Too Generic

**Symptoms:** Parameters like "title: string", no validation rules, generic examples

**Solution:**
- Provide more specific constraints in your prompt
- Reference the spec file explicitly
- Specify field lengths, formats, and validation rules

**Example Fix:**
```bash
# Before
"Design add_task tool"

# After
"Design add_task tool with title (1-200 chars, not empty),
description (optional, max 1000 chars), user_id required.
Based on specs/phase3/spec.md"
```

### Issue: Missing Error Cases

**Symptoms:** Only ValidationError documented, no auth/not found errors

**Solution:**
- Explicitly request "Include all error cases: validation, authorization, not found, database"
- Mention specific scenarios you need handled

### Issue: Security Considerations Missing

**Symptoms:** No mention of user isolation, XSS prevention, rate limiting

**Solution:**
- Add to prompt: "Include security analysis for multi-user isolation, input sanitization, and rate limiting"
- Reference constitution security principles

### Issue: Examples Use Placeholders

**Symptoms:** Examples show `{value}`, `<parameter>`, `...` instead of concrete data

**Solution:**
- Request: "Provide concrete examples with realistic data, no placeholders"
- Give example data in your prompt: "User 'user_abc123' creating task 'Buy groceries'"

---

## FAQ

### Q: Can this subagent write Python code?

**A:** No. This is a planning subagent that generates documentation. Use an implementation subagent to generate actual code from this documentation.

### Q: How do I use the output?

**A:** Copy the generated markdown to your `specs/phase3/plan.md` file. This becomes the blueprint for implementation.

### Q: Can I modify the subagent definition?

**A:** Yes. Edit `agent.md` to customize the subagent's behavior, output format, or design principles.

### Q: What if my project doesn't use MCP?

**A:** This subagent is specifically for MCP tool design. For REST APIs, create a different subagent or use general planning tools.

### Q: How long does it take to run?

**A:** Typically 30-60 seconds for 5 tools. Complex tools with many parameters may take longer.

### Q: Can I run this for multiple features?

**A:** Yes, but run separately for each feature and combine outputs manually. Better to keep tool sets focused.

---

## Performance Metrics

Based on Phase 3 Todo Chatbot test:

| Metric | Value |
|--------|-------|
| **Input:** | 2,500 words (spec.md) |
| **Output:** | 14,000 words (test-output.md) |
| **Tools Designed:** | 5 (add, list, update, delete, complete) |
| **Time Saved:** | ~4 hours (manual design time) |
| **Completeness:** | 100% (all acceptance criteria met) |

---

## Contributing

To improve this subagent:

1. Edit `agent.md` to modify behavior
2. Add new examples to `examples.md`
3. Update output template in `template-output.md`
4. Test with real specs and document results

---

## Version History

**Version 1.0.0** (2025-12-18)
- Initial release
- Supports CRUD tool design
- Includes validation, error handling, security notes
- Comprehensive examples and templates

---

## License

Part of Todo AI Chatbot project (Phase 3 Hackathon)

---

## Related Files

- **Constitution:** `.specify/memory/constitution.md` (project principles)
- **Spec Template:** `.specify/templates/spec-template.md`
- **Plan Template:** `.specify/templates/plan-template.md`
- **Phase 3 Spec:** `specs/phase3/spec.md`
- **Test Output:** `.claude/agents/mcp-builder/test-output.md`

---

## Support

For issues or questions:
1. Check `examples.md` for usage patterns
2. Review `test-output.md` for expected results
3. Consult `agent.md` for subagent definition
4. Refer to constitution for project principles

---

**MCP Server Builder Subagent - Ready to Use** ✅
