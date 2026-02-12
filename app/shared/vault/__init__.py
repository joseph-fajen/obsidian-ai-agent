"""Vault utilities - shared vault management functionality."""

from app.shared.vault.exceptions import (
    ConversationHistoryError,
    FolderAlreadyExistsError,
    FolderNotEmptyError,
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    PreferencesParseError,
    TaskNotFoundError,
    VaultError,
)
from app.shared.vault.manager import FolderNode, VaultManager

__all__ = [
    "ConversationHistoryError",
    "FolderAlreadyExistsError",
    "FolderNode",
    "FolderNotEmptyError",
    "FolderNotFoundError",
    "NoteAlreadyExistsError",
    "NoteNotFoundError",
    "PathTraversalError",
    "PreferencesParseError",
    "TaskNotFoundError",
    "VaultError",
    "VaultManager",
]
