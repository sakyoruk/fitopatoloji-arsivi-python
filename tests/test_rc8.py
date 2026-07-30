# -*- coding: utf-8 -*-
import os, tempfile, unittest
from fitopatoloji.database import Database

class RC8Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'test.db'))
        self.did=self.db.add({'scientific_name':'Testus plantarum','disease_name':'Test hastalığı','group_name':'Fungus'})
    def tearDown(self): self.db.close(); self.tmp.cleanup()
    def test_question_crud_and_filter(self):
        qid=self.db.quiz_question_save(disease_id=self.did,question_type='Çoktan seçmeli',question_text='Etmen nedir?',difficulty='Kolay',topic_tag='Etmen',option_a='A',option_b='B',option_c='C',option_d='D',correct_answer='A',explanation='Açıklama',source_text='Kaynak')
        self.assertEqual(self.db.quiz_question_count(self.did),1)
        self.assertEqual(len(self.db.quiz_questions(disease_id=self.did,difficulty='Kolay',active_only=True)),1)
        self.assertEqual(self.db.quiz_question_get(qid)['correct_answer'],'A')
    def test_session_stats(self):
        self.db.quiz_session_save('Sınav',10,8,2,0,80.0,120,[])
        stats=self.db.quiz_stats(); self.assertEqual(stats['sessions'],1); self.assertEqual(stats['questions'],10); self.assertEqual(stats['average_score'],80.0)
    def test_schema_version(self): self.assertEqual(self.db.schema_version(),20009)
if __name__=='__main__': unittest.main()
