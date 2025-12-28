from __future__ import annotations

from zotomatic.utils import slug


def test_slugify_basic() -> None:
    assert slug.slugify("Hello, World!") == "hello-world"


def test_slugify_non_ascii_fallback() -> None:
    assert slug.slugify("タイトル") == "note"


def test_slugify_max_length() -> None:
    assert slug.slugify("hello world", max_length=5) == "hello"


def test_sanitize_filename_empty() -> None:
    assert slug.sanitize_filename("") == "note"


def test_sanitize_filename_invalid_chars() -> None:
    assert slug.sanitize_filename("a<>b:c") == "a--b-c"


def test_sanitize_filename_reserved_windows_name() -> None:
    assert slug.sanitize_filename("CON") == "CON_"
