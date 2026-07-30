# -*- coding: utf-8 -*-
import os, tempfile, unittest
from fitopatoloji.database import Database

class RC9Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'test.db'))
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def test_schema_and_photo_metadata(self):
        self.assertGreaterEqual(self.db.schema_version(),20011)
        now='2026-07-30 00:00:00'
        cur=self.db.conn.execute("INSERT INTO diseases(scientific_name,disease_name,created_at,updated_at) VALUES(?,?,?,?)",('A b','H',now,now)); did=cur.lastrowid
        cur=self.db.conn.execute("INSERT INTO attachments(disease_id,file_type,relative_path,created_at) VALUES(?,?,?,?)",(did,'image','x.jpg',now)); aid=cur.lastrowid; self.db.conn.commit()
        self.db.update_attachment_metadata(aid,'t','d','2026','s','Makro','p','c','CC','1 mm','Ankara')
        row=self.db.get_attachment(aid)
        self.assertEqual(row['photographer'],'p'); self.assertEqual(row['scale_info'],'1 mm'); self.assertEqual(row['location_text'],'Ankara')
    def test_reporting_indexes_exist(self):
        names={r[1] for r in self.db.conn.execute("PRAGMA index_list(diseases)").fetchall()}
        self.assertIn('idx_diseases_agent_group',names)
