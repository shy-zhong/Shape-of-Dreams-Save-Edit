"""JSON 读写：保留数字原始文本，未改动的字段逐字节不变。"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

__all__ = ["loads", "dumps", "kind", "show", "field_text", "make_scalar"]


def loads(text: str):
    """解析 JSON，数字用 Decimal 保存原始十进制文本。"""
    return json.loads(text, parse_float=Decimal, parse_int=Decimal)


def dumps(obj) -> str:
    """序列化，Decimal 原样输出，保持键顺序。"""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if obj is None:
        return "null"
    if isinstance(obj, dict):
        parts = []
        for key, value in obj.items():
            parts.append(json.dumps(key, ensure_ascii=False) + ":" + dumps(value))
        return "{" + ",".join(parts) + "}"
    if isinstance(obj, list):
        return "[" + ",".join(dumps(item) for item in obj) + "]"
    raise TypeError("unsupported type: %r" % (type(obj),))


def kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Decimal):
        return "number"
    if isinstance(value, str):
        return "string"
    return "unknown"


def show(value) -> str:
    k = kind(value)
    if k == "object":
        return "{ %d 个字段 }" % len(value)
    if k == "array":
        return "[ %d 项 ]" % len(value)
    if k == "null":
        return "null"
    if k == "boolean":
        return "true" if value else "false"
    return str(value)


def field_text(value, hint: str = "integer") -> str:
    """输入框里显示的值：整数字段去掉多余的 .0。"""
    text = show(value)
    if hint == "integer" and text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def make_scalar(text: str, value_type: str):
    """把输入框文本转成要写回 JSON 的值。"""
    if value_type == "string":
        return text
    if value_type == "integer":
        stripped = text.strip()
        try:
            number = Decimal(stripped)
        except InvalidOperation:
            raise ValueError("请输入整数")
        if number == number.to_integral_value():
            return Decimal(int(number))
        raise ValueError("请输入整数")
    if value_type == "number":
        try:
            return Decimal(text.strip())
        except InvalidOperation:
            raise ValueError("请输入数字")
    if value_type == "boolean":
        low = text.strip().lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
        raise ValueError("请输入 true 或 false")
    if value_type == "null":
        return None
    if value_type == "json":
        return loads(text)
    raise ValueError("未知类型")
