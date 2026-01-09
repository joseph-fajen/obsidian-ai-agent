"""Vault utilities - shared vault management functionality."""

from app.shared.vault.exceptions import (
    FolderNotFoundError,
    NoteNotFoundError,
    PathTraversalError,
    VaultError,
)
from app.shared.vault.manager import VaultManager

__all__ = [
    "FolderNotFoundError",
    "NoteNotFoundError",
    "PathTraversalError",
    "VaultError",
    "VaultManager",
]
