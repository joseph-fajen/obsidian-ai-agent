# Connecting Obsidian Copilot to Jasque

This guide explains how to configure the Obsidian Copilot plugin to use Jasque as your AI backend.

## Prerequisites

- Jasque running at `localhost:8123`
- Obsidian with the Copilot plugin installed
- Your Obsidian vault configured in Jasque's `.env` file

## Configuration Steps

1. **Start Jasque**
   ```bash
   uv run uvicorn app.main:app --reload --port 8123
   ```

2. **Open Obsidian Settings**
   - Click the settings gear icon in the bottom-left corner
   - Or use `Cmd/Ctrl + ,`

3. **Navigate to Copilot Settings**
   - In the left sidebar, scroll down to "Community plugins"
   - Click on "Copilot"

4. **Configure the Provider**

   | Setting | Value |
   |---------|-------|
   | **Provider** | `3rd party (openai format)` |
   | **Base URL** | `http://localhost:8123/v1` |
   | **Model** | `jasque` |
   | **API Key** | Any non-empty value (e.g., `jasque`) |

   > **Important:** Do NOT add `/chat/completions` to the Base URL. The OpenAI SDK automatically appends this path.

5. **Save Settings**
   - Close the settings dialog
   - Changes take effect immediately

## Testing the Connection

1. Open the Copilot chat panel in Obsidian
2. Send a test message like "Hello"
3. You should receive a response from Jasque

## Troubleshooting

### CORS Errors

If you see CORS-related errors in the browser console:

1. Ensure Jasque is running with the correct CORS configuration
2. Check that `app://obsidian.md` is in the `ALLOWED_ORIGINS` setting
3. Restart Jasque after changing CORS settings

### Connection Refused

If the connection is refused:

1. Verify Jasque is running: `curl http://localhost:8123/health`
2. Check the port number matches your configuration
3. Ensure no firewall is blocking the connection

### 404 Not Found

If you get 404 errors:

1. Verify the Base URL is `http://localhost:8123/v1` (not `/v1/chat/completions`)
2. Check that Jasque started without errors in the terminal

### Streaming Issues

If responses appear all at once instead of streaming:

1. This may be a Copilot plugin limitation
2. Check the Jasque logs for streaming-related errors
3. Try disabling and re-enabling streaming in Copilot settings

## Verifying with curl

You can test the endpoint directly:

**Non-streaming:**
```bash
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}]}'
```

**Streaming:**
```bash
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "jasque", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'
```

## Technical Details

- **Endpoint:** `POST /v1/chat/completions`
- **Format:** OpenAI Chat Completions API
- **Streaming:** Server-Sent Events (SSE)
- **Message History:** Fully supported
- **Multi-modal:** Text content supported (images ignored)

## See Also

- [Jasque PRD](.agents/reference/PRD.md) - Full product requirements
- [Obsidian Copilot Documentation](https://www.obsidiancopilot.com/en/docs/settings)
