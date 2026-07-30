# -*- coding: utf-8 -*-
import os, tempfile, unittest
from fitopatoloji.database import Database

class RC109Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'test.db'))
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def test_combined_content_field_and_migration_schema(self):
        cols={r['name'] for r in self.db.conn.execute('PRAGMA table_info(diseases)').fetchall()}
        self.assertIn('content_body', cols)
        self.assertEqual(self.db.schema_version(), 20014)
    def test_many_documents_can_be_attached(self):
        did=self.db.add({'group_name':'ASCOMYCOTA','scientific_name':'Testus alpha','disease_name':'Test','content_body':'Belirti\nÖrnek'})
        self.db.add_attachment(did,'document','Documents/a.txt','A')
        self.assertEqual(len([x for x in self.db.attachments(did) if x['file_type']=='document']),1)
if __name__=='__main__': unittest.main()
