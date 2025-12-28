from __future__ import annotations

from zotomatic import i18n


def test_get_language_display_known() -> None:
    assert i18n.get_language_display("ja") == "Japanese"


def test_get_language_display_unknown() -> None:
    assert i18n.get_language_display("xx") == "xx"


def test_get_language_display_default() -> None:
    assert i18n.get_language_display("") == "English"
