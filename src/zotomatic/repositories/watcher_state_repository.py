"""
PDFストレージの探索情報ログRepository


想定：SQLite
"""

from dataclasses import dataclass

from .types import WatcherStateRepositoryConfig


@dataclass(slots=True)
class WatcherStateRepository:
    """SQLiteに保存するPDFストレージの監視記録の読み書きを司る"""

    config: WatcherStateRepositoryConfig
