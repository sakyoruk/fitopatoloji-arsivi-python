import json, os, tempfile, unittest
from fitopatoloji.database import Database

class RC103QuizTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'t.db'))
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def test_question_types_are_filtered_and_preserved(self):
        ids=[]
        for typ,answer in (("Çoktan seçmeli","A"),("Doğru / Yanlış","Doğru"),("Kısa cevap","yanıklık")):
            ids.append(self.db.quiz_question_save(question_type=typ,question_text=typ,difficulty="Orta",topic_tag="",source_text="",option_a="a",option_b="b",option_c="c",option_d="d",option_e="e",question_format_json="{}",option_a_format_json="{}",option_b_format_json="{}",option_c_format_json="{}",option_d_format_json="{}",option_e_format_json="{}",explanation_format_json="{}",correct_answer_format_json="{}",correct_answer=answer,explanation=""))
        self.assertEqual(len(self.db.quiz_questions(question_type="Doğru / Yanlış")),1)
        self.assertEqual(self.db.quiz_question_get(ids[2])["correct_answer"],"yanıklık")
    def test_rich_format_and_five_options_survive_edit(self):
        qid=self.db.quiz_question_save(question_type="Çoktan seçmeli",question_text="Alternaria",difficulty="Orta",topic_tag="",source_text="",option_a="a",option_b="b",option_c="c",option_d="d",option_e="e",question_format_json=json.dumps({"bolditalic":[["1.0","1.10"]]}),option_a_format_json="{}",option_b_format_json="{}",option_c_format_json="{}",option_d_format_json="{}",option_e_format_json="{}",explanation_format_json="{}",correct_answer_format_json="{}",correct_answer="A",explanation="")
        row=self.db.quiz_question_get(qid)
        self.assertEqual(row["option_e"],"e")
        self.assertIn("bolditalic",row["question_format_json"])
        self.assertIn("correct_answer_format_json",row.keys())
    def test_schema_20014(self): self.assertEqual(self.db.schema_version(),20014)
if __name__=='__main__': unittest.main()
