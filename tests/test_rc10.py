# -*- coding: utf-8 -*-
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RC10VisualTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual((ROOT / "VERSION.txt").read_text(encoding="utf-8").strip(), "2.0.0 RC10.10")

    def test_theme_has_visual_tokens(self):
        text=(ROOT / "fitopatoloji" / "theme.py").read_text(encoding="utf-8")
        for token in ("nav_active", "NavActive.TButton", "Badge.TLabel", "MetricValue.TLabel"):
            self.assertIn(token, text)

    def test_main_window_has_record_metrics(self):
        text=(ROOT / "fitopatoloji" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("record_metric_vars", text)
        self.assertIn("list_count_label", text)
        self.assertIn("ÖĞRENME VE ANALİZ", text)

    def test_dashboard_has_extended_metrics(self):
        text=(ROOT / "fitopatoloji" / "dashboard.py").read_text(encoding="utf-8")
        for word in ("Konukçular", "Literatür", "Fotoğraflar", "Sorular"):
            self.assertIn(word, text)

if __name__ == "__main__": unittest.main()
