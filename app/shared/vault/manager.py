"""Async VaultManager class for filesystem operations on Obsidian vaults."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import aiofiles
import aiofiles.os
import frontmatter  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.shared.vault.exceptions import (
    FolderAlreadyExistsError,
    FolderNotEmptyError,
    FolderNotFoundError,
    NoteAlreadyExistsError,
    NoteNotFoundError,
    PathTraversalError,
    PreferencesParseError,
    TaskNotFoundError,
)

if TYPE_CHECKING:
    from app.features.chat.preferences import VaultPreferences

logger = get_logger(__name__)


# =============================================================================
# Regex Patterns
# =============================================================================

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
TASK_PATTERN = re.compile(r"^(\s*)-\s*\[([ xX])\]\s*(.+)$", re.MULTILINE)
TAG_PATTERN = re.compile(r"#([a-zA-Z][a-zA-Z0-9_/-]*)")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class NoteInfo:
    """Basic information about a note."""

    path: str
    title: str
    tags: list[str]
    modified: datetime | None = None


@dataclass
class FolderInfo:
    """Information about a folder."""

    path: str
    name: str


@dataclass
class SearchResult:
    """A search result with matching line context."""

    path: str
    title: str
    snippet: str
    line_number: int


@dataclass
class BacklinkResult:
    """A note that links to another note."""

    path: str
    title: str
    context: str


@dataclass
class TaskInfo:
    """A task (checkbox) found in a note."""

    path: str
    task_text: str
    completed: bool
    line_number: int


@dataclass
class NoteContent:
    """Full note content including metadata."""

    path: str
    title: str
    content: str
    tags: list[str]
    metadata: dict[str, Any]


@dataclass
class FolderNode:
    """A node in the vault folder tree structure."""

    name: str
    path: str
    node_type: Literal["folder", "note"]
    children: list[FolderNode] | None = None


# =============================================================================
# VaultManager Class
# =============================================================================


class VaultManager:
    """Async manager for Obsidian vault filesystem operations.

    Provides methods for searching, listing, and reading notes and folders
    within an Obsidian vault. All paths are validated to prevent directory
    traversal attacks.
    """

    def __init__(self, vault_path: Path) -> None:
        """Initialize the VaultManager.

        Args:
            vault_path: Path to the Obsidian vault root.
        """
        self.vault_path = vault_path.resolve()

    def validate_path(self, path: str) -> Path:
        """Validate that a path stays within the vault root.

        Args:
            path: Relative path from vault root.

        Returns:
            Resolved absolute path within the vault.

        Raises:
            PathTraversalError: If path attempts to escape vault root.
        """
        # Handle empty or None path
        if not path:
            return self.vault_path

        full_path = (self.vault_path / path).resolve()
        if not full_path.is_relative_to(self.vault_path):
            raise PathTraversalError(f"Access denied: {path}")
        return full_path

    def _is_hidden(self, name: str) -> bool:
        """Check if a file or folder is hidden (starts with dot)."""
        return name.startswith(".")

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison (lowercase, spaces/hyphens/underscores equivalent)."""
        return name.casefold().replace("-", " ").replace("_", " ")

    async def _get_note_title(self, path: Path, content: str | None = None) -> str:
        """Extract title from note (frontmatter or filename).

        Args:
            path: Path to the note file.
            content: Optional pre-read content.

        Returns:
            Note title from frontmatter or filename stem.
        """
        if content is None:
            try:
                async with aiofiles.open(path, encoding="utf-8") as f:
                    content = await f.read()
            except (UnicodeDecodeError, OSError):
                return path.stem

        try:
            post = frontmatter.loads(content)
            if "title" in post.metadata:
                return str(post.metadata["title"])
        except Exception:  # noqa: S110 - Gracefully handle malformed frontmatter
            pass

        return path.stem

    async def _get_note_tags(self, content: str) -> list[str]:
        """Extract all tags from note content (frontmatter + inline).

        Args:
            content: Note content string.

        Returns:
            List of unique tags found in the note.
        """
        tags: set[str] = set()

        # Parse frontmatter tags
        # frontmatter library is untyped, so we cast to known types
        try:
            post = frontmatter.loads(content)
            fm_tags = post.metadata.get("tags", [])
            if isinstance(fm_tags, list):
                for tag_item in cast(list[object], fm_tags):
                    tags.add(str(tag_item))
            elif isinstance(fm_tags, str):
                tags.add(fm_tags)
        except Exception:  # noqa: S110 - Gracefully handle malformed frontmatter
            pass

        # Find inline tags
        inline_tags = TAG_PATTERN.findall(content)
        tags.update(inline_tags)

        return sorted(tags)

    async def _read_note_content(self, path: Path) -> str | None:
        """Read note content, returning None on error.

        Args:
            path: Path to the note file.

        Returns:
            Note content string or None if unreadable.
        """
        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                return await f.read()
        except (UnicodeDecodeError, OSError):
            return None

    async def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically using temp file + replace."""
        temp_path = path.with_suffix(f".{uuid.uuid4().hex[:8]}.tmp")
        try:
            async with aiofiles.open(temp_path, "w", encoding="utf-8") as f:
                await f.write(content)
            await aiofiles.os.replace(temp_path, path)
        except Exception:
            try:
                if await aiofiles.os.path.exists(temp_path):
                    await aiofiles.os.remove(temp_path)
            except OSError:
                pass
            raise

    async def list_notes(self, folder: str | None = None) -> list[NoteInfo]:
        """List all notes in the vault or a specific folder.

        Args:
            folder: Optional folder path to scope the listing.

        Returns:
            List of NoteInfo objects for each markdown file found.

        Raises:
            FolderNotFoundError: If the specified folder doesn't exist.
        """
        base_path = self.validate_path(folder or "")

        if not await aiofiles.os.path.exists(base_path):
            raise FolderNotFoundError(
                f"Folder not found: {folder}. "
                "Use obsidian_query_vault with operation='list_folders' to see available paths."
            )

        notes: list[NoteInfo] = []
        await self._collect_notes(base_path, notes)

        logger.info(
            "vault.query.list_notes_completed",
            folder=folder,
            count=len(notes),
        )
        return notes

    async def _collect_notes(self, path: Path, notes: list[NoteInfo]) -> None:
        """Recursively collect notes from a directory.

        Args:
            path: Directory path to scan.
            notes: List to append found notes to.
        """
        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._collect_notes(full_path, notes)
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                title = await self._get_note_title(full_path, content)
                tags = await self._get_note_tags(content) if content else []
                modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                rel_path = str(full_path.relative_to(self.vault_path))

                notes.append(NoteInfo(path=rel_path, title=title, tags=tags, modified=modified))

    async def list_folders(self, path: str | None = None) -> list[FolderInfo]:
        """List folders in the vault or a specific path.

        Args:
            path: Optional path to list folders from.

        Returns:
            List of FolderInfo objects for each folder found.

        Raises:
            FolderNotFoundError: If the specified path doesn't exist.
        """
        base_path = self.validate_path(path or "")

        if not await aiofiles.os.path.exists(base_path):
            raise FolderNotFoundError(
                f"Path not found: {path}. "
                "Use obsidian_query_vault with operation='list_folders' to see available paths."
            )

        folders: list[FolderInfo] = []

        try:
            entries = await aiofiles.os.listdir(base_path)
        except OSError:
            return folders

        for entry in entries:
            if self._is_hidden(entry):
                continue

            full_path = base_path / entry
            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                rel_path = str(full_path.relative_to(self.vault_path))
                folders.append(FolderInfo(path=rel_path, name=entry))

        logger.info("vault.query.list_folders_completed", path=path, count=len(folders))
        return sorted(folders, key=lambda f: f.name)

    async def read_note(self, path: str) -> NoteContent:
        """Read a note's full content and metadata.

        Args:
            path: Relative path to the note.

        Returns:
            NoteContent with full content and metadata.

        Raises:
            NoteNotFoundError: If the note doesn't exist.
        """
        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise NoteNotFoundError(
                f"Note not found: {path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        content = await self._read_note_content(full_path)
        if content is None:
            raise NoteNotFoundError(f"Could not read note: {path}")

        title = await self._get_note_title(full_path, content)
        tags = await self._get_note_tags(content)

        try:
            post = frontmatter.loads(content)
            metadata = dict(post.metadata)
            body = post.content
        except Exception:
            metadata = {}
            body = content

        return NoteContent(path=path, title=title, content=body, tags=tags, metadata=metadata)

    async def create_note(
        self,
        path: str,
        content: str,
        folder: str | None = None,
    ) -> NoteContent:
        """Create a new note in the vault."""
        if folder:
            full_rel_path = f"{folder.rstrip('/')}/{path.lstrip('/')}"
        else:
            full_rel_path = path

        if not full_rel_path.endswith(".md"):
            full_rel_path += ".md"

        full_path = self.validate_path(full_rel_path)

        if await aiofiles.os.path.exists(full_path):
            raise NoteAlreadyExistsError(
                f"Note already exists: {full_rel_path}. "
                "Use operation='update' to modify existing notes."
            )

        parent = full_path.parent
        if not await aiofiles.os.path.exists(parent):
            await aiofiles.os.makedirs(parent, exist_ok=True)

        await self._atomic_write(full_path, content)
        logger.info("vault.notes.create_completed", path=full_rel_path)

        return await self.read_note(full_rel_path)

    async def update_note(
        self,
        path: str,
        content: str,
        preserve_frontmatter: bool = True,
    ) -> NoteContent:
        """Update an existing note's content."""
        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise NoteNotFoundError(
                f"Note not found: {path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        if preserve_frontmatter:
            existing = await self._read_note_content(full_path)
            if existing:
                try:
                    post = frontmatter.loads(existing)
                    post.content = content
                    final_content = frontmatter.dumps(post, sort_keys=False)
                except Exception:
                    final_content = content
            else:
                final_content = content
        else:
            final_content = content

        await self._atomic_write(full_path, final_content)
        logger.info("vault.notes.update_completed", path=path)

        return await self.read_note(path)

    async def append_note(self, path: str, content: str) -> NoteContent:
        """Append content to an existing note."""
        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise NoteNotFoundError(
                f"Note not found: {path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        existing = await self._read_note_content(full_path)
        if existing is None:
            raise NoteNotFoundError(f"Could not read note: {path}")

        if existing and not existing.endswith("\n"):
            new_content = existing + "\n" + content
        else:
            new_content = (existing or "") + content

        await self._atomic_write(full_path, new_content)
        logger.info("vault.notes.append_completed", path=path)

        return await self.read_note(path)

    async def delete_note(self, path: str) -> None:
        """Delete a note from the vault."""
        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise NoteNotFoundError(
                f"Note not found: {path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        await aiofiles.os.remove(full_path)
        logger.info("vault.notes.delete_completed", path=path)

    async def complete_task(self, path: str, task_identifier: str) -> TaskInfo:
        """Mark a task as complete using cascading match: line number -> exact -> substring."""
        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise NoteNotFoundError(
                f"Note not found: {path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        content = await self._read_note_content(full_path)
        if content is None:
            raise NoteNotFoundError(f"Could not read note: {path}")

        # Find all tasks
        tasks: list[tuple[re.Match[str], int, str, bool]] = []
        for match in TASK_PATTERN.finditer(content):
            checkbox = match.group(2)
            task_text = match.group(3).strip()
            line_num = content[: match.start()].count("\n") + 1
            completed = checkbox.lower() == "x"
            tasks.append((match, line_num, task_text, completed))

        if not tasks:
            raise TaskNotFoundError(
                f"No tasks found in {path}. "
                "Use obsidian_query_vault with operation='list_tasks' to find notes with tasks."
            )

        # Find target task
        target_match: re.Match[str] | None = None
        target_info: tuple[int, str, bool] | None = None

        # 1. Try line number
        try:
            line_num = int(task_identifier)
            for match, ln, text, completed in tasks:
                if ln == line_num:
                    if completed:
                        raise TaskNotFoundError(
                            f"Task at line {line_num} is already completed: '{text}'"
                        )
                    target_match = match
                    target_info = (ln, text, completed)
                    break
            if target_match is None:
                task_lines = [str(ln) for _, ln, _, _ in tasks]
                raise TaskNotFoundError(
                    f"No task at line {line_num}. Tasks at lines: {', '.join(task_lines)}"
                )
        except ValueError:
            id_lower = task_identifier.lower()

            # 2. Exact match
            exact = [(m, ln, t, c) for m, ln, t, c in tasks if t.lower() == id_lower and not c]
            if len(exact) == 1:
                target_match, ln, text, _ = exact[0]
                target_info = (ln, text, False)
            elif len(exact) == 0:
                # 3. Substring match
                substr = [(m, ln, t, c) for m, ln, t, c in tasks if id_lower in t.lower() and not c]
                if len(substr) == 1:
                    target_match, ln, text, _ = substr[0]
                    target_info = (ln, text, False)
                elif len(substr) > 1:
                    matches_str = ", ".join([f"'{t}' (line {ln})" for _, ln, t, _ in substr])
                    raise TaskNotFoundError(
                        f"Multiple tasks match '{task_identifier}': {matches_str}"
                    ) from None
                else:
                    available = ", ".join([f"'{t}'" for _, _, t, c in tasks if not c])
                    raise TaskNotFoundError(
                        f"Task not found: '{task_identifier}'. Available: {available or 'none'}"
                    ) from None
            else:
                matches_str = ", ".join([f"'{t}' (line {ln})" for _, ln, t, _ in exact])
                raise TaskNotFoundError(
                    f"Multiple tasks match '{task_identifier}': {matches_str}"
                ) from None

        # Type narrowing: all branches above either set target_match/target_info or raise
        assert target_match is not None  # noqa: S101
        assert target_info is not None  # noqa: S101

        # Replace checkbox
        line_num, task_text, _ = target_info
        replacement = f"{target_match.group(1)}- [x] {target_match.group(3)}"
        new_content = content[: target_match.start()] + replacement + content[target_match.end() :]

        await self._atomic_write(full_path, new_content)
        logger.info("vault.notes.complete_task_completed", path=path, task=task_text)

        return TaskInfo(path=path, task_text=task_text, completed=True, line_number=line_num)

    async def search_text(
        self,
        query: str,
        path: str | None = None,
        limit: int = 50,
    ) -> list[SearchResult]:
        """Full-text search across notes.

        Args:
            query: Search query string (case-insensitive).
            path: Optional folder to scope the search.
            limit: Maximum number of results to return.

        Returns:
            List of SearchResult objects with matching notes.
        """
        base_path = self.validate_path(path or "")
        results: list[SearchResult] = []
        query_lower = query.lower()

        await self._search_directory(base_path, query_lower, results, limit)

        logger.info(
            "vault.query.search_text_completed",
            query=query,
            path=path,
            count=len(results),
        )
        return results

    async def _search_directory(
        self,
        path: Path,
        query: str,
        results: list[SearchResult],
        limit: int,
    ) -> None:
        """Recursively search a directory for matching notes.

        Args:
            path: Directory path to search.
            query: Lowercase search query.
            results: List to append results to.
            limit: Maximum total results.
        """
        if len(results) >= limit:
            return

        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if len(results) >= limit:
                return

            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._search_directory(full_path, query, results, limit)
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                if content is None:
                    continue

                lines = content.split("\n")
                for i, line in enumerate(lines, start=1):
                    if query in line.lower():
                        title = await self._get_note_title(full_path, content)
                        rel_path = str(full_path.relative_to(self.vault_path))
                        # Create snippet: line with context
                        snippet = line.strip()[:200]
                        results.append(
                            SearchResult(
                                path=rel_path,
                                title=title,
                                snippet=snippet,
                                line_number=i,
                            )
                        )
                        if len(results) >= limit:
                            return
                        break  # One result per file

    async def find_by_tag(
        self,
        tags: list[str],
        path: str | None = None,
        limit: int = 50,
    ) -> list[NoteInfo]:
        """Find notes containing specified tags.

        Args:
            tags: List of tags to search for (matches any).
            path: Optional folder to scope the search.
            limit: Maximum number of results.

        Returns:
            List of NoteInfo objects for matching notes.
        """
        base_path = self.validate_path(path or "")
        results: list[NoteInfo] = []
        tag_set = {t.lower().lstrip("#") for t in tags}

        await self._find_by_tag_directory(base_path, tag_set, results, limit)

        logger.info(
            "vault.query.find_by_tag_completed",
            tags=tags,
            path=path,
            count=len(results),
        )
        return results

    async def _find_by_tag_directory(
        self,
        path: Path,
        tags: set[str],
        results: list[NoteInfo],
        limit: int,
    ) -> None:
        """Recursively find notes with matching tags.

        Args:
            path: Directory path to search.
            tags: Set of lowercase tags to match.
            results: List to append results to.
            limit: Maximum total results.
        """
        if len(results) >= limit:
            return

        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if len(results) >= limit:
                return

            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._find_by_tag_directory(full_path, tags, results, limit)
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                if content is None:
                    continue

                note_tags = await self._get_note_tags(content)
                note_tags_lower = {t.lower() for t in note_tags}

                if tags & note_tags_lower:  # Any tag matches
                    title = await self._get_note_title(full_path, content)
                    rel_path = str(full_path.relative_to(self.vault_path))
                    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                    results.append(
                        NoteInfo(path=rel_path, title=title, tags=note_tags, modified=modified)
                    )

    async def find_by_name(
        self,
        query: str,
        path: str | None = None,
        limit: int = 50,
    ) -> list[NoteInfo]:
        """Find notes by filename or frontmatter title.

        Args:
            query: Note name to search for (case-insensitive, normalized).
                   The .md extension is stripped if present.
            path: Optional folder to scope the search.
            limit: Maximum number of results.

        Returns:
            List of NoteInfo objects, sorted by match quality:
            1. Exact filename matches (shortest path first)
            2. Filename contains matches (shortest path first)
            3. Frontmatter title matches (shortest path first)
        """
        base_path = self.validate_path(path or "")

        # Normalize query: strip .md extension, normalize for comparison
        query_clean = query.removesuffix(".md")
        query_normalized = self._normalize_name(query_clean)

        # Collect all matching notes with match type for sorting
        exact_matches: list[NoteInfo] = []
        contains_matches: list[NoteInfo] = []
        title_matches: list[NoteInfo] = []

        await self._find_by_name_directory(
            base_path,
            query_normalized,
            exact_matches,
            contains_matches,
            title_matches,
        )

        # Combine results: exact first, then contains, then title matches
        # Within each category, sort by path length (shorter = more relevant)
        exact_matches.sort(key=lambda n: len(n.path))
        contains_matches.sort(key=lambda n: len(n.path))
        title_matches.sort(key=lambda n: len(n.path))

        results = exact_matches + contains_matches + title_matches
        results = results[:limit]

        logger.info(
            "vault.query.find_by_name_completed",
            query=query,
            path=path,
            count=len(results),
        )
        return results

    async def _find_by_name_directory(
        self,
        path: Path,
        query_normalized: str,
        exact_matches: list[NoteInfo],
        contains_matches: list[NoteInfo],
        title_matches: list[NoteInfo],
    ) -> None:
        """Recursively find notes matching the query by name or title.

        Args:
            path: Directory path to search.
            query_normalized: Normalized query string.
            exact_matches: List to append exact filename matches to.
            contains_matches: List to append filename contains matches to.
            title_matches: List to append frontmatter title matches to.
        """
        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._find_by_name_directory(
                    full_path,
                    query_normalized,
                    exact_matches,
                    contains_matches,
                    title_matches,
                )
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                if content is None:
                    continue

                # Normalize filename (without .md extension)
                filename_stem = entry.removesuffix(".md")
                filename_normalized = self._normalize_name(filename_stem)

                rel_path = str(full_path.relative_to(self.vault_path))
                title = await self._get_note_title(full_path, content)
                tags = await self._get_note_tags(content)
                modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)

                note_info = NoteInfo(path=rel_path, title=title, tags=tags, modified=modified)

                # Check for exact filename match
                if filename_normalized == query_normalized:
                    exact_matches.append(note_info)
                # Check for filename contains match
                elif query_normalized in filename_normalized:
                    contains_matches.append(note_info)
                # Check for frontmatter title match
                else:
                    title_normalized = self._normalize_name(title)
                    if query_normalized == title_normalized or query_normalized in title_normalized:
                        title_matches.append(note_info)

    async def get_backlinks(self, note_path: str, limit: int = 50) -> list[BacklinkResult]:
        """Find notes that link to the specified note.

        Args:
            note_path: Path to the target note.
            limit: Maximum number of results.

        Returns:
            List of BacklinkResult objects for linking notes.
        """
        # Validate the target note exists
        target_path = self.validate_path(note_path)
        if not await aiofiles.os.path.exists(target_path):
            raise NoteNotFoundError(
                f"Note not found: {note_path}. "
                "Use obsidian_query_vault with operation='list_notes' to see available notes."
            )

        # Get the note name without extension for wikilink matching
        note_name = Path(note_path).stem

        results: list[BacklinkResult] = []
        await self._find_backlinks(self.vault_path, note_name, note_path, results, limit)

        logger.info(
            "vault.query.get_backlinks_completed",
            note_path=note_path,
            count=len(results),
        )
        return results

    async def _find_backlinks(
        self,
        path: Path,
        note_name: str,
        original_path: str,
        results: list[BacklinkResult],
        limit: int,
    ) -> None:
        """Recursively find notes linking to the target.

        Args:
            path: Directory path to search.
            note_name: Target note name (without extension).
            original_path: Original path to exclude from results.
            results: List to append results to.
            limit: Maximum total results.
        """
        if len(results) >= limit:
            return

        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if len(results) >= limit:
                return

            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._find_backlinks(full_path, note_name, original_path, results, limit)
            elif entry.endswith(".md"):
                rel_path = str(full_path.relative_to(self.vault_path))
                if rel_path == original_path:
                    continue

                content = await self._read_note_content(full_path)
                if content is None:
                    continue

                # Find wikilinks
                links = WIKILINK_PATTERN.findall(content)
                if note_name in links:
                    title = await self._get_note_title(full_path, content)
                    # Find context line
                    context = ""
                    for line in content.split("\n"):
                        if f"[[{note_name}]]" in line or f"[[{note_name}|" in line:
                            context = line.strip()[:200]
                            break
                    results.append(BacklinkResult(path=rel_path, title=title, context=context))

    async def get_tags(self) -> list[str]:
        """Get all unique tags in the vault.

        Returns:
            Sorted list of unique tags.
        """
        tags: set[str] = set()
        await self._collect_tags(self.vault_path, tags)

        logger.info("vault.query.get_tags_completed", count=len(tags))
        return sorted(tags)

    async def _collect_tags(self, path: Path, tags: set[str]) -> None:
        """Recursively collect tags from all notes.

        Args:
            path: Directory path to scan.
            tags: Set to add found tags to.
        """
        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._collect_tags(full_path, tags)
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                if content:
                    note_tags = await self._get_note_tags(content)
                    tags.update(note_tags)

    async def list_tasks(
        self,
        path: str | None = None,
        include_completed: bool = False,
        limit: int = 50,
    ) -> list[TaskInfo]:
        """Find task checkboxes across the vault.

        Args:
            path: Optional folder to scope the search.
            include_completed: Whether to include completed tasks.
            limit: Maximum number of results.

        Returns:
            List of TaskInfo objects for found tasks.
        """
        base_path = self.validate_path(path or "")
        results: list[TaskInfo] = []

        await self._find_tasks(base_path, include_completed, results, limit)

        logger.info(
            "vault.query.list_tasks_completed",
            path=path,
            include_completed=include_completed,
            count=len(results),
        )
        return results

    async def _find_tasks(
        self,
        path: Path,
        include_completed: bool,
        results: list[TaskInfo],
        limit: int,
    ) -> None:
        """Recursively find tasks in notes.

        Args:
            path: Directory path to search.
            include_completed: Whether to include completed tasks.
            results: List to append results to.
            limit: Maximum total results.
        """
        if len(results) >= limit:
            return

        try:
            entries = await aiofiles.os.listdir(path)
        except OSError:
            return

        for entry in entries:
            if len(results) >= limit:
                return

            if self._is_hidden(entry):
                continue

            full_path = path / entry

            try:
                stat = await aiofiles.os.stat(full_path)
            except OSError:
                continue

            if stat.st_mode & 0o170000 == 0o040000:  # Is directory
                await self._find_tasks(full_path, include_completed, results, limit)
            elif entry.endswith(".md"):
                content = await self._read_note_content(full_path)
                if content is None:
                    continue

                rel_path = str(full_path.relative_to(self.vault_path))

                # Find tasks using regex
                for match in TASK_PATTERN.finditer(content):
                    if len(results) >= limit:
                        return

                    checkbox = match.group(2)
                    task_text = match.group(3).strip()
                    completed = checkbox.lower() == "x"

                    if not include_completed and completed:
                        continue

                    # Calculate line number
                    line_number = content[: match.start()].count("\n") + 1

                    results.append(
                        TaskInfo(
                            path=rel_path,
                            task_text=task_text,
                            completed=completed,
                            line_number=line_number,
                        )
                    )

    # =========================================================================
    # Structure Management Methods
    # =========================================================================

    async def create_folder(self, path: str) -> FolderInfo:
        """Create a folder, including any necessary parent folders.

        Args:
            path: Relative path for the new folder.

        Returns:
            FolderInfo for the created folder.

        Raises:
            FolderAlreadyExistsError: If the folder already exists.
            PathTraversalError: If path attempts to escape vault root.
        """
        full_path = self.validate_path(path)
        if await aiofiles.os.path.exists(full_path):
            raise FolderAlreadyExistsError(
                f"Folder already exists: {path}. Use a different path or delete existing folder first."
            )
        await aiofiles.os.makedirs(full_path, exist_ok=False)
        logger.info("vault.structure.folder_created", path=path)
        return FolderInfo(path=path, name=full_path.name)

    async def rename(self, path: str, new_path: str) -> FolderInfo | NoteContent:
        """Rename a file or folder.

        Args:
            path: Current relative path of the item.
            new_path: New relative path for the item.

        Returns:
            FolderInfo for folders, NoteContent for notes.

        Raises:
            NoteNotFoundError: If source note doesn't exist.
            FolderNotFoundError: If source folder doesn't exist.
            NoteAlreadyExistsError: If destination note exists.
            FolderAlreadyExistsError: If destination folder exists.
        """
        full_path = self.validate_path(path)
        full_new_path = self.validate_path(new_path)

        if not await aiofiles.os.path.exists(full_path):
            if path.endswith(".md"):
                raise NoteNotFoundError(
                    f"Note not found: {path}. Use obsidian_query_vault to list notes."
                )
            raise FolderNotFoundError(
                f"Folder not found: {path}. Use list_structure to see folders."
            )

        if await aiofiles.os.path.exists(full_new_path):
            if new_path.endswith(".md"):
                raise NoteAlreadyExistsError(f"Note already exists: {new_path}.")
            raise FolderAlreadyExistsError(f"Folder already exists: {new_path}.")

        await aiofiles.os.rename(full_path, full_new_path)
        logger.info("vault.structure.renamed", old_path=path, new_path=new_path)

        if await aiofiles.os.path.isfile(full_new_path):
            return await self.read_note(new_path)
        return FolderInfo(path=new_path, name=full_new_path.name)

    async def delete_folder(self, path: str, force: bool = False) -> None:
        """Delete a folder. Use force=True for non-empty folders.

        Args:
            path: Relative path of the folder to delete.
            force: If True, delete even if folder is not empty.

        Raises:
            FolderNotFoundError: If folder doesn't exist or path is a file.
            FolderNotEmptyError: If folder is not empty and force=False.
        """
        import asyncio
        import shutil

        full_path = self.validate_path(path)

        if not await aiofiles.os.path.exists(full_path):
            raise FolderNotFoundError(f"Folder not found: {path}.")
        if not await aiofiles.os.path.isdir(full_path):
            raise FolderNotFoundError(
                f"Path is not a folder: {path}. Use obsidian_manage_notes to delete notes."
            )

        contents = await aiofiles.os.listdir(full_path)
        if contents and not force:
            raise FolderNotEmptyError(
                f"Folder not empty: {path}. Use force=True or empty folder first."
            )

        if force and contents:
            await asyncio.to_thread(shutil.rmtree, full_path)
        else:
            await aiofiles.os.rmdir(full_path)

        logger.info("vault.structure.folder_deleted", path=path, force=force)

    async def move(self, path: str, new_path: str) -> FolderInfo | NoteContent:
        """Move a file or folder to a new location. Creates parent dirs if needed.

        Args:
            path: Current relative path of the item.
            new_path: Destination relative path.

        Returns:
            FolderInfo for folders, NoteContent for notes.

        Raises:
            NoteNotFoundError: If source note doesn't exist.
            FolderNotFoundError: If source folder doesn't exist.
            NoteAlreadyExistsError: If destination note exists.
            FolderAlreadyExistsError: If destination folder exists.
        """
        full_path = self.validate_path(path)
        full_new_path = self.validate_path(new_path)

        if not await aiofiles.os.path.exists(full_path):
            if path.endswith(".md"):
                raise NoteNotFoundError(f"Note not found: {path}.")
            raise FolderNotFoundError(f"Folder not found: {path}.")

        if await aiofiles.os.path.exists(full_new_path):
            if new_path.endswith(".md"):
                raise NoteAlreadyExistsError(f"Destination exists: {new_path}.")
            raise FolderAlreadyExistsError(f"Destination exists: {new_path}.")

        parent = full_new_path.parent
        if not await aiofiles.os.path.exists(parent):
            await aiofiles.os.makedirs(parent, exist_ok=True)

        await aiofiles.os.rename(full_path, full_new_path)
        logger.info("vault.structure.moved", old_path=path, new_path=new_path)

        if await aiofiles.os.path.isfile(full_new_path):
            return await self.read_note(new_path)
        return FolderInfo(path=new_path, name=full_new_path.name)

    async def list_structure(self, path: str | None = None) -> list[FolderNode]:
        """Get hierarchical folder/file tree structure.

        Args:
            path: Optional folder to scope the listing.

        Returns:
            List of FolderNode objects representing the tree structure.

        Raises:
            FolderNotFoundError: If the specified path doesn't exist.
        """
        if path:
            full_path = self.validate_path(path)
            if not await aiofiles.os.path.exists(full_path):
                raise FolderNotFoundError(f"Folder not found: {path}.")
        else:
            full_path = self.vault_path
        return await self._build_structure_tree(full_path, path or "")

    async def _build_structure_tree(self, full_path: Path, rel_path: str) -> list[FolderNode]:
        """Recursively build folder tree structure.

        Args:
            full_path: Absolute path to scan.
            rel_path: Relative path for the current directory.

        Returns:
            List of FolderNode objects for children.
        """
        nodes: list[FolderNode] = []
        try:
            entries = await aiofiles.os.listdir(full_path)
        except OSError:
            return nodes

        for name in sorted(entries):
            if self._is_hidden(name):
                continue
            entry_path = full_path / name
            entry_rel = f"{rel_path}/{name}".lstrip("/")
            is_dir = await aiofiles.os.path.isdir(entry_path)

            if is_dir:
                children = await self._build_structure_tree(entry_path, entry_rel)
                nodes.append(
                    FolderNode(name=name, path=entry_rel, node_type="folder", children=children)
                )
            elif name.endswith(".md"):
                nodes.append(FolderNode(name=name, path=entry_rel, node_type="note", children=None))
        return nodes

    # =========================================================================
    # Preferences Methods
    # =========================================================================

    async def load_preferences(self) -> VaultPreferences | None:
        """Load user preferences from _jasque/preferences.md.

        Behavior:
        - If file exists: parse and return preferences
        - If folder exists but file doesn't: create template, return None
        - If folder doesn't exist: return None (log warning)
        - If YAML is malformed: raise PreferencesParseError

        Returns:
            VaultPreferences if file exists and is valid, None otherwise.

        Raises:
            PreferencesParseError: If file exists but has invalid YAML syntax.
        """
        from yaml import YAMLError  # type: ignore[import-untyped]

        from app.features.chat.preferences import (
            PREFERENCES_TEMPLATE,
            UserPreferences,
            VaultPreferences,
        )

        prefs_path = self.vault_path / "_jasque" / "preferences.md"
        folder_path = self.vault_path / "_jasque"

        # Check if preferences file exists
        if not await aiofiles.os.path.exists(prefs_path):
            # Check if folder exists - if so, create template
            if await aiofiles.os.path.exists(folder_path):
                await self._atomic_write(prefs_path, PREFERENCES_TEMPLATE)
                logger.info(
                    "vault.preferences.template_created",
                    path="_jasque/preferences.md",
                )
            else:
                logger.warning(
                    "vault.preferences.not_found",
                    path="_jasque/preferences.md",
                )
            return None

        # Read the file
        content = await self._read_note_content(prefs_path)
        if content is None:
            logger.warning(
                "vault.preferences.read_failed",
                path="_jasque/preferences.md",
            )
            return None

        # Parse frontmatter
        try:
            post = frontmatter.loads(content)
            metadata = dict(post.metadata)
            body = post.content
        except YAMLError as e:
            raise PreferencesParseError(
                f"Invalid YAML in _jasque/preferences.md: {e}. "
                "Check the file for syntax errors (missing colons, incorrect indentation)."
            ) from e

        # Validate against schema
        try:
            structured = UserPreferences.model_validate(metadata)
        except Exception as e:
            # Log validation error but use defaults for invalid fields
            logger.warning(
                "vault.preferences.validation_warning",
                error=str(e),
            )
            structured = UserPreferences()

        logger.info("vault.preferences.loaded", has_structured=bool(metadata))

        return VaultPreferences(
            structured=structured,
            additional_context=body,
        )
