from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RC105QuizLayoutTests(unittest.TestCase):
    def test_compact_multiple_choice_layout(self):
        text = (ROOT / "fitopatoloji" / "quiz.py").read_text(encoding="utf-8")
        self.assertIn('self.geometry("1040x760")', text)
        self.assertIn('option_area.columnconfigure(0,weight=1)', text)
        self.assertIn('ans.grid(row=2,column=1', text)
        self.assertIn('height=1', text)

if __name__ == "__main__":
    unittest.main()
