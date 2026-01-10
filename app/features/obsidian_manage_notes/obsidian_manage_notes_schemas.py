"""Pydantic schemas for obsidian_manage_notes tool."""

from pydantic import BaseModel


class BulkNoteItem(BaseModel):
    """Item for bulk note operations."""

    path: str
    content: str | None = None
    folder: str | None = None
    task_identifier: str | None = None


class BulkErrorItem(BaseModel):
    """Error information for a failed bulk item."""

    path: str
    error: str


class NoteOperationResult(BaseModel):
    """Result from obsidian_manage_notes operations."""

    success: bool
    operation: str
    path: str
    message: str
    content: str | None = None
    affected_count: int | None = None
    errors: list[BulkErrorItem] | None = None
