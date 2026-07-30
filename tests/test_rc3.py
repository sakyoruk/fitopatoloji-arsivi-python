# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from fitopatoloji.database import Database


class RC3RegressionTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fito_rc3_")
        self.db = Database(os.path.join(self.root, "test.db"))

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass
        shutil.rmtree(self.root, ignore_errors=True)

    def test_rc3_schema_and_catalogs(self):
        self.assertEqual(
            self.db.conn.execute("PRAGMA user_version").fetchone()[0],
            20010,
        )
        self.db.taxonomy_save(
            None, "Familya", "Peronosporaceae", "Oomycetes", ""
        )
        self.assertEqual(self.db.taxonomy_list()[0]["name"], "Peronosporaceae")

        self.db.host_save(None, {
            "taxon_level": "Tür",
            "common_name": "Domates",
            "scientific_name": "Solanum lycopersicum",
            "family_name": "Solanaceae",
            "genus_name": "Solanum",
            "species_name": "lycopersicum",
            "alternative_names": "",
            "notes": "",
        })
        self.assertEqual(self.db.host_list("Domates")[0]["family_name"], "Solanaceae")

    def test_structured_host_filter_does_not_use_free_text(self):
        disease_id = self.db.add({
            "scientific_name": "Etmen test",
            "disease_name": "Test hastalığı",
            "hosts": "Bu açıklamada hıyar sözcüğü geçiyor.",
        })
        self.db.host_save(None, {
            "taxon_level": "Tür",
            "common_name": "Kavun",
            "scientific_name": "Cucumis melo",
            "family_name": "Cucurbitaceae",
            "genus_name": "Cucumis",
            "species_name": "melo",
            "alternative_names": "",
            "notes": "",
        })
        host_id = self.db.host_list("Kavun")[0]["id"]
        self.db.disease_host_add(disease_id, host_id)

        self.assertEqual(len(self.db.search(host="Kavun")), 1)
        self.assertEqual(len(self.db.search(host="hıyar")), 0)


if __name__ == "__main__":
    unittest.main()
