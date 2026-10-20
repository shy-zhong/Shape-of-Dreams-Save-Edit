"""备份的创建、列举与恢复。"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .documents import target_from_backup

__all__ = ["BackupStore"]


class BackupStore:
    def __init__(self, save_dir: Path):
        self.save_dir = save_dir

    @property
    def folder(self) -> Path:
        return self.save_dir / "_EditorBackups"

    def ensure(self) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        return self.folder

    def list(self) -> list[Path]:
        if not self.folder.is_dir():
            return []
        return sorted(self.folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    def create(self, source: Path, prefix: str = "") -> Path:
        """复制当前文件到备份目录，返回备份路径。"""
        folder = self.ensure()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        middle = (prefix + "_") if prefix else ""
        target = folder / ("%s_%s%s" % (stamp, middle, source.name))
        shutil.copy2(source, target)
        return target

    def restore(self, backup: Path) -> Path:
        """用备份覆盖对应存档，恢复前先把当前文件再备份一次。"""
        target = self.save_dir / target_from_backup(backup.name)
        if target.exists():
            self.create(target, prefix="beforeRestore")
        shutil.copy2(backup, target)
        return target
