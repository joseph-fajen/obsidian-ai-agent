# Feature: Conversation History Resilience

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Implement three defensive layers to handle malformed conversation history that causes crashes when Pydantic AI attempts to replay tool call arguments. This addresses the `ValueError: EOF while parsing an object` errors observed in production when conversation history contains truncated or corrupted JSON in tool call arguments.

**The Three Layers:**
1. **Input Validation** - Validate tool call JSON arguments at the API boundary before Pydantic AI processes them
2. **Graceful Error Recovery** - Catch parsing errors during streaming and return user-friendly messages instead of crashing
3. **History Limits** - Limit conversation history size to reduce costs and probability of encountering corrupted entries

## User Story

As a Jasque user having long conversations via Obsidian Copilot
I want the agent to handle malformed conversation history gracefully
So that my conversations don't crash unexpectedly and I can continue working

## Problem Statement

When users have long conversations with multiple tool calls, the conversation history can accumulate malformed JSON in tool call arguments. This happens because:
1. LLMs occasionally generate truncated or invalid JSON for tool arguments
2. This corrupted data gets stored in conversation history by Obsidian Copilot
3. When Pydantic AI replays the history, `args_as_dict()` fails to parse the malformed JSON
4. The entire request crashes with `ValueError: EOF while parsing an object`

Additionally, long conversations accumulate excessive tokens (125K+ observed), leading to high costs ($38+ per request).

## Solution Statement

Implement defense-in-depth with three layers:
1. **Validate incoming messages** at the API boundary, rejecting requests with malformed tool call arguments with actionable error messages
2. **Catch and handle errors gracefully** in the streaming code, returning user-friendly errors instead of 500s
3. **Limit conversation history** to a configurable number of messages (default 50), reducing both cost and failure probability

## Feature Metadata

**Feature Type**: Enhancement / Bug Fix (defensive hardening)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `app/features/chat/openai_routes.py`, `app/features/chat/streaming.py`, `app/features/chat/openai_schemas.py`, `app/core/config.py`
**Dependencies**: None (internal defensive code)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: READ THESE FILES BEFORE IMPLEMENTING!

- `app/features/chat/openai_routes.py` (lines 39-177) - Why: Main endpoint, where validation and truncation will be added
- `app/features/chat/streaming.py` (lines 58-86, 177-199) - Why: History conversion and error handling patterns
- `app/features/chat/openai_schemas.py` (lines 45-54) - Why: ChatMessage schema to extend with tool_calls
- `app/core/config.py` (lines 15-59) - Why: Settings class pattern for adding max_conversation_messages
- `app/core/exceptions.py` (lines 14-29) - Why: Custom exception patterns
- `app/features/chat/tests/test_streaming.py` - Why: Test patterns for streaming module
- `app/features/chat/tests/test_openai_routes.py` - Why: Test patterns for routes

### New Files to Create

- `app/features/chat/history.py` - Conversation history validation and truncation utilities
- `app/features/chat/tests/test_history.py` - Tests for history validation and truncation

### Relevant Documentation READ THESE BEFORE IMPLEMENTING!

