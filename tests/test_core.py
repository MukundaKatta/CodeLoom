"""Tests for codeloom.core — uses in-memory SQLite."""

import json
import tempfile
from pathlib import Path

from codeloom.core import Snippet, SnippetStore, detect_language


class TestSnippetStore:
    """CRUD, search, filtering, import/export, and statistics tests."""

    def _make_store(self) -> SnippetStore:
        return SnippetStore(":memory:")

    # -- CRUD --------------------------------------------------------------

    def test_add_and_get(self):
        store = self._make_store()
        s = Snippet(title="Hello World", language="python", code="print('hi')", tags=["demo"])
        added = store.add(s)
        assert added.id is not None
        fetched = store.get(added.id)
        assert fetched is not None
        assert fetched.title == "Hello World"
        assert fetched.language == "python"
        assert fetched.tags == ["demo"]
        store.close()

    def test_update(self):
        store = self._make_store()
        s = store.add(Snippet(title="Old", code="x = 1", language="python"))
        s.title = "New"
        assert store.update(s) is True
        updated = store.get(s.id)
        assert updated.title == "New"
        store.close()

    def test_delete(self):
        store = self._make_store()
        s = store.add(Snippet(title="Temp", code="pass", language="python"))
        assert store.delete(s.id) is True
        assert store.get(s.id) is None
        store.close()

    # -- Search & filter ---------------------------------------------------

    def test_full_text_search(self):
        store = self._make_store()
        store.add(Snippet(title="Fibonacci", code="def fib(n): ...", language="python", tags=["math"]))
        store.add(Snippet(title="Sorting", code="arr.sort()", language="python", tags=["algo"]))
        results = store.search("Fibonacci")
        assert len(results) == 1
        assert results[0].title == "Fibonacci"
        store.close()

    def test_filter_by_tag(self):
        store = self._make_store()
        store.add(Snippet(title="A", code="a", language="python", tags=["web", "api"]))
        store.add(Snippet(title="B", code="b", language="go", tags=["api"]))
        store.add(Snippet(title="C", code="c", language="rust", tags=["cli"]))
        api_snippets = store.filter_by_tag("api")
        assert len(api_snippets) == 2
        cli_snippets = store.filter_by_tag("cli")
        assert len(cli_snippets) == 1
        store.close()

    def test_filter_by_language(self):
        store = self._make_store()
        store.add(Snippet(title="A", code="a", language="python"))
        store.add(Snippet(title="B", code="b", language="go"))
        assert len(store.filter_by_language("python")) == 1
        store.close()

    # -- Language detection ------------------------------------------------

    def test_detect_language_python(self):
        code = "import os\ndef main():\n    print('hello')"
        assert detect_language(code) == "python"

    def test_detect_language_javascript(self):
        code = "const x = 10;\nconsole.log(x);"
        assert detect_language(code) == "javascript"

    def test_detect_language_unknown(self):
        assert detect_language("just some random text") == "text"

    # -- Import / Export ---------------------------------------------------

    def test_export_import_json(self):
        store = self._make_store()
        store.add(Snippet(title="X", code="x=1", language="python", tags=["test"]))
        store.add(Snippet(title="Y", code="y=2", language="go", tags=["test"]))

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        assert store.export_json(path) == 2

        store2 = self._make_store()
        assert store2.import_json(path) == 2
        assert len(store2.list_all()) == 2

        Path(path).unlink()
        store.close()
        store2.close()

    # -- Statistics --------------------------------------------------------

    def test_stats_by_language(self):
        store = self._make_store()
        store.add(Snippet(title="A", code="a", language="python"))
        store.add(Snippet(title="B", code="b", language="python"))
        store.add(Snippet(title="C", code="c", language="go"))
        stats = store.stats_by_language()
        assert stats["python"] == 2
        assert stats["go"] == 1
        store.close()

    def test_stats_by_tag(self):
        store = self._make_store()
        store.add(Snippet(title="A", code="a", language="python", tags=["web", "api"]))
        store.add(Snippet(title="B", code="b", language="go", tags=["api"]))
        stats = store.stats_by_tag()
        assert stats["api"] == 2
        assert stats["web"] == 1
        store.close()

    def test_most_recent(self):
        store = self._make_store()
        store.add(Snippet(title="First", code="1", language="python", created_at="2026-01-01T00:00:00"))
        store.add(Snippet(title="Second", code="2", language="python", created_at="2026-01-02T00:00:00"))
        store.add(Snippet(title="Third", code="3", language="python", created_at="2026-01-03T00:00:00"))
        recent = store.most_recent(2)
        assert len(recent) == 2
        assert recent[0].title == "Third"
        store.close()

    def test_all_tags(self):
        store = self._make_store()
        store.add(Snippet(title="A", code="a", language="python", tags=["beta", "alpha"]))
        store.add(Snippet(title="B", code="b", language="go", tags=["alpha", "gamma"]))
        tags = store.all_tags()
        assert tags == ["alpha", "beta", "gamma"]
        store.close()

    def test_auto_detect_language_on_add(self):
        store = self._make_store()
        s = store.add(Snippet(title="Auto", code="def foo():\n    print('bar')\nimport sys"))
        assert s.language == "python"
        store.close()
