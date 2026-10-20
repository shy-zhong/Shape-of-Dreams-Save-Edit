"""包入口：``python -m sod_save_editor``。"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    shot = ""
    tab = 0
    file_index = 0
    for index, arg in enumerate(argv):
        if arg == "--shot" and index + 1 < len(argv):
            shot = argv[index + 1]
        elif arg == "--tab" and index + 1 < len(argv):
            tab = int(argv[index + 1])
        elif arg == "--file" and index + 1 < len(argv):
            file_index = int(argv[index + 1])

    try:
        from .app import run

        run(shot, tab, file_index)
        return 0
    except Exception:  # noqa: BLE001
        log = Path(os.environ.get("LOCALAPPDATA", ".")) / "ShapeOfDreamsSaveEditor" / "error.log"
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox

            tk.Tk().withdraw()
            messagebox.showerror("梦之形 · 存档修改器", "启动失败：\n\n" + traceback.format_exc(limit=3))
        except Exception:  # noqa: BLE001
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
