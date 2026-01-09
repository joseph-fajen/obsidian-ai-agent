# Pydantic AI Streaming & OpenAI-Compatible SSE Research Report

**Date:** 2026-01-07
**Purpose:** Research how to implement OpenAI-compatible streaming responses using Pydantic AI's `agent.iter()` and FastAPI SSE.

---

## Part 1: Pydantic AI `agent.iter()` Deep Dive

### Core Mechanism

`agent.iter()` is a **context manager** that returns an `AgentRun` object for iterating over the agent's execution graph node-by-node.

```python
async with agent.iter('user prompt', deps=deps) as agent_run:
    async for node in agent_run:
        # Process each node
```

### Execution Node Types

The iteration yields different node types:

| Node Type | Description | Streamable? |
|-----------|-------------|-------------|
| `UserPromptNode` | Initial user input | No |
| `ModelRequestNode` | Model API call | **Yes** - via `node.stream()` |
| `CallToolsNode` | Tool execution | Yes - via `node.stream()` |
| `End` | Final completion | No |

### Streaming Text from Nodes

For `ModelRequestNode`, call `.stream()` to access streaming events:

```python
from pydantic_ai.messages import (
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)

async with agent.iter(user_prompt, deps=deps) as run:
    async for node in run:
        if Agent.is_model_request_node(node):
            async with node.stream(run.ctx) as request_stream:
                async for event in request_stream:
                    if isinstance(event, PartStartEvent):
                        # IMPORTANT: Initial text content is in PartStartEvent!
                        if isinstance(event.part, TextPart) and event.part.content:
                            yield event.part.content
                    elif isinstance(event, PartDeltaEvent):
                        if isinstance(event.delta, TextPartDelta):
                            # Extract text delta
                            text_chunk = event.delta.content_delta
                            yield text_chunk
```

### Event Types for Text Extraction

```python
from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)
```

| Event | When to Yield |
|-------|---------------|
| `PartStartEvent` with `TextPart` | **Yield `event.part.content`** (contains initial text!) |
| `PartDeltaEvent` with `TextPartDelta` | **Yield `event.delta.content_delta`** |
| `PartDeltaEvent` with `ThinkingPartDelta` | Skip (internal reasoning) |
| `PartDeltaEvent` with `ToolCallPartDelta` | Skip (tool invocation) |
| `FinalResultEvent` | May signal completion |

**IMPORTANT:** The `PartStartEvent` may contain the initial text content in `event.part.content`. If you only handle `PartDeltaEvent`, you will miss the first token(s) of the response. Always check `PartStartEvent` for `TextPart` content first.

### Message History Handling

Pydantic AI uses its own message format, not OpenAI's directly.

**Pydantic AI Message Structure:**
```python
from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

# Creating message history programmatically
history = []
history.append(ModelRequest(parts=[UserPromptPart(content="User question")]))
history.append(ModelResponse(parts=[TextPart(content="Assistant answer")]))

# Pass to agent
async with agent.iter(new_prompt, message_history=history, deps=deps) as run:
    ...
```

**Converting OpenAI Messages to Pydantic AI:**
```python
def openai_to_pydantic_history(openai_messages: list[dict]) -> list[ModelMessage]:
    """Convert OpenAI format messages to Pydantic AI format."""
    history = []
    for msg in openai_messages:
        role = msg["role"]
        content = normalize_content(msg["content"])  # Handle string or array

        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
        elif role == "system":
            # System prompts go in the first ModelRequest
            pass  # Handle separately or prepend to first user message
    return history
```

### Token Usage Tracking

```python
# During streaming - call anytime
usage = agent_run.usage()
# Returns: RunUsage(input_tokens=57, output_tokens=8, requests=1)

# After completion
result = agent_run.result
usage = result.usage()
```

**RunUsage Fields:**
- `input_tokens`: Prompt tokens
- `output_tokens`: Completion tokens (alias: `response_tokens`)
- `requests`: Number of API calls
- `total_tokens`: Property returning `input_tokens + output_tokens`

---

## Part 2: OpenAI Streaming Chunk Format

### Chunk Structure (ChatCompletionChunk)

