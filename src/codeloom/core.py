"""Core module — Snippet dataclass and SQLite-backed SnippetStore."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Snippet:
    """Represents a single code snippet."""

    id: Optional[int] = None
    title: str = ""
    language: str = ""
    code: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def tags_csv(self) -> str:
        """Return tags as a comma-separated string."""
        return ",".join(self.tags)

    @staticmethod
    def tags_from_csv(csv: str) -> list[str]:
        """Parse a comma-separated string into a tag list."""
        return [t.strip() for t in csv.split(",") if t.strip()] if csv else []


# ---------------------------------------------------------------------------
# Language detection heuristic
# ---------------------------------------------------------------------------

_LANG_KEYWORDS: dict[str, list[str]] = {
    "python": ["def ", "import ", "class ", "print(", "self.", "elif ", "lambda "],
    "javascript": ["const ", "let ", "function ", "=>", "console.log", "require(", "module.exports"],
    "typescript": ["interface ", ": string", ": number", ": boolean", "import {", "export default"],
    "java": ["public class", "System.out", "void ", "String[]", "private ", "protected "],
    "go": ["func ", "package ", "fmt.", "import (", ":= ", "go func"],
    "rust": ["fn ", "let mut", "impl ", "pub fn", "println!", "use std"],
    "c": ["#include", "printf(", "int main", "malloc(", "sizeof("],
    "sql": ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE", "ALTER TABLE"],
    "bash": ["#!/bin/bash", "echo ", "if [", "fi", "done", "#!/bin/sh"],
    "html": ["<!DOCTYPE", "<html", "<div", "<span", "<head>", "<body>"],
    "css": ["{", "color:", "margin:", "padding:", "display:", "@media"],
    "ruby": ["def ", "end", "puts ", "require ", "class ", "attr_accessor"],
}


def detect_language(code: str) -> str:
    """Detect programming language from code content using keyword heuristics."""
    scores: dict[str, int] = {}
    for lang, keywords in _LANG_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in code)
        if score > 0:
            scores[lang] = score
    if not scores:
        return "text"
    return max(scores, key=scores.get)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# SQLite-backed snippet store
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT '',
    code        TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS snippets_fts USING fts5(
    title, description, code, tags, content=snippets, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS snippets_ai AFTER INSERT ON snippets BEGIN
    INSERT INTO snippets_fts(rowid, title, description, code, tags)
    VALUES (new.id, new.title, new.description, new.code, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS snippets_ad AFTER DELETE ON snippets BEGIN
    INSERT INTO snippets_fts(snippets_fts, rowid, title, description, code, tags)
    VALUES ('delete', old.id, old.title, old.description, old.code, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS snippets_au AFTER UPDATE ON snippets BEGIN
    INSERT INTO snippets_fts(snippets_fts, rowid, title, description, code, tags)
    VALUES ('delete', old.id, old.title, old.description, old.code, old.tags);
    INSERT INTO snippets_fts(rowid, title, description, code, tags)
    VALUES (new.id, new.title, new.description, new.code, new.tags);
END;
"""


class SnippetStore:
    """SQLite-backed code snippet storage with full-text search."""

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    # -- CRUD ---------------------------------------------------------------

    def add(self, snippet: Snippet) -> Snippet:
        """Add a new snippet and return it with its assigned id."""
        if not snippet.language and snippet.code:
            snippet.language = detect_language(snippet.code)
        cur = self._conn.execute(
            "INSERT INTO snippets (title, language, code, tags, description, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snippet.title, snippet.language, snippet.code,
             snippet.tags_csv(), snippet.description, snippet.created_at),
        )
        self._conn.commit()
        snippet.id = cur.lastrowid
        return snippet

    def get(self, snippet_id: int) -> Optional[Snippet]:
        """Retrieve a snippet by id."""
        row = self._conn.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,)).fetchone()
        return self._row_to_snippet(row) if row else None

    def update(self, snippet: Snippet) -> bool:
        """Update an existing snippet. Returns True on success."""
        if snippet.id is None:
            return False
        self._conn.execute(
            "UPDATE snippets SET title=?, language=?, code=?, tags=?, description=? WHERE id=?",
            (snippet.title, snippet.language, snippet.code,
             snippet.tags_csv(), snippet.description, snippet.id),
        )
        self._conn.commit()
        return self._conn.total_changes > 0

    def delete(self, snippet_id: int) -> bool:
        """Delete a snippet by id. Returns True if a row was deleted."""
        self._conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
        self._conn.commit()
        return self._conn.total_changes > 0

    # -- Search & filter ----------------------------------------------------

    def search(self, query: str) -> list[Snippet]:
        """Full-text search across title, description, code, and tags."""
        escaped = query.replace('"', '""')
        rows = self._conn.execute(
            'SELECT s.* FROM snippets s JOIN snippets_fts f ON s.id = f.rowid '
            'WHERE snippets_fts MATCH ? ORDER BY rank',
            (f'"{escaped}"',),
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def filter_by_tag(self, tag: str) -> list[Snippet]:
        """Return snippets that contain the given tag."""
        rows = self._conn.execute(
            "SELECT * FROM snippets WHERE ',' || tags || ',' LIKE ?",
            (f"%,{tag},%",),
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def filter_by_language(self, language: str) -> list[Snippet]:
        """Return snippets matching a language."""
        rows = self._conn.execute(
            "SELECT * FROM snippets WHERE language = ?", (language,)
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def list_all(self) -> list[Snippet]:
        """Return every snippet, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM snippets ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    def all_tags(self) -> list[str]:
        """Return a sorted list of unique tags."""
        rows = self._conn.execute("SELECT tags FROM snippets").fetchall()
        tags: set[str] = set()
        for row in rows:
            tags.update(Snippet.tags_from_csv(row["tags"]))
        return sorted(tags)

    # -- Import / Export ----------------------------------------------------

    def export_json(self, path: str | Path) -> int:
        """Export all snippets to a JSON file. Returns count exported."""
        snippets = self.list_all()
        data = [asdict(s) for s in snippets]
        Path(path).write_text(json.dumps(data, indent=2))
        return len(data)

    def import_json(self, path: str | Path) -> int:
        """Import snippets from a JSON file. Returns count imported."""
        data = json.loads(Path(path).read_text())
        count = 0
        for item in data:
            item.pop("id", None)
            self.add(Snippet(**item))
            count += 1
        return count

    # -- Statistics ---------------------------------------------------------

    def stats_by_language(self) -> dict[str, int]:
        """Return snippet counts grouped by language."""
        rows = self._conn.execute(
            "SELECT language, COUNT(*) as cnt FROM snippets GROUP BY language ORDER BY cnt DESC"
        ).fetchall()
        return {r["language"]: r["cnt"] for r in rows}

    def stats_by_tag(self) -> dict[str, int]:
        """Return snippet counts per tag."""
        counts: dict[str, int] = {}
        for row in self._conn.execute("SELECT tags FROM snippets").fetchall():
            for tag in Snippet.tags_from_csv(row["tags"]):
                counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def most_recent(self, n: int = 5) -> list[Snippet]:
        """Return the n most recently created snippets."""
        rows = self._conn.execute(
            "SELECT * FROM snippets ORDER BY created_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [self._row_to_snippet(r) for r in rows]

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_snippet(row: sqlite3.Row) -> Snippet:
        return Snippet(
            id=row["id"],
            title=row["title"],
            language=row["language"],
            code=row["code"],
            tags=Snippet.tags_from_csv(row["tags"]),
            description=row["description"],
            created_at=row["created_at"],
        )

    def close(self) -> None:
        self._conn.close()
