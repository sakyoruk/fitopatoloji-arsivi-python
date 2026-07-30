# -*- coding: utf-8 -*-
import os, tempfile, unittest
from pathlib import Path
from fitopatoloji.database import Database

ROOT=Path(__file__).resolve().parents[1]

class RC106QuizImageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,"fitopatoloji.db"))
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def test_quiz_image_metadata_roundtrip(self):
        qid=self.db.quiz_question_save(question_type="Doğru / Yanlış",question_text="Görsel soru",difficulty="Orta",topic_tag="Tanı",correct_answer="Doğru",explanation="Açıklama",source_text="Kaynak",image_path="quiz_test.jpg",image_caption="Yaprak belirtisi",image_source="Makale",image_copyright="CC BY")
        row=self.db.quiz_question_get(qid)
        self.assertEqual(row["image_path"],"quiz_test.jpg"); self.assertEqual(row["image_caption"],"Yaprak belirtisi"); self.assertEqual(row["image_copyright"],"CC BY")
    def test_startup_does_not_auto_open_dashboard(self):
        text=(ROOT/"fitopatoloji"/"main_window.py").read_text(encoding="utf-8")
        self.assertNotIn('self.after(500, self.open_dashboard)',text)
        settings=(ROOT/"fitopatoloji"/"maintenance.py").read_text(encoding="utf-8")
        self.assertIn('"open_dashboard": False',settings)