From [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat):

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion.chunk",
  "created": 1694268190,
  "model": "gpt-4o-mini",
  "system_fingerprint": "fp_44709d6fcb",
  "choices": [{
    "index": 0,
    "delta": {
      "content": "Hello"
    },
    "logprobs": null,
    "finish_reason": null
  }]
}
```

### Delta Progression

| Chunk # | Delta Content | finish_reason |
|---------|---------------|---------------|
| First | `{"role": "assistant"}` | `null` |
| Middle | `{"content": "text..."}` | `null` |
| Last | `{}` or `{"content": ""}` | `"stop"` |
| Usage (optional) | Empty choices | `null` (includes `usage`) |

### Required vs Optional Fields

**Required:**
- `id`: Unique identifier (same across all chunks)
- `object`: Always `"chat.completion.chunk"`
- `created`: Unix timestamp
- `model`: Model name
- `choices`: Array with at least one choice

**Per Choice (Required):**
- `index`: Choice index (usually 0)
- `delta`: Object containing incremental content
- `finish_reason`: `null` until final chunk, then `"stop"`, `"length"`, `"tool_calls"`, etc.

**Optional:**
- `usage`: Token counts (only if `stream_options: {"include_usage": true}`)

### SSE Wire Format

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"jasque","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"jasque","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1694268190,"model":"jasque","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]

```

**Critical formatting:**
- Each chunk prefixed with `data: `
- Double newline (`\n\n`) after each chunk
- Final `data: [DONE]` signals end of stream

### How Obsidian Copilot Processes Chunks

From `ChatOpenRouter.ts`:

```typescript
for await (const rawChunk of stream as AsyncIterable<OpenRouterChatChunk>) {
    // Extract delta content
    const content = extractDeltaContent(rawChunk.choices[0]?.delta?.content);
    // Yield to UI
}
```

The `extractDeltaContent` function handles both string and array content formats.

---

## Part 3: FastAPI Streaming Implementation

### Basic SSE Pattern

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

async def event_generator():
    """Async generator yielding SSE-formatted chunks."""
    for i in range(10):
        chunk = {"data": f"message {i}"}
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"

@app.get("/stream")
async def stream():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### OpenAI-Compatible Streaming Endpoint

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import time
import uuid

router = APIRouter()

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = False
    # ... other fields

