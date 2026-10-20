"""备份与记录页：改动预览、备份列表、恢复。"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from ...core import documents, jsonio
from ...core.backups import BackupStore
from ...core.edits import diff
from .. import theme, widgets

__all__ = ["BackupPage"]


class BackupPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app

        widgets.label(self, "改动预览（相对磁盘上的原文件）", 4, 4, 420, 18, theme.FONT_SMALL)

        self.change_tree = ttk.Treeview(
            self, columns=("path", "old", "new"), show="headings", style="Treeview", selectmode="browse"
        )
        for column, text, width, stretch in (
            ("path", "字段", 430, True),
            ("old", "原值", 220, False),
            ("new", "新值", 220, False),
        ):
            self.change_tree.heading(column, text=text, anchor="w")
            self.change_tree.column(column, width=width, anchor="w", stretch=stretch)
        self.change_tree.place(x=4, y=26, relwidth=1, width=-12, height=190)

        widgets.button(self, "刷新改动预览", 4, 222, 130, 30, self.refresh_changes)

        widgets.label(self, "备份文件（QuickSave\\_EditorBackups，最新在上）", 4, 262, 480, 18, theme.FONT_SMALL)

        self.backup_tree = ttk.Treeview(
            self, columns=("time", "name", "size", "path"), show="headings", style="Treeview", selectmode="browse"
        )
        for column, text, width, stretch in (
            ("time", "备份时间", 130, False),
            ("name", "原文件", 300, False),
            ("size", "大小", 90, False),
            ("path", "完整路径", 340, True),
        ):
            self.backup_tree.heading(column, text=text, anchor="w")
            self.backup_tree.column(column, width=width, anchor="w", stretch=stretch)
        self.backup_tree.place(x=4, y=284, relwidth=1, width=-12, relheight=1.0, height=-334)

        self.empty_hint = tk.Label(
            self, text="暂无备份 · 勾选底部「保存前备份」后保存会生成，也可以用「备份当前文件」手动留档",
            bg=theme.CARD, fg=theme.DIM, font=theme.FONT_BODY,
        )
        self.empty_hint.place(x=4, y=320, relwidth=1, width=-12, height=26)

        for x, width, text, command in (
            (4, 190, "用选中备份覆盖当前文件", self.restore),
            (202, 130, "打开备份目录", self.app.open_backup_dir),
            (340, 130, "备份当前文件", self.manual_backup),
        ):
            button = tk.Button(
                self, text=text, bg=theme.BTN, fg=theme.TEXT, activebackground=theme.BTN_HOVER,
                activeforeground=theme.TEXT, relief="flat", bd=0, font=theme.FONT_BODY,
                cursor="hand2", command=command,
            )
            button.place(x=x, rely=1.0, y=-38, width=width, height=30)
            widgets.hover_effect(button)

    # ---------------------------------------------------------------- 改动
    def refresh_changes(self):
        for item in self.change_tree.get_children():
            self.change_tree.delete(item)
        doc = self.app.doc
        if doc is None:
            return
        try:
            original = jsonio.loads(doc.original)
        except Exception:  # noqa: BLE001
            return
        changes = diff(original, doc.node)
        for path, old, new in changes[:400]:
            self.change_tree.insert("", "end", values=(path, old, new))
        if not changes:
            self.change_tree.insert("", "end", values=("（当前没有未保存的改动）", "", ""))
        elif len(changes) > 400:
            self.change_tree.insert("", "end", values=("… 另有 %d 处改动未列出" % (len(changes) - 400), "", ""))
        self.app.set_status("当前共 %d 处改动（尚未写入磁盘）" % len(changes), theme.ACCENT)

    # ---------------------------------------------------------------- 备份
    def refresh(self):
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
        store: BackupStore = self.app.backups
        files = store.list()
        for path in files:
            stat = path.stat()
            self.backup_tree.insert(
                "", "end",
                values=(
                    datetime.fromtimestamp(stat.st_mtime).strftime("%m-%d %H:%M:%S"),
                    documents.target_from_backup(path.name),
                    documents.human_size(stat.st_size),
                    str(path),
                ),
            )
        if files:
            self.empty_hint.place_forget()
        else:
            self.empty_hint.place(x=4, y=320, relwidth=1, width=-12, height=26)

    def manual_backup(self):
        doc = self.app.doc
        if doc is None:
            return
        try:
            target = self.app.backups.create(doc.path, prefix="manual")
            self.refresh()
            self.app.set_status("已备份：%s" % target.name, theme.GOOD)
        except Exception as exc:  # noqa: BLE001
            self.app.set_status("备份失败：%s" % exc, theme.BAD)

    def restore(self):
        selection = self.backup_tree.selection()
        if not selection:
            self.app.set_status("请先在下方列表选中一个备份", theme.WARN)
            return
        values = self.backup_tree.item(selection[0], "values")
        source = self.app.save_dir / values[3]
        target_name = values[1]
        if not messagebox.askyesno(
            "恢复备份",
            "用这个备份覆盖：\n%s\n\n备份时间：%s\n\n当前文件也会先备份一份。继续？" % (target_name, values[0]),
            parent=self.app,
        ):
            return
        try:
            target = self.app.backups.restore(source)
            self.app.docs.pop(target, None)
            self.refresh()
            self.app.set_status("已恢复 %s，请在左侧重新点选该文件" % target_name, theme.GOOD)
            self.app.reload_files()
        except Exception as exc:  # noqa: BLE001
            self.app.set_status("恢复失败：%s" % exc, theme.BAD)
            messagebox.showerror("恢复失败", str(exc), parent=self.app)
