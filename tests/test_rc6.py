# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from fitopatoloji.database import Database
from fitopatoloji.rich_utils import to_html, to_reportlab


class RC6CombinedTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="fitopatoloji_rc6_")
        self.db = Database(os.path.join(self.tempdir, "fitopatoloji.db"))

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_extended_taxonomy_catalog(self):
        self.db.taxonomy_save(None, "Familya", "Pseudomonadaceae", "Pseudomonadales", "", "Bakteriyel etmenler", "Bakteri", "LPSN", "2026-07-30")
        row = self.db.taxonomy_list(agent_group="Bakteri")[0]
        self.assertEqual(row["source"], "LPSN")
        self.assertEqual(row["agent_group"], "Bakteri")

    def test_host_detail_and_relation_replacement(self):
        self.db.host_save(None, {"taxon_level":"Tür","common_name":"Domates","scientific_name":"Solanum lycopersicum","family_name":"Solanaceae","genus_name":"Solanum","species_name":"lycopersicum","subspecies_name":"","variety_name":"","cultivar_name":"Marmande","host_group":"Sebzeler","alternative_names":"","notes":""})
        host_id = self.db.host_list("Domates")[0]["id"]
        disease_id = self.db.add({"scientific_name":"Testus pathogenus","disease_name":"Test hastalığı"})
        self.db.replace_disease_hosts(disease_id,[{"host_id":host_id,"relation_type":"Deneysel konukçu","scope_type":"Çeşit / kültivar düzeyi","relation_note":"Kontrollü koşullar","is_excluded":0}])
        relation = self.db.disease_hosts(disease_id)[0]
        self.assertEqual(relation["relation_type"], "Deneysel konukçu")
        self.assertEqual(relation["cultivar_name"], "Marmande")

    def test_combined_rich_text_html_and_pdf_markup(self):
        formatting={"version":2,"tags":[
            {"name":"bold","ranges":[["1.0","1.8"]]},
            {"name":"italic","ranges":[["1.0","1.8"]]},
            {"name":"strikethrough","ranges":[["1.0","1.8"]]},
            {"name":"fontsize_12","ranges":[["1.0","1.8"]]},
        ]}
        html=to_html("Alternaria",formatting)
        pdf=to_reportlab("Alternaria",formatting)
        self.assertIn("<b>",html); self.assertIn("<i>",html); self.assertIn("<s>",html)
        self.assertIn("<b>",pdf); self.assertIn("<i>",pdf); self.assertIn("<strike>",pdf)


if __name__ == "__main__":
    unittest.main()