async def generate_sse_chunks(
    request: ChatCompletionRequest,
    agent,
    deps,
) -> AsyncIterator[str]:
    """Generate OpenAI-compatible SSE chunks from Pydantic AI agent."""

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = request.model or "jasque"

    # First chunk: role announcement
    first_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None,
        }]
    }
    yield f"data: {json.dumps(first_chunk)}\n\n"

    # Extract user message and history
    user_message = extract_last_user_message(request.messages)
    history = convert_to_pydantic_history(request.messages[:-1])

    # Stream from agent
    async with agent.iter(user_message, message_history=history, deps=deps) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as stream:
                    async for event in stream:
                        content = None
                        # IMPORTANT: Handle PartStartEvent for initial text!
                        if isinstance(event, PartStartEvent):
                            if isinstance(event.part, TextPart) and event.part.content:
                                content = event.part.content
                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                content = event.delta.content_delta

                        if content:
                            chunk = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": None,
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"

    # Final chunk: finish_reason
    final_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"

    # Optional: usage chunk (if stream_options.include_usage)
    usage = run.usage()
    usage_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [],
        "usage": {
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }
    }
    yield f"data: {json.dumps(usage_chunk)}\n\n"

    # Termination signal
    yield "data: [DONE]\n\n"

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    agent = get_agent()
    deps = AgentDependencies(request_id=get_request_id())

    if request.stream:
        return StreamingResponse(
            generate_sse_chunks(request, agent, deps),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    else:
        # Non-streaming response
        result = await agent.run(user_message, deps=deps)
        return create_completion_response(result)
```

### Error Handling in Streams

```python
async def safe_generate_sse_chunks(...) -> AsyncIterator[str]:
    """Wrap generator with error handling."""
    try:
        async for chunk in generate_sse_chunks(...):
            yield chunk
    except Exception as e:
        logger.error("streaming.error", error=str(e), exc_info=True)
        # Send error as final chunk (graceful degradation)
        error_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "jasque",
            "choices": [{
                "index": 0,
                "delta": {"content": f"\n\n[Error: {str(e)}]"},
                "finish_reason": "stop",
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"
```

---

## Part 4: Complete Integration Flow

### Request → Agent → Chunks → SSE

```
┌─────────────────┐
│ OpenAI Request  │
│ POST /v1/chat/  │
│   completions   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse Request   │
│ - Extract msgs  │
│ - Normalize     │
│   content       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Convert History │
│ OpenAI → Pydantic│
│   AI format     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ agent.iter()    │
│ - Iterate nodes │
│ - Stream from   │
│   ModelRequest  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TextPartDelta   │
│ → OpenAI Chunk  │
│ → SSE Format    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ StreamingResp   │
│ text/event-     │
│   stream        │
└─────────────────┘
```

### Type Definitions

```python
from typing import Literal, Union, AsyncIterator
from pydantic import BaseModel

# Content normalization (from previous research)
class TextContent(BaseModel):
    type: Literal["text"]
    text: str

class ImageContent(BaseModel):
    type: Literal["image_url"]
    image_url: str | dict

ContentPart = Union[TextContent, ImageContent]

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]

class ChatCompletionRequest(BaseModel):
    model: str = "jasque"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    stream_options: dict | None = None

class DeltaContent(BaseModel):
    role: str | None = None
    content: str | None = None

class ChunkChoice(BaseModel):
    index: int
    delta: DeltaContent
    finish_reason: str | None = None

class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
    usage: dict | None = None
```

### Helper Functions

```python
def normalize_content(content: str | list[dict]) -> str:
    """Extract text from OpenAI message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if item.get("type") == "text"
        )
    return str(content or "")

def extract_last_user_message(messages: list[ChatMessage]) -> str:
    """Get the last user message for the agent prompt."""
    for msg in reversed(messages):
        if msg.role == "user":
            return normalize_content(msg.content)
    return ""

def convert_to_pydantic_history(
    messages: list[ChatMessage]
) -> list[ModelMessage]:
    """Convert OpenAI messages to Pydantic AI message history."""
    from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

    history = []
    for msg in messages:
        content = normalize_content(msg.content)
        if msg.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif msg.role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
        # system messages: handled via agent instructions or prepended
    return history
```

---

## Summary: Implementation Checklist

| Component | Implementation |
|-----------|---------------|
| **Endpoint** | `POST /v1/chat/completions` |
| **Content parsing** | Accept `string` or `[{type, text}]` |
| **History conversion** | OpenAI → `ModelRequest`/`ModelResponse` |
| **Streaming** | `agent.iter()` + `node.stream()` |
| **Text extraction** | `PartStartEvent` → `TextPart.content` (initial) + `PartDeltaEvent` → `TextPartDelta.content_delta` |
| **Chunk format** | `ChatCompletionChunk` with `delta.content` |
| **SSE format** | `data: {json}\n\n` + `data: [DONE]\n\n` |
| **Response type** | `StreamingResponse(media_type="text/event-stream")` |
| **Usage tracking** | `run.usage()` → final chunk with `usage` field |

---

## Sources

- [Pydantic AI Agents Documentation](https://ai.pydantic.dev/agents/)
- [Pydantic AI Message History](https://ai.pydantic.dev/message-history/)
- [Pydantic AI API Reference - Agent](https://ai.pydantic.dev/api/agent/)
- [Pydantic AI API Reference - Messages](https://ai.pydantic.dev/api/messages/)
- [Pydantic AI API Reference - Usage](https://ai.pydantic.dev/api/usage/)
- [Streaming with Pydantic AI Blog](https://datastud.dev/posts/pydantic-ai-streaming/)
- [GitHub Issue #1574 - Final Response Determination](https://github.com/pydantic/pydantic-ai/issues/1574)
- [OpenAI API Chat Completions](https://platform.openai.com/docs/api-reference/chat)
- [OpenAI Cookbook - How to Stream Completions](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_stream_completions.ipynb)
- [Obsidian Copilot - ChatOpenRouter.ts](https://github.com/logancyang/obsidian-copilot)
- [FastAPI SSE with React/LangGraph](https://www.softgrade.org/sse-with-fastapi-react-langgraph/)
- [Streaming APIs for Beginners - Python/FastAPI](https://python.plainenglish.io/streaming-apis-for-beginners-python-fastapi-and-async-generators-848b73a8fc06)
- [LiteLLM OpenAI Compatible Providers](https://docs.litellm.ai/docs/providers/openai_compatible)
