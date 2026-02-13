# About Jasque

**Jasque** is a custom AI agent for Obsidian vault management through natural language. It provides capabilities that go beyond what you can do with Obsidian Copilot and a standard LLM provider like OpenAI.

This document explains what Jasque is, why it exists, and the value it provides.

**MVP Status:** February 2026 - All 3 tools implemented and tested with 333 unit tests.

---

## What Problem Does Jasque Solve?

Obsidian Copilot is a popular plugin that lets you chat with an AI inside Obsidian. When connected to OpenAI (or another LLM provider), it can answer questions and have conversations.

But there's a fundamental limitation: **OpenAI is just a brain in a jar.**

It can only work with what you send it. It has no hands, no eyes into your files, no ability to take action. It's read-only.

### Retrieval vs. Agency

| Approach | What Happens | Limitations |
|----------|--------------|-------------|
| **Retrieval** (Copilot + OpenAI) | Copilot searches your vault, copies text, sends it to OpenAI, OpenAI responds | Read-only. Cannot create, edit, delete, or organize. |
| **Agency** (Copilot + Jasque) | Jasque's agent decides what to do, then executes actions on your vault | Read AND write. Full vault management. |

**Jasque is an agent with hands, not just a brain.** It can think *and* act on your vault.

---

## What Can Jasque Do?

Jasque provides 3 tools with 19 total operations:

### Tool 1: `obsidian_manage_notes` - Note Lifecycle

| Operation | What It Does |
|-----------|--------------|
| `read` | Read note content |
| `create` | Create new notes |
| `update` | Replace note content |
| `append` | Add content to existing notes |
| `delete` | Delete notes |
| `complete_task` | Check off task checkboxes |

### Tool 2: `obsidian_query_vault` - Search & Discovery

| Operation | What It Does |
|-----------|--------------|
| `search_text` | Full-text search across vault |
| `find_by_name` | Find notes by filename (wikilink resolution) |
| `find_by_tag` | Find notes with specific tags |
| `list_notes` | List notes in a folder |
| `list_folders` | List subfolders |
| `get_backlinks` | Find notes linking to a note |
| `get_tags` | List all tags in vault |
| `list_tasks` | Find incomplete tasks |

### Tool 3: `obsidian_manage_structure` - Organization

| Operation | What It Does |
|-----------|--------------|
| `create_folder` | Create new folders |
| `rename` | Rename files or folders |
| `delete_folder` | Delete empty folders |
| `move` | Move files or folders |
| `list_structure` | Show folder tree |

---

## Concrete Examples

| You Say | OpenAI + Copilot | Jasque |
|---------|------------------|--------|
| "Create a note about today's meeting" | "I can't create files" | Creates the note in your vault |
| "Mark 'Buy groceries' as done" | "I can't modify files" | Finds the task, checks the checkbox |
| "Move all #archive notes to Archive/" | "I can't move files" | Moves every matching file |
| "Delete the meeting notes from last week" | "I can't delete files" | Deletes the files |
| "Rename 'Projects' folder to 'Active'" | "I can't rename folders" | Renames the folder |
| "What tasks do I have outstanding?" | Works (if Copilot sends context) | Works (searches locally) |

---

## How Does It Work?

Jasque sits between Obsidian Copilot and the LLM (Claude, Gemini, etc.):

```
You type in Obsidian
        │
        ▼
┌───────────────────┐
│ Obsidian Copilot  │  "Create a note about Python"
│    (plugin)       │
└───────────────────┘
        │ HTTP request to localhost:8123
        ▼
┌───────────────────┐
│   Jasque API      │  Receives request
│  (your server)    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Pydantic AI      │  Agent thinks: "I should create a note"
│    Agent          │  Decides to call obsidian_manage_notes
└───────────────────┘
        │
        ├──────────────────────────┐
        ▼                          ▼
┌───────────────────┐      ┌───────────────────┐
│   VaultManager    │      │   Claude/Gemini   │
│ (creates the .md  │      │   (decides what   │
│  file locally)    │      │    to write)      │
└───────────────────┘      └───────────────────┘
        │                          │
        └──────────┬───────────────┘
                   ▼
           Response streams back
                   │
                   ▼
        You see the result in Obsidian
```

### Why "OpenAI-Compatible API"?

Obsidian Copilot was designed to talk to OpenAI. It sends messages in OpenAI's format and expects responses in OpenAI's format.

Jasque **speaks the same language** - it implements the same API that OpenAI uses (`/v1/chat/completions`). This lets us:

1. **Use an existing plugin** - No need to build a custom Obsidian plugin
2. **Add capabilities** - Jasque adds tools that OpenAI doesn't have
3. **Swap in any LLM** - Claude, Gemini, or OpenAI can power the agent

---

## Privacy Benefits

With **Copilot + OpenAI directly:**
- Your note content is sent to OpenAI's servers
- OpenAI processes and stores your data per their policies

With **Jasque:**
- Only your *question* goes to the LLM provider
- The LLM says "search for X" → Jasque searches locally → results stay local
- Your actual vault files never leave your machine
- The LLM only sees what the agent chooses to include in its response

---

## Technical Requirements

Jasque runs as a local server alongside Obsidian:

- **Python 3.12+**
- **PostgreSQL** (for future features)
- **Docker** (recommended) or direct execution
- **LLM API key** (Anthropic, Google, or OpenAI)

Your Obsidian vault is mounted into the Jasque container, giving the agent sandboxed access to read and write files.

---

## Current Status (MVP + Phase 1)

As of February 2026:

| Component | Status |
|-----------|--------|
| All 3 tools (19 operations) | Complete |
| OpenAI-compatible API | Complete |
| Streaming responses | Complete |
| Multi-LLM support | Complete (Claude, Gemini, OpenAI) |
| Vault-based preferences | Complete (`_jasque/preferences.md`) |
| Conversation resilience | Complete (validation + truncation) |
| Folder exclusion | Complete (noise reduction from system folders) |
| Unit tests | 333 passing |
| Obsidian Copilot integration | Verified |
| Datadog LLM Observability | Available (optional) |

### Future Possibilities

- Chat history persistence (PostgreSQL)
- Embeddings API for semantic search
- Additional vault operations

---

## Learn More

- [Architecture Layers](./architecture-layers.md) - Technical deep-dive into Jasque's infrastructure
- [README](../README.md) - Quick start guide
- [PRD](../.agents/reference/PRD.md) - Full product requirements
