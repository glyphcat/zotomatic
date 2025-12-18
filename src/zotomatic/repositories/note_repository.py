from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zotomatic.errors import NoteRepositoryError

from .types import NoteRepositoryConfig


@dataclass(slots=True)
class NoteRepository:
    """ノート（Markdownファイル）の読み書きを担当。"""

    config: NoteRepositoryConfig
    _citekey_index: dict[str, Path] = field(
        init=False, default_factory=dict, repr=False
    )

    @classmethod
    def from_settings(cls, settings: Mapping[str, Any]) -> NoteRepository:
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
