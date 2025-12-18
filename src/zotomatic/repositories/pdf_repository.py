"""
PDFファイルリポジトリ

将来的にZoteroのクラウドを直接参照する場合を想定
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zotomatic.errors import PDFRepositoryError

from .types import PDFRepositoryConfig


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
