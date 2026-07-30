# -*- coding: utf-8 -*-
import os, tempfile, unittest, json
from fitopatoloji.database import Database

class RC102Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'t.db'))
        now='2026-01-01 00:00:00'
        cur=self.db.conn.execute("INSERT INTO diseases(scientific_name,disease_name,created_at,updated_at) VALUES(?,?,?,?)",('A a','Hastalık A',now,now)); self.d1=cur.lastrowid
        cur=self.db.conn.execute("INSERT INTO diseases(scientific_name,disease_name,created_at,updated_at) VALUES(?,?,?,?)",('B b','Hastalık B',now,now)); self.d2=cur.lastrowid; self.db.conn.commit()
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_five_options_and_multiple_diseases(self):
        qid=self.db.quiz_question_save(disease_ids=[self.d1,self.d2],question_type='Çoktan seçmeli',question_text='Soru',difficulty='Orta',topic_tag='Taksonomi, Belirti',option_a='A',option_b='B',option_c='C',option_d='D',option_e='E',correct_answer='E',explanation='Açıklama',source_text='DOI:10.x',question_format_json='{}',option_a_format_json='{}',option_b_format_json='{}',option_c_format_json='{}',option_d_format_json='{}',option_e_format_json=json.dumps({'italic':[['1.0','1.1']]}),explanation_format_json='{}')
        row=self.db.quiz_question_get(qid); self.assertEqual(row['option_e'],'E'); self.assertEqual(self.db.quiz_question_disease_ids(qid),[self.d1,self.d2]); self.assertEqual(len(self.db.quiz_questions(disease_id=self.d2)),1)
    def test_question_types_and_history_delete(self):
        for typ,ans in [('Doğru / Yanlış','Doğru'),('Kısa cevap','yanıt')]:
            self.db.quiz_question_save(disease_ids=[],question_type=typ,question_text=typ,difficulty='Kolay',topic_tag='',option_a='',option_b='',option_c='',option_d='',option_e='',correct_answer=ans,explanation='',source_text='')
        self.assertEqual(len(self.db.quiz_questions()),2)
        sid=self.db.quiz_session_save('Sınav',2,1,1,0,50,12,[]); self.db.quiz_session_delete(sid); self.assertEqual(self.db.quiz_stats()['sessions'],0)
    def test_topic_tags(self):
        self.db.quiz_question_save(disease_ids=[],question_type='Kısa cevap',question_text='x',difficulty='Kolay',topic_tag='Taksonomi, Belirti',correct_answer='x')
        self.assertEqual(self.db.quiz_topic_tags(),['Belirti','Taksonomi'])

if __name__=='__main__':unittest.main()
