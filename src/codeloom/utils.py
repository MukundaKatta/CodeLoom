"""Utility helpers for CodeLoom."""

from __future__ import annotations

import textwrap


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max_len characters, appending '...' if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_snippet_row(snippet_id: int, title: str, language: str, tags: list[str]) -> str:
    """Format a snippet as a single CLI table row."""
    tag_str = ", ".join(tags) if tags else "-"
    return f"  {snippet_id:<6} {truncate(title, 30):<32} {language:<12} {truncate(tag_str, 30)}"


def format_snippet_detail(
    snippet_id: int,
    title: str,
    language: str,
    tags: list[str],
    description: str,
    code: str,
    created_at: str,
) -> str:
    """Format a full snippet detail view for CLI output."""
    tag_str = ", ".join(tags) if tags else "-"
    lines = [
        f"ID:          {snippet_id}",
        f"Title:       {title}",
        f"Language:    {language}",
        f"Tags:        {tag_str}",
        f"Created:     {created_at}",
        f"Description: {description or '-'}",
        "Code:",
        "─" * 60,
        textwrap.dedent(code),
        "─" * 60,
    ]
    return "\n".join(lines)


def print_table(snippets: list) -> None:
    """Print a formatted table of snippets to stdout."""
    header = f"  {'ID':<6} {'Title':<32} {'Language':<12} {'Tags'}"
    print(header)
    print("  " + "─" * 70)
    for s in snippets:
        print(format_snippet_row(s.id, s.title, s.language, s.tags))
    print(f"\n  {len(snippets)} snippet(s) found.")
