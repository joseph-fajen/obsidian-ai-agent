# Obsidian Copilot OpenAI API Integration Research Report

**Date:** 2026-01-07
**Purpose:** Research how Obsidian Copilot communicates with OpenAI-compatible APIs to inform Jasque's `/v1/chat/completions` implementation.

---

## Part 1: Message Content Format

### Discovery: Content Can Be String OR Array

From the **actual source code** in `obsidian-copilot/src/utils.ts`, I found the critical function:

```typescript
export function extractTextFromChunk(content: any): string {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    return content
      .filter((item) => item.type === "text")
      .map((item) => item.text)
      .join("");
  }
  return String(content || "");
}
```

And from `ChatOpenRouter.ts`, the `extractDeltaContent()` method:

```typescript
// Handles delta content from streaming responses:
// - String values return directly
// - Arrays map to text strings (extracts .text from objects)
// - Joins results with no separator
// - Defaults to empty string if undefined
```

### Why Array Format Is Used

From [LangChain.js documentation](https://v03.api.js.langchain.com/types/_langchain_core.messages.MessageContentComplex.html), the `MessageContentComplex` type supports multi-modal content:

```typescript
export type MessageContentComplex =
  MessageContentText |
  MessageContentImageUrl |
  (Record<string, any> & { type?: "text" | "image_url" | string; });

export type MessageContentText = {
  type: "text";
  text: string;
};

export type MessageContentImageUrl = {
  type: "image_url";
  image_url: string | { url: string; detail?: ImageDetail; };
};
```

The plugin uses array format to support:
1. **Multi-modal messages** (text + images)
2. **LangChain compatibility** which uses this structure internally
3. **Future-proofing** for additional content types

### Request Format Examples

**Simple text (most common):**
```json
{
  "messages": [
    {"role": "user", "content": "What tasks do I have?"}
  ]
}
```

**Structured array (multi-modal or LangChain):**
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
      ]
    }
  ]
}
```

---

## Part 2: Endpoint Path Construction

### Critical Finding: SDK Auto-Appends `/chat/completions`

From [GitHub issue #1344](https://github.com/openai/openai-python/issues/1344) and [LiteLLM docs](https://docs.litellm.ai/docs/providers/openai_compatible):

> **The `/chat/completions` path is hardcoded and automatically appended by the SDK.**
> Do NOT add anything additional to the base URL like `/v1/embedding`. The OpenAI client automatically adds the relevant endpoints.

### URL Construction Logic

From `ChatOpenRouter.ts`:

```typescript
this.openaiClient = new OpenAI({
  apiKey: fields.apiKey,
  baseURL: fields.configuration?.baseURL || "https://openrouter.ai/api/v1",
  dangerouslyAllowBrowser: true,
})
```

**The math:**

| User Enters (Base URL) | SDK Appends | Final Request URL |
|------------------------|-------------|-------------------|
| `http://localhost:8123/v1` | `/chat/completions` | `http://localhost:8123/v1/chat/completions` |
| `http://localhost:8123` | `/chat/completions` | `http://localhost:8123/chat/completions` |

### Recommended Jasque Configuration

For users configuring Obsidian Copilot to use Jasque:

| Setting | Value |
|---------|-------|
| **Base URL** | `http://localhost:8123/v1` |
| **Provider** | "3rd party (openai format)" |
| **Model** | `jasque` |

This means **Jasque must implement:**
```
POST /v1/chat/completions
```

### Verified from PR #1385

From [PR #1385](https://github.com/logancyang/obsidian-copilot/pull/1385) fixing Azure OpenAI URLs:

> "The fix implements baseURL as `https://{instanceName}.openai.azure.com/openai/deployments/{deploymentName}`. The path `/chat/completions` is appended by the client library rather than included in the baseURL itself."

---

## Part 3: Multi-Modal & Structured Content

### Image Support Confirmed

From the source code analysis, the plugin has multi-modal support:
- `extractChatHistory()` recommends using `processRawChatHistory` "for multimodal chains (CopilotPlus, AutonomousAgent) to preserve image content"
- Content arrays support `{"type": "image_url", "image_url": {...}}` format

### Content Part Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"text"` \| `"image_url"` | Yes | Discriminator |
| `text` | `string` | If type="text" | The text content |
| `image_url` | `string` \| `{url, detail?}` | If type="image_url" | Image data |

---

## Implementation Requirements for Jasque

### 1. Pydantic Models for Messages

```python
from typing import Literal, Union
from pydantic import BaseModel, field_validator

class TextContent(BaseModel):
    type: Literal["text"]
    text: str

class ImageUrlDetail(BaseModel):
    url: str
    detail: str | None = None

class ImageContent(BaseModel):
    type: Literal["image_url"]
    image_url: str | ImageUrlDetail

ContentPart = Union[TextContent, ImageContent]

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]

    @property
    def text_content(self) -> str:
        """Extract plain text from content (handles both formats)."""
        if isinstance(self.content, str):
            return self.content
        # Array format - extract text parts
        return "".join(
            part.text for part in self.content
            if isinstance(part, TextContent) or (isinstance(part, dict) and part.get("type") == "text")
        )
```

### 2. Content Normalization Strategy

```python
def normalize_content(content: str | list[dict]) -> str:
    """
    Normalize message content to plain text.
    Mirrors obsidian-copilot's extractTextFromChunk() logic.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if item.get("type") == "text"
        )
    return str(content or "")
```

### 3. Endpoint Implementation

```python
# Jasque must expose:
# POST /v1/chat/completions

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    # Normalize all message contents
    messages = [
        {"role": msg.role, "content": normalize_content(msg.content)}
        for msg in request.messages
    ]
    # ... process with agent
```

### 4. Required Response Format

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "jasque",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Here are your tasks..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

---

## Summary

| Requirement | Implementation |
|-------------|---------------|
| **Endpoint** | `POST /v1/chat/completions` |
| **Content format** | Accept both `string` and `[{type, text/image_url}]` |
| **Normalization** | Extract text from array format via `type: "text"` filter |
| **Response** | OpenAI-compatible with `choices[].message.content` |
| **User config** | Base URL: `http://localhost:8123/v1` |

---

## Sources

- [Obsidian Copilot GitHub Repository](https://github.com/logancyang/obsidian-copilot)
- [Obsidian Copilot Settings Documentation](https://www.obsidiancopilot.com/en/docs/settings)
- [LangChain.js MessageContentComplex](https://v03.api.js.langchain.com/types/_langchain_core.messages.MessageContentComplex.html)
- [GitHub Issue #1385 - Azure baseURL Construction](https://github.com/logancyang/obsidian-copilot/pull/1385)
- [GitHub Issue #2097 - OpenAI Format Endpoint Routing](https://github.com/logancyang/obsidian-copilot/issues/2097)
- [GitHub Issue #1924 - Ollama 404 URL Construction](https://github.com/logancyang/obsidian-copilot/issues/1924)
- [OpenAI Python SDK Issue #1344 - Path Customization](https://github.com/openai/openai-python/issues/1344)
- [LiteLLM OpenAI Compatible Docs](https://docs.litellm.ai/docs/providers/openai_compatible)
- [LM Studio OpenAI Compatibility](https://lmstudio.ai/docs/developer/openai-compat)
- [LangChain ChatOpenAI Integration](https://js.langchain.com/docs/integrations/chat/openai/)
