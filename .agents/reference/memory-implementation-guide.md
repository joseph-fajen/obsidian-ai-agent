# Jasque Memory Implementation Guide

**Created:** 2026-01-15
**Status:** Phase 1 ready to implement, Phases 2-4 planned
**Related:** `.agents/report/research-report-conversation-memory.md`

---

## Overview

This document captures the phased approach for adding memory capabilities to Jasque. Each phase is self-contained and delivers standalone value. Phases can be implemented incrementally based on interest and need.

### Motivation

- **Learning-driven**: Understanding memory patterns through direct implementation
- **Not pain-driven**: Current stateless model works; memory is "nice to have"
- **Target use cases**: Past decision reference, learned preferences, audit trail

### The Memory Spectrum

```
Simple                                                     Complex
───────────────────────────────────────────────────────────────────►

[Phase 1]           [Phase 2]              [Phase 3]         [Phase 4]
Vault File          Conversation Log       Audit Trail       Extracted Facts
     │                   │                      │                  │
   Static              Append-only          Tool tracking      Structured
   preferences         history              + querying         knowledge
     │                   │                      │                  │
   ~2-3 hours          ~1 day                ~0.5 day           ~2-3 days
```

---

## Phase 1: Vault-Based Preferences

**Goal:** Agent reads user preferences from a markdown file in the vault.

**What You Learn:**
- How agent context is constructed
- File-based configuration pattern
- User-editable preferences with transparency
- Integration with existing VaultManager

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File location | `_jasque/preferences.md` | Visible in vault, underscore convention signals "system" folder |
| File format | YAML frontmatter + markdown | Structured preferences + free-form notes |
| Missing file behavior | Work normally, log warning | Non-blocking, observable |

### File Format Specification

```markdown
---
# Jasque User Preferences
# Edit this file to customize how Jasque behaves

# Date/time formatting preferences
date_format: "YYYY-MM-DD"
time_format: "HH:mm"

# Default locations for different note types
default_folders:
  meeting_notes: "Meetings/"
  daily_notes: "Daily/"
  projects: "Projects/"

# Response style preferences
response_style:
  verbosity: "concise"  # concise | detailed
  use_bullet_points: true
  include_timestamps: false
---

## Additional Context

Any free-form notes you want Jasque to know about. For example:

- I use the PARA method for organizing my vault
- Meeting notes should always include attendees and action items
- I prefer tasks formatted as `- [ ] task @due(date)`
```

### Implementation Plan

#### Step 1: Create preferences schema

**File:** `app/features/chat/preferences.py`

```python
from pydantic import BaseModel

class DefaultFolders(BaseModel):
    meeting_notes: str | None = None
    daily_notes: str | None = None
    projects: str | None = None

class ResponseStyle(BaseModel):
    verbosity: str = "concise"
    use_bullet_points: bool = True
    include_timestamps: bool = False

class UserPreferences(BaseModel):
    """Structured preferences from YAML frontmatter."""
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    default_folders: DefaultFolders = DefaultFolders()
    response_style: ResponseStyle = ResponseStyle()

class VaultPreferences(BaseModel):
    """Complete preferences including free-form context."""
    structured: UserPreferences
    additional_context: str  # Markdown body after frontmatter
```

#### Step 2: Add preferences loading to VaultManager

**File:** `app/shared/vault/manager.py`

Add method:
```python
async def load_preferences(self) -> VaultPreferences | None:
    """Load user preferences from _jasque/preferences.md."""
```

- Use existing `read_note` logic
- Parse YAML frontmatter with `python-frontmatter`
- Return `None` if file doesn't exist (with log warning)
- Validate against `UserPreferences` schema

#### Step 3: Inject preferences into agent context

**File:** `app/core/agents/base.py`

Modify agent creation or system prompt to include preferences:
- Load preferences on agent initialization (or per-request)
- Append structured preferences and additional context to system prompt
- Format as natural language for LLM consumption

#### Step 4: Add tests

**File:** `app/features/chat/tests/test_preferences.py`

- Test YAML parsing with valid frontmatter
- Test missing file behavior
- Test malformed YAML handling
- Test preferences injection into agent context

#### Step 5: Create template file (optional helper)

