"""PyInstaller 入口脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sod_save_editor.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
