from __future__ import annotations

from zotomatic.utils import note


def test_parse_frontmatter_basic() -> None:
    text = """---
title: Example
year: 2020
---
content
"""
    assert note.parse_frontmatter(text) == {"title": "Example", "year": "2020"}


def test_parse_frontmatter_missing() -> None:
    assert note.parse_frontmatter("no frontmatter") == {}


def test_parse_tags() -> None:
    assert note.parse_tags("[\"a\", 'b']") == ("a", "b")
    assert note.parse_tags("[]") == ()
    assert note.parse_tags("not list") == ()


def test_extract_summary_block() -> None:
    text = """# Title
[!summary]
> line1
> line2

body
"""
    assert note.extract_summary_block(text) == "line1\nline2"


def test_update_frontmatter_value_updates_existing() -> None:
    text = """---
key: old
---
body
"""
    updated, changed = note.update_frontmatter_value(text, "key", "new")
    assert changed is True
    assert "key: new" in updated


def test_update_frontmatter_value_inserts_missing() -> None:
    text = """---
other: value
---
body
"""
    updated, changed = note.update_frontmatter_value(text, "key", "new")
    assert changed is True
    assert "key: new" in updated


def test_update_frontmatter_value_no_frontmatter() -> None:
    text = "body"
    updated, changed = note.update_frontmatter_value(text, "key", "new")
    assert changed is False
    assert updated == text


def test_ensure_frontmatter_keys_adds_block() -> None:
    text = "Body only"
    updated = note.ensure_frontmatter_keys(text, {"citekey": "X"})
    assert updated.startswith("---\n")
    assert "citekey: X" in updated


def test_ensure_frontmatter_keys_preserves_existing() -> None:
    text = """---
citekey: X
---
Body
"""
    updated = note.ensure_frontmatter_keys(text, {"citekey": "X"})
    assert updated == text


def test_normalize_path_value() -> None:
    decomposed = "マイドライブ"
    normalized = note.normalize_path_value(decomposed)
    assert normalized == "マイドライブ"
