"""存档文件与文档对象。"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import jsonio

__all__ = [
    "KIND_LABELS",
    "detect_kind",
    "human_size",
    "file_time",
    "target_from_backup",
    "default_save_dir",
    "SaveFile",
    "Document",
    "scan_save_files",
]

KIND_LABELS = {
    "profile": "玩家档案",
    "stats": "生涯统计",
    "continue": "当前局进度",
    "platform": "平台设置",
    "items": "物品记录",
    "unknown": "其他数据",
}

SCAN_PATTERNS = ("r_profile*", "r_stats*", "r_continue*", "r_platform*", "r_items*", "dl_*")


def default_save_dir() -> Path:
    home = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(home) / "AppData/LocalLow/Lizard Smoothie/Shape of Dreams/QuickSave"


def detect_kind(name: str) -> str:
    low = name.lower()
    if low.startswith("r_profile"):
        return "profile"
    if low.startswith("r_stats"):
        return "stats"
    if low.startswith("r_continue"):
        return "continue"
    if low.startswith("r_platform") or low.startswith("dl_platform"):
        return "platform"
    if "items" in low:
        return "items"
    return "unknown"


def human_size(size: int) -> str:
    if size < 1024:
        return "%d B" % size
    if size < 1024 * 1024:
        return "%.1f KB" % (size / 1024.0)
    return "%.1f MB" % (size / (1024.0 * 1024.0))


def file_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def target_from_backup(name: str) -> str:
    """从备份文件名还原原文件名。"""
    import re

    stripped = re.sub(r"^\d{8}_\d{6}_", "", name)
    stripped = re.sub(r"^(manual_|beforeRestore_)", "", stripped)
    return stripped


@dataclass
class SaveFile:
    path: Path
    kind: str
    label: str
    size: int


def scan_save_files(folder: Path) -> list[SaveFile]:
    if not folder.is_dir():
        return []
    seen: set[Path] = set()
    files: list[SaveFile] = []
    for pattern in SCAN_PATTERNS:
        for path in sorted(folder.glob(pattern)):
            if not path.is_file() or path.suffix.lower() != ".json" or path in seen:
                continue
            seen.add(path)
            kind = detect_kind(path.name)
            label = "扩展数据 (dl_)" if path.name.lower().startswith("dl_") else KIND_LABELS[kind]
            files.append(SaveFile(path, kind, label, path.stat().st_size))
    return files


@dataclass
class Document:
    """一份已载入内存的存档。"""

    path: Path
    node: dict
    original: str
    dirty: bool = False

    @classmethod
    def load(cls, path: Path) -> "Document":
        text = path.read_text(encoding="utf-8")
        return cls(path=path, node=jsonio.loads(text), original=text)

    def text(self) -> str:
        return jsonio.dumps(self.node)

    def refresh_dirty(self) -> bool:
        self.dirty = self.text() != self.original
        return self.dirty

    def root(self) -> dict:
        return self.node.get("root", self.node)

    def touch_upsert(self) -> None:
        root = self.node.get("root")
        if isinstance(root, dict) and "lastUpsert" in root:
            root["lastUpsert"] = Decimal(int(time.time()))
