from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RC1011RegressionTests(unittest.TestCase):
    def test_host_editor_callbacks_exist(self):
        text=(ROOT / "fitopatoloji" / "editor.py").read_text(encoding="utf-8")
        for name in ("_select_hosts", "_remove_selected_hosts", "_edit_selected_host_relation", "_refresh_selected_hosts"):
            self.assertIn("def %s(" % name, text)

if __name__ == "__main__":
    unittest.main()
