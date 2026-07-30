# -*- coding: utf-8 -*-
import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RC108Tests(unittest.TestCase):
    def test_exam_scrollable_and_fixed_footer(self):
        text=(ROOT/'fitopatoloji'/'quiz.py').read_text(encoding='utf-8')
        self.assertIn('self.exam_canvas=tk.Canvas', text)
        self.assertIn('footer.pack(fill="x",side="bottom"', text)
        self.assertIn('def _option_height', text)
    def test_compact_richtext_toolbar(self):
        text=(ROOT/'fitopatoloji'/'quiz.py').read_text(encoding='utf-8')
        self.assertIn('text="B", width=2', text)
        self.assertNotIn('Ctrl+B / Ctrl+I", style="Muted.TLabel"', text)
if __name__=='__main__': unittest.main()