- [Pydantic AI Message History](https://ai.pydantic.dev/message-history/)
  - Specific section: Message types and history_processors
  - Why: Understanding how Pydantic AI handles message history
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
  - Specific section: Tool calls validation guidance
  - Why: OpenAI recommends validating tool arguments in your code

### Patterns to Follow

**Settings Pattern (from config.py):**
```python
class Settings(BaseSettings):
    # ... existing settings ...
    max_conversation_messages: int = 50
```

**HTTPException Pattern (from openai_routes.py):**
```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Actionable error message here",
)
```

**Logging Pattern (from streaming.py):**
```python
logger.error(
    "agent.history.validation_failed",
    error=str(e),
    error_type=type(e).__name__,
    exc_info=True,
)
```

**Pydantic Schema Pattern (from openai_schemas.py):**
```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]
    # New optional field for tool calls
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Schema and Settings

Add the configuration setting and extend the ChatMessage schema to support tool_calls validation.

**Tasks:**
- Add `max_conversation_messages` setting to config
- Add `tool_calls` field to `ChatMessage` schema
- Create `ToolCall` and `ToolCallFunction` schemas

### Phase 2: Core Implementation - Validation and Truncation

Create the history management module with validation and truncation functions.

**Tasks:**
- Create `history.py` with validation logic
- Implement JSON argument validation
- Implement message truncation
- Add custom exception for validation errors

### Phase 3: Integration

Wire the validation and truncation into the request flow.

**Tasks:**
- Add validation call in openai_routes.py
- Add truncation call in openai_routes.py
- Enhance error handling in streaming.py

### Phase 4: Testing & Validation

Comprehensive tests for all new functionality.

**Tasks:**
- Unit tests for validation functions
- Unit tests for truncation functions
- Integration tests for error scenarios

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: UPDATE `app/core/config.py` - Add max_conversation_messages setting

- **IMPLEMENT**: Add `max_conversation_messages: int = 50` to the Settings class after `llm_model`
- **PATTERN**: Follow existing settings pattern (lines 32-52)
- **IMPORTS**: None needed
- **GOTCHA**: Keep alphabetical/logical grouping with other settings
- **VALIDATE**: `uv run python -c "from app.core.config import get_settings; s = get_settings(); print(f'max_conversation_messages: {s.max_conversation_messages}')"`

### Task 2: UPDATE `app/features/chat/openai_schemas.py` - Add tool_calls schema

- **IMPLEMENT**: Add ToolCallFunction, ToolCall, and update ChatMessage with optional tool_calls field
- **PATTERN**: Follow existing BaseModel patterns in the file
- **IMPORTS**: None additional needed
- **SCHEMA**:
  ```python
  class ToolCallFunction(BaseModel):
      """Function details in a tool call."""
      name: str
      arguments: str  # JSON string - this is what we validate

  class ToolCall(BaseModel):
      """A tool call from the assistant."""
      id: str
      type: Literal["function"] = "function"
      function: ToolCallFunction

  class ChatMessage(BaseModel):
      # ... existing fields ...
      tool_calls: list[ToolCall] | None = None  # Only present on assistant messages
  ```
- **GOTCHA**: tool_calls is optional - only assistant messages have it
- **VALIDATE**: `uv run python -c "from app.features.chat.openai_schemas import ChatMessage, ToolCall; print('Schema imports OK')"`

### Task 3: CREATE `app/features/chat/history.py` - History validation and truncation module

- **IMPLEMENT**: Create new module with validation and truncation functions
- **PATTERN**: Mirror structure of other chat feature modules
- **IMPORTS**:
  ```python
  import json
  from app.core.logging import get_logger
  from app.features.chat.openai_schemas import ChatMessage
  ```
- **FUNCTIONS TO IMPLEMENT**:
  1. `validate_tool_call_arguments(messages: list[ChatMessage]) -> None` - Raises ConversationHistoryError if invalid JSON found
  2. `truncate_conversation_history(messages: list[ChatMessage], max_messages: int) -> list[ChatMessage]` - Returns truncated list, keeping most recent
- **ERROR MESSAGE**: "Conversation history contains invalid data (malformed tool call at message {index}). Please start a new conversation in Obsidian Copilot."
- **GOTCHA**: Only validate messages that have tool_calls (assistant messages)
- **VALIDATE**: `uv run python -c "from app.features.chat.history import validate_tool_call_arguments, truncate_conversation_history; print('History module OK')"`

### Task 4: UPDATE `app/shared/vault/exceptions.py` - Add ConversationHistoryError

- **IMPLEMENT**: Add ConversationHistoryError exception class for history validation failures
- **PATTERN**: Follow existing exception pattern (NotFoundError, etc.)
- **IMPORTS**: None additional
- **GOTCHA**: This exception will be caught in openai_routes.py and converted to HTTP 400
- **VALIDATE**: `uv run python -c "from app.shared.vault.exceptions import ConversationHistoryError; print('Exception OK')"`

### Task 5: UPDATE `app/features/chat/openai_routes.py` - Integrate validation and truncation

- **IMPLEMENT**:
  1. Import new functions and exception
  2. After extracting history_messages (line 100), add truncation call
  3. After truncation, add validation call
  4. Add exception handler for ConversationHistoryError → HTTP 400
- **PATTERN**: Follow existing exception handling pattern (lines 71-77)
- **IMPORTS**:
  ```python
  from app.features.chat.history import validate_tool_call_arguments, truncate_conversation_history
  from app.shared.vault.exceptions import ConversationHistoryError
  ```
- **LOCATION**: Insert between lines 100-101 (after history_messages assignment, before convert_to_pydantic_history)
- **GOTCHA**: Apply truncation BEFORE validation (no point validating messages we'll drop)
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_openai_routes.py -v`

### Task 6: UPDATE `app/features/chat/streaming.py` - Enhance error recovery

- **IMPLEMENT**: In the except block (lines 177-199), add specific detection for history parse errors
- **PATTERN**: Existing error handling pattern in generate_sse_stream
- **DETECTION**: Check for `ValueError` with "EOF while parsing" or "Expecting" in the message
- **ERROR MESSAGE**: "Conversation history contains corrupted data. Please start a new conversation in Obsidian Copilot."
- **GOTCHA**: Keep generic error handling for other exceptions
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_streaming.py -v`

### Task 7: CREATE `app/features/chat/tests/test_history.py` - Unit tests for history module

- **IMPLEMENT**: Comprehensive tests for validation and truncation
- **PATTERN**: Follow test_streaming.py patterns
- **TEST CASES**:
  1. `test_validate_tool_call_arguments_valid_json` - Valid JSON passes
  2. `test_validate_tool_call_arguments_invalid_json` - Raises ConversationHistoryError
  3. `test_validate_tool_call_arguments_no_tool_calls` - Messages without tool_calls pass
  4. `test_validate_tool_call_arguments_empty_list` - Empty list passes
  5. `test_truncate_conversation_history_under_limit` - Returns unchanged if under limit
  6. `test_truncate_conversation_history_over_limit` - Truncates oldest messages
  7. `test_truncate_conversation_history_exact_limit` - Edge case at exact limit
  8. `test_truncate_conversation_history_empty` - Empty list returns empty
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_history.py -v`

### Task 8: UPDATE `app/features/chat/tests/test_openai_routes.py` - Add integration tests

- **IMPLEMENT**: Add tests for malformed history handling at the route level
- **PATTERN**: Follow existing route test patterns
- **TEST CASES**:
  1. `test_chat_completions_rejects_malformed_tool_calls` - HTTP 400 with actionable message
  2. `test_chat_completions_truncates_long_history` - History gets truncated
- **VALIDATE**: `uv run pytest app/features/chat/tests/test_openai_routes.py -v`

### Task 9: UPDATE `.env.example` - Document new setting

- **IMPLEMENT**: Add MAX_CONVERSATION_MESSAGES with comment explaining its purpose
- **PATTERN**: Follow existing env var documentation style
- **LOCATION**: After LLM settings section
- **VALIDATE**: `grep MAX_CONVERSATION .env.example`

---

## TESTING STRATEGY

### Unit Tests

**test_history.py** (new file):
- Validation with valid JSON tool calls
- Validation with malformed JSON (various corruption types)
- Validation with empty/missing tool_calls
- Truncation preserving most recent messages
- Truncation edge cases (empty, exact limit, over limit)

### Integration Tests

**test_openai_routes.py** (additions):
- Full request with malformed tool_calls returns HTTP 400
- Error message is actionable (mentions starting new conversation)
- Long history gets truncated before processing

### Edge Cases

1. **Empty tool_calls array**: Should pass validation
2. **Null tool_calls**: Should pass validation (field is optional)
3. **Valid JSON but wrong type**: e.g., arguments is `"123"` (valid JSON string) - should pass (it's valid JSON)
4. **Truncation at exactly max_messages**: Should not truncate
5. **Truncation with max_messages=0**: Should return empty list
6. **Mixed valid/invalid in same request**: Should fail on first invalid

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check app/features/chat/history.py
uv run ruff format app/features/chat/
```

### Level 2: Type Checking

```bash
uv run mypy app/features/chat/history.py
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests

```bash
uv run pytest app/features/chat/tests/test_history.py -v
uv run pytest app/features/chat/tests/ -v
```

### Level 4: Integration Tests

```bash
uv run pytest app/features/chat/tests/test_openai_routes.py -v
uv run pytest -v
```

### Level 5: Manual Validation

```bash
# Start the server
uv run uvicorn app.main:app --port 8123

# Test 1: Valid request should work
curl -s -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}]}'

# Test 2: Request with malformed tool_calls should return 400
curl -s -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi", "tool_calls": [
      {"id": "1", "type": "function", "function": {"name": "test", "arguments": "{invalid json"}}
    ]}
  ]}'
# Expected: HTTP 400 with "invalid data" message
```

---

## ACCEPTANCE CRITERIA

- [ ] Valid conversations work exactly as before (no regression)
- [ ] Malformed tool_calls JSON returns HTTP 400 with actionable message
- [ ] Error message tells user to start a new conversation
- [ ] Conversations over 50 messages are automatically truncated
- [ ] MAX_CONVERSATION_MESSAGES is configurable via environment variable
- [ ] Streaming errors for history parse failures show user-friendly message
- [ ] All validation commands pass with zero errors
- [ ] All existing tests continue to pass
- [ ] New tests cover validation and truncation edge cases

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration): `uv run pytest -v`
- [ ] Type checking passes: `uv run mypy app/ && uv run pyright app/`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

### Design Decisions

1. **Message count vs token count**: Chose message count for simplicity. Token counting requires either API calls (slow, costs money) or inaccurate estimation. 50 messages provides sufficient protection while being simple to implement and understand.

2. **Validation location**: Validating at the API boundary (openai_routes.py) rather than deeper in the stack ensures we fail fast with clear errors before any processing begins.

3. **Exception type**: Created `ConversationHistoryError` as a domain exception rather than reusing `ValueError` to make error handling explicit and allow for different HTTP status codes if needed.

4. **Truncation strategy**: Keep most recent messages, drop oldest. This preserves conversational context while removing potentially stale/corrupted older entries.

### Trade-offs

- **50 message default**: Generous enough for normal conversations, but may need adjustment for specific use cases. Made configurable via env var.
- **No token estimation**: Simpler but less precise. Could add token-based limits later if message count proves insufficient.
- **Fail-fast on first invalid**: Could alternatively skip invalid messages and continue, but failing fast is more predictable and encourages users to fix the root cause.

### Future Enhancements

If needed later:
1. Add token-based limits using Anthropic's count_tokens API
2. Implement conversation summarization for very long conversations
3. Add metrics/alerting for validation failures to track error rates
