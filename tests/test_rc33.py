# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest

from fitopatoloji.database import Database
from fitopatoloji.editor import merge_host_ids


class MultiHostRelationTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fito_rc33_")
        self.db = Database(os.path.join(self.root, "test.db"))

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.root, ignore_errors=True)

    def _host(self, common, scientific):
        self.db.host_save(None, {
            "taxon_level": "Tür", "common_name": common,
            "scientific_name": scientific, "family_name": "Testaceae",
            "genus_name": scientific.split()[0], "species_name": scientific.split()[-1],
            "alternative_names": "", "notes": "",
        })
        return int(self.db.host_list(common)[0]["id"])

    def test_merge_preserves_existing_and_removes_duplicates(self):
        self.assertEqual(merge_host_ids([1, 2], [2, 3, "3", 4]), [1, 2, 3, 4])

    def test_one_disease_can_have_many_hosts(self):
        disease_id = self.db.add({"scientific_name": "Test pathogen", "disease_name": "Test disease"})
        ids = [self._host("Kavun", "Cucumis melo"), self._host("Karpuz", "Citrullus lanatus"), self._host("Hıyar", "Cucumis sativus")]
        for host_id in ids:
            self.db.disease_host_add(disease_id, host_id)
        rows = self.db.disease_hosts(disease_id)
        self.assertEqual({int(r["id"]) for r in rows}, set(ids))
        self.assertEqual(len(self.db.search(host="Kavun")), 1)
        self.assertEqual(len(self.db.search(host="Karpuz")), 1)
        self.assertEqual(len(self.db.search(host="Hıyar")), 1)


if __name__ == "__main__":
    unittest.main()
