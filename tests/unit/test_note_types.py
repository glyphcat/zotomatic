from __future__ import annotations

import pytest

from zotomatic.errors import ZotomaticMissingSettingError
from zotomatic.note.types import NoteBuilderConfig, NoteBuilderContext


def test_note_builder_config_missing() -> None:
    with pytest.raises(ZotomaticMissingSettingError):
        NoteBuilderConfig.from_settings({})


def test_note_builder_context_updates() -> None:
    ctx = NoteBuilderContext(title="Title", tags=["a"], generated_tags=("b",))
    assert ctx.tags == ("a",)
    updated = ctx.with_updates(title="New")
    assert updated.title == "New"
