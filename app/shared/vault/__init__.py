"""Vault utilities - shared vault management functionality."""

from app.shared.vault.exceptions import (
    FolderAlreadyExistsError,
    FolderNotEmptyError,
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    TaskNotFoundError,
    VaultError,
)
from app.shared.vault.manager import FolderNode, VaultManager

__all__ = [
    "FolderAlreadyExistsError",
    "FolderNode",
    "FolderNotEmptyError",
    "FolderNotFoundError",
    "NoteAlreadyExistsError",
    "NoteNotFoundError",
    "PathTraversalError",
    "TaskNotFoundError",
    "VaultError",
    "VaultManager",
]
