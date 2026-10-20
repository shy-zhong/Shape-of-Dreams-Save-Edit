"""解锁逻辑（全部为纯函数，方便测试）。"""

from __future__ import annotations

import time
from decimal import Decimal

__all__ = [
    "UNLOCK_LABELS",
    "unlock_status_dict",
    "unlock_category",
    "unlock_achievements",
    "unlock_stars",
    "unlock_cosmetics",
    "unlock_memories",
    "boost_dejavu_stats",
]

UNLOCK_LABELS = {
    "heroes": "英雄",
    "skills": "技能",
    "gems": "宝石",
    "artifacts": "遗物",
    "lucidDreams": "清晰梦境",
    "achievements": "成就",
    "memories": "记忆（旅人故事）",
    "cosmetics": "皮肤/饰品/表情/铭牌",
    "stars": "星象等级",
}

STATUS_CATEGORIES = ("heroes", "skills", "gems", "artifacts", "lucidDreams")
COSMETIC_CATEGORIES = ("skins", "accessories", "emotes", "nametags")


def _int(value, default=0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def unlock_status_dict(mapping) -> int:
    """把一组 {id: {status: ...}} 条目全部标为已解锁（status=2）。"""
    changed = 0
    if not isinstance(mapping, dict):
        return 0
    for entry in mapping.values():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status")) != "2":
            entry["status"] = Decimal(2)
            changed += 1
        if "isAvailableInGame" in entry:
            entry["isAvailableInGame"] = True
        if "isNewHeroOrHeroSkill" in entry:
            entry["isNewHeroOrHeroSkill"] = False
    return changed


def unlock_category(root: dict, mode: str) -> int:
    if mode in STATUS_CATEGORIES:
        return unlock_status_dict(root.get(mode))
    if mode == "achievements":
        return unlock_achievements(root)
    if mode == "stars":
        return unlock_stars(root)
    if mode == "cosmetics":
        return unlock_cosmetics(root)
    if mode == "memories":
        return unlock_memories(root)
    raise ValueError("未知解锁类别：%s" % mode)


def unlock_achievements(root: dict, now: int | None = None) -> int:
    now = int(now if now is not None else time.time())
    changed = 0
    for entry in (root.get("achievements") or {}).values():
        if not isinstance(entry, dict):
            continue
        if entry.get("isCompleted") is not True:
            entry["isCompleted"] = True
            changed += 1
        maximum = _int(entry.get("maxProgress", 0))
        if maximum > 0:
            entry["currentProgress"] = Decimal(maximum)
        if "completeTimestamp" in entry and _int(entry.get("completeTimestamp")) == 0:
            entry["completeTimestamp"] = Decimal(now)
    return changed


def unlock_stars(root: dict, target: int = 5) -> int:
    changed = 0
    for entry in (root.get("newStars") or {}).values():
        if not isinstance(entry, dict):
            continue
        if _int(entry.get("level")) != target:
            entry["level"] = Decimal(target)
            changed += 1
    return changed


def unlock_cosmetics(root: dict) -> int:
    changed = 0
    for category in COSMETIC_CATEGORIES:
        for entry in (root.get(category) or {}).values():
            if isinstance(entry, dict) and entry.get("isUnlocked") is not True:
                entry["isUnlocked"] = True
                changed += 1
    return changed


def unlock_memories(root: dict) -> int:
    """旅人故事：解锁节点 + 章节，并把阅读进度推进（-1 会被当成未读）。"""
    changed = 0
    for story in (root.get("storyNodes") or {}).values():
        if not isinstance(story, dict):
            continue
        if story.get("isUnlocked") is not True:
            story["isUnlocked"] = True
            changed += 1
        chunks = story.get("chunks")
        chapter_count = 0
        if isinstance(chunks, list):
            chapter_count = len(chunks)
            for chunk in chunks:
                if isinstance(chunk, dict) and chunk.get("isUnlocked") is not True:
                    chunk["isUnlocked"] = True
                    changed += 1
        if _int(story.get("lastReadChunk"), -1) < 0 and chapter_count > 0:
            story["lastReadChunk"] = Decimal(max(0, chapter_count - 1))
            changed += 1
    for category in ("heroes", "skills", "gems", "artifacts", "lucidDreams"):
        for entry in (root.get(category) or {}).values():
            if isinstance(entry, dict) and "didReadMemory" in entry and entry.get("didReadMemory") is not True:
                entry["didReadMemory"] = True
                changed += 1
    return changed


def boost_dejavu_stats(root: dict, target: int = 5) -> int:
    """既视感可用性：每条记忆/精粹的胜场 + 纯白之梦记录至少到 target。"""
    changed = 0
    for category in ("skills", "gems"):
        for item in (root.get(category) or {}).values():
            if not isinstance(item, dict):
                continue
            if _int(item.get("wins")) < target:
                item["wins"] = Decimal(target)
                changed += 1
            if _int(item.get("playCount")) < target:
                item["playCount"] = Decimal(target)
                changed += 1
    total = root.setdefault("total", {})
    if isinstance(total, dict) and _int(total.get("pureWhiteDreams")) < target:
        total["pureWhiteDreams"] = Decimal(target)
        changed += 1
    for hero in (root.get("heroes") or {}).values():
        if isinstance(hero, dict) and _int(hero.get("pureWhiteDreams")) < target:
            hero["pureWhiteDreams"] = Decimal(target)
            changed += 1
    return changed
