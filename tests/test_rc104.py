from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RC104RegressionTests(unittest.TestCase):
    def test_question_editor_uses_database_get_api(self):
        source = (ROOT / "fitopatoloji" / "quiz.py").read_text(encoding="utf-8")
        self.assertNotIn("self.db.get_disease(", source)
        self.assertIn("self.db.get(int(did))", source)

    def test_runtime_version_matches_package(self):
        common = (ROOT / "fitopatoloji" / "common.py").read_text(encoding="utf-8")
        self.assertIn('APP_VERSION = "2.0.0 RC10.11"', common)

if __name__ == "__main__":
    unittest.main()
