# Feature: Multi-LLM Provider Support

Enable switching between LLM providers (Anthropic Claude, Google Gemini, OpenAI) via a single `.env` configuration change.

## Feature Description

Add the ability to switch LLM providers by changing one environment variable (`LLM_MODEL`). The model string follows Pydantic AI's native format: `provider:model-name`. This leverages Pydantic AI's built-in multi-provider support, which was explicitly chosen in the PRD for this capability.

## User Story

```
As a Jasque user
I want to switch LLM providers by changing one line in my .env file
So that I can experiment with different models and optimize for cost vs quality
```

## Problem Statement

Currently, Jasque is hardcoded to use Anthropic Claude. Users cannot switch to alternative providers (like Google Gemini for cost optimization) without code changes.

## Solution Statement

Replace the separate `ANTHROPIC_MODEL` setting with a unified `LLM_MODEL` setting that uses Pydantic AI's native model string format (`provider:model-name`). Parse the provider prefix to determine which API key environment variable to validate on startup.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Low
**Primary Systems Affected**: `app/core/config.py`, `app/core/agents/base.py`
**Dependencies**: None (Pydantic AI already supports multi-provider)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - READ BEFORE IMPLEMENTING

- `app/core/config.py` (lines 44-46) - Current Anthropic-only settings to replace
- `app/core/agents/base.py` (lines 69-103) - Agent creation with hardcoded Anthropic logic
- `app/core/agents/tests/test_base.py` (lines 46-51) - Test that expects `anthropic:` prefix
- `.env.example` (lines 24-32) - Current LLM configuration section

### New Files to Create

None - this is a modification of existing files only.

### Relevant Documentation - READ BEFORE IMPLEMENTING

