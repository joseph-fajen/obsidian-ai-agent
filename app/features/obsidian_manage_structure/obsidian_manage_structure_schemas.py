"""Pydantic schemas for obsidian_manage_structure tool."""

from pydantic import BaseModel

from app.shared.vault import FolderNode


class BulkStructureItem(BaseModel):
    """Item for bulk structure operations (move/rename)."""

    path: str
    new_path: str


class BulkErrorItem(BaseModel):
    """Error information for a failed bulk item."""

    path: str
    error: str


class StructureOperationResult(BaseModel):
    """Result from obsidian_manage_structure operations."""

    success: bool
    operation: str
    path: str
    message: str
    new_path: str | None = None
    affected_count: int | None = None
    errors: list[BulkErrorItem] | None = None
    structure: list[FolderNode] | None = None
