"""快捷修改页。"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from ...core import jsonio
from ...core.unlocks import UNLOCK_LABELS, unlock_category
from .. import theme, widgets

__all__ = ["QuickPage", "Binding"]

LANGUAGES = ["zh-CN", "zh-TW", "en-US", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES", "pt-BR", "ru-RU"]


@dataclass
class Binding:
    var: tk.StringVar
    path: tuple
    kind: str
    widget: object


class QuickPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=theme.BG)
        self.app = app
        self.bindings: list[Binding] = []

        self.content = tk.Frame(self, bg=theme.BG)
        self.content.place(x=0, y=0, relwidth=1, relheight=1)

    # ---------------------------------------------------------------- 构建
    def build(self, kind: str) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.bindings = []
        if self.app.doc is None:
            return
        root = self.app.doc.root()
        builder = {
            "profile": self._profile,
            "stats": self._stats,
            "platform": self._platform,
            "continue": self._continue,
            "items": self._items,
        }.get(kind, self._unknown)
        builder(root if isinstance(root, dict) else {})
        self.load_values()

    def _card(self, title, y, height, subtitle=""):
        return widgets.card(self.content, title, y, height, subtitle)

    def _field(self, parent, text, path, kind, x, y, width=190):
        widgets.label(parent, text, x, y + 5, 114, 20)
        var = tk.StringVar()
        widget = widgets.entry(parent, x + 120, y, width, 26, textvariable=var)
        binding = Binding(var, path, kind, widget)
        widget.bind("<FocusOut>", lambda _e, b=binding: self.commit(b))
        widget.bind("<Return>", lambda _e, b=binding: self.commit(b, force_root=True))
        self.bindings.append(binding)
        return widget

    def _combo_field(self, parent, text, path, values, x, y, width=190):
        widgets.label(parent, text, x, y + 5, 114, 20)
        var = tk.StringVar()
        widget = widgets.combo(parent, x + 120, y, width, values, var)
        binding = Binding(var, path, "string", widget)
        widget.bind("<<ComboboxSelected>>", lambda _e, b=binding: self.commit(b))
        widget.bind("<FocusOut>", lambda _e, b=binding: self.commit(b))
        self.bindings.append(binding)
        return widget

    def _profile(self, root):
        card = self._card(
            "玩家档案", 10, 196,
            "改动先写入内存中的存档，点右下角「保存到磁盘」才写盘；需要备份可勾选底部的「保存前备份」",
        )
        self._field(card, "玩家名称", ("root", "name"), "string", 16, 60)
        self._combo_field(card, "界面语言", ("root", "language"), LANGUAGES, 348, 60)
        self._field(card, "星尘余额", ("root", "stardust"), "integer", 16, 98)
        self._field(card, "累计消耗星尘", ("root", "spentStardust"), "integer", 348, 98)
        self._field(card, "总游玩时长(分钟)", ("root", "totalPlayTimeMinutes"), "integer", 16, 136)
        self._field(card, "已清 Reverie 数", ("root", "completedReveries"), "integer", 348, 136)
        self._field(card, "剩余重选次数", ("root", "remainingRerolls"), "integer", 16, 174)

        unlock_card = self._card("解锁工具", 216, 240, "对未解锁内容批量放开；改完记得保存")
        entries = [
            ("全部英雄", "heroes", ("root", "heroes")),
            ("全部技能", "skills", ("root", "skills")),
            ("全部宝石", "gems", ("root", "gems")),
            ("全部遗物", "artifacts", ("root", "artifacts")),
            ("清晰梦境", "lucidDreams", ("root", "lucidDreams")),
            ("全部成就", "achievements", ("root", "achievements")),
            ("全部记忆", "memories", ("root", "storyNodes")),
        ]
        positions = [(16, 60), (200, 60), (384, 60), (568, 60), (16, 102), (200, 102), (384, 102)]
        for (text, mode, path), (x, y) in zip(entries, positions):
            count = len(self._get(path) or {})
            widgets.button(
                unlock_card, "%s (%d)" % (text, count), x, y, 174, 34,
                lambda m=mode: self.app.invoke_unlock(m),
            )
        widgets.button(unlock_card, "皮肤/饰品/表情/铭牌", 568, 102, 174, 34,
                       lambda: self.app.invoke_unlock("cosmetics"))
        widgets.button(unlock_card, "星象等级统一设为", 16, 144, 130, 34,
                       lambda: self.app.invoke_unlock("stars"))
        self.star_var = tk.StringVar(value="5")
        widgets.entry(unlock_card, 152, 148, 38, 26, textvariable=self.star_var, justify="center")
        widgets.button(
            unlock_card,
            "一键全部解锁（英雄 / 技能 / 宝石 / 遗物 / 梦境 / 记忆 / 成就 / 外观 / 星象）",
            16, 186, 726, 40, self.app.unlock_all, primary=True,
        )

        tips_card = self._card("使用提示", 468, 138)
        tips = [
            "• 所有修改只在内存里；点右下角「保存到磁盘」才写盘。默认不备份，需要留底就勾选底部「保存前备份」。",
            "• 写入后请在游戏里重新读档；建议先退出游戏再改，避免退出时被游戏的自动存档覆盖。",
            "• 解锁类改动若被 Steam/服务器校验拦下属正常；星尘、精通点、统计数据最稳定。",
            "• 快捷面板只覆盖常用字段，其余字段请到「JSON 树」页按路径修改。",
        ]
        for index, text in enumerate(tips):
            widgets.label(tips_card, text, 16, 42 + index * 22, 820, 20, theme.FONT_SMALL)

    def _stats(self, root):
        card = self._card("生涯统计（total）", 10, 292, "只影响统计面板显示，不会改变已解锁内容")
        rows = [
            ("精通等级", ("root", "total", "masteryLevel"), 16, 52),
            ("当前精通点", ("root", "total", "currentMasteryPoints"), 348, 52),
            ("累计精通点", ("root", "total", "totalMasteryPoints"), 16, 90),
            ("胜利场次", ("root", "total", "wins"), 348, 90),
            ("总场次", ("root", "total", "playCount"), 16, 128),
            ("失败场次", ("root", "total", "loses"), 348, 128),
            ("击杀总数", ("root", "total", "kills"), 16, 166),
            ("死亡次数", ("root", "total", "deaths"), 348, 166),
            ("游玩分钟", ("root", "total", "playTimeMinutes"), 16, 204),
            ("猎人击杀", ("root", "total", "hunterKills"), 348, 204),
            ("英雄首领击杀", ("root", "total", "heroicBossKills"), 16, 242),
            ("最长单局(秒)", ("root", "total", "maxElapsedGameTimeSeconds"), 348, 242),
        ]
        for text, path, x, y in rows:
            self._field(card, text, path, "integer", x, y)

        dejavu = self._card(
            "既视感（DeJaVu）", 422, 104,
            "让所有记忆/精粹都能在既视感里使用：把每条的胜场补到 5（需要先修好“纯白之梦”记录）",
        )
        widgets.button(dejavu, "全部记忆 / 精粹胜场设为 5", 16, 60, 260, 32, self.app.boost_dejavu_stats)

        tips = self._card("提示", 314, 96)
        lines = [
            "• 每个英雄的分项统计在「JSON 树」的 root.heroes.<英雄名> 下，可单独修改。",
            "• 精通等级影响局外成长，改太高会明显降低难度，请自行斟酌。",
        ]
        for index, text in enumerate(lines):
            widgets.label(tips, text, 16, 42 + index * 24, 820, 20, theme.FONT_SMALL)

    def _platform(self, root):
        graphics = (root or {}).get("graphics")
        if not isinstance(graphics, dict):
            card = self._card("画面设置", 10, 110)
            widgets.label(card, "这个文件里没有 graphics 段，画面设置可能存在 dl_platform.json 里。",
                          16, 50, 820, 24)
            return
        card = self._card("画面设置", 10, 196, "修改分辨率 / 帧率后需要重启游戏")
        rows = [
            ("分辨率宽", ("root", "graphics", "resolutionWidth"), "integer", 16, 60),
            ("分辨率高", ("root", "graphics", "resolutionHeight"), "integer", 348, 60),
            ("游戏帧率上限", ("root", "graphics", "gameFrameLimit"), "integer", 16, 98),
            ("菜单帧率上限", ("root", "graphics", "menuFrameLimit"), "integer", 348, 98),
            ("垂直同步", ("root", "graphics", "vSync"), "boolean", 16, 136),
            ("全屏模式(0-3)", ("root", "graphics", "fullScreenMode"), "integer", 348, 136),
        ]
        for text, path, kind, x, y in rows:
            self._field(card, text, path, kind, x, y)
        tips = self._card("说明", 216, 96)
        lines = [
            "• 全屏模式：0=独占全屏，1=无边框全屏，2=最大化窗口，3=窗口化。",
            "• 帧率上限填 -1 表示不限制。",
        ]
        for index, text in enumerate(lines):
            widgets.label(tips, text, 16, 42 + index * 24, 820, 20, theme.FONT_SMALL)

    def _continue(self, root):
        card = self._card("当前局进度", 10, 160)
        lines = [
            "这个文件保存「继续游戏」用的局内状态（英雄、技能、地图、掉落等），结构复杂且与进行中的对局绑定。",
            "建议不要手改；要清进度请在游戏里放弃本局。真要改，请用「JSON 树」页，并先保存一份备份。",
            "如果读档后卡住，用「备份与记录」页恢复最近一次备份即可。",
        ]
        for index, text in enumerate(lines):
            widgets.label(card, text, 16, 50 + index * 34, 820, 20,
                          theme.FONT_BODY if index == 0 else theme.FONT_SMALL)

    def _items(self, root):
        card = self._card("加密物品文件", 10, 130)
        lines = [
            "这个文件存的是加密后的物品归属记录（带 SteamID 签名），直接改会失效。",
            "需要解锁内容请回「玩家档案」用解锁工具。",
        ]
        for index, text in enumerate(lines):
            widgets.label(card, text, 16, 50 + index * 30, 820, 20,
                          theme.FONT_BODY if index == 0 else theme.FONT_SMALL)

    def _unknown(self, root):
        card = self._card("未知文件", 10, 100)
        widgets.label(card, "没有为这个文件准备快捷面板，请使用「JSON 树」页编辑。", 16, 50, 820, 20)

    # ---------------------------------------------------------------- 绑定
    def _get(self, path):
        node = self.app.doc.node if self.app.doc else None
        for key in path:
            if node is None:
                return None
            try:
                node = node[key]
            except (KeyError, IndexError, TypeError):
                return None
        return node

    def _set(self, path, value):
        node = self.app.doc.node
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    def load_values(self):
        for binding in self.bindings:
            value = self._get(binding.path)
            if binding.kind in ("integer", "number"):
                binding.var.set(jsonio.field_text(value, binding.kind))
            else:
                binding.var.set(jsonio.show(value))
            self._paint(binding, True)

    def _paint(self, binding, ok):
        widget = binding.widget
        try:
            if isinstance(widget, ttk.Combobox):
                return
            widget.configure(
                highlightbackground=theme.BORDER if ok else theme.BAD,
                highlightcolor=theme.ACCENT if ok else theme.BAD,
            )
        except tk.TclError:
            pass

    def commit(self, binding: Binding, force_root: bool = False):
        doc = self.app.doc
        if doc is None or self.app.suppress:
            return
        text = binding.var.get()
        if binding.kind != "string" and not text.strip():
            return
        old_value = self._get(binding.path)
        if binding.kind in ("integer", "number"):
            old_text = jsonio.field_text(old_value, binding.kind)
        else:
            old_text = jsonio.show(old_value)
        if text == old_text:
            self._paint(binding, True)
            if force_root:
                self.app.focus_set()
            return
        try:
            value = jsonio.make_scalar(text, binding.kind)
            self._set(binding.path, value)
            self._paint(binding, True)
            self.app.mark_changed("%s：%s → %s" % (".".join(binding.path), old_text, jsonio.show(value)))
        except Exception as exc:  # noqa: BLE001
            self._paint(binding, False)
            self.app.set_status("数值无效：%s" % exc, theme.BAD)
            if force_root:
                from tkinter import messagebox

                messagebox.showwarning("数值无效", str(exc), parent=self.app)
        finally:
            if force_root:
                self.app.focus_set()
