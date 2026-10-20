"""与 Windows 打交道的部分：进程检测、窗口截图。"""

from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from pathlib import Path

__all__ = ["game_running", "capture_window"]


def game_running(exe_prefix: str = "shape of dreams") -> bool:
    """用 Toolhelp 快照判断游戏是否在跑。"""
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (0, INVALID_HANDLE_VALUE):
        return False
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    try:
        ok = kernel32.Process32First(snapshot, ctypes.byref(entry))
        while ok:
            name = entry.szExeFile.decode("mbcs", "ignore").lower()
            if name.startswith(exe_prefix):
                return True
            ok = kernel32.Process32Next(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(snapshot))
    return False


def capture_window(hwnd: int, path: str | Path) -> None:
    """把窗口内容抓成 BMP（不依赖第三方库）。"""
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError("窗口尺寸无效")

    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    gdi32.SelectObject(hdc_mem, hbitmap)
    user32.PrintWindow(hwnd, hdc_mem, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0

    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buffer, ctypes.byref(header), 0)

    data = bytearray(buffer.raw)
    data[3::4] = b"\xff" * (width * height)
    row = width * 4
    with open(path, "wb") as handle:
        handle.write(b"BM")
        handle.write(struct.pack("<IHHI", 54 + row * height, 0, 0, 54))
        handle.write(struct.pack("<IiiHHIIiiII", 40, width, height, 1, 32, 0, row * height, 2835, 2835, 0, 0))
        for y in range(height - 1, -1, -1):
            handle.write(data[y * row:(y + 1) * row])

    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)
