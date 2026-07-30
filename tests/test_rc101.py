# -*- coding: utf-8 -*-
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RC101RegressionTests(unittest.TestCase):
    def test_disease_file_does_not_leave_global_mousewheel_callback(self):
        source = (ROOT / "fitopatoloji" / "disease_file.py").read_text(encoding="utf-8")
        self.assertNotIn('bind_all("<MouseWheel>"', source)
        self.assertIn('self.bind("<MouseWheel>", self._on_mousewheel', source)
        self.assertIn('except (tk.TclError, AttributeError)', source)

if __name__ == "__main__":
    unittest.main()
