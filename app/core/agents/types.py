"""Type definitions for Pydantic AI agents."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel


@dataclass
class AgentDependencies:
    """Dependencies injected into agent tools via RunContext."""

    request_id: str = ""
    vault_path: Path = field(default_factory=lambda: Path("/vault"))


class TokenUsage(BaseModel):
    """Token usage information from LLM call."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
