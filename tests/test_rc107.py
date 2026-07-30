from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RC107QuizLayoutTests(unittest.TestCase):
    def test_image_precedes_question_and_result_footer_is_fixed(self):
        text=(ROOT / "fitopatoloji" / "quiz.py").read_text(encoding="utf-8")
        self.assertIn('before=self.q_text', text)
        self.assertIn('footer.pack(fill="x",side="bottom")', text)
        self.assertIn('exp.pack(fill="both",expand=True', text)
    def test_mode_help_is_explained(self):
        text=(ROOT / "fitopatoloji" / "quiz.py").read_text(encoding="utf-8")
        self.assertIn('Çalışma modunda her soruda doğru cevap ve açıklama', text)
        self.assertIn('Sınav modunda cevaplar değerlendirme sonuna kadar gizli tutulur', text)

if __name__ == "__main__": unittest.main()
