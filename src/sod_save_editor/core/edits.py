"""改动对比。"""

from __future__ import annotations

from . import jsonio

__all__ = ["segment", "diff"]


def segment(key, is_index: bool) -> str:
    if is_index:
        return "[%s]" % key
    text = str(key)
    if text and all(ch.isalnum() or ch == "_" for ch in text) and not text[0].isdigit():
        return text
    return '["%s"]' % text


def diff(a, b, path: str = "", out: list | None = None, limit: int = 400) -> list:
    """比较两份 JSON，产出 (路径, 旧值, 新值) 列表。"""
    if out is None:
        out = []
    _diff(a, b, path, out, limit)
    return out


def _diff(a, b, path, out, limit):
    if len(out) >= limit:
        return
    ka, kb = jsonio.kind(a), jsonio.kind(b)
    if ka != kb:
        out.append((path, jsonio.show(a), jsonio.show(b)))
        return
    if ka == "object":
        for key in a:
            child = path + "." + segment(key, False) if path else segment(key, False)
            if key in b:
                _diff(a[key], b[key], child, out, limit)
            else:
                out.append((child, jsonio.show(a[key]), "(已删除)"))
        for key in b:
            if key not in a:
                child = path + "." + segment(key, False) if path else segment(key, False)
                out.append((child, "(新增)", jsonio.show(b[key])))
        return
    if ka == "array":
        for index in range(max(len(a), len(b))):
            child = path + "[%d]" % index
            if index >= len(a):
                out.append((child, "(新增)", jsonio.show(b[index])))
            elif index >= len(b):
                out.append((child, jsonio.show(a[index]), "(已删除)"))
            else:
                _diff(a[index], b[index], child, out, limit)
        return
    sa, sb = jsonio.show(a), jsonio.show(b)
    if sa != sb:
        if len(sa) > 90:
            sa = sa[:90] + "…"
        if len(sb) > 90:
            sb = sb[:90] + "…"
        out.append((path, sa, sb))
