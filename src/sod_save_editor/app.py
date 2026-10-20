"""主窗口与应用状态。"""

from __future__ import annotations

import os
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_SUBTITLE, APP_TITLE, __version__
from .core import backups, documents, jsonio, unlocks
from .core.edits import diff
from .core.system import capture_window, game_running
from .ui import theme, widgets
from .ui.pages.backup import BackupPage
from .ui.pages.quick import QuickPage
from .ui.pages.tree import TreePage

__all__ = ["SaveEditor", "run"]

TAB_NAMES = ["快捷修改", "JSON 树", "备份与记录"]


class SaveEditor(tk.Tk):
    def __init__(self, shot_path: str = "", shot_tab: int = 0, shot_file: int = 0):
        super().__init__()
        self.title("%s  v%s" % (APP_TITLE, __version__))
        self.configure(bg=theme.BG)
        self.geometry("%dx%d" % (theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT))
        self.minsize(1000, 660)
        self._center()

        self.shot_path = shot_path
        self.shot_tab = shot_tab
        self.shot_file = shot_file

        self.docs: dict[Path, documents.Document] = {}
        self.save_dir: Path = documents.default_save_dir()
        self.files: list[documents.SaveFile] = []
        self.doc: documents.Document | None = None
        self.current_index = -1
        self.tab_index = 0
        self.suppress = False
        self.backups = backups.BackupStore(self.save_dir)

        style = ttk.Style(self)
        widgets.configure_treeview(self, style)

        self._build_shell()
        self._set_tab(0)
        self.reload_files()
        self.refresh_backups()
        self.set_status("就绪 · 左侧选择要修改的文件 · 改完点右下角保存", theme.DIM)
        self.bind("<Control-s>", lambda _e: self.save_current())

        if self.shot_path:
            self.after(600, self._begin_shot)

    # ---------------------------------------------------------------- 布局
    def _center(self):
        self.update_idletasks()
        try:
            x = max(0, (self.winfo_screenwidth() - theme.WINDOW_WIDTH) // 2)
            y = max(0, (self.winfo_screenheight() - theme.WINDOW_HEIGHT) // 2 - 20)
            self.geometry("+%d+%d" % (x, y))
        except tk.TclError:
            pass

    def _build_shell(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self._build_header()
        self._build_file_list()
        self._build_pages()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self, bg=theme.HEADER, height=76)
        header.grid(row=0, column=0, columnspan=2, sticky="nsew")
        header.grid_propagate(False)

        widgets.label(header, APP_TITLE, 18, 8, 420, 30, theme.FONT_H1, theme.TEXT)
        widgets.label(header, APP_SUBTITLE, 18, 40, 460, 20, theme.FONT_SMALL)
        widgets.label(header, "存档目录", 470, 4, 120, 18, theme.FONT_SMALL)

        self.dir_var = tk.StringVar(value=str(self.save_dir))
        widgets.entry(header, 470, 22, 462, 26, textvariable=self.dir_var)
        widgets.button(header, "浏览…", 938, 21, 66, 28, self.browse_dir)
        widgets.button(header, "重新读取", 1010, 21, 66, 28, self.reload_all)
        widgets.button(header, "打开目录", 1082, 21, 80, 28, self.open_save_dir)

        self.game_label = widgets.label(header, "", 470, 54, 700, 18, theme.FONT_SMALL)
        self.update_game_hint()

    def _build_file_list(self):
        left = tk.Frame(self, bg=theme.BG, width=236)
        left.grid(row=1, column=0, sticky="nsew")
        left.grid_propagate(False)

        widgets.label(left, "存档文件", 12, 8, 200, 20, theme.FONT_SMALL)
        self.file_list = tk.Listbox(
            left, bg=theme.CARD, fg=theme.TEXT, selectbackground=theme.ACCENT_DIM,
            selectforeground=theme.TEXT, bd=0, highlightthickness=0, activestyle="none",
            font=theme.FONT_BODY, exportselection=False,
        )
        self.file_list.place(x=12, y=30, width=210, height=590)
        self.file_list.bind("<<ListboxSelect>>", self._on_file_select)
        self.file_info = widgets.label(left, "", 12, 630, 210, 24, theme.FONT_SMALL)

    def _build_pages(self):
        right = tk.Frame(self, bg=theme.BG)
        right.grid(row=1, column=1, sticky="nsew")

        tab_bar = tk.Frame(right, bg=theme.BG, height=40)
        tab_bar.pack(side="top", fill="x", padx=(0, 8), pady=(6, 0))
        tab_bar.pack_propagate(False)

        self.tab_buttons: list[tk.Button] = []
        for index, name in enumerate(TAB_NAMES):
            button = tk.Button(
                tab_bar, text=name, bg=theme.BG, fg=theme.DIM, activebackground=theme.BG,
                activeforeground=theme.TEXT, relief="flat", bd=0, font=theme.FONT_BODY,
                cursor="hand2", command=lambda i=index: self._set_tab(i),
            )
            button.place(x=index * 132, y=0, width=132, height=33)
            self.tab_buttons.append(button)
        self.tab_underline = tk.Frame(tab_bar, bg=theme.ACCENT, height=3)
        self.tab_underline.place(x=0, y=33, width=132)
        tk.Frame(tab_bar, bg=theme.BORDER, height=1).place(x=0, y=37, relwidth=1)

        host = tk.Frame(right, bg=theme.BG)
        host.pack(side="top", fill="both", expand=True, padx=(0, 8), pady=(4, 0))

        self.quick_page = QuickPage(host, self)
        self.tree_page = TreePage(host, self)
        self.backup_page = BackupPage(host, self)
        self.pages = [self.quick_page, self.tree_page, self.backup_page]
        for page in self.pages:
            page.place(x=0, y=0, relwidth=1, relheight=1)

    def _build_footer(self):
        footer = tk.Frame(self, bg=theme.HEADER, height=58)
        footer.grid(row=2, column=0, columnspan=2, sticky="nsew")
        footer.grid_propagate(False)

        self.dot = widgets.label(footer, "●", 18, 16, 16, 22, theme.FONT_BODY, theme.GOOD)
        self.save_state = widgets.label(footer, "无未保存改动", 40, 16, 130, 22, theme.FONT_BODY)
        self.status_label = widgets.label(footer, "", 172, 17, 600, 22, theme.FONT_SMALL)

        self.backup_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            footer, text="保存前备份", variable=self.backup_var, bg=theme.HEADER, fg=theme.DIM,
            activebackground=theme.HEADER, activeforeground=theme.TEXT, selectcolor=theme.INPUT,
            highlightthickness=0, bd=0, font=theme.FONT_SMALL, cursor="hand2",
        ).place(relx=1.0, x=-470, y=17, width=140, height=26)

        revert = tk.Button(
            footer, text="撤销全部改动", bg=theme.BTN, fg=theme.TEXT, activebackground=theme.BTN_HOVER,
            activeforeground=theme.TEXT, relief="flat", bd=0, font=theme.FONT_BODY,
            cursor="hand2", command=self.revert_current,
        )
        revert.place(relx=1.0, x=-322, y=13, width=118, height=32)
        widgets.hover_effect(revert)

        save = tk.Button(
            footer, text="保存到磁盘", bg=theme.ACCENT, fg="#10151F",
            activebackground="#9CBCFF", activeforeground="#10151F", relief="flat", bd=0,
            font=theme.FONT_BOLD, cursor="hand2", command=self.save_current,
        )
        save.place(relx=1.0, x=-206, y=11, width=196, height=36)

    # ---------------------------------------------------------------- 页签
    def _set_tab(self, index: int):
        self.tab_index = index
        for i, button in enumerate(self.tab_buttons):
            button.configure(bg=theme.CARD if i == index else theme.BG,
                             fg=theme.TEXT if i == index else theme.DIM)
        self.tab_underline.place(x=index * 132, y=33, width=132)
        self.pages[index].lift()
        if index == 1:
            self.tree_page.build()
        elif index == 2:
            self.backup_page.refresh_changes()
            self.backup_page.refresh()

    # ---------------------------------------------------------------- 文件
    def _on_file_select(self, _event=None):
        if self.suppress:
            return
        selection = self.file_list.curselection()
        if selection:
            self.select_file(int(selection[0]))

    def reload_files(self):
        self.save_dir = Path(self.dir_var.get())
        self.backups = backups.BackupStore(self.save_dir)
        self.files = documents.scan_save_files(self.save_dir)
        self._refresh_file_list()
        if self.files:
            self.file_list.selection_set(0)
            self.select_file(0)
        else:
            self.set_status("这个目录里没有找到存档文件", theme.BAD)

    def _refresh_file_list(self):
        self.file_list.delete(0, "end")
        for info in self.files:
            doc = self.docs.get(info.path)
            mark = "● " if (doc and doc.dirty) else "   "
            self.file_list.insert("end", "%s%s   ·   %s" % (mark, info.label, documents.human_size(info.size)))
        if 0 <= self.current_index < len(self.files):
            self.file_list.selection_clear(0, "end")
            self.file_list.selection_set(self.current_index)

    def select_file(self, index: int):
        if index < 0 or index >= len(self.files) or self.suppress:
            return
        self.suppress = True
        try:
            info = self.files[index]
            doc = self.docs.get(info.path)
            if doc is None:
                try:
                    doc = documents.Document.load(info.path)
                except Exception as exc:  # noqa: BLE001
                    messagebox.showerror("读取失败", "无法解析该文件：\n%s\n\n%s" % (info.path, exc), parent=self)
                    return
                self.docs[info.path] = doc
            self.doc = doc
            self.current_index = index
            self.quick_page.build(info.kind)
            if self.tab_index == 1:
                self.tree_page.build()
            self.file_info.configure(
                text="%s  ·  %s" % (documents.human_size(info.size), documents.file_time(info.path))
            )
            self.update_dirty()
            self.set_status("已载入「%s」：%s" % (info.label, info.path.name), theme.DIM)
        finally:
            self.suppress = False

    # ---------------------------------------------------------------- 状态
    def set_status(self, text: str, color: str = theme.DIM):
        self.status_label.configure(text=text, fg=color)

    def mark_changed(self, message: str):
        self.update_dirty()
        self.set_status("已修改 " + message, theme.ACCENT)

    def update_dirty(self):
        dirty = bool(self.doc and self.doc.refresh_dirty())
        self.dot.configure(fg=theme.WARN if dirty else theme.GOOD)
        self.save_state.configure(
            text="有未保存改动" if dirty else "无未保存改动", fg=theme.WARN if dirty else theme.DIM
        )
        self._refresh_file_list()

    def update_game_hint(self):
        if game_running():
            self.game_label.configure(text="⚠ 检测到游戏正在运行：写入可能被游戏退出时的自动存档覆盖，建议先退出游戏",
                                      fg=theme.WARN)
        else:
            self.game_label.configure(text="✓ 未检测到游戏进程；仍建议先退出游戏再写入", fg=theme.GOOD)

    # ---------------------------------------------------------------- 解锁
    def invoke_unlock(self, mode: str):
        if self.doc is None:
            return
        root = self.doc.root()
        if not isinstance(root, dict):
            return
        if mode == "stars":
            try:
                target = int(self.quick_page.star_var.get().strip())
            except (ValueError, AttributeError):
                target = 5
            changed = unlocks.unlock_stars(root, target)
        else:
            changed = unlocks.unlock_category(root, mode)
        self.update_dirty()
        self.set_status("已解锁「%s」，本次变更 %d 项" % (unlocks.UNLOCK_LABELS.get(mode, mode), changed), theme.GOOD)

    def unlock_all(self):
        if not messagebox.askyesno(
            "确认全部解锁",
            "这会一次性放开所有收藏类内容。\n\n建议先勾选「保存前备份」再操作。\n\n确定全部解锁？",
            parent=self,
        ):
            return
        for mode in ("heroes", "skills", "gems", "artifacts", "lucidDreams",
                     "achievements", "memories", "cosmetics", "stars"):
            self.invoke_unlock(mode)
        self.set_status("已执行一键全部解锁，请确认后保存", theme.GOOD)

    def boost_dejavu_stats(self):
        if self.doc is None:
            return
        if not self.doc.path.name.lower().startswith("r_stats"):
            messagebox.showinfo(
                "请先选择「生涯统计」",
                "这个按钮修改的是「生涯统计」文件。\n\n请在左侧点一下「生涯统计」，再点这个按钮。",
                parent=self,
            )
            return
        root = self.doc.root()
        if not isinstance(root, dict):
            return
        changed = unlocks.boost_dejavu_stats(root)
        self.update_dirty()
        self.set_status("已补齐既视感统计：%d 处改为 5，记得保存" % changed, theme.GOOD)

    # ---------------------------------------------------------------- 保存
    def save_current(self):
        doc = self.doc
        if doc is None:
            return
        if not doc.refresh_dirty():
            self.set_status("没有未保存的改动，无需写入", theme.DIM)
            return
        if game_running() and not messagebox.askyesno(
            "游戏正在运行",
            "游戏正在运行。\n\n现在写入，可能被游戏退出时的自动存档覆盖。\n\n建议先退出游戏。仍要写入吗？",
            parent=self,
        ):
            return
        try:
            doc.touch_upsert()
            text = doc.text()
            jsonio.loads(text)
            changes = len(diff(jsonio.loads(doc.original), doc.node))

            backup = None
            if self.backup_var.get():
                backup = self.backups.create(doc.path)

            temp = doc.path.with_suffix(".json.new")
            temp.write_text(text, encoding="utf-8", newline="")
            os.replace(temp, doc.path)

            doc.original = text
            doc.dirty = False
            for info in self.files:
                if info.path == doc.path:
                    info.size = doc.path.stat().st_size
            self.update_dirty()
            self.refresh_backups()
            self.backup_page.refresh_changes()
            tail = (" · 备份 " + backup.name) if backup else " · 未备份"
            self.set_status("已保存 %s · %d 处改动%s" % (doc.path.name, changes, tail), theme.GOOD)
        except Exception as exc:  # noqa: BLE001
            self.set_status("保存失败：%s" % exc, theme.BAD)
            messagebox.showerror("保存失败", "%s\n\n%s" % (exc, traceback.format_exc(limit=2)), parent=self)

    def revert_current(self):
        if self.doc is None:
            return
        if not messagebox.askyesno("撤销改动", "丢弃当前文件所有未保存的改动，重新从磁盘读取？", parent=self):
            return
        self.docs.pop(self.doc.path, None)
        self.doc = None
        self.select_file(self.current_index)
        self.set_status("已撤销改动，重新载入磁盘版本", theme.DIM)

    # ---------------------------------------------------------------- 目录
    def browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=str(self.save_dir), title="选择 Shape of Dreams 的 QuickSave 目录")
        if not chosen:
            return
        self.dir_var.set(chosen)
        self.docs.clear()
        self.doc = None
        self.reload_files()
        self.refresh_backups()

    def reload_all(self):
        self.docs.clear()
        self.doc = None
        self.reload_files()
        self.refresh_backups()
        self.update_game_hint()
        self.set_status("已重新读取存档目录", theme.DIM)

    def open_save_dir(self):
        try:
            os.startfile(str(self.save_dir))
        except Exception as exc:  # noqa: BLE001
            self.set_status("无法打开目录：%s" % exc, theme.BAD)

    def open_backup_dir(self):
        try:
            self.backups.ensure()
            os.startfile(str(self.backups.folder))
        except Exception as exc:  # noqa: BLE001
            self.set_status("无法打开备份目录：%s" % exc, theme.BAD)

    def refresh_backups(self):
        self.backup_page.refresh()

    # ---------------------------------------------------------------- 截图
    def _begin_shot(self):
        try:
            if 0 < self.shot_file < len(self.files):
                self.file_list.selection_clear(0, "end")
                self.file_list.selection_set(self.shot_file)
                self.select_file(self.shot_file)
            if 0 <= self.shot_tab < len(self.pages):
                self._set_tab(self.shot_tab)
            self.update_idletasks()
            self.update()
            self.after(400, self._take_shot)
        except Exception:  # noqa: BLE001
            self.destroy()

    def _take_shot(self):
        try:
            capture_window(int(self.wm_frame(), 16), self.shot_path)
        finally:
            self.destroy()

    # ---------------------------------------------------------------- 退出
    def destroy(self):
        super().destroy()


def run(shot_path: str = "", shot_tab: int = 0, shot_file: int = 0) -> None:
    app = SaveEditor(shot_path, shot_tab, shot_file)
    if not shot_path:
        icon = Path(__file__).resolve().parent / "assets" / "app.ico"
        if icon.exists():
            try:
                app.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
    app.mainloop()
