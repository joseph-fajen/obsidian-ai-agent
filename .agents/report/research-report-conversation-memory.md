# Conversation Memory Research Report

**Date:** 2026-01-15
**Purpose:** Research conversation memory patterns for Jasque, identify implementation approaches, and surface key architectural questions.

---

## Executive Summary

Conversation memory for Jasque involves persisting message history across sessions so the agent can "remember" previous interactions. This research identifies **three distinct memory scopes** with different complexity levels, surfaces **12 senior-level architectural questions**, and recommends a phased approach starting with the simplest option.

---

## Part 1: Pydantic AI Message History Mechanics

### Current Implementation

Jasque currently uses **stateless, in-request history** passed by the client:

```
┌─────────────────────────────────────────────────────┐
│ Obsidian Copilot                                    │
│  ┌─────────────────────────────────────────────────┤
│  │ Request Body                                    │
│  │  messages: [                                    │
│  │    {role: "user", content: "msg 1"},           │
│  │    {role: "assistant", content: "response 1"}, │
│  │    {role: "user", content: "msg 2"}  ← current │
│  │  ]                                              │
│  └─────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ Jasque (openai_routes.py)                           │
│  1. Extract history_messages (all but last)        │
│  2. Convert to Pydantic AI format                  │
│  3. Pass to agent.run(message_history=...)         │
│  4. Agent sees full context                        │
└─────────────────────────────────────────────────────┘
```

**Key insight:** The client (Obsidian Copilot) maintains history during a session. Jasque is stateless—it receives the full history in each request and forgets everything when the request completes.

### Pydantic AI Persistence Pattern

Pydantic AI provides `ModelMessagesTypeAdapter` for serialization:

```python
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

# After a run, extract messages
history = result.all_messages()

# Serialize to JSON-compatible format (for database storage)
as_json = to_jsonable_python(history)

# Reconstruct later
same_history = ModelMessagesTypeAdapter.validate_python(as_json)

# Use in new run
result2 = agent.run("next message", message_history=same_history)
```

**Important:** Messages are model-agnostic. History from Claude can be reused with Gemini.

### History Processors

Pydantic AI supports intercepting history before model calls:

```python
def trim_old_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep only last N messages to control token usage."""
    return messages[-10:]  # Keep last 10

agent = Agent(history_processors=[trim_old_messages])
```

Use cases: token management, privacy filtering, summarization.

---

## Part 2: Memory Scope Options

### Option A: Session Memory (Simplest)

**Scope:** Within a single Obsidian Copilot session (until window close/refresh)

**How it works today:** Client already handles this! Obsidian Copilot maintains message history and sends it with each request. No server-side changes needed.

**What's missing:** Nothing—this already works. When user refreshes Obsidian or restarts the plugin, history is lost (expected behavior for a "session").

### Option B: Conversation Persistence (Medium)

**Scope:** Named conversations that survive application restart

**Implementation:** Store conversations in PostgreSQL with a conversation ID.

```
┌──────────────────────────────────────────────────────┐
│ conversations table                                  │
├──────────────────────────────────────────────────────┤
│ id (uuid), title, created_at, updated_at, metadata  │
└──────────────────────────────────────────────────────┘
                         │
                         │ 1:N
                         ▼
┌──────────────────────────────────────────────────────┐
│ messages table                                       │
├──────────────────────────────────────────────────────┤
│ id, conversation_id, role, content, created_at,     │
│ token_count, model_used                             │
└──────────────────────────────────────────────────────┘
```

**API change required:** Need a way to specify conversation_id. Options:
1. Custom header: `X-Conversation-Id`
2. Extended request body (breaks OpenAI compatibility)
3. Query parameter: `/v1/chat/completions?conversation_id=xxx`

**Challenge:** Obsidian Copilot uses standard OpenAI SDK—may not support custom headers easily.

### Option C: Long-Term Memory (Complex)

**Scope:** Cross-conversation knowledge that persists indefinitely

**Components:**
- **Episodic memory:** Full conversation history (what Option B provides)
- **Semantic memory:** Extracted facts, user preferences, vault patterns
- **Procedural memory:** Learned behaviors (e.g., "user prefers daily notes in YYYY-MM-DD format")

**Implementation:** Requires additional infrastructure:
- Vector database for semantic search
- Extraction pipeline to identify memorable facts
- Retrieval system to inject relevant memories into context

