# -*- coding: utf-8 -*-
import os, shutil, tempfile, unittest, zipfile
from fitopatoloji.common import AppPaths
from fitopatoloji.database import Database

class RC2RegressionTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.mkdtemp(prefix="fito_rc2_")
        self.paths=AppPaths(self.root)
        self.db=Database(self.paths.database, None)
    def tearDown(self):
        try:self.db.close()
        except Exception:pass
        shutil.rmtree(self.root,ignore_errors=True)
    def test_schema_version_and_integrity(self):
        self.assertEqual(self.db.schema_version(), Database.SCHEMA_VERSION)
        self.assertEqual(self.db.conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
    def test_schema_is_idempotent(self):
        self.db.create_schema(); self.db.create_schema()
        self.assertEqual(self.db.schema_version(), Database.SCHEMA_VERSION)
    def test_pre_migration_backup(self):
        self.db.close()
        import sqlite3
        conn=sqlite3.connect(self.paths.database); conn.execute("PRAGMA user_version=1"); conn.commit(); conn.close()
        self.db=Database(self.paths.database,None)
        files=[x for x in os.listdir(self.paths.backups) if x.startswith("PreMigration_RC2_")]
        self.assertTrue(files)
    def test_core_crud(self):
        did=self.db.add({"scientific_name":"Testus rc2","disease_name":"RC2 test"})
        self.assertEqual(self.db.get(did)["disease_name"],"RC2 test")
        self.db.delete(did); self.assertIsNone(self.db.get(did))

if __name__=='__main__': unittest.main()
