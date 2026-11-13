import json
from pathlib import Path
import tempfile
import unittest
from journal import Journal


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "events.jsonl"

    def test_durable_replay_and_unicode(self):
        self.assertTrue(Journal(self.path).append("one", {"温度": 21}))
        self.assertFalse(Journal(self.path).append("one", {"温度": 21}))
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 1)

    def test_conflict_does_not_append_or_replace(self):
        journal = Journal(self.path)
        journal.append("one", {"value": 1})
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "conflicting event"):
            journal.append("one", {"value": 2})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(Journal(self.path).events["one"], {"value": 1})

    def test_invalid_id_has_no_file_side_effect(self):
        for key in ("", None, 3):
            with self.assertRaises(ValueError):
                Journal(self.path).append(key, {})
        self.assertFalse(self.path.exists())

    def test_unserializable_payload_has_no_file_side_effect(self):
        with self.assertRaises(TypeError):
            Journal(self.path).append("bad", {1, 2})
        self.assertFalse(self.path.exists())

    def test_torn_record_is_explicit_failure(self):
        self.path.write_text('{"id":', encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            Journal(self.path)

    def test_conflicting_replay_is_explicit_failure(self):
        self.path.write_text('{"id":"a","payload":1}\n{"id":"a","payload":2}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting replay"):
            Journal(self.path)
