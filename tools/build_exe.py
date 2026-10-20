"""构建入口：把包打成单文件 exe。

用法（在仓库根目录、已激活 .venv 的情况下）：

    python tools/build_exe.py

产物：dist/梦之形存档修改器.exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "tools" / "run.py"
ICON = ROOT / "src" / "sod_save_editor" / "assets" / "app.ico"
NAME = "ShapeOfDreamsSaveEditor"


def main() -> int:
    if shutil.which("pyinstaller") is None and not _module_available("PyInstaller"):
        print("未找到 PyInstaller，请先 pip install -r requirements.txt", file=sys.stderr)
        return 1
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", NAME,
        "--icon", str(ICON),
        "--add-data", "%s;sod_save_editor/assets" % ICON,
        "--paths", str(ROOT / "src"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        str(ENTRY),
    ]
    print(" ".join(args))
    return subprocess.call(args)


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
