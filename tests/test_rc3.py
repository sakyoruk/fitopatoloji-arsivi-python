import os, tempfile
from fitopatoloji.database import Database


def make_db():
    root=tempfile.mkdtemp(prefix="fito_rc3_")
    return Database(os.path.join(root,"test.db"))


def test_rc3_schema_and_catalogs():
    db=make_db()
    assert db.conn.execute("PRAGMA user_version").fetchone()[0] == 20003
    db.taxonomy_save(None,"Familya","Peronosporaceae","Oomycetes","")
    assert db.taxonomy_list()[0]["name"] == "Peronosporaceae"
    db.host_save(None,{"taxon_level":"Tür","common_name":"Domates","scientific_name":"Solanum lycopersicum","family_name":"Solanaceae","genus_name":"Solanum","species_name":"lycopersicum","alternative_names":"","notes":""})
    assert db.host_list("Domates")[0]["family_name"] == "Solanaceae"


def test_structured_host_filter_does_not_use_free_text():
    db=make_db()
    disease_id=db.add({"scientific_name":"Etmen test","disease_name":"Test hastalığı","hosts":"Bu açıklamada hıyar sözcüğü geçiyor."})
    db.host_save(None,{"taxon_level":"Tür","common_name":"Kavun","scientific_name":"Cucumis melo","family_name":"Cucurbitaceae","genus_name":"Cucumis","species_name":"melo","alternative_names":"","notes":""})
    host_id=db.host_list("Kavun")[0]["id"]
    db.disease_host_add(disease_id,host_id)
    assert len(db.search(host="Kavun")) == 1
    assert len(db.search(host="hıyar")) == 0
