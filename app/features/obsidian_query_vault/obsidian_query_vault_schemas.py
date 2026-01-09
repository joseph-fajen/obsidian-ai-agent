"""Pydantic schemas for obsidian_query_vault tool."""

from datetime import datetime

from pydantic import BaseModel

# =============================================================================
# Result Item Models
# =============================================================================


class QueryResultItem(BaseModel):
    """A single item in query results."""

    path: str
    title: str | None = None
    snippet: str | None = None
    tags: list[str] | None = None
    modified: datetime | None = None
    task_text: str | None = None
    task_completed: bool | None = None
    line_number: int | None = None


# =============================================================================
# Query Result Model
# =============================================================================


class QueryResult(BaseModel):
    """Result from obsidian_query_vault operations."""

    success: bool
    operation: str
    total_count: int
    results: list[QueryResultItem]
    truncated: bool = False
    message: str | None = None
