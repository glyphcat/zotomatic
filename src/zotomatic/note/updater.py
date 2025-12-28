from __future__ import annotations

from pathlib import Path

from zotomatic.note.builder import NoteBuilder
from zotomatic.note.types import NoteBuilderContext


class NoteUpdater:
    """既存ノートの更新を行うサービス."""

    def __init__(
        self,
        note_builder: NoteBuilder,
        logger,
    ) -> None:
        self._note_builder = note_builder
        self._logger = logger

    def update_existing(self, context: NoteBuilderContext, existing: Path) -> None:
        self._note_builder.generate_note(context=context, relative_path=existing)
