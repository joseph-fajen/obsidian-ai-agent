# Feature: Add Datadog LLM Observability

The following plan should be complete, but validate documentation and codebase patterns before implementing.

Pay special attention to the exact formatting of existing files. Match indentation, comment styles, and section headers precisely.

## Feature Description

Add Datadog LLM Observability and APM tracing to Jasque using the ddtrace-run wrapper approach. This enables monitoring of:
- Pydantic AI agent invocations and tool calls
- Anthropic LLM API requests (latency, tokens, errors)
- FastAPI HTTP request traces
- Database query performance

The implementation is purely additive - no existing Python code is modified. Users opt-in to observability by running with ddtrace-run or using the Docker Compose override.

## User Story

As a developer running Jasque
I want to enable Datadog LLM Observability with minimal configuration
So that I can monitor agent behavior, LLM calls, tool usage, and API performance

## Problem Statement

Jasque currently has no observability into agent behavior, LLM call performance, or tool execution. Developers cannot see what the agent is doing, how long LLM calls take, or track errors across the system.

## Solution Statement

Add Datadog LLM Observability using the ddtrace-run wrapper approach, which auto-instruments Pydantic AI, Anthropic, FastAPI, and SQLAlchemy without code changes. Provide configuration for both local development and Docker deployment via a compose override file.

## Feature Metadata

**Feature Type**: New Capability (Observability Integration)
**Estimated Complexity**: Low
**Primary Systems Affected**: Build configuration, environment configuration, Docker, documentation
**Dependencies**: ddtrace >= 3.11.0

---

## CONTEXT REFERENCES

### Relevant Codebase Files - READ BEFORE IMPLEMENTING

- `pyproject.toml` (lines 7-20) - Dependency list format and alphabetical ordering
- `.env.example` (lines 17-58) - Section header style (`# ====`) and comment patterns
- `README.md` (lines 74-84) - Documentation section style (brief intro + bash blocks)
- `docker-compose.yml` (lines 20-52) - App service configuration, env_file usage
- `Dockerfile` (line 54) - Current CMD uses `python -m app.main`

### New Files to Create

- `docker-compose.observability.yml` - Docker Compose override for Datadog-enabled runs

### Relevant Documentation - READ BEFORE IMPLEMENTING

