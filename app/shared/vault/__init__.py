"""Vault utilities - shared vault management functionality."""

from app.shared.vault.exceptions import (
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    TaskNotFoundError,
    VaultError,
)
from app.shared.vault.manager import VaultManager

__all__ = [
    "FolderNotFoundError",
    "NoteAlreadyExistsError",
    "NoteNotFoundError",
    "PathTraversalError",
    "TaskNotFoundError",
    "VaultError",
    "VaultManager",
]