- [Pydantic AI Models Overview](https://ai.pydantic.dev/models/overview/)
  - Model string format: `provider:model-name`
  - Why: Defines the format we'll use for LLM_MODEL
- [Pydantic AI Google Provider](https://ai.pydantic.dev/models/google/)
  - Google uses `google-gla:` prefix for Generative Language API
  - Why: Needed for Gemini support
- [Pydantic AI Providers API](https://ai.pydantic.dev/api/providers/)
  - Environment variable naming: `{PROVIDER}_API_KEY`
  - Why: Determines which env var to validate

### Patterns to Follow

**Settings Pattern** (from `config.py`):
```python
# Optional settings use: field_name: str | None = None
# Required settings use: field_name: str
# Defaults use: field_name: str = "default_value"
```

**Logging Pattern** (from `base.py:82`):
```python
logger.info("agent.lifecycle.creating", model=settings.anthropic_model)
```

**Error Pattern** (from project conventions):
- Fail fast on startup with clear error messages
- Use ValueError for configuration errors

---

## IMPLEMENTATION PLAN

### Phase 1: Configuration Updates

Update `config.py` to support the new unified model setting while keeping individual API keys.

### Phase 2: Agent Factory Updates

Update `create_agent()` to parse the model string and inject the appropriate API key.

### Phase 3: Test Updates

Update tests to be provider-agnostic (test with configured model, not hardcoded).

### Phase 4: Documentation Updates

Update `.env.example` with clear placeholders and examples for all supported providers.

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE `app/core/config.py`

**IMPLEMENT**: Replace Anthropic-specific settings with unified LLM model setting

**Changes:**
1. Replace `anthropic_api_key: str` with `anthropic_api_key: str | None = None`
2. Replace `anthropic_model: str = "claude-sonnet-4-5"` with `llm_model: str = "anthropic:claude-sonnet-4-5"`
3. Add `google_api_key: str | None = None`
4. Add `openai_api_key: str | None = None`

**PATTERN**: Follow existing optional field pattern (see `allowed_origins` default)

**IMPORTS**: None needed

**GOTCHA**: Keep the default as `anthropic:claude-sonnet-4-5` for backward compatibility

**VALIDATE**: `uv run mypy app/core/config.py && uv run pyright app/core/config.py`

---

### Task 2: UPDATE `app/core/agents/base.py`

**IMPLEMENT**: Update `create_agent()` to handle multiple providers

**Changes to `create_agent()` function (lines 69-103):**

1. Add helper function to extract provider from model string:
```python
def _get_provider_from_model(model: str) -> str:
    """Extract provider prefix from model string (e.g., 'anthropic' from 'anthropic:claude-sonnet-4-5')."""
    if ":" not in model:
        raise ValueError(
            f"Invalid model format: '{model}'. Expected 'provider:model-name' "
            "(e.g., 'anthropic:claude-sonnet-4-5', 'google-gla:gemini-2.5-pro')"
        )
    return model.split(":")[0]
```

2. Add helper function to get and validate API key:
```python
def _get_api_key_for_provider(provider: str, settings: Settings) -> tuple[str, str]:
    """Get API key environment variable name and value for provider.

    Returns:
        Tuple of (env_var_name, api_key_value)

    Raises:
        ValueError: If API key not configured for provider.
    """
    provider_key_map: dict[str, tuple[str, str | None]] = {
        "anthropic": ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        "google-gla": ("GOOGLE_API_KEY", settings.google_api_key),
        "google-vertex": ("GOOGLE_API_KEY", settings.google_api_key),
        "openai": ("OPENAI_API_KEY", settings.openai_api_key),
    }

    if provider not in provider_key_map:
        supported = ", ".join(sorted(provider_key_map.keys()))
        raise ValueError(
            f"Unsupported provider: '{provider}'. Supported providers: {supported}"
        )

    env_var, api_key = provider_key_map[provider]
    if not api_key:
        raise ValueError(
            f"API key not configured for provider '{provider}'. "
            f"Set {env_var} in your .env file."
        )

    return env_var, api_key
```

3. Update `create_agent()` to use these helpers:
```python
def create_agent() -> Agent[AgentDependencies, str]:
    settings = get_settings()

    # Parse and validate model configuration
    provider = _get_provider_from_model(settings.llm_model)
    env_var, api_key = _get_api_key_for_provider(provider, settings)

    # Set API key in environment for Pydantic AI
    os.environ[env_var] = api_key

    logger.info("agent.lifecycle.creating", model=settings.llm_model, provider=provider)

    # ... rest of function unchanged, but use settings.llm_model directly
    agent: Agent[AgentDependencies, str] = Agent(
        settings.llm_model,  # Use full model string directly
        # ... rest unchanged
    )

    logger.info(
        "agent.lifecycle.created",
        model=settings.llm_model,
        provider=provider,
        tools=["obsidian_query_vault", "obsidian_manage_notes", "obsidian_manage_structure"],
    )
    return agent
```

**PATTERN**: Follow existing logging pattern with structured keys

**IMPORTS**: Add `from app.core.config import Settings` for type hint (if not already imported via get_settings)

**GOTCHA**: The model string goes directly to Agent() - Pydantic AI handles the rest

**VALIDATE**: `uv run mypy app/core/agents/base.py && uv run pyright app/core/agents/base.py`

---

### Task 3: UPDATE `app/core/agents/tests/test_base.py`

**IMPLEMENT**: Make tests provider-agnostic

**Changes:**

1. Update `mock_environment` fixture (lines 15-19) to use new env var name:
```python
env_vars = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "ANTHROPIC_API_KEY": "sk-ant-test-key",
    "LLM_MODEL": "anthropic:claude-sonnet-4-5",  # Changed from ANTHROPIC_MODEL
}
```

2. Update `test_create_agent_uses_correct_model` (line 51) to use configured model:
```python
def test_create_agent_uses_correct_model():
    """Test that create_agent uses the configured model."""
    with patch("app.core.agents.base.Agent") as mock_agent_class:
        create_agent()
        # Verify model string matches LLM_MODEL env var
        assert mock_agent_class.call_args[0][0] == "anthropic:claude-sonnet-4-5"
```

3. Add new test for invalid model format:
```python
def test_create_agent_invalid_model_format():
    """Test that invalid model format raises clear error."""
    with patch.dict(os.environ, {"LLM_MODEL": "invalid-no-colon"}):
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="Invalid model format"):
            create_agent()
```

4. Add new test for missing API key:
```python
def test_create_agent_missing_api_key():
    """Test that missing API key raises clear error."""
    env_vars = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "LLM_MODEL": "google-gla:gemini-2.5-pro",
        # Note: GOOGLE_API_KEY not set
    }
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="API key not configured"):
            create_agent()
```

**PATTERN**: Follow existing test structure with mock_environment fixture

**IMPORTS**: None additional needed

**GOTCHA**: Remember to call `get_settings.cache_clear()` when changing env vars in tests

**VALIDATE**: `uv run pytest app/core/agents/tests/test_base.py -v`

---

### Task 4: UPDATE `.env.example`

**IMPLEMENT**: Add clear placeholders for all supported providers

**Replace lines 24-32 with:**
```bash
# =============================================================================
# LLM Provider Configuration
# =============================================================================
# Model to use - format: provider:model-name
# Uncomment ONE of the following lines:

# Anthropic Claude (default)
LLM_MODEL=anthropic:claude-sonnet-4-5
# LLM_MODEL=anthropic:claude-opus-4-5
# LLM_MODEL=anthropic:claude-haiku-4-5

# Google Gemini (cost-effective alternative)
# LLM_MODEL=google-gla:gemini-2.5-pro
# LLM_MODEL=google-gla:gemini-2.5-flash

# OpenAI
# LLM_MODEL=openai:gpt-4o
# LLM_MODEL=openai:gpt-4o-mini

# -----------------------------------------------------------------------------
# API Keys - set the key(s) for provider(s) you want to use
# -----------------------------------------------------------------------------

# Anthropic API key (required if using anthropic: models)
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Google API key (required if using google-gla: models)
# Get your key at: https://aistudio.google.com/apikey
# GOOGLE_API_KEY=your-google-api-key-here

# OpenAI API key (required if using openai: models)
# Get your key at: https://platform.openai.com/api-keys
# OPENAI_API_KEY=your-openai-api-key-here
```

**PATTERN**: Follow existing .env.example comment style with section headers

**VALIDATE**: Manual review - ensure placeholders are clear

---

### Task 5: UPDATE user's actual `.env` file structure

**NOTE**: This is not a code change - document for user that they may need to:
1. Rename `ANTHROPIC_MODEL` to `LLM_MODEL` with full model string
2. Keep their existing `ANTHROPIC_API_KEY`
3. Add other API keys as needed

**VALIDATE**: N/A - user action

---

## TESTING STRATEGY

### Unit Tests

Run the updated test suite:
```bash
uv run pytest app/core/agents/tests/test_base.py -v
```

Expected: All tests pass including new validation tests.

### Integration Tests

The existing integration tests should continue to work since they use the configured model.

### Edge Cases

1. Invalid model format (no colon) - should fail fast with clear error
2. Missing API key for provider - should fail fast with clear error
3. Unsupported provider - should fail fast listing supported providers
4. Default model (no LLM_MODEL set) - should work with anthropic:claude-sonnet-4-5

---

## VALIDATION COMMANDS

Execute in order to ensure zero regressions:

### Level 1: Syntax & Style
```bash
uv run ruff check .
uv run ruff format --check .
```

### Level 2: Type Checking
```bash
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests
```bash
uv run pytest -v
```

### Level 4: Manual Validation

Test with Anthropic (default):
```bash
# Ensure .env has: LLM_MODEL=anthropic:claude-sonnet-4-5
docker compose up -d --build
curl -s http://localhost:8123/health
# Check logs for: "agent.lifecycle.created" with correct model
docker compose logs app | grep "agent.lifecycle"
```

Test with Google Gemini (if you have API key):
```bash
# Update .env: LLM_MODEL=google-gla:gemini-2.5-pro and set GOOGLE_API_KEY
docker compose down && docker compose up -d --build
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"jasque","messages":[{"role":"user","content":"Hello"}]}'
```

---

## ACCEPTANCE CRITERIA

- [ ] Single `LLM_MODEL` env var controls provider and model
- [ ] Startup fails fast with clear error if model format invalid
- [ ] Startup fails fast with clear error if API key missing for provider
- [ ] Default value maintains backward compatibility (anthropic:claude-sonnet-4-5)
- [ ] All existing tests pass
- [ ] New validation tests added and passing
- [ ] `.env.example` has clear placeholders for all providers
- [ ] Logs show provider and model on startup

---

## COMPLETION CHECKLIST

- [ ] Task 1: config.py updated with unified LLM_MODEL setting
- [ ] Task 2: base.py updated with provider parsing and validation
- [ ] Task 3: Tests updated and new validation tests added
- [ ] Task 4: .env.example updated with clear placeholders
- [ ] All validation commands pass
- [ ] Manual testing confirms feature works

---

## NOTES

### Backward Compatibility

The default value `anthropic:claude-sonnet-4-5` ensures existing deployments continue working without `.env` changes. Users who have `ANTHROPIC_MODEL` set will need to update to `LLM_MODEL` format.

### Supported Providers

Initial support for 3 providers:
- `anthropic:` - Anthropic Claude models
- `google-gla:` - Google Gemini via Generative Language API
- `openai:` - OpenAI models

Additional providers can be added by extending the `provider_key_map` in `base.py`.

### Why Not Runtime Switching?

The user requested simple env-based switching. Runtime switching would require:
- API endpoint for model changes
- Agent recreation logic
- State management

This is out of scope but could be added later if needed.

### Risk: Model Behavior Differences

Different LLMs may interpret the SYSTEM_PROMPT differently or have varying tool-calling capabilities. The prompt is generic enough that this should be minimal, but users should test with their specific use cases.