- [Datadog LLM Observability Quickstart](https://docs.datadoghq.com/llm_observability/quickstart/)
  - Section: Python setup with ddtrace-run
  - Why: Exact environment variables and command format

- [Datadog LLM Observability Auto-Instrumentation](https://docs.datadoghq.com/llm_observability/instrumentation/auto_instrumentation/)
  - Section: Pydantic AI integration
  - Why: Version requirements (ddtrace >= 3.11.0, pydantic-ai >= 0.3.0)

- [Anthropic Integration](https://docs.datadoghq.com/integrations/anthropic/)
  - Section: Setup and traced operations
  - Why: Confirms Anthropic SDK is auto-instrumented

### Patterns to Follow

**Dependency Format (pyproject.toml):**
```toml
dependencies = [
    "aiofiles>=24.1.0",
    "alembic>=1.17.1",
    # ... alphabetically ordered
]
```

**Environment Section Format (.env.example):**
```bash
# =============================================================================
# Section Name
# =============================================================================
# Description of what this section configures

VARIABLE_NAME=default-value
```

**README Section Format:**
```markdown
## Section Title

Brief one-line description.

```bash
# Command with comment
actual-command here
```

Additional context if needed.
```

**Docker Compose Override Pattern:**
Override files extend the base compose file. Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up
```

---

## IMPLEMENTATION PLAN

### Phase 1: Add Dependency

Add ddtrace to project dependencies so it's available for instrumentation.

### Phase 2: Document Configuration

Add Datadog environment variables to .env.example so users know what to configure.

### Phase 3: Create Docker Override

Create compose override file that enables Datadog tracing in containerized runs.

### Phase 4: Document Usage

Add README section explaining how to run with observability enabled (local and Docker).

### Phase 5: Validate

Run dependency sync and verify no conflicts.

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE pyproject.toml - Add ddtrace dependency

- **IMPLEMENT**: Add `"ddtrace>=3.11.0",` to the dependencies array
- **LOCATION**: Insert alphabetically between `"anthropic>=0.40.0",` and `"asyncpg>=0.30.0",`
- **PATTERN**: Match existing format - quoted string with version specifier and trailing comma
- **GOTCHA**: Must be >= 3.11.0 for Pydantic AI support (current latest is 4.4.0)
- **VALIDATE**: `grep -n "ddtrace" pyproject.toml` should show the new line

### Task 2: UPDATE .env.example - Add Datadog configuration section

- **IMPLEMENT**: Add new section after the "LLM Provider Configuration" section (after line 57)
- **CONTENT**: Add the following section:

```bash
# =============================================================================
# Datadog Observability (Optional)
# =============================================================================
# Enable Datadog LLM Observability for monitoring agent behavior, LLM calls,
# and application performance. Requires a Datadog account.
# Get your API key at: https://app.datadoghq.com/organization-settings/api-keys

# Required for Datadog integration
# DD_API_KEY=your-datadog-api-key-here

# Datadog site (us1, us3, us5, eu, ap1, or custom)
# DD_SITE=datadoghq.com

# Enable LLM Observability features
# DD_LLMOBS_ENABLED=1

# Application name shown in Datadog LLM Observability dashboard
# DD_LLMOBS_ML_APP=jasque

# Enable agentless mode (sends directly to Datadog, no Agent required)
# DD_LLMOBS_AGENTLESS_ENABLED=1

# Optional: Set service name for APM traces
# DD_SERVICE=jasque

# Optional: Set environment tag
# DD_ENV=development
```

- **PATTERN**: Match existing section header style with `# ===` borders
- **GOTCHA**: Keep variables commented out by default (opt-in)
- **VALIDATE**: `grep -c "DD_" .env.example` should return 8

### Task 3: CREATE docker-compose.observability.yml

- **IMPLEMENT**: Create new file at project root
- **CONTENT**:

```yaml
# Docker Compose override for Datadog LLM Observability
#
# Usage:
#   docker-compose -f docker-compose.yml -f docker-compose.observability.yml up
#
# Requires Datadog environment variables to be set in .env:
#   DD_API_KEY, DD_SITE, DD_LLMOBS_ENABLED, DD_LLMOBS_ML_APP, DD_LLMOBS_AGENTLESS_ENABLED

services:
  app:
    # Override command to use ddtrace-run wrapper
    command: ddtrace-run uvicorn app.main:app --host 0.0.0.0 --port 8123

    # Pass Datadog environment variables to container
    environment:
      - DD_API_KEY=${DD_API_KEY}
      - DD_SITE=${DD_SITE:-datadoghq.com}
      - DD_LLMOBS_ENABLED=${DD_LLMOBS_ENABLED:-1}
      - DD_LLMOBS_ML_APP=${DD_LLMOBS_ML_APP:-jasque}
      - DD_LLMOBS_AGENTLESS_ENABLED=${DD_LLMOBS_AGENTLESS_ENABLED:-1}
      - DD_SERVICE=${DD_SERVICE:-jasque}
      - DD_ENV=${DD_ENV:-development}
      # Enable trace correlation in logs
      - DD_LOGS_INJECTION=true
```

- **PATTERN**: Standard docker-compose format, comments explain usage
- **GOTCHA**: Use `${VAR:-default}` syntax for optional defaults
- **VALIDATE**: `docker-compose -f docker-compose.yml -f docker-compose.observability.yml config` should output merged config without errors

### Task 4: UPDATE README.md - Add Observability section

- **IMPLEMENT**: Add new section after "Docker Deployment" (after line 84)
- **CONTENT**:

```markdown
## Observability (Datadog)

Enable Datadog LLM Observability to monitor agent behavior, LLM calls, and performance.

### Prerequisites

1. [Create a Datadog account](https://www.datadoghq.com/) (free tier available)
2. Get your API key from [Organization Settings](https://app.datadoghq.com/organization-settings/api-keys)
3. Add to your `.env` file:

```bash
DD_API_KEY=your-api-key
DD_SITE=datadoghq.com
DD_LLMOBS_ENABLED=1
DD_LLMOBS_ML_APP=jasque
DD_LLMOBS_AGENTLESS_ENABLED=1
```

### Local Development

Run with the `ddtrace-run` wrapper:

```bash
# Install dependencies (includes ddtrace)
uv sync

# Run with Datadog tracing enabled
ddtrace-run uv run uvicorn app.main:app --port 8123
```

### Docker

Use the observability override file:

```bash
# Start with Datadog tracing enabled
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d --build

# View logs
docker-compose logs -f app
```

### What You'll See in Datadog

- **LLM Observability**: Agent runs, tool calls, LLM request/response traces
- **APM**: HTTP request traces, database queries, error tracking
- **Metrics**: Latency, token usage, error rates

View traces at: [LLM Observability](https://app.datadoghq.com/llm) | [APM Traces](https://app.datadoghq.com/apm/traces)
```

- **PATTERN**: Match existing README style - concise sections with bash code blocks
- **GOTCHA**: Ensure code blocks are properly fenced with triple backticks
- **VALIDATE**: Visual inspection - section should appear after Docker Deployment

### Task 5: Sync dependencies

- **IMPLEMENT**: Run uv sync to install ddtrace
- **COMMAND**: `uv sync`
- **VALIDATE**: `uv run python -c "import ddtrace; print(ddtrace.__version__)"` should print version >= 3.11.0

### Task 6: Validate Docker configuration

- **IMPLEMENT**: Verify compose files merge correctly
- **COMMAND**: `docker-compose -f docker-compose.yml -f docker-compose.observability.yml config`
- **VALIDATE**: Output shows merged config with ddtrace-run command and DD_* environment variables

---

## TESTING STRATEGY

### Configuration Tests

1. **Dependency installation**: `uv sync` completes without errors
2. **Import test**: `uv run python -c "import ddtrace"` succeeds
3. **Docker config merge**: Compose config command outputs valid YAML

### Integration Test (Manual)

1. Set Datadog env vars in .env (requires real DD_API_KEY)
2. Run: `ddtrace-run uv run uvicorn app.main:app --port 8123`
3. Make a request: `curl http://localhost:8123/health`
4. Check Datadog APM for traces within 1-2 minutes

### LLM Observability Test (Manual)

1. With Datadog enabled, make a chat request to `/v1/chat/completions`
2. Check Datadog LLM Observability dashboard
3. Verify agent span contains tool call child spans

---

## VALIDATION COMMANDS

Execute all commands to ensure zero regressions.

### Level 1: Syntax & Style

```bash
# Check Python formatting
uv run ruff check .
uv run ruff format --check .
```

### Level 2: Type Checking

```bash
# Type checking (should still pass - no Python changes)
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests

```bash
# Run all tests (should still pass - no code changes)
uv run pytest -v
```

### Level 4: Configuration Validation

```bash
# Verify ddtrace installed
uv run python -c "import ddtrace; print(f'ddtrace {ddtrace.__version__}')"

# Verify docker compose config merges
docker-compose -f docker-compose.yml -f docker-compose.observability.yml config > /dev/null && echo "Docker config valid"
```

### Level 5: Manual Validation

```bash
# Test local run with ddtrace (Ctrl+C to stop)
# Note: Will show warnings if DD_API_KEY not set - that's expected
timeout 5 ddtrace-run uv run uvicorn app.main:app --port 8123 || true

# Verify health endpoint works
curl -s http://localhost:8123/health | head -1
```

---

## ACCEPTANCE CRITERIA

- [ ] `ddtrace>=3.11.0` is in pyproject.toml dependencies
- [ ] `.env.example` contains Datadog configuration section with all required variables
- [ ] `docker-compose.observability.yml` exists and merges correctly with base compose
- [ ] `README.md` contains Observability section with local and Docker instructions
- [ ] `uv sync` installs ddtrace without errors
- [ ] All existing tests still pass (no regressions)
- [ ] Docker config validation passes

---

## COMPLETION CHECKLIST

- [ ] Task 1: ddtrace dependency added to pyproject.toml
- [ ] Task 2: Datadog section added to .env.example
- [ ] Task 3: docker-compose.observability.yml created
- [ ] Task 4: Observability section added to README.md
- [ ] Task 5: Dependencies synced successfully
- [ ] Task 6: Docker configuration validated
- [ ] All validation commands pass
- [ ] All acceptance criteria met

---

## NOTES

### Design Decisions

1. **ddtrace-run over programmatic**: Chose wrapper approach for zero code changes and proven reliability
2. **Agentless mode**: Simpler setup, no Datadog Agent container needed
3. **Override file over inline**: Keeps base docker-compose.yml unchanged, opt-in pattern
4. **Variables commented in .env.example**: Datadog is optional, shouldn't be required for basic usage

### Future Enhancements (Out of Scope)

- Custom span annotations for business logic
- Log shipping to Datadog
- Datadog Agent container for non-agentless mode
- Dashboard-as-code configuration

### Interview Talking Points

After implementation, you can speak to:
- "I used ddtrace-run for auto-instrumentation of Pydantic AI agents"
- "The integration captures agent invocations, tool calls, and LLM API requests"
- "I configured both local and containerized deployment patterns"
- "Agentless mode sends traces directly without requiring a Datadog Agent"