Consider adding a command or automatic creation of template preferences file when folder exists but file doesn't.

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app/features/chat/preferences.py` | Create | Preferences schemas |
| `app/shared/vault/manager.py` | Modify | Add `load_preferences()` method |
| `app/core/agents/base.py` | Modify | Inject preferences into context |
| `app/features/chat/tests/test_preferences.py` | Create | Unit tests |

### Success Criteria

- [ ] Preferences file is read from `_jasque/preferences.md`
- [ ] Missing file logs warning but doesn't break agent
- [ ] Structured preferences are validated with Pydantic
- [ ] Additional context (markdown body) is captured
- [ ] Agent receives preferences in its context
- [ ] All tests pass

---

## Phase 2: Conversation Logging

**Goal:** Persist conversations to PostgreSQL, enable resumption across sessions.

**What You Learn:**
- Pydantic AI message serialization/deserialization (`ModelMessagesTypeAdapter`)
- Database schema design for chat applications
- The "conversation boundary" problem
- Token management strategies (truncation, summarization)
- Merging server-side history with client-provided history

### Design Decisions (To Be Made)

| Decision | Options | Notes |
|----------|---------|-------|
| Conversation identification | Header, query param, auto-generate | Need to check Obsidian Copilot capabilities |
| History merge strategy | Server-first, client-first, deduplicate | How to handle overlap |
| Retention policy | Forever, N days, user-controlled | Storage and privacy implications |
| Token limits | Fixed cap, sliding window, summarize | Cost control |

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
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'tool_call', 'tool_result'
    content TEXT NOT NULL,
    pydantic_message JSONB,     -- Full Pydantic AI message for reconstruction
    token_count INTEGER,
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(conversation_id, sequence_number)
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, sequence_number);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);
```

### Implementation Plan (High-Level)

1. **Create database models** - SQLAlchemy models for conversations and messages
2. **Create repository layer** - CRUD operations for conversations/messages
3. **Add serialization utilities** - Convert between Pydantic AI and DB formats
4. **Modify chat routes** - Accept conversation ID, load/save history
5. **Add conversation management endpoints** - List, delete, rename conversations
6. **Implement token management** - Truncation or summarization strategy
7. **Add migration** - Alembic migration for new tables
8. **Add tests** - Unit and integration tests

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `app/features/chat/models.py` | Create | SQLAlchemy models |
| `app/features/chat/repository.py` | Create | Database operations |
| `app/features/chat/memory.py` | Create | History loading/saving logic |
| `app/features/chat/openai_routes.py` | Modify | Conversation ID handling |
| `app/features/chat/conversation_routes.py` | Create | Conversation management API |
| `alembic/versions/xxx_add_conversations.py` | Create | Database migration |

### Open Questions

- Does Obsidian Copilot support custom headers for conversation ID?
- How should we handle the first message of a new conversation (auto-title)?
- What's the right token limit before truncation?

---

## Phase 3: Audit Trail

**Goal:** Track tool calls and their effects for accountability and debugging.

**What You Learn:**
- Tool call representation in Pydantic AI message format
- Structured logging for agent actions
- Querying historical agent behavior
- Building on Phase 2's conversation storage

### Design Decisions (To Be Made)

| Decision | Options | Notes |
|----------|---------|-------|
| Storage granularity | Per-tool-call, per-conversation, both | Affects query patterns |
| What to capture | Tool name + args, results, timing | Balance detail vs storage |
| Queryable fields | Tool name, operation, affected paths | Index design |

### Schema Extension (Draft)

```sql
-- Extends Phase 2 schema
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(50),
    arguments JSONB NOT NULL,
    result JSONB,
    affected_paths TEXT[],  -- Vault paths that were read/modified
    duration_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tool_calls_conversation ON tool_calls(conversation_id, created_at);
CREATE INDEX idx_tool_calls_tool ON tool_calls(tool_name, operation);
CREATE INDEX idx_tool_calls_paths ON tool_calls USING GIN(affected_paths);
```

### Implementation Plan (High-Level)

1. **Extend message storage** - Capture tool calls from Pydantic AI messages
2. **Create tool_calls table** - Migration and model
3. **Add extraction logic** - Parse tool calls from message history
4. **Create audit query API** - Endpoints to query tool history
5. **Add tests**

### Query Examples

```sql
-- What did Jasque do to my vault today?
SELECT tool_name, operation, affected_paths, created_at
FROM tool_calls
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;

-- What notes were modified?
SELECT DISTINCT unnest(affected_paths) as path
FROM tool_calls
WHERE tool_name = 'obsidian_manage_notes'
  AND operation IN ('create', 'update', 'delete');
```

---

## Phase 4: Extracted Facts

**Goal:** Use LLM to extract and store structured knowledge from conversations.

**What You Learn:**
- LLM-as-extractor pattern (using the agent to analyze its own conversations)
- Structured output with Pydantic AI
- Knowledge representation tradeoffs
- Retrieval and injection of relevant facts
- When to extract vs when to store raw history

### Design Decisions (To Be Made)

| Decision | Options | Notes |
|----------|---------|-------|
| Extraction trigger | End of conversation, periodic, on-demand | When to run extraction |
| Fact types | Preferences, decisions, entities, events | What to extract |
| Storage format | Flat table, graph, hybrid | Query pattern implications |
| Retrieval strategy | Always inject all, semantic search, rule-based | Context window management |

### Fact Types to Consider

