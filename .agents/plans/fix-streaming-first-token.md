# Fix Missing First Token in Streaming

## Problem Summary

Jasque drops the first word/token when streaming responses to Obsidian Copilot. The root cause is that our streaming implementation only handles `PartDeltaEvent` but misses the initial text content embedded in `PartStartEvent`.

**Evidence:** Screenshot shows response starting with `"!"` instead of `"Hello!"` or `"Hi!"`.

## Root Cause

From Pydantic AI documentation, the streaming event sequence is:

```
PartStartEvent(part=TextPart(content='It will be '))  <- Initial text HERE
PartDeltaEvent(delta=TextPartDelta(content_delta='warm and sunny '))
PartDeltaEvent(delta=TextPartDelta(content_delta='in Paris on '))
```

**Our code only handles `PartDeltaEvent`, missing the `PartStartEvent` content.**

---

## Files to Modify

| File | Purpose |
|------|---------|
| `app/features/chat/streaming.py` | Add `PartStartEvent` handling |
| `.agents/report/research-report-pydantic-ai-streaming-sse.md` | Correct the streaming pattern documentation |

---

## Implementation Plan

### Task 1: Update Research Report

**File:** `.agents/report/research-report-pydantic-ai-streaming-sse.md`

**Change:** Update the event handling table (around line 72) from:

```markdown
| Event | When to Yield |
|-------|---------------|
| `PartStartEvent` | Skip (just marks start) |
| `PartDeltaEvent` with `TextPartDelta` | **Yield `event.delta.content_delta`** |
```

**To:**

```markdown
| Event | When to Yield |
|-------|---------------|
| `PartStartEvent` with `TextPart` | **Yield `event.part.content`** (contains initial text!) |
| `PartDeltaEvent` with `TextPartDelta` | **Yield `event.delta.content_delta`** |
```

**Also update:** The code examples in Part 3 to show the correct pattern.

### Task 2: Fix streaming.py Implementation

**File:** `app/features/chat/streaming.py`

**Current code (lines 138-150):**
```python
async for event in stream:
    if isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            content = event.delta.content_delta
            # ... yield content
```

**Updated code:**
```python
async for event in stream:
    if isinstance(event, PartStartEvent):
        if isinstance(event.part, TextPart) and event.part.content:
            content = event.part.content
            total_content += content
            # yield SSE chunk with content
    elif isinstance(event, PartDeltaEvent):
        if isinstance(event.delta, TextPartDelta):
            content = event.delta.content_delta
            total_content += content
            # yield SSE chunk with content
```

**Required imports to add:**
```python
from pydantic_ai.messages import (
    # ... existing imports ...
    PartStartEvent,  # ADD
    TextPart,        # ADD
)
```

### Task 3: Add/Update Tests

**File:** `app/features/chat/tests/test_streaming.py`

Add test case to verify `PartStartEvent` handling:
- Mock agent that emits `PartStartEvent` with initial `TextPart` content
- Verify the initial content appears in the SSE stream

---

## Verification

### Manual Test

1. Start Jasque API: `uv run uvicorn app.main:app --reload --port 8123`
2. Open Obsidian with Copilot configured to use Jasque
3. Send a message like "Hello, which agent am I chatting with?"
4. **Verify:** Response starts with complete first word (e.g., "Hello" or "Hi"), not just punctuation

### Automated Test

```bash
uv run pytest app/features/chat/tests/test_streaming.py -v -k "part_start"
```

### Full Validation

```bash
uv run ruff check app/features/chat/
uv run mypy app/features/chat/
uv run pyright app/features/chat/
uv run pytest app/features/chat/tests/ -v
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing streaming | Existing tests + manual verification |
| Empty `PartStartEvent.part.content` | Check for truthy content before yielding |
| Type errors from new imports | Run mypy/pyright validation |

---

## Checklist

- [ ] Update research report with correct streaming pattern
- [ ] Add `PartStartEvent` and `TextPart` imports to streaming.py
- [ ] Add `PartStartEvent` handling in `generate_sse_stream()`
- [ ] Add test case for `PartStartEvent` handling
- [ ] Run full validation (ruff, mypy, pyright, pytest)
- [ ] Manual test with Obsidian Copilot
- [ ] Verify first token is no longer dropped

---

## References

- [Pydantic AI Agents - Streaming](https://ai.pydantic.dev/agents/)
- [GitHub Issue #2428 - Missing Tokens](https://github.com/pydantic/pydantic-ai/issues/2428)
- [Pydantic AI API - Messages](https://ai.pydantic.dev/api/messages/)
