# -*- coding: utf-8 -*-
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RC1010RegressionTests(unittest.TestCase):
    def test_file_manager_callback_exists(self):
        source = (ROOT / "fitopatoloji" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("def open_file_manager(self):", source)
        self.assertIn("FileManager(self, self.db, self.paths, self.selected_id", source)

if __name__ == "__main__":
    unittest.main()
