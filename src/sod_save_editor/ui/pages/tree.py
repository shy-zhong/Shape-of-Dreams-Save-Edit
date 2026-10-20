"""JSON 树页：整份存档可点选编辑。"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

from ...core import jsonio
from ...core.edits import segment
from .. import theme, widgets

__all__ = ["TreePage"]


class TreePage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self._map: dict[str, dict] = {}
        self._selected: dict | None = None

        toolbar = tk.Frame(self, bg=theme.BG, height=42)
        toolbar.pack(side="top", fill="x")
        toolbar.pack_propagate(False)

        self.filter_var = tk.StringVar()
        self.filter_entry = widgets.entry(toolbar, 4, 8, 300, 26, textvariable=self.filter_var)
        widgets.button(toolbar, "搜索", 312, 8, 64, 26, self.build)
        widgets.button(toolbar, "清空", 382, 8, 64, 26, self._clear_filter)
        widgets.button(toolbar, "全部展开", 460, 8, 80, 26, lambda: self._expand_all(True))
        widgets.button(toolbar, "全部折叠", 546, 8, 80, 26, lambda: self._expand_all(False))
        widgets.button(toolbar, "刷新树", 640, 8, 80, 26, self.build)

        body = tk.Frame(self, bg=theme.BG)
        body.pack(side="top", fill="both", expand=True, pady=(4, 0))

        tree_box = tk.Frame(body, bg=theme.CARD, width=448)
        tree_box.pack(side="left", fill="y")
        tree_box.pack_propagate(False)

        self.tree = ttk.Treeview(tree_box, style="Treeview", show="tree", selectmode="browse")
        bar = widgets.scrollbar(tree_box, self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("obj", foreground=theme.DIM)
        self.tree.tag_configure("str", foreground=theme.STR)
        self.tree.tag_configure("number", foreground=theme.NUM)
        self.tree.tag_configure("boolean", foreground=theme.BOOL)
        self.tree.tag_configure("null", foreground=theme.DIM)
        self.tree.tag_configure("root", foreground=theme.ACCENT)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.editor = tk.Frame(body, bg=theme.BG)
        self.editor.pack(side="left", fill="both", expand=True, padx=(10, 0))

        widgets.label(self.editor, "字段路径", 0, 0, 120, 18, theme.FONT_SMALL)
        self.path_box = self._textbox(0, 20, height=44, disabled=True)
        widgets.label(self.editor, "类型", 0, 72, 40, 18, theme.FONT_SMALL)
        self.type_label = tk.Label(self.editor, text="—", bg=theme.BG, fg=theme.ACCENT,
                                   font=theme.FONT_BODY, anchor="w")
        self.type_label.place(x=44, y=70, width=240, height=20)
        widgets.label(self.editor, "当前值", 0, 96, 120, 18, theme.FONT_SMALL)
        self.current_box = self._textbox(0, 116, height=70, disabled=True)
        widgets.label(self.editor, "新值", 0, 194, 120, 18, theme.FONT_SMALL)
        self.new_box = self._textbox(0, 214, height=70)

        self.type_var = tk.StringVar(value="自动")
        self.type_combo = widgets.combo(self.editor, 0, 292, 112,
                                        ["自动", "字符串", "整数", "数字", "布尔", "null", "JSON"],
                                        textvariable=self.type_var)
        self.type_combo.configure(state="readonly")
        widgets.button(self.editor, "应用修改", 124, 292, 110, 30, self.apply, primary=True)
        self.hint = widgets.label(self.editor, "", 0, 330, 430, 60, theme.FONT_SMALL, anchor="nw")

    def _textbox(self, x, y, height, disabled=False):
        box = tk.Text(self.editor, bg=theme.INPUT, fg=theme.TEXT, relief="flat", highlightthickness=1,
                      highlightbackground=theme.BORDER, font=theme.FONT_MONO, wrap="word",
                      insertbackground=theme.TEXT)
        box.place(x=x, y=y, relwidth=1, height=height)
        if disabled:
            box.configure(state="disabled")
        return box

    # ---------------------------------------------------------------- 构建
    def build(self):
        if self.app.doc is None:
            return
        started = time.time()
        self.app.configure(cursor="watch")
        self.update_idletasks()
        try:
            keyword = self.filter_var.get().strip().lower()
            root = self.app.doc.node.get("root", self.app.doc.node)
            self.tree.delete(*self.tree.get_children())
            self._map = {}
            if not isinstance(root, (dict, list)):
                return
            item = self.tree.insert("", "end", text="root   {%d}" % len(root), tags=("root",), open=True)
            self._map[item] = {"node": root, "parent": self.app.doc.node, "key": "root",
                               "is_index": False, "path": "root", "kind": jsonio.kind(root)}
            count = self._insert(item, root, "root", keyword, False)
            elapsed = time.time() - started
            self.app.set_status("JSON 树已刷新（%d 个节点，%.2f 秒）" % (count + 1, elapsed), theme.DIM)
        finally:
            self.app.configure(cursor="")
            self.update_idletasks()

    def _insert(self, parent_item, node, path, keyword, forced) -> int:
        count = 0
        if isinstance(node, dict):
            pairs = [(str(k), v) for k, v in node.items()]
            is_index = False
        else:
            pairs = [(str(i), v) for i, v in enumerate(node)]
            is_index = True
        for key, value in pairs:
            matched = forced or not keyword or keyword in key.lower()
            if not matched:
                if isinstance(value, (dict, list)):
                    matched = self._subtree_match(value, keyword)
                else:
                    matched = keyword in jsonio.show(value).lower()
            if not matched:
                continue
            kind = jsonio.kind(value)
            segment_text = segment(key, is_index)
            child_path = path + "." + segment_text if path else segment_text
            item = self.tree.insert(parent_item, "end", text=self._label(segment_text, value, kind), tags=(kind,))
            self._map[item] = {"node": value, "parent": node, "key": key if not is_index else int(key),
                               "is_index": is_index, "path": child_path, "kind": kind}
            count += 1
            if isinstance(value, (dict, list)) and value:
                count += self._insert(item, value, child_path, keyword, forced or matched)
        return count

    @staticmethod
    def _subtree_match(node, keyword) -> bool:
        if isinstance(node, dict):
            return any(keyword in str(k).lower() or TreePage._subtree_match(v, keyword) for k, v in node.items())
        if isinstance(node, list):
            return any(TreePage._subtree_match(item, keyword) for item in node)
        return keyword in jsonio.show(node).lower()

    @staticmethod
    def _label(key, value, kind) -> str:
        if kind == "object":
            return "%s   {%d}" % (key, len(value))
        if kind == "array":
            return "%s   [%d 项]" % (key, len(value))
        text = jsonio.show(value).replace("\n", " ").replace("\r", " ")
        if len(text) > 80:
            text = text[:80] + "…"
        return "%s = %s" % (key, text)

    def _clear_filter(self):
        self.filter_var.set("")
        self.build()

    def _expand_all(self, expand: bool):
        def walk(item):
            for child in self.tree.get_children(item):
                self.tree.item(child, open=expand)
                walk(child)

        walk("")
        if not expand and self.tree.get_children():
            self.tree.item(self.tree.get_children()[0], open=True)

    # ---------------------------------------------------------------- 交互
    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        tag = self._map.get(selection[0])
        if not tag:
            return
        self._selected = tag
        self._set_text(self.path_box, tag["path"])
        self.type_label.configure(text=tag["kind"],
                                  fg=theme.WARN if tag["kind"] in ("object", "array") else theme.ACCENT)
        self._set_text(self.current_box, jsonio.show(tag["node"]))
        self.new_box.delete("1.0", "end")
        if tag["kind"] in ("object", "array"):
            self.hint.configure(text="对象 / 数组：可以把整个节点替换为粘贴的 JSON（谨慎操作）。")
        else:
            self.hint.configure(text="字符串直接输入文本（不用加引号）；数字直接输入；布尔写 true / false；null 直接写 null。")

    @staticmethod
    def _set_text(box: tk.Text, text: str):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def apply(self):
        tag = self._selected
        if not tag:
            return
        raw = self.new_box.get("1.0", "end").rstrip("\n")
        if not raw.strip():
            return
        value_type = self.type_var.get()
        if value_type == "自动":
            kind = tag["kind"]
            if kind in ("object", "array"):
                value_type = "json"
            elif kind == "number":
                value_type = "integer" if raw.strip().lstrip("-").isdigit() else "number"
            elif kind == "boolean":
                value_type = "boolean"
            elif kind == "null":
                value_type = "null" if raw.strip() == "null" else "string"
            else:
                value_type = "string"
        try:
            value = jsonio.make_scalar(raw, value_type)
            parent = tag["parent"]
            parent[tag["key"]] = value
            item = self.tree.selection()[0]
            self.tree.item(item, text=self._label(segment(str(tag["key"]), tag["is_index"]), value, jsonio.kind(value)),
                           tags=(jsonio.kind(value),))
            tag["node"] = value
            tag["kind"] = jsonio.kind(value)
            self._set_text(self.current_box, jsonio.show(value))
            self.new_box.delete("1.0", "end")
            self.app.mark_changed("%s → %s" % (tag["path"], jsonio.show(value)))
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning("修改失败", str(exc), parent=self.app)
