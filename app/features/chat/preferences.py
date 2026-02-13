"""User preferences loaded from vault.

This module provides:
- Pydantic schemas for structured preferences (YAML frontmatter)
- VaultPreferences container combining structured + free-form context
- Formatting utility to convert preferences to agent context string
"""

from pydantic import BaseModel, Field


class DefaultFolders(BaseModel):
    """Default folder locations for different note types."""

    meeting_notes: str | None = None
    daily_notes: str | None = None
    projects: str | None = None


class ResponseStyle(BaseModel):
    """Preferences for how Jasque responds."""

    verbosity: str = Field(default="concise", description="concise or detailed")
    use_bullet_points: bool = True
    include_timestamps: bool = False


class UserPreferences(BaseModel):
    """Structured preferences parsed from YAML frontmatter."""

    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    default_folders: DefaultFolders = Field(default_factory=DefaultFolders)
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)
    search_exclude_folders: list[str] = Field(
        default_factory=lambda: ["copilot"],
        description="Folders to exclude from search operations",
    )


class VaultPreferences(BaseModel):
    """Complete preferences including free-form context."""

    structured: UserPreferences = Field(default_factory=UserPreferences)
    additional_context: str = ""  # Markdown body after frontmatter


def format_preferences_for_agent(preferences: VaultPreferences) -> str:
    """Format preferences as context string for agent prompt.

    Args:
        preferences: The loaded vault preferences.

    Returns:
        Formatted string to prepend to agent context.
    """
    lines: list[str] = ["## User Preferences", ""]

    s = preferences.structured

    # Date/time
    lines.append(f"- Date format: {s.date_format}")
    lines.append(f"- Time format: {s.time_format}")

    # Default folders (only if set)
    if s.default_folders.meeting_notes:
        lines.append(f"- Meeting notes folder: {s.default_folders.meeting_notes}")
    if s.default_folders.daily_notes:
        lines.append(f"- Daily notes folder: {s.default_folders.daily_notes}")
    if s.default_folders.projects:
        lines.append(f"- Projects folder: {s.default_folders.projects}")

    # Response style
    lines.append(f"- Response verbosity: {s.response_style.verbosity}")
    if s.response_style.use_bullet_points:
        lines.append("- Prefer bullet points in responses")
    if s.response_style.include_timestamps:
        lines.append("- Include timestamps in responses")

    # Additional context
    if preferences.additional_context.strip():
        lines.append("")
        lines.append("## Additional User Context")
        lines.append("")
        lines.append(preferences.additional_context.strip())

    return "\n".join(lines)


# Template for auto-creation
PREFERENCES_TEMPLATE = """---
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

# Folders to exclude from search results (default: ["copilot"])
# The _jasque folder is always excluded automatically
search_exclude_folders:
  - copilot
  # - templates  # Uncomment to also exclude templates folder
---

## Additional Context

Any free-form notes you want Jasque to know about. For example:

- I use the PARA method for organizing my vault
- Meeting notes should always include attendees and action items
- I prefer tasks formatted as `- [ ] task @due(date)`
"""
