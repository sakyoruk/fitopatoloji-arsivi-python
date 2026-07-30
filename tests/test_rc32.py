# -*- coding: utf-8 -*-
import unittest
from types import SimpleNamespace

from fitopatoloji.editor import DiseaseEditor


class AutosaveDraftTests(unittest.TestCase):
    def _fake_editor(self, draft_key, initial):
        calls = []
        fake = SimpleNamespace(
            _draft_job=123,
            dirty=True,
            on_draft=lambda *args: calls.append(args),
            draft_key=draft_key,
            initial=initial,
            change_var=SimpleNamespace(set=lambda value: None),
            _collect=lambda: {"scientific_name": "Test", "_rich_text": {"symptoms": []}},
        )
        return fake, calls

    def test_existing_record_autosave_passes_disease_id(self):
        fake, calls = self._fake_editor("edit:42", {"id": 42})
        DiseaseEditor._autosave_draft(fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "edit:42")
        self.assertEqual(calls[0][1], 42)
        self.assertEqual(calls[0][2]["scientific_name"], "Test")
        self.assertEqual(calls[0][3], {"symptoms": []})

    def test_recovered_draft_gets_id_from_key(self):
        fake, calls = self._fake_editor("edit:77", {})
        DiseaseEditor._autosave_draft(fake)
        self.assertEqual(calls[0][1], 77)

    def test_new_record_autosave_passes_none_id(self):
        fake, calls = self._fake_editor("new", {})
        DiseaseEditor._autosave_draft(fake)
        self.assertIsNone(calls[0][1])


if __name__ == "__main__":
    unittest.main()
