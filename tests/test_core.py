"""核心逻辑单元测试：python -m unittest discover -s tests"""

from __future__ import annotations

import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sod_save_editor.core import edits, jsonio, unlocks  # noqa: E402
from sod_save_editor.core.backups import BackupStore  # noqa: E402
from sod_save_editor.core.documents import Document, detect_kind, target_from_backup  # noqa: E402


class JsonIoTest(unittest.TestCase):
    def test_roundtrip_is_byte_identical(self):
        raw = '{"root":{"a":1,"b":38642.0,"c":"中文","d":[1,2],"e":true,"f":null}}'
        self.assertEqual(jsonio.dumps(jsonio.loads(raw)), raw)

    def test_large_float_kept(self):
        raw = '{"damage":321547.36102294922}'
        self.assertEqual(jsonio.dumps(jsonio.loads(raw)), raw)

    def test_field_text_trims_zero(self):
        self.assertEqual(jsonio.field_text(Decimal("1042.0")), "1042")
        self.assertEqual(jsonio.field_text(Decimal("1042")), "1042")

    def test_make_scalar(self):
        self.assertEqual(jsonio.make_scalar("42", "integer"), Decimal(42))
        self.assertEqual(jsonio.make_scalar("1042.0", "integer"), Decimal(1042))
        self.assertEqual(jsonio.make_scalar("abc", "string"), "abc")
        self.assertIs(jsonio.make_scalar("true", "boolean"), True)
        self.assertIsNone(jsonio.make_scalar("null", "null"))
        with self.assertRaises(ValueError):
            jsonio.make_scalar("abc", "integer")


class DiffTest(unittest.TestCase):
    def test_diff_reports_changed_path(self):
        a = jsonio.loads('{"root":{"x":1,"y":2}}')
        b = jsonio.loads('{"root":{"x":1,"y":3}}')
        changes = edits.diff(a, b)
        self.assertEqual(changes, [("root.y", "2", "3")])

    def test_diff_reports_added(self):
        a = jsonio.loads('{"root":{}}')
        b = jsonio.loads('{"root":{"k":1}}')
        self.assertEqual(edits.diff(a, b), [("root.k", "(新增)", "1")])


class UnlockTest(unittest.TestCase):
    def _root(self):
        return jsonio.loads(
            '{"root":{'
            '"skills":{"St_A":{"status":0,"didReadMemory":false,"isAvailableInGame":false}},'
            '"gems":{"Gem_A":{"status":1,"didReadMemory":false}},'
            '"achievements":{"ACH":{"isCompleted":false,"currentProgress":0,"maxProgress":5,'\
            '"completeTimestamp":0}},'
            '"newStars":{"Se_A":{"level":1}},'
            '"skins":{"Skin_A":{"isUnlocked":false}},'
            '"storyNodes":{"S1":{"isUnlocked":false,"lastReadChunk":-1,"chunks":null},'
            '"S2":{"isUnlocked":false,"lastReadChunk":-1,"chunks":[{"isUnlocked":false,"lastPage":0},'
            '{"isUnlocked":false,"lastPage":0}]}},'
            '"total":{"pureWhiteDreams":0},'
            '"heroes":{"Hero_A":{"pureWhiteDreams":0}}'
            "}}"
        )["root"]

    def test_status_dict(self):
        root = self._root()
        changed = unlocks.unlock_category(root, "skills")
        self.assertEqual(changed, 1)
        self.assertEqual(root["skills"]["St_A"]["status"], Decimal(2))
        self.assertTrue(root["skills"]["St_A"]["isAvailableInGame"])
        self.assertFalse(root["skills"]["St_A"]["didReadMemory"])  # 只由 memories 模式补齐

    def test_achievements(self):
        root = self._root()
        unlocks.unlock_category(root, "achievements")
        entry = root["achievements"]["ACH"]
        self.assertTrue(entry["isCompleted"])
        self.assertEqual(entry["currentProgress"], Decimal(5))
        self.assertGreater(int(entry["completeTimestamp"]), 0)

    def test_stars_and_cosmetics(self):
        root = self._root()
        self.assertEqual(unlocks.unlock_stars(root, 5), 1)
        self.assertEqual(root["newStars"]["Se_A"]["level"], Decimal(5))
        self.assertEqual(unlocks.unlock_cosmetics(root), 1)

    def test_memories(self):
        root = self._root()
        changed = unlocks.unlock_memories(root)
        self.assertGreater(changed, 0)
        self.assertTrue(root["storyNodes"]["S1"]["isUnlocked"])
        self.assertTrue(root["storyNodes"]["S2"]["chunks"][0]["isUnlocked"])
        self.assertGreaterEqual(int(root["storyNodes"]["S2"]["lastReadChunk"]), 0)
        self.assertTrue(root["skills"]["St_A"]["didReadMemory"])

    def test_dejavu_stats(self):
        root = self._root()
        unlocks.boost_dejavu_stats(root)
        self.assertEqual(root["total"]["pureWhiteDreams"], Decimal(5))
        self.assertEqual(root["heroes"]["Hero_A"]["pureWhiteDreams"], Decimal(5))


class DocumentTest(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(detect_kind("r_profile1df00.json"), "profile")
        self.assertEqual(detect_kind("r_stats1df00.json"), "stats")
        self.assertEqual(detect_kind("dl_platform.json"), "platform")
        self.assertEqual(detect_kind("backup_items.json"), "items")

    def test_backup_name(self):
        self.assertEqual(
            target_from_backup("20261020_163038_r_profile1df00.json"), "r_profile1df00.json"
        )
        self.assertEqual(
            target_from_backup("20261020_163038_manual_r_stats1df00.json"), "r_stats1df00.json"
        )

    def test_document_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r_profile1.json"
            raw = '{"root":{"stardust":3606}}'
            path.write_text(raw, encoding="utf-8")
            doc = Document.load(path)
            self.assertEqual(doc.text(), raw)
            doc.node["root"]["stardust"] = Decimal(999)
            self.assertTrue(doc.refresh_dirty())

    def test_backup_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            target = folder / "r_profile1.json"
            target.write_text('{"root":{"a":1}}', encoding="utf-8")
            store = BackupStore(folder)
            backup = store.create(target)
            self.assertTrue(backup.is_file())
            self.assertEqual(len(store.list()), 1)
            target.write_text('{"root":{"a":2}}', encoding="utf-8")
            restored = store.restore(backup)
            self.assertEqual(restored.read_text(encoding="utf-8"), '{"root":{"a":1}}')
            self.assertEqual(len(store.list()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