---

## Part 3: Senior-Level Architectural Questions

These are questions a senior engineer would ask before implementing memory. Less experienced engineers often jump straight to implementation without considering these implications.

### 1. Scope & Identity

| Question | Why It Matters |
|----------|----------------|
| **Who is the memory for—user, vault, or agent instance?** | Single-user vs multi-user deployment model. Jasque currently assumes single-user (one vault per instance). |
| **How do you identify a "conversation" in a stateless API?** | OpenAI API has no session concept. Conversation boundaries are ambiguous. |
| **Should Jasque remember across vaults if user switches?** | Affects data model design. |

### 2. Protocol Compatibility

| Question | Why It Matters |
|----------|----------------|
| **How do you inject server-side memory into a stateless protocol?** | Client sends history; if server also has history, you get duplication or conflicts. |
| **Should memory supplement or replace client-provided history?** | Merge strategies are complex and error-prone. |
| **Does Obsidian Copilot support conversation IDs or custom headers?** | Determines implementation feasibility without client changes. |

### 3. Data Lifecycle

| Question | Why It Matters |
|----------|----------------|
| **What's the retention policy?** | Disk space, privacy, GDPR considerations. |
| **How do you handle history from deleted notes?** | Memory may reference content that no longer exists. |
| **Can users delete their memory?** | Privacy control, "right to be forgotten". |

### 4. Performance & Cost

| Question | Why It Matters |
|----------|----------------|
| **How do you prevent unbounded token growth?** | Long conversations become expensive. Need truncation/summarization strategy. |
| **What's the query pattern?** | Recent messages vs semantic search vs full history affects database design. |
| **How does memory retrieval latency impact response time?** | Adding DB queries to every request adds latency. |

### 5. Consistency & Correctness

| Question | Why It Matters |
|----------|----------------|
| **How do you handle tool results in history?** | Tool calls create complex message structures (request → tool_call → tool_result → response). |
| **What happens if memory contradicts vault state?** | Agent might "remember" a note that was deleted, or remember old content. |
| **How do you version or migrate stored messages?** | Pydantic AI message format may change between versions. |

### 6. User Experience

| Question | Why It Matters |
|----------|----------------|
| **How does user know what's remembered?** | Transparency builds trust. Hidden memory can be confusing. |
| **Can user start a "fresh" conversation?** | Sometimes you don't want prior context influencing responses. |

---

## Part 4: Memory Patterns from Industry Research

### Pattern 1: MemGPT / Operating System Model

**Approach:** Treat memory like OS paging—automatic writeback of working memory to long-term storage.

```
┌─────────────────────────────────────────────────┐
│ Context Window (Working Memory)                 │
│  - System prompt                                │
│  - Recent messages                              │
│  - Retrieved memories                           │
└─────────────────────────────────────────────────┘
         ▲                    │
         │ retrieve           │ archive
         │                    ▼
┌─────────────────────────────────────────────────┐
│ External Storage                                │
│  - Recall: Full conversation logs               │
│  - Archival: Vector DB for semantic search     │
└─────────────────────────────────────────────────┘
```

**Fit for Jasque:** Overkill for MVP. This pattern suits autonomous agents with long-running tasks.

### Pattern 2: OpenAI's Saved Facts Model

**Approach:** Extract and store discrete facts from conversations, retrieve relevant ones per request.

```
User: "I always put meeting notes in the Meetings folder"
      ↓ extraction
Fact: {type: "preference", key: "meeting_notes_location", value: "Meetings/"}
      ↓ stored
[Later, when user says "save the meeting notes":]
      ↓ retrieval
Agent sees: "User preference: meeting notes go in Meetings/ folder"
```

**Fit for Jasque:** Good for Phase 2. Requires extraction logic and retrieval pipeline.

### Pattern 3: Simple Conversation Log (LangGraph + MongoDB pattern)

**Approach:** Store full conversation history, load recent turns on session start.

```
┌─────────────────────────────────────────────────┐
│ On Request:                                     │
│  1. Check for conversation_id header            │
│  2. If found, load last N messages from DB      │
│  3. Prepend to client-provided history          │
│  4. Run agent                                   │
│  5. Save new messages to DB                     │
│  6. Return response                             │
└─────────────────────────────────────────────────┘
```

