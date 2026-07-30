# -*- coding: utf-8 -*-
import os, tempfile, unittest
from fitopatoloji.database import Database
from fitopatoloji.scientific import split_synonyms, scientific_name_suggestion

class RC71Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'x.db'))
    def tearDown(self): self.db.close(); self.tmp.cleanup()
    def test_synonym_split_and_search(self):
        did=self.db.add({'scientific_name':'Alternaria solani','disease_name':'Erken yanıklık','synonyms':'Macrosporium solani; Alternaria porri f. sp. solani'})
        self.assertEqual(len(self.db.disease_synonyms(did)),2)
        self.assertEqual(self.db.search('Macrosporium')[0]['id'],did)
    def test_scientific_suggestion(self):
        suggestion,notes=scientific_name_suggestion('alternaria Solani.')
        self.assertEqual(suggestion,'Alternaria solani')
        self.assertTrue(notes)
    def test_photo_category(self):
        did=self.db.add({'scientific_name':'X y','disease_name':'Test'})
        aid=self.db.add_attachment(did,'image','Attachments/a.jpg')
        self.db.update_attachment_metadata(aid,'T','D','2026','K','Mikroskop')
        self.assertEqual(self.db.get_attachment(aid)['image_category'],'Mikroskop')
if __name__=='__main__': unittest.main()
