# -*- coding: utf-8 -*-
from .common import *
from .database import Database

def self_test():
    root = tempfile.mkdtemp(prefix="fitopatoloji_test_")
    try:
        paths = AppPaths(root)
        seed = resource_path("seed", "diseases.csv")
        if not os.path.exists(seed):
            seed = os.path.join(root, "diseases.csv")
            with open(seed, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["group_name", "scientific_name", "synonyms", "disease_name"],
                )
                writer.writeheader()
                for index in range(283):
                    writer.writerow({
                        "group_name": "TEST",
                        "scientific_name": "Etmen {}".format(index + 1),
                        "synonyms": "",
                        "disease_name": "Hastalık {}".format(index + 1),
                    })
        db = Database(paths.database, seed)
        assert db.count() == 283, "Beklenen başlangıç kayıt sayısı 283, bulunan: {}".format(db.count())
        new_id = db.add({
            "group_name": "TEST",
            "scientific_name": "Testus exemplum",
            "disease_name": "Test hastalığı",
            "hosts": "Test konukçusu",
            "affected_organs": "Test yaprağı",
            "symptoms": "Test lekesi ve solgunluk",
            "distribution_turkey": "Ankara",
            "favorite": 1,
        })
        assert db.get(new_id)["scientific_name"] == "Testus exemplum"
        db.save_rich_text(new_id, {"symptoms": {"tags": [{"name": "italic", "ranges": [["1.0", "1.4"]]}]}})
        assert db.rich_text(new_id)["symptoms"]["tags"][0]["name"] == "italic"

        db.update(new_id, {
            "group_name": "TEST",
            "scientific_name": "Testus exemplum",
            "disease_name": "Güncel test hastalığı",
            "hosts": "Test konukçusu",
            "affected_organs": "Test yaprağı",
            "symptoms": "Test lekesi ve solgunluk",
            "distribution_turkey": "Ankara",
            "favorite": 1,
        })
        assert db.get(new_id)["disease_name"] == "Güncel test hastalığı"

        # Arama ve teşhis testleri gerçek seed içeriğine bağlı olmamalı.
        assert any(row["id"] == new_id for row in db.search("Testus exemplum"))
        assert any(row["id"] == new_id for row in db.search(host="Test konukçusu"))
        assert any(item[1]["id"] == new_id for item in db.diagnose(
            host="Test konukçusu", organ="Test yaprağı", symptom="leke", group_name="TEST"
        ))
        assert db.search(favorites_only=True)
        ref_id = db.add_reference(new_id, "Makale", "Test kaynak", "10.0000/test")
        assert db.references(new_id)
        assert db.statistics()["references"] >= 1
        db.delete_reference(ref_id)

        db.delete(new_id)
        assert db.get(new_id) is None
        backup = os.path.join(root, "backup.db")
        db.backup_to(backup)
        assert os.path.exists(backup)
        db.close()
        print("SELF-TEST OK: seed, CRUD, gelişmiş arama, teşhis ve SQLite yedekleme başarılı.")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