**Fit for Jasque:** Most appropriate for initial implementation. Aligns with PRD scope.

---

## Part 5: Recommended Approach

### Phase 1: Validate the Need (Now)

Before building anything, answer:

1. **Does the current stateless model actually cause problems?**
   - Obsidian Copilot already maintains session history
   - Are users actually losing context in practice?

2. **What specific use cases require persistence?**
   - Resume conversation after Obsidian restart?
   - Reference yesterday's conversation?
   - Agent learns user preferences over time?

3. **Can we test with manual workarounds first?**
   - User could say "As I mentioned before, I keep notes in YYYY-MM-DD format"
   - Does this reveal what memory would actually help with?

### Phase 2: Simple Conversation Persistence (If Validated)

**Scope:** Store conversations, allow resumption via conversation ID.

**Implementation:**
1. Add `conversations` and `messages` tables
2. Accept optional `X-Conversation-Id` header
3. On request: load history from DB, merge with client history
4. On response: save new messages to DB
5. Add cleanup/retention policy

**Questions to answer first:**
- Does Obsidian Copilot allow custom headers?
- How do we surface conversation management in UI?

### Phase 3: Smart Memory (Future)

**Scope:** Extract and retrieve relevant facts/preferences.

**Requires:**
- Vector database integration
- Extraction prompt/logic
- Retrieval ranking
- Memory management UI

---

## Part 6: Integration Points in Current Codebase

### Where Memory Would Hook In

```
app/features/chat/openai_routes.py:
  ├── Line 58-64: Extract deps and user message
  │   └── HERE: Load memory if conversation_id provided
  │
  ├── Line 76-83: Build message_history
  │   └── HERE: Merge DB history with client history
  │
  ├── Line 117: agent.run() / Line 99: generate_sse_stream()
  │   └── Uses message_history
  │
  └── Line 136-146: Return response
      └── HERE: Save messages to DB
```

### New Files Needed (Phase 2)

```
app/features/chat/
├── models.py        # Conversation, Message SQLAlchemy models
├── repository.py    # DB queries for conversation/message CRUD
├── memory.py        # Memory loading/saving logic
└── routes updated   # Add conversation_id handling
```

### Database Schema (Draft)

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    pydantic_message JSONB,     -- Full Pydantic AI message format
    token_count INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(conversation_id, sequence_number)
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, sequence_number);
```

---

## Summary: Key Questions Before Implementation

### Must Answer

1. **Is memory actually needed?** Current stateless model may be sufficient for most use cases.
2. **What's the conversation boundary?** How do we know when one conversation ends and another begins?
3. **How do we identify conversations?** Need a mechanism compatible with OpenAI protocol.
4. **What's the retention policy?** Forever? 30 days? User-controlled?

### Should Consider

5. **How do we handle token growth?** Summarization? Truncation? Both?
6. **How do we merge server memory with client history?** Deduplication strategy.
7. **What about tool call history?** Tool results can be large; store full or summarized?

### Nice to Understand

8. **Can we make memory optional?** Some conversations shouldn't be remembered.
9. **How do we expose memory to users?** They should know what's stored.
10. **What about multi-model history?** Claude history used with Gemini later?

---

## Sources

- [Pydantic AI Message History Documentation](https://ai.pydantic.dev/message-history/)
- [Pydantic AI GitHub Issue #530 - Persist Messages in External Stores](https://github.com/pydantic/pydantic-ai/issues/530)
- [Design Patterns for Long-Term Memory in LLM-Powered Architectures](https://serokell.io/blog/design-patterns-for-long-term-memory-in-llm-powered-architectures)
- [MongoDB + LangGraph Long-Term Memory Integration](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph)
- [Unlock Your AI's Memory: Pydantic-AI Agents & MongoDB](https://learnitnow.medium.com/unlock-your-ais-memory-a-practical-guide-to-pydantic-ai-agents-mongodb-09476ddc2963)
- [A-MEM: Agentic Memory for LLM Agents (arXiv 2502.12110)](https://arxiv.org/abs/2502.12110)
- [Agent Memory: How to Build Agents that Learn and Remember (Letta)](https://www.letta.com/blog/agent-memory)
- [Building AI Agents That Actually Remember (Medium)](https://medium.com/@nomannayeem/building-ai-agents-that-actually-remember-a-developers-guide-to-memory-management-in-2025-062fd0be80a1)
