from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zotomatic.errors import (
    MissingSettingError,
    NoteRepositoryError,
    PDFRepositoryError,
)


@dataclass(frozen=True, slots=True)
class NoteRepositoryConfig:
    """ノート保存に必要な設定値を束ねる。"""

    root_dir: Path
    encoding: str = "utf-8"

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "root_dir", Path(self.root_dir).expanduser())

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "NoteRepositoryConfig":
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
    def from_settings(cls, settings: Mapping[str, Any]) -> "PDFRepositoryConfig":
        pdf_dir = settings.get("pdf_library_dir")
        if not pdf_dir:
            raise MissingSettingError("pdf_library_dir")
        recursive = bool(settings.get("pdf_scan_recursive", True))
        pattern = str(settings.get("pdf_glob_pattern", "*.pdf"))
        return cls(library_dir=Path(pdf_dir), recursive=recursive, pattern=pattern)


@dataclass(slots=True)
class NoteRepository:
    """ノート（Markdownファイル）の読み書きを担当するスタブ実装。"""

    config: NoteRepositoryConfig
    _citekey_index: dict[str, Path] = field(
        init=False, default_factory=dict, repr=False
    )

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "NoteRepository":
        return cls(NoteRepositoryConfig.from_settings(settings))

    def resolve(self, relative_path: str | Path) -> Path:
        """ノートの保存先パスを返す（親ディレクトリを未作成なら確保）。"""

        target = (self.config.root_dir / relative_path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def write(self, relative_path: str | Path, content: str) -> Path:
        """ノートをUTF-8で書き出し、書き込んだパスを返す。"""

        target = self.resolve(relative_path)
        try:
            target.write_text(content, encoding=self.config.encoding)
        except OSError as exc:  # pragma: no cover - filesystem dependent
            raise NoteRepositoryError(f"Failed to write note: {target}") from exc
        return target

    def exists(self, relative_path: str | Path) -> bool:
        """指定ノートがすでに存在するか確認する。"""

        return (self.config.root_dir / relative_path).expanduser().exists()

    def build_citekey_index(self) -> dict[str, Path]:
        """簡易的に既存ノートを走査して citekey → パスの辞書を返す。"""

        index: dict[str, Path] = {}
        root = self.config.root_dir
        if not root.exists():
            self._citekey_index = {}
            return index

        pattern = re.compile(r"^citekey:\s*(?P<value>.+)$", re.MULTILINE)

        for note_path in root.rglob("*.md"):
            try:
                text = note_path.read_text(encoding=self.config.encoding)
            except OSError:
                continue
            match = pattern.search(text)
            if not match:
                continue
            citekey = match.group("value").strip().strip('"')
            if citekey:
                index[citekey] = note_path
        self._citekey_index = index
        return index

    def find_by_citekey(self, citekey: str) -> Path | None:
        if not self._citekey_index:
            return None
        return self._citekey_index.get(citekey)

    def add_to_index(self, citekey: str, path: Path) -> None:
        if not citekey:
            return
        self._citekey_index[citekey] = path

    def read(self, relative_path: str | Path) -> str:
        """ノートを読み込む（未実装スタブ）。"""

        ...

    def append(self, relative_path: str | Path, content: str) -> Path:
        """ノートへ追記する（未実装スタブ）。"""

        ...

    def remove(self, relative_path: str | Path) -> None:
        """ノートを削除する（未実装スタブ）。"""

        ...


@dataclass(slots=True)
class PDFRepository:
    """PDFファイルへのアクセスを司るスタブ実装。"""

    config: PDFRepositoryConfig

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> "PDFRepository":
        return cls(PDFRepositoryConfig.from_settings(settings))

    def resolve(self, path: str | Path) -> Path:
        """絶対パスへ正規化する。相対指定の場合はライブラリ配下とみなす。"""

        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            return candidate
        return (self.config.library_dir / candidate).resolve()

    def read_bytes(self, path: str | Path) -> bytes:
        """PDFファイルをバイナリで読み込む。"""

        resolved = self.resolve(path)
        try:
            return resolved.read_bytes()
        except FileNotFoundError as exc:
            raise PDFRepositoryError(f"PDF not found: {resolved}") from exc
        except OSError as exc:  # pragma: no cover - filesystem dependent
            raise PDFRepositoryError(f"Failed to read PDF: {resolved}") from exc

    def list_pdfs(self) -> Iterable[Path]:
        """ライブラリ直下のPDF一覧を返す。存在しない場合は空イテレータ。"""

        library_dir = self.config.library_dir
        if not library_dir.exists():
            return ()
        pattern = self.config.pattern
        if self.config.recursive:
            iterator = library_dir.rglob(pattern)
        else:
            iterator = library_dir.glob(pattern)
        return sorted(iterator)
