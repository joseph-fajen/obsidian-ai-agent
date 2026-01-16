"""Tests for user preferences loading and formatting."""

from pathlib import Path

import pytest

from app.features.chat.preferences import (
    PREFERENCES_TEMPLATE,
    DefaultFolders,
    ResponseStyle,
    UserPreferences,
    VaultPreferences,
    format_preferences_for_agent,
)
from app.shared.vault import PreferencesParseError, VaultManager


# =============================================================================
# Schema Tests
# =============================================================================


def test_user_preferences_defaults() -> None:
    """UserPreferences should have sensible defaults."""
    prefs = UserPreferences()
    assert prefs.date_format == "YYYY-MM-DD"
    assert prefs.time_format == "HH:mm"
    assert prefs.response_style.verbosity == "concise"


def test_user_preferences_custom_values() -> None:
    """UserPreferences should accept custom values."""
    prefs = UserPreferences(
        date_format="DD/MM/YYYY",
        default_folders=DefaultFolders(meeting_notes="Meetings/"),
    )
    assert prefs.date_format == "DD/MM/YYYY"
    assert prefs.default_folders.meeting_notes == "Meetings/"


def test_vault_preferences_with_context() -> None:
    """VaultPreferences should store additional context."""
    prefs = VaultPreferences(
        structured=UserPreferences(),
        additional_context="I use PARA method.",
    )
    assert prefs.additional_context == "I use PARA method."


# =============================================================================
# Formatting Tests
# =============================================================================


def test_format_preferences_basic() -> None:
    """format_preferences_for_agent should produce readable output."""
    prefs = VaultPreferences()
    result = format_preferences_for_agent(prefs)

    assert "## User Preferences" in result
    assert "Date format: YYYY-MM-DD" in result
    assert "Response verbosity: concise" in result


def test_format_preferences_with_folders() -> None:
    """format_preferences_for_agent should include folder preferences."""
    prefs = VaultPreferences(
        structured=UserPreferences(
            default_folders=DefaultFolders(
                meeting_notes="Meetings/",
                daily_notes="Daily/",
            )
        )
    )
    result = format_preferences_for_agent(prefs)

    assert "Meeting notes folder: Meetings/" in result
    assert "Daily notes folder: Daily/" in result


def test_format_preferences_with_additional_context() -> None:
    """format_preferences_for_agent should include additional context."""
    prefs = VaultPreferences(
        additional_context="I prefer bullet points.\nUse PARA method.",
    )
    result = format_preferences_for_agent(prefs)

    assert "## Additional User Context" in result
    assert "I prefer bullet points." in result


# =============================================================================
# VaultManager.load_preferences Tests
# =============================================================================


@pytest.fixture
def vault_with_preferences(tmp_path: Path) -> Path:
    """Create a vault with valid preferences file."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text("""---
date_format: "DD-MM-YYYY"
time_format: "HH:mm:ss"
default_folders:
  meeting_notes: "Meetings/"
  daily_notes: "Journal/"
response_style:
  verbosity: "detailed"
  use_bullet_points: false
---

## My Notes

I organize using the PARA method.
Meeting notes always include action items.
""")
    return tmp_path


@pytest.fixture
def vault_with_empty_jasque_folder(tmp_path: Path) -> Path:
    """Create a vault with _jasque folder but no preferences file."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()
    return tmp_path


@pytest.fixture
def vault_without_jasque_folder(tmp_path: Path) -> Path:
    """Create a vault without _jasque folder."""
    return tmp_path


@pytest.fixture
def vault_with_malformed_yaml(tmp_path: Path) -> Path:
    """Create a vault with invalid YAML in preferences."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text("""---
date_format: "YYYY-MM-DD"
  bad_indent: this is wrong
response_style
  missing_colon: true
---

Content here.
""")
    return tmp_path


@pytest.mark.asyncio
async def test_load_preferences_valid_file(vault_with_preferences: Path) -> None:
    """load_preferences should parse valid preferences file."""
    manager = VaultManager(vault_with_preferences)
    prefs = await manager.load_preferences()

    assert prefs is not None
    assert prefs.structured.date_format == "DD-MM-YYYY"
    assert prefs.structured.time_format == "HH:mm:ss"
    assert prefs.structured.default_folders.meeting_notes == "Meetings/"
    assert prefs.structured.default_folders.daily_notes == "Journal/"
    assert prefs.structured.response_style.verbosity == "detailed"
    assert prefs.structured.response_style.use_bullet_points is False
    assert "PARA method" in prefs.additional_context


@pytest.mark.asyncio
async def test_load_preferences_creates_template(vault_with_empty_jasque_folder: Path) -> None:
    """load_preferences should create template if folder exists but file doesn't."""
    manager = VaultManager(vault_with_empty_jasque_folder)
    prefs = await manager.load_preferences()

    # Should return None (template just created)
    assert prefs is None

    # Template should exist
    template_path = vault_with_empty_jasque_folder / "_jasque" / "preferences.md"
    assert template_path.exists()

    content = template_path.read_text()
    assert "Jasque User Preferences" in content
    assert "date_format:" in content


@pytest.mark.asyncio
async def test_load_preferences_no_folder(vault_without_jasque_folder: Path) -> None:
    """load_preferences should return None if _jasque folder doesn't exist."""
    manager = VaultManager(vault_without_jasque_folder)
    prefs = await manager.load_preferences()

    assert prefs is None

    # Should NOT create the folder
    jasque_dir = vault_without_jasque_folder / "_jasque"
    assert not jasque_dir.exists()


@pytest.mark.asyncio
async def test_load_preferences_malformed_yaml(vault_with_malformed_yaml: Path) -> None:
    """load_preferences should raise PreferencesParseError for invalid YAML."""
    manager = VaultManager(vault_with_malformed_yaml)

    with pytest.raises(PreferencesParseError) as exc_info:
        await manager.load_preferences()

    error_msg = str(exc_info.value)
    assert "Invalid YAML" in error_msg
    assert "_jasque/preferences.md" in error_msg


@pytest.mark.asyncio
async def test_load_preferences_partial_yaml(tmp_path: Path) -> None:
    """load_preferences should use defaults for missing/invalid fields."""
    jasque_dir = tmp_path / "_jasque"
    jasque_dir.mkdir()

    prefs_file = jasque_dir / "preferences.md"
    prefs_file.write_text("""---
date_format: "custom-format"
unknown_field: "ignored"
---

Just some context.
""")

    manager = VaultManager(tmp_path)
    prefs = await manager.load_preferences()

    assert prefs is not None
    assert prefs.structured.date_format == "custom-format"
    # Missing fields should have defaults
    assert prefs.structured.time_format == "HH:mm"
    assert prefs.structured.response_style.verbosity == "concise"


# =============================================================================
# Template Tests
# =============================================================================


def test_preferences_template_is_valid_yaml() -> None:
    """PREFERENCES_TEMPLATE should be parseable."""
    import frontmatter

    post = frontmatter.loads(PREFERENCES_TEMPLATE)
    assert "date_format" in post.metadata
    assert "default_folders" in post.metadata
    assert "response_style" in post.metadata


def test_preferences_template_validates_as_schema() -> None:
    """PREFERENCES_TEMPLATE should validate against UserPreferences schema."""
    import frontmatter

    post = frontmatter.loads(PREFERENCES_TEMPLATE)
    prefs = UserPreferences.model_validate(post.metadata)

    assert prefs.date_format == "YYYY-MM-DD"
    assert prefs.default_folders.meeting_notes == "Meetings/"
