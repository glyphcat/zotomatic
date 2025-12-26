"""リポジトリデータクラス"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from zotomatic.errors import MissingSettingError


# --- Config. ---
@dataclass(frozen=True, slots=True)
class NoteRepositoryConfig:
    """ノート保存に必要な設定値を束ねる。"""

    root_dir: Path
    encoding: str = "utf-8"

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "root_dir", Path(self.root_dir).expanduser())

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> NoteRepositoryConfig:
        note_dir = settings.get("notes_output_dir")
        if not note_dir:
            raise MissingSettingError("notes_output_dir")
        encoding = settings.get("notes_encoding", "utf-8")
        return cls(root_dir=Path(note_dir), encoding=encoding)


@dataclass(frozen=True, slots=True)
class PDFRepositoryConfig:
    """PDF読み込みに必要な設定値を束ねる。"""

    library_dir: Path
    recursive: bool = True
    pattern: str = "*.pdf"

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "library_dir", Path(self.library_dir).expanduser())

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> PDFRepositoryConfig:
        pdf_dir = settings.get("pdf_library_dir")
        if not pdf_dir:
            raise MissingSettingError("pdf_library_dir")
        recursive = bool(settings.get("pdf_scan_recursive", True))
        pattern = str(settings.get("pdf_glob_pattern", "*.pdf"))
        return cls(library_dir=Path(pdf_dir), recursive=recursive, pattern=pattern)


@dataclass(frozen=True, slots=True)
class WatcherStateRepositoryConfig:
    """
    PDFストレージ監視状態の読み書きに必要な設定値を束ねる。
    バックエンドは今の所SQLiteを想定。
    """

    sqlite_path: Path

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "sqlite_path", Path(self.sqlite_path).expanduser())

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> WatcherStateRepositoryConfig:
        return cls(sqlite_path=cls.default_path())

    @staticmethod
    def default_path() -> Path:
        return Path(".zotomatic/db/zotomatic.db")


@dataclass(frozen=True, slots=True)
class WatcherFileState:
    """SQLiteに保存するPDFファイルの監視状態。"""

    file_path: Path
    mtime_ns: int
    size: int
    last_seen_at: int
    sha1: str | None = None

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "file_path", Path(self.file_path).expanduser())
