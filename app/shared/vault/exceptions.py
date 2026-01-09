"""Vault-specific exception classes."""


class VaultError(Exception):
    """Base exception for vault-related errors."""

    pass


class PathTraversalError(VaultError):
    """Exception raised when path attempts to escape vault root."""

    pass


class NoteNotFoundError(VaultError):
    """Exception raised when a note is not found."""

    pass


class FolderNotFoundError(VaultError):
    """Exception raised when a folder is not found."""

    pass
