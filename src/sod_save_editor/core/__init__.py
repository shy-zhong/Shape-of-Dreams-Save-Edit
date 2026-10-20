"""核心逻辑：JSON 保真、文档、解锁、备份、系统交互。"""

from .backups import BackupStore
from .documents import (
    KIND_LABELS,
    Document,
    SaveFile,
    default_save_dir,
    detect_kind,
    file_time,
    human_size,
    scan_save_files,
    target_from_backup,
)
from .edits import diff, segment
from .jsonio import dumps, field_text, kind, loads, make_scalar, show
from .unlocks import (
    UNLOCK_LABELS,
    boost_dejavu_stats,
    unlock_category,
    unlock_memories,
    unlock_status_dict,
)
from .system import capture_window, game_running

__all__ = [
    "BackupStore",
    "Document",
    "SaveFile",
    "KIND_LABELS",
    "UNLOCK_LABELS",
    "default_save_dir",
    "detect_kind",
    "file_time",
    "human_size",
    "scan_save_files",
    "target_from_backup",
    "diff",
    "segment",
    "loads",
    "dumps",
    "kind",
    "show",
    "field_text",
    "make_scalar",
    "boost_dejavu_stats",
    "unlock_category",
    "unlock_memories",
    "unlock_status_dict",
    "capture_window",
    "game_running",
]
