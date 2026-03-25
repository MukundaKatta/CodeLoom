"""CLI entry point — python -m codeloom or 'codeloom' console script."""

from __future__ import annotations

import argparse
import sys

from .config import get_db_path
from .core import Snippet, SnippetStore
from .utils import format_snippet_detail, print_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeloom",
        description="CodeLoom — Code snippet manager with search and tagging.",
    )
    sub = parser.add_subparsers(dest="command")

    # --- add ---
    add_p = sub.add_parser("add", help="Add a new snippet")
    add_p.add_argument("--title", "-t", required=True, help="Snippet title")
    add_p.add_argument("--language", "-l", default="", help="Language (auto-detected if omitted)")
    add_p.add_argument("--tags", default="", help="Comma-separated tags")
    add_p.add_argument("--description", "-d", default="", help="Short description")
    add_p.add_argument("--code", "-c", default="", help="Code string (or pipe via stdin)")

    # --- search ---
    search_p = sub.add_parser("search", help="Full-text search snippets")
    search_p.add_argument("query", help="Search query")

    # --- list ---
    sub.add_parser("list", help="List all snippets")

    # --- show ---
    show_p = sub.add_parser("show", help="Show snippet detail")
    show_p.add_argument("id", type=int, help="Snippet ID")

    # --- delete ---
    del_p = sub.add_parser("delete", help="Delete a snippet")
    del_p.add_argument("id", type=int, help="Snippet ID")

    # --- tags ---
    sub.add_parser("tags", help="List all tags")

    # --- stats ---
    sub.add_parser("stats", help="Show statistics")

    # --- export ---
    export_p = sub.add_parser("export", help="Export snippets to JSON")
    export_p.add_argument("path", help="Output JSON file path")

    # --- import ---
    import_p = sub.add_parser("import", help="Import snippets from JSON")
    import_p.add_argument("path", help="Input JSON file path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    store = SnippetStore(get_db_path())

    try:
        if args.command == "add":
            code = args.code
            if not code and not sys.stdin.isatty():
                code = sys.stdin.read()
            snippet = Snippet(
                title=args.title,
                language=args.language,
                code=code,
                tags=Snippet.tags_from_csv(args.tags),
                description=args.description,
            )
            result = store.add(snippet)
            print(f"Snippet added with ID {result.id} (language: {result.language})")

        elif args.command == "search":
            results = store.search(args.query)
            if results:
                print_table(results)
            else:
                print("No snippets matched your query.")

        elif args.command == "list":
            snippets = store.list_all()
            if snippets:
                print_table(snippets)
            else:
                print("No snippets yet. Add one with: codeloom add -t 'My snippet' -c 'code'")

        elif args.command == "show":
            snippet = store.get(args.id)
            if snippet:
                print(format_snippet_detail(
                    snippet.id, snippet.title, snippet.language,
                    snippet.tags, snippet.description, snippet.code, snippet.created_at,
                ))
            else:
                print(f"Snippet {args.id} not found.")
                return 1

        elif args.command == "delete":
            if store.delete(args.id):
                print(f"Snippet {args.id} deleted.")
            else:
                print(f"Snippet {args.id} not found.")
                return 1

        elif args.command == "tags":
            tags = store.all_tags()
            if tags:
                for tag in tags:
                    print(f"  {tag}")
            else:
                print("No tags yet.")

        elif args.command == "stats":
            by_lang = store.stats_by_language()
            by_tag = store.stats_by_tag()
            total = sum(by_lang.values())
            print(f"Total snippets: {total}\n")
            print("By language:")
            for lang, cnt in by_lang.items():
                print(f"  {lang:<20} {cnt}")
            print("\nBy tag:")
            for tag, cnt in by_tag.items():
                print(f"  {tag:<20} {cnt}")

        elif args.command == "export":
            count = store.export_json(args.path)
            print(f"Exported {count} snippets to {args.path}")

        elif args.command == "import":
            count = store.import_json(args.path)
            print(f"Imported {count} snippets from {args.path}")

    finally:
        store.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
