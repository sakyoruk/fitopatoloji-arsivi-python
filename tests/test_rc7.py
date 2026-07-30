# -*- coding: utf-8 -*-
import os, tempfile, unittest
from fitopatoloji.database import Database

class RC7Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Database(os.path.join(self.tmp.name,'test.db'))
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()
    def test_schema_version(self):
        self.assertEqual(self.db.schema_version(),20011)
    def test_literature_reuse_and_links(self):
        lid=self.db.literature_save(title='Plant Pathology',authors='Agrios',year_text='2005',publication_type='Kitap')
        base={'group_name':'Fungus','scientific_name':'A a','disease_name':'A','hosts':'','affected_organs':'','symptoms':'','pathogen_features':'','disease_cycle':'','epidemiology':'','differential_diagnosis':'','cultural_control':'','biological_control':'','chemical_control':'','distribution_turkey':'','distribution_world':'','climate_notes':'','sources':'','favorite':0,'notes':''}
        d1=self.db.add(base); base['scientific_name']='B b'; base['disease_name']='B'; d2=self.db.add(base)
        self.db.link_literature(d1,lid); self.db.link_literature(d2,lid)
        self.assertEqual(self.db.disease_literature(d1)[0]['title'],'Plant Pathology')
        self.assertEqual(self.db.disease_literature(d2)[0]['id'],lid)
    def test_private_notes_are_separate(self):
        base={'group_name':'','scientific_name':'C c','disease_name':'C','hosts':'','affected_organs':'','symptoms':'','pathogen_features':'','disease_cycle':'','epidemiology':'','differential_diagnosis':'','cultural_control':'','biological_control':'','chemical_control':'','distribution_turkey':'','distribution_world':'','climate_notes':'','sources':'','favorite':0,'notes':''}
        did=self.db.add(base); self.db.save_private_note(did,'rapora girmez')
        self.assertEqual(self.db.private_note(did),'rapora girmez')
        self.assertEqual(self.db.get(did)['notes'],'')
if __name__=='__main__': unittest.main()