| Type | Example | Use Case |
|------|---------|----------|
| **Preference** | "User prefers YYYY-MM-DD date format" | Customize responses |
| **Decision** | "Decided to organize projects in Projects/ folder" | Reference past choices |
| **Entity** | "Project Alpha is the Q1 initiative" | Understand references |
| **Relationship** | "Sarah is the project lead for Alpha" | Context enrichment |

### Schema (Draft)

```sql
CREATE TABLE extracted_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    fact_type VARCHAR(50) NOT NULL,  -- preference, decision, entity, relationship
    subject VARCHAR(255),
    predicate VARCHAR(255),
    object TEXT,
    confidence FLOAT,
    source_message_id UUID REFERENCES messages(id),
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,  -- NULL means still valid
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_facts_type ON extracted_facts(fact_type);
CREATE INDEX idx_facts_subject ON extracted_facts(subject);
```

### Extraction Prompt Pattern

```python
EXTRACTION_PROMPT = """
Analyze this conversation and extract any facts worth remembering.

Focus on:
- User preferences (how they like things done)
- Decisions made (choices about organization, naming, etc.)
- Important entities mentioned (projects, people, concepts)

For each fact, provide:
- type: preference | decision | entity | relationship
- subject: what/who the fact is about
- predicate: the relationship or attribute
- object: the value or target
- confidence: 0.0-1.0 how certain you are

Conversation:
{conversation}

Return as JSON array of facts.
"""
```

### Implementation Plan (High-Level)

1. **Design fact schema** - Finalize what to extract and how to store
2. **Create extraction prompt** - Prompt engineering for reliable extraction
3. **Build extraction pipeline** - Run extraction on conversation end
4. **Create facts table** - Migration and model
5. **Implement retrieval** - Query relevant facts for new conversations
6. **Inject into context** - Add retrieved facts to agent prompt
7. **Add fact management** - View, edit, delete extracted facts
8. **Add tests**

---

## Implementation Order

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
  │            │            │           │
  │            │            │           └── Optional: Advanced learning
  │            │            │
  │            │            └── Requires Phase 2 (uses conversation storage)
  │            │
  │            └── Standalone (but more valuable with Phase 1 preferences)
  │
  └── Standalone (start here)
```

**Dependencies:**
- Phase 1: No dependencies
- Phase 2: No strict dependencies (Phase 1 enhances but not required)
- Phase 3: Requires Phase 2 (extends conversation storage)
- Phase 4: Requires Phase 2 (analyzes stored conversations)

---

## Reference: Key Concepts

### Agent Context Model

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT CONTEXT                            │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ System Prompt   │  │ Retrieved       │  │ Conversation│ │
│  │ (static)        │  │ Memory          │  │ History     │ │
│  │                 │  │ (dynamic)       │  │ (session)   │ │
│  │ "You are       │  │ Phase 1: prefs  │  │ Recent      │ │
│  │  Jasque..."    │  │ Phase 4: facts  │  │ messages    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│              ↓ All injected into LLM prompt ↓               │
└─────────────────────────────────────────────────────────────┘
```

### Pydantic AI Message Serialization

```python
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

# Serialize for database storage
history = result.all_messages()
json_data = to_jsonable_python(history)

# Deserialize for reuse
restored = ModelMessagesTypeAdapter.validate_python(json_data)
result = agent.run("next message", message_history=restored)
```

### Token Management Strategies

| Strategy | Approach | Tradeoff |
|----------|----------|----------|
| **Truncation** | Keep last N messages | Loses old context |
| **Sliding window** | Keep last N tokens | More precise, complex |
| **Summarization** | LLM summarizes old messages | Preserves meaning, costs tokens |
| **Hybrid** | Summarize old + keep recent | Best of both, most complex |

---

## Progress Tracking

### Phase 1: Vault-Based Preferences
- [x] Design decisions made (B, B, B)
- [ ] Implementation started
- [ ] Schema created
- [ ] VaultManager method added
- [ ] Agent integration complete
- [ ] Tests passing
- [ ] Documentation updated

### Phase 2: Conversation Logging
- [ ] Design decisions made
- [ ] Implementation started
- [ ] Database schema created
- [ ] Migration applied
- [ ] Routes updated
- [ ] Tests passing

### Phase 3: Audit Trail
- [ ] Design decisions made
- [ ] Implementation started
- [ ] Schema extension created
- [ ] Query API implemented
- [ ] Tests passing

### Phase 4: Extracted Facts
- [ ] Design decisions made
- [ ] Implementation started
- [ ] Extraction pipeline built
- [ ] Retrieval implemented
- [ ] Tests passing

---

## Related Documents

- Research report: `.agents/report/research-report-conversation-memory.md`
- PRD (memory in MVP scope): `.agents/reference/PRD.md` (line 158)
- Tool designs: `.agents/reference/mvp-tool-designs.md`
- Current state: `CURRENT_STATE.md`
