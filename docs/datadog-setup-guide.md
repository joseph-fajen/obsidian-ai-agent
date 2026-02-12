# Datadog LLM Observability Setup Guide

This guide walks you through setting up Datadog LLM Observability for Jasque from scratch. By the end, you'll be able to see your agent's behavior, LLM calls, and tool usage in Datadog's dashboards.

## What You'll Get

With Datadog observability enabled, you can monitor:

- **Agent Runs** - Each conversation with Jasque appears as a trace
- **Tool Calls** - See which Obsidian tools the agent uses and how long they take
- **LLM Requests** - Track Anthropic API calls including latency and token usage
- **HTTP Requests** - Monitor FastAPI endpoint performance
- **Errors** - Get visibility into failures across the stack

## Prerequisites

- Jasque running locally or in Docker
- An email address for Datadog signup
- About 15 minutes for initial setup

---

## Step 1: Create a Datadog Account

1. Go to [datadoghq.com](https://www.datadoghq.com/)

2. Click **"Get Started Free"** (or "Free Trial")

3. **Choose your region** - This determines your `DD_SITE` value:

   | Region | DD_SITE Value | Best For |
   |--------|---------------|----------|
   | US1 (default) | `datadoghq.com` | US East users |
   | US3 | `us3.datadoghq.com` | US users (alternate) |
   | US5 | `us5.datadoghq.com` | US users (alternate) |
   | EU1 | `datadoghq.eu` | European users (GDPR) |
   | AP1 | `ap1.datadoghq.com` | Asia-Pacific users |

   > **Tip:** If you're in the US and unsure, choose US1 (the default). You can see which site you're on by looking at the URL after logging in.

4. Complete the signup form with your email and create a password

5. You may be asked about your use case - select options related to "APM" or "Application Performance Monitoring"

### Free Tier Limits

Datadog's free tier includes:
- **APM**: 1 million trace events per month
- **LLM Observability**: Currently in the free tier includes generous limits for evaluation
- **14-day retention** for trace data

For personal/development use with Jasque, you'll likely stay well within free limits.

---

## Step 2: Get Your API Key

1. After logging in, click on your profile icon (bottom-left corner)

2. Navigate to **Organization Settings** → **API Keys**

   Or go directly to: `https://app.datadoghq.com/organization-settings/api-keys`

   > **Note:** Replace `app.datadoghq.com` with your region's domain if different (e.g., `app.datadoghq.eu` for EU)

3. You should see a default API key already created. Click the **key icon** to reveal it, or click **"Copy"**

4. If no key exists, click **"+ New Key"**, give it a name like "jasque-local", and copy it

> **Security Note:** Treat your API key like a password. Don't commit it to git or share it publicly.

---

## Step 3: Configure Jasque

Add the Datadog environment variables to your `.env` file:

```bash
# Datadog Configuration
DD_API_KEY=your-actual-api-key-here
DD_SITE=datadoghq.com
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=jasque
DD_LLMOBS_AGENTLESS_ENABLED=1
```

**Variable explanations:**

| Variable | Purpose |
|----------|---------|
| `DD_API_KEY` | Authenticates with Datadog (required) |
| `DD_SITE` | Your Datadog region - must match where you signed up |
| `DD_LLMOBS_ENABLED` | Enables LLM Observability features |
| `DD_LLMOBS_ML_APP` | Application name shown in dashboards |
| `DD_LLMOBS_AGENTLESS_ENABLED` | Sends traces directly to Datadog (no Agent needed) |

---

## Step 4: Run Jasque with Tracing

### Option A: Local Development

```bash
# Make sure dependencies are installed
uv sync

# Run with ddtrace-run wrapper
ddtrace-run uv run uvicorn app.main:app --port 8123
```

### Option B: Docker

```bash
# Use the observability compose override
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d --build
```

### What You'll See in the Terminal

When ddtrace initializes successfully, you'll see output like:

```
DATADOG TRACER CONFIGURATION - ...
    agent_url: None
    dd_version: 4.4.0
    env: development
    service: jasque
    ...
```

You may also see this warning - **it's normal and can be ignored**:

```
OpenTelemetry configuration OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE is not supported by Datadog.
```

---

## Step 5: Generate Some Traces

Make a request to Jasque to generate trace data:

```bash
# Simple health check (generates APM trace)
curl http://localhost:8123/health

# Chat request (generates LLM Observability trace)
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jasque",
    "messages": [{"role": "user", "content": "List the folders in my vault"}]
  }'
```

Or use Obsidian Copilot to chat with Jasque - each conversation generates traces.

---

## Step 6: View Your Traces in Datadog

Traces typically appear within **1-2 minutes** of the request.

### LLM Observability Dashboard

1. Go to [app.datadoghq.com/llm](https://app.datadoghq.com/llm) (or your region's equivalent)

2. You should see **"jasque"** listed as an ML application

3. Click into it to see:
   - **Traces** - Each agent run with timing breakdown
   - **Spans** - Individual operations (LLM calls, tool calls)
   - **Token Usage** - Input/output tokens per request
   - **Latency** - How long each operation took

### APM Traces

1. Go to [app.datadoghq.com/apm/traces](https://app.datadoghq.com/apm/traces)

2. Filter by `service:jasque`

3. You'll see HTTP request traces with:
   - Endpoint path (`/v1/chat/completions`, `/health`)
   - Response times
   - Status codes
   - Nested spans for database queries, etc.

### Understanding a Trace

A typical Jasque chat trace looks like:

```
POST /v1/chat/completions (2.3s)
├── LLM Request to Anthropic (1.8s)
│   └── claude-sonnet-4-5 completion
├── Tool: obsidian_query_vault (0.2s)
│   └── list_folders operation
└── LLM Request to Anthropic (0.3s)
    └── Final response generation
```

This shows the agent made two LLM calls with a tool call in between.

---

## Troubleshooting

### No Traces Appearing

**Check your API key:**
```bash
# Verify DD_API_KEY is set
echo $DD_API_KEY
```

**Check your site matches your account:**
- Log into Datadog and look at the URL
- `app.datadoghq.com` → use `DD_SITE=datadoghq.com`
- `app.datadoghq.eu` → use `DD_SITE=datadoghq.eu`
- etc.

**Check ddtrace is running:**
Look for the `DATADOG TRACER CONFIGURATION` output when Jasque starts. If you don't see it, ddtrace isn't wrapping the process.

### "Unauthorized" or 403 Errors

- Your API key may be incorrect or revoked
- Go to Organization Settings → API Keys and verify/regenerate

### Traces Appear but No LLM Data

- Verify `DD_LLMOBS_ENABLED=1` is set
- Check that you're making actual chat requests (not just health checks)
- LLM Observability may take a few extra minutes to populate

### High Latency in Traces

This is normal! LLM calls to Anthropic typically take 1-5 seconds depending on:
- Response length
- Model used (Claude Opus is slower than Sonnet)
- Anthropic API load

---

## Optional: Additional Configuration

### Environment Tags

Add environment context to your traces:

```bash
DD_ENV=development  # or "staging", "production"
DD_SERVICE=jasque
DD_VERSION=0.1.0
```

### Log Correlation

Enable trace IDs in your logs (already set in the Docker override):

```bash
DD_LOGS_INJECTION=true
```

### Disable Tracing

To run without Datadog, simply run Jasque normally without `ddtrace-run`:

```bash
# No tracing
uv run uvicorn app.main:app --port 8123

# With tracing
ddtrace-run uv run uvicorn app.main:app --port 8123
```

---

## Quick Reference

### Environment Variables

```bash
# Required
DD_API_KEY=your-api-key

# Recommended
DD_SITE=datadoghq.com
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=jasque
DD_LLMOBS_AGENTLESS_ENABLED=1

# Optional
DD_ENV=development
DD_SERVICE=jasque
DD_LOGS_INJECTION=true
```

### Useful Links

| Resource | URL |
|----------|-----|
| LLM Observability | [app.datadoghq.com/llm](https://app.datadoghq.com/llm) |
| APM Traces | [app.datadoghq.com/apm/traces](https://app.datadoghq.com/apm/traces) |
| API Keys | [app.datadoghq.com/organization-settings/api-keys](https://app.datadoghq.com/organization-settings/api-keys) |
| ddtrace Docs | [docs.datadoghq.com/tracing/](https://docs.datadoghq.com/tracing/) |
| LLM Obs Docs | [docs.datadoghq.com/llm_observability/](https://docs.datadoghq.com/llm_observability/) |

### Commands

```bash
# Local with tracing
ddtrace-run uv run uvicorn app.main:app --port 8123

# Docker with tracing
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d --build

# Local without tracing
uv run uvicorn app.main:app --port 8123
```
