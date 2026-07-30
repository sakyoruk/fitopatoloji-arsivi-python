# -*- coding: utf-8 -*-
from .common import *

class Database(object):
    def __init__(self, db_path, seed_csv=None):
        self.db_path = db_path
        self.seed_csv = seed_csv
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.create_schema()
        self.seed_if_empty()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def create_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS diseases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL DEFAULT '',
                scientific_name TEXT NOT NULL,
                synonyms TEXT NOT NULL DEFAULT '',
                disease_name TEXT NOT NULL,
                hosts TEXT NOT NULL DEFAULT '',
                affected_organs TEXT NOT NULL DEFAULT '',
                symptoms TEXT NOT NULL DEFAULT '',
                pathogen_features TEXT NOT NULL DEFAULT '',
                disease_cycle TEXT NOT NULL DEFAULT '',
                epidemiology TEXT NOT NULL DEFAULT '',
                differential_diagnosis TEXT NOT NULL DEFAULT '',
                cultural_control TEXT NOT NULL DEFAULT '',
                biological_control TEXT NOT NULL DEFAULT '',
                chemical_control TEXT NOT NULL DEFAULT '',
                distribution_turkey TEXT NOT NULL DEFAULT '',
                distribution_world TEXT NOT NULL DEFAULT '',
                climate_notes TEXT NOT NULL DEFAULT '',
                sources TEXT NOT NULL DEFAULT '',
                favorite INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_id INTEGER NOT NULL,
                file_type TEXT NOT NULL DEFAULT 'document',
                relative_path TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_diseases_group ON diseases(group_name);
            CREATE INDEX IF NOT EXISTS idx_diseases_scientific ON diseases(scientific_name);
            CREATE TABLE IF NOT EXISTS disease_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_id INTEGER NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'Makale',
                citation TEXT NOT NULL DEFAULT '',
                identifier TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_attachments_disease ON attachments(disease_id);
            CREATE INDEX IF NOT EXISTS idx_references_disease ON disease_references(disease_id);

            CREATE TABLE IF NOT EXISTS disease_rich_text (
                disease_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                formatting_json TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY (disease_id, field_name),
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attachment_annotations (
                attachment_id INTEGER PRIMARY KEY,
                annotations_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(attachment_id) REFERENCES attachments(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS disease_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, disease_id INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL, rich_json TEXT NOT NULL DEFAULT '{}',
                changed_fields TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_history_disease ON disease_history(disease_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS disease_drafts (
                draft_key TEXT PRIMARY KEY, disease_id INTEGER, data_json TEXT NOT NULL,
                rich_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS disease_tags (
                disease_id INTEGER NOT NULL, tag TEXT NOT NULL,
                PRIMARY KEY(disease_id, tag),
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS workspace_notes (
                id INTEGER PRIMARY KEY CHECK (id = 1), note_text TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS disease_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, disease_id INTEGER, task_text TEXT NOT NULL,
                is_done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_done ON disease_tasks(is_done, updated_at DESC);
            CREATE TABLE IF NOT EXISTS monograph_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
                config_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS monograph_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                output_path TEXT NOT NULL, disease_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            """
        )
        disease_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(diseases)").fetchall()]
        for column_name, definition in [
            ("distribution_turkey", "TEXT NOT NULL DEFAULT ''"),
            ("distribution_world", "TEXT NOT NULL DEFAULT ''"),
            ("climate_notes", "TEXT NOT NULL DEFAULT ''"),
            ("favorite", "INTEGER NOT NULL DEFAULT 0"),
            ("deleted_at", "TEXT NOT NULL DEFAULT ''"),
        ]:
            if column_name not in disease_columns:
                self.conn.execute("ALTER TABLE diseases ADD COLUMN {} {}".format(column_name, definition))

        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(attachments)").fetchall()]
        for column_name, definition in [
            ("is_primary", "INTEGER NOT NULL DEFAULT 0"),
            ("title", "TEXT NOT NULL DEFAULT ''"),
            ("captured_at", "TEXT NOT NULL DEFAULT ''"),
            ("source", "TEXT NOT NULL DEFAULT ''"),
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if column_name not in columns:
                self.conn.execute("ALTER TABLE attachments ADD COLUMN {} {}".format(column_name, definition))
        self.conn.execute("UPDATE attachments SET sort_order = id WHERE sort_order = 0")
        self.conn.commit()

    def seed_if_empty(self):
        count = self.conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
        if count or not self.seed_csv or not os.path.exists(self.seed_csv):
            return
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.seed_csv, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for row in reader:
                rows.append((
                    row.get("group_name", "").strip(),
                    row.get("scientific_name", "").strip(),
                    row.get("synonyms", "").strip(),
                    row.get("disease_name", "").strip(),
                    now, now,
                ))
        self.conn.executemany(
            """INSERT INTO diseases
               (group_name, scientific_name, synonyms, disease_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            rows,
        )
        self.conn.commit()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM diseases WHERE COALESCE(deleted_at, '')=''").fetchone()[0]

    def list_groups(self):
        return [row[0] for row in self.conn.execute(
            "SELECT DISTINCT group_name FROM diseases WHERE group_name <> '' AND COALESCE(deleted_at, '')='' ORDER BY group_name COLLATE NOCASE"
        ).fetchall()]

    def search(self, query="", group_name="", host="", organ="", symptom="", favorites_only=False):
        query = (query or "").strip()
        group_name = (group_name or "").strip()
        host = (host or "").strip()
        organ = (organ or "").strip()
        symptom = (symptom or "").strip()
        favorites_only = bool(favorites_only)
        clauses = ["COALESCE(deleted_at, '') = ''"]
        params = []

        if favorites_only:
            clauses.append("favorite = 1")

        if group_name and group_name != "TÜMÜ":
            clauses.append("group_name = ?")
            params.append(group_name)

        searchable = [
            "group_name", "scientific_name", "synonyms", "disease_name",
            "hosts", "affected_organs", "symptoms", "pathogen_features",
            "disease_cycle", "epidemiology", "differential_diagnosis",
            "cultural_control", "biological_control", "chemical_control",
            "distribution_turkey", "distribution_world", "climate_notes",
            "sources", "notes"
        ]
        if query:
            like = "%" + query + "%"
            clauses.append("(" + " OR ".join([field + " LIKE ?" for field in searchable]) + ")")
            params.extend([like] * len(searchable))
        if host:
            clauses.append("hosts LIKE ?")
            params.append("%" + host + "%")
        if organ:
            clauses.append("affected_organs LIKE ?")
            params.append("%" + organ + "%")
        if symptom:
            clauses.append("symptoms LIKE ?")
            params.append("%" + symptom + "%")

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = (
            "SELECT id, group_name, scientific_name, disease_name, favorite "
            "FROM diseases" + where +
            " ORDER BY scientific_name COLLATE NOCASE, disease_name COLLATE NOCASE"
        )
        return self.conn.execute(sql, params).fetchall()

    def distinct_terms(self, field_name):
        allowed = {"hosts", "affected_organs", "symptoms"}
        if field_name not in allowed:
            return []
        rows = self.conn.execute(
            "SELECT {} FROM diseases WHERE {} <> ''".format(field_name, field_name)
        ).fetchall()
        terms = set()
        for row in rows:
            value = row[0] or ""
            for part in re.split(r"[,;\n/|]+", value):
                part = " ".join(part.strip().split())
                if 2 <= len(part) <= 80:
                    terms.add(part)
        return sorted(terms, key=lambda value: value.lower())

    def diagnose(self, host="", organ="", symptom="", group_name=""):
        host = (host or "").strip().lower()
        organ = (organ or "").strip().lower()
        group_name = (group_name or "").strip().lower()
        symptom_text = (symptom or "").strip().lower()
        symptom_words = [w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", symptom_text) if len(w) > 2]
        rows = self.conn.execute(
            """SELECT id, group_name, scientific_name, disease_name,
                      hosts, affected_organs, symptoms, epidemiology,
                      differential_diagnosis
               FROM diseases"""
        ).fetchall()
        results = []
        for row in rows:
            score = 0
            matched = []
            row_group = (row["group_name"] or "").lower()
            hosts = (row["hosts"] or "").lower()
            organs = (row["affected_organs"] or "").lower()
            symptoms = (row["symptoms"] or "").lower()
            extra_text = "{} {}".format(
                row["epidemiology"] or "",
                row["differential_diagnosis"] or "",
            ).lower()

            if group_name and group_name != "tümü":
                if group_name == row_group:
                    score += 2
                    matched.append("etmen grubu")
                else:
                    continue

            if host:
                if host in hosts:
                    score += 6
                    matched.append("konukçu")
                else:
                    host_tokens = [w for w in host.split() if len(w) > 2]
                    partial = sum(1 for word in host_tokens if word in hosts)
                    if partial:
                        score += partial * 2
                        matched.append("kısmi konukçu")
                    else:
                        continue

            if organ:
                if organ in organs:
                    score += 5
                    matched.append("organ")
                else:
                    organ_tokens = [w for w in organ.split() if len(w) > 2]
                    partial = sum(1 for word in organ_tokens if word in organs)
                    if partial:
                        score += partial * 2
                        matched.append("kısmi organ")
                    else:
                        continue

            if symptom_words:
                exact_phrase = bool(symptom_text and symptom_text in symptoms)
                symptom_hits = sum(1 for word in symptom_words if word in symptoms)
                context_hits = sum(1 for word in symptom_words if word in extra_text)
                if exact_phrase:
                    score += 8
                    matched.append("tam belirti")
                if symptom_hits:
                    score += symptom_hits * 3
                    matched.append("{} belirti sözcüğü".format(symptom_hits))
                if context_hits:
                    score += context_hits
                    matched.append("{} ek bağlam".format(context_hits))
                if not exact_phrase and not symptom_hits and not context_hits:
                    continue

            if score:
                results.append((score, row, ", ".join(matched)))
        results.sort(key=lambda item: (-item[0], item[1]["scientific_name"].lower()))
        return results[:100]

    def get(self, disease_id):
        return self.conn.execute("SELECT * FROM diseases WHERE id = ? AND COALESCE(deleted_at, '')=''", (disease_id,)).fetchone()

    def add(self, data):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [f for f in ALL_DB_FIELDS if f not in ("id", "created_at", "updated_at")]
        values = [data.get(f, 0 if f == "favorite" else "") for f in fields]
        sql = "INSERT INTO diseases ({}, created_at, updated_at) VALUES ({}, ?, ?)".format(
            ", ".join(fields), ", ".join(["?"] * len(fields))
        )
        cur = self.conn.execute(sql, values + [now, now])
        self.conn.commit()
        return cur.lastrowid

    def update(self, disease_id, data):
        current = self.get(disease_id)
        if current:
            before = dict(current)
            changed = [f for f in ALL_DB_FIELDS if f in before and str(before.get(f, "")) != str(data.get(f, before.get(f, "")))]
            self._save_history(disease_id, before, self.rich_text(disease_id), changed)
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [f for f in ALL_DB_FIELDS if f not in ("id", "created_at", "updated_at")]
        assignments = ", ".join([f + " = ?" for f in fields])
        values = [data.get(f, 0 if f == "favorite" else "") for f in fields]
        self.conn.execute(
            "UPDATE diseases SET {}, updated_at = ? WHERE id = ?".format(assignments),
            values + [now, disease_id],
        )
        self.conn.commit()

    def _save_history(self, disease_id, snapshot, rich_data=None, changed_fields=None):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT INTO disease_history(disease_id,snapshot_json,rich_json,changed_fields,created_at) VALUES(?,?,?,?,?)",
            (disease_id, json.dumps(snapshot, ensure_ascii=False), json.dumps(rich_data or {}, ensure_ascii=False), ", ".join(changed_fields or []), now))
        self.conn.commit()

    def history(self, disease_id):
        return self.conn.execute("SELECT * FROM disease_history WHERE disease_id=? ORDER BY id DESC", (disease_id,)).fetchall()

    def restore_history(self, history_id):
        row = self.conn.execute("SELECT * FROM disease_history WHERE id=?", (history_id,)).fetchone()
        if not row: return False
        data = json.loads(row["snapshot_json"]); disease_id = row["disease_id"]
        current = self.get(disease_id)
        if current: self._save_history(disease_id, dict(current), self.rich_text(disease_id), ["geri yükleme öncesi"])
        fields=[f for f in ALL_DB_FIELDS if f not in ("id","created_at","updated_at")]
        vals=[data.get(f, 0 if f=="favorite" else "") for f in fields]
        self.conn.execute("UPDATE diseases SET "+", ".join(f+"=?" for f in fields)+", updated_at=? WHERE id=?", vals+[dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),disease_id])
        self.save_rich_text(disease_id, json.loads(row["rich_json"] or "{}")); self.conn.commit(); return True

    def delete(self, disease_id):
        self.conn.execute("UPDATE diseases SET deleted_at=?, updated_at=? WHERE id=?", (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), disease_id))
        self.conn.commit()

    def trash(self):
        return self.conn.execute("SELECT * FROM diseases WHERE COALESCE(deleted_at,'')<>'' ORDER BY deleted_at DESC").fetchall()

    def restore_from_trash(self, disease_id):
        self.conn.execute("UPDATE diseases SET deleted_at='', updated_at=? WHERE id=?", (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), disease_id)); self.conn.commit()

    def permanent_delete(self, disease_id):
        self.conn.execute("DELETE FROM diseases WHERE id=?", (disease_id,)); self.conn.commit()

    def save_draft(self, draft_key, disease_id, data, rich_data):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT OR REPLACE INTO disease_drafts(draft_key,disease_id,data_json,rich_json,updated_at) VALUES(?,?,?,?,?)", (draft_key,disease_id,json.dumps(data,ensure_ascii=False),json.dumps(rich_data or {},ensure_ascii=False),now)); self.conn.commit()

    def get_draft(self, draft_key):
        row=self.conn.execute("SELECT * FROM disease_drafts WHERE draft_key=?",(draft_key,)).fetchone()
        if not row:return None
        return {"data":json.loads(row["data_json"]),"rich":json.loads(row["rich_json"] or "{}"),"updated_at":row["updated_at"]}

    def delete_draft(self, draft_key):
        self.conn.execute("DELETE FROM disease_drafts WHERE draft_key=?",(draft_key,)); self.conn.commit()

    def tags(self, disease_id):
        return [r[0] for r in self.conn.execute("SELECT tag FROM disease_tags WHERE disease_id=? ORDER BY tag COLLATE NOCASE",(disease_id,)).fetchall()]

    def save_tags(self, disease_id, tags):
        self.conn.execute("DELETE FROM disease_tags WHERE disease_id=?",(disease_id,))
        for tag in sorted(set(t.strip() for t in tags if t.strip()), key=str.lower): self.conn.execute("INSERT INTO disease_tags(disease_id,tag) VALUES(?,?)",(disease_id,tag))
        self.conn.commit()

    def add_tags_bulk(self, disease_ids, tags):
        for disease_id in disease_ids:
            current=self.tags(disease_id); self.save_tags(disease_id,current+list(tags))

    def attachments(self, disease_id):
        return self.conn.execute(
            "SELECT * FROM attachments WHERE disease_id = ? ORDER BY created_at DESC, id DESC",
            (disease_id,),
        ).fetchall()

    def add_attachment(self, disease_id, file_type, relative_path, description="", title="", captured_at="", source=""):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        next_order = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM attachments WHERE disease_id = ? AND file_type = ?",
            (disease_id, file_type),
        ).fetchone()[0]
        cur = self.conn.execute(
            """INSERT INTO attachments
               (disease_id, file_type, relative_path, description, title, captured_at, source, sort_order, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (disease_id, file_type, relative_path, description, title, captured_at, source, next_order, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_attachment(self, attachment_id):
        return self.conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()

    def delete_attachment(self, attachment_id):
        self.conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        self.conn.commit()

    def export_csv(self, output_path):
        rows = self.conn.execute("SELECT * FROM diseases ORDER BY id").fetchall()
        with open(output_path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ALL_DB_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

    def rich_text(self, disease_id):
        rows = self.conn.execute(
            "SELECT field_name, formatting_json FROM disease_rich_text WHERE disease_id = ?",
            (disease_id,),
        ).fetchall()
        result = {}
        for row in rows:
            try:
                result[row["field_name"]] = json.loads(row["formatting_json"] or "{}")
            except Exception:
                result[row["field_name"]] = {}
        return result

    def save_rich_text(self, disease_id, rich_data):
        self.conn.execute("DELETE FROM disease_rich_text WHERE disease_id = ?", (disease_id,))
        for field_name, formatting in (rich_data or {}).items():
            if formatting:
                self.conn.execute(
                    """INSERT INTO disease_rich_text (disease_id, field_name, formatting_json)
                       VALUES (?, ?, ?)""",
                    (disease_id, field_name, json.dumps(formatting, ensure_ascii=False)),
                )
        self.conn.commit()

    def export_excel(self, output_path):
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("Excel dışa aktarımı için openpyxl bileşeni bulunamadı.")
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Hastalıklar"
        labels = {
            "id": "ID", "group_name": "Etmen grubu", "scientific_name": "Bilimsel ad",
            "synonyms": "Sinonimler", "disease_name": "Hastalık adı",
            "hosts": "Konukçular", "affected_organs": "Etkilenen organlar",
            "symptoms": "Belirtiler", "pathogen_features": "Etmenin özellikleri",
            "disease_cycle": "Hastalık döngüsü", "epidemiology": "Epidemiyoloji",
            "differential_diagnosis": "Ayırıcı teşhis",
            "cultural_control": "Kültürel mücadele",
            "biological_control": "Biyolojik mücadele",
            "chemical_control": "Kimyasal mücadele",
            "distribution_turkey": "Türkiye dağılımı",
            "distribution_world": "Dünya dağılımı",
            "climate_notes": "İklim / çevre notları",
            "sources": "Kaynaklar", "notes": "Notlar", "favorite": "Favori",
            "created_at": "Oluşturulma", "updated_at": "Güncellenme",
        }
        sheet.append([labels.get(field, field) for field in ALL_DB_FIELDS])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
        rows = self.conn.execute("SELECT * FROM diseases ORDER BY scientific_name").fetchall()
        for row in rows:
            sheet.append([row[field] for field in ALL_DB_FIELDS])
        for column in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(max_len + 2, 12), 45)
            for cell in column:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.freeze_panes = "A2"
        workbook.save(output_path)

    def duplicate_candidates(self):
        rows = self.conn.execute(
            "SELECT id, scientific_name, disease_name FROM diseases ORDER BY scientific_name"
        ).fetchall()
        groups = {}
        for row in rows:
            sci = re.sub(r"[^a-z0-9çğıöşü]+", "", (row["scientific_name"] or "").lower())
            dis = re.sub(r"[^a-z0-9çğıöşü]+", "", (row["disease_name"] or "").lower())
            for kind, key in (("Bilimsel ad", sci), ("Hastalık adı", dis)):
                if key:
                    groups.setdefault((kind, key), []).append(row)
        return [(kind, values) for (kind, _key), values in groups.items() if len(values) > 1]

    def toggle_favorite(self, disease_id):
        row = self.get(disease_id)
        if not row:
            return False
        new_value = 0 if row["favorite"] else 1
        self.conn.execute("UPDATE diseases SET favorite = ? WHERE id = ?", (new_value, disease_id))
        self.conn.commit()
        return bool(new_value)

    def references(self, disease_id):
        return self.conn.execute(
            "SELECT * FROM disease_references WHERE disease_id = ? ORDER BY created_at DESC, id DESC",
            (disease_id,),
        ).fetchall()

    def add_reference(self, disease_id, source_type, citation, identifier=""):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.execute(
            """INSERT INTO disease_references
               (disease_id, source_type, citation, identifier, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (disease_id, source_type, citation, identifier, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_reference(self, reference_id):
        self.conn.execute("DELETE FROM disease_references WHERE id = ?", (reference_id,))
        self.conn.commit()

    def statistics(self):
        group_rows = self.conn.execute(
            """SELECT CASE WHEN group_name = '' THEN '(Grupsuz)' ELSE group_name END AS label,
                      COUNT(*) AS total
               FROM diseases GROUP BY group_name ORDER BY total DESC, label"""
        ).fetchall()
        return {
            "total": self.count(),
            "favorites": self.conn.execute("SELECT COUNT(*) FROM diseases WHERE favorite = 1").fetchone()[0],
            "photos": self.conn.execute("SELECT COUNT(*) FROM attachments WHERE file_type = 'image'").fetchone()[0],
            "documents": self.conn.execute("SELECT COUNT(*) FROM attachments WHERE file_type <> 'image'").fetchone()[0],
            "references": self.conn.execute("SELECT COUNT(*) FROM disease_references").fetchone()[0],
            "groups": group_rows,
        }

    def image_attachments(self, disease_id):
        return self.conn.execute(
            """SELECT * FROM attachments
               WHERE disease_id = ? AND file_type = 'image'
               ORDER BY is_primary DESC, sort_order, created_at, id""",
            (disease_id,),
        ).fetchall()

    def set_primary_attachment(self, disease_id, attachment_id):
        self.conn.execute(
            "UPDATE attachments SET is_primary = 0 WHERE disease_id = ? AND file_type = 'image'",
            (disease_id,),
        )
        self.conn.execute(
            "UPDATE attachments SET is_primary = 1 WHERE id = ? AND disease_id = ? AND file_type = 'image'",
            (attachment_id, disease_id),
        )
        self.conn.commit()

    def update_attachment_description(self, attachment_id, description):
        self.conn.execute(
            "UPDATE attachments SET description = ? WHERE id = ?",
            ((description or "").strip(), attachment_id),
        )
        self.conn.commit()



    def update_attachment_metadata(self, attachment_id, title, description, captured_at, source):
        self.conn.execute(
            """UPDATE attachments
               SET title = ?, description = ?, captured_at = ?, source = ?
               WHERE id = ?""",
            ((title or "").strip(), (description or "").strip(),
             (captured_at or "").strip(), (source or "").strip(), attachment_id),
        )
        self.conn.commit()

    def set_attachment_order(self, attachment_ids):
        for index, attachment_id in enumerate(attachment_ids, 1):
            self.conn.execute(
                "UPDATE attachments SET sort_order = ? WHERE id = ?",
                (index, attachment_id),
            )
        self.conn.commit()

    def attachment_annotations(self, attachment_id):
        row = self.conn.execute(
            "SELECT annotations_json FROM attachment_annotations WHERE attachment_id = ?",
            (attachment_id,),
        ).fetchone()
        if not row:
            return []
        try:
            value = json.loads(row["annotations_json"] or "[]")
            return value if isinstance(value, list) else []
        except Exception:
            return []

    def save_attachment_annotations(self, attachment_id, annotations):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = json.dumps(annotations or [], ensure_ascii=False, separators=(",", ":"))
        self.conn.execute(
            """INSERT OR REPLACE INTO attachment_annotations
               (attachment_id, annotations_json, updated_at) VALUES (?, ?, ?)""",
            (attachment_id, payload, now),
        )
        self.conn.commit()

    def dashboard_stats(self):
        row = self.conn.execute("""
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN favorite=1 THEN 1 ELSE 0 END) AS favorites,
              SUM(CASE WHEN TRIM(scientific_name)='' THEN 1 ELSE 0 END) AS no_pathogen,
              SUM(CASE WHEN TRIM(symptoms)='' THEN 1 ELSE 0 END) AS no_symptoms,
              SUM(CASE WHEN TRIM(sources)='' THEN 1 ELSE 0 END) AS no_sources,
              SUM(CASE WHEN
                TRIM(scientific_name)<>'' AND TRIM(disease_name)<>'' AND TRIM(hosts)<>'' AND
                TRIM(affected_organs)<>'' AND TRIM(symptoms)<>'' AND TRIM(pathogen_features)<>'' AND
                TRIM(disease_cycle)<>'' AND TRIM(epidemiology)<>'' AND TRIM(differential_diagnosis)<>'' AND
                TRIM(cultural_control)<>'' AND TRIM(biological_control)<>'' AND TRIM(chemical_control)<>'' AND
                TRIM(sources)<>'' THEN 1 ELSE 0 END) AS complete
            FROM diseases WHERE COALESCE(deleted_at,'')=''
        """).fetchone()
        no_photo = self.conn.execute("""
            SELECT COUNT(*) FROM diseases d
            WHERE COALESCE(d.deleted_at,'')='' AND NOT EXISTS (SELECT 1 FROM attachments a WHERE a.disease_id=d.id AND a.file_type='image')
        """).fetchone()[0]
        total = int(row["total"] or 0)
        complete = int(row["complete"] or 0)
        return {"total": total, "favorites": int(row["favorites"] or 0),
                "no_pathogen": int(row["no_pathogen"] or 0), "no_symptoms": int(row["no_symptoms"] or 0),
                "no_sources": int(row["no_sources"] or 0), "no_photo": int(no_photo or 0),
                "complete": complete, "incomplete": max(0, total-complete)}

    def _dashboard_base_sql(self):
        return """SELECT d.*, (SELECT COUNT(*) FROM attachments a
                  WHERE a.disease_id=d.id AND a.file_type='image') AS photo_count
                  FROM diseases d WHERE COALESCE(d.deleted_at,'')=''"""

    def dashboard_records(self, mode="recent", limit=100):
        where = ""
        if mode == "no_photo":
            where = " AND COALESCE(d.deleted_at,'')='' AND NOT EXISTS (SELECT 1 FROM attachments a WHERE a.disease_id=d.id AND a.file_type='image')"
        elif mode == "no_sources": where = " AND TRIM(d.sources)=''"
        elif mode == "no_pathogen": where = " AND TRIM(d.scientific_name)=''"
        elif mode == "no_symptoms": where = " AND TRIM(d.symptoms)=''"
        elif mode == "favorites": where = " AND d.favorite=1"
        complete_condition = """TRIM(d.scientific_name)<>'' AND TRIM(d.disease_name)<>'' AND TRIM(d.hosts)<>'' AND
            TRIM(d.affected_organs)<>'' AND TRIM(d.symptoms)<>'' AND TRIM(d.pathogen_features)<>'' AND
            TRIM(d.disease_cycle)<>'' AND TRIM(d.epidemiology)<>'' AND TRIM(d.differential_diagnosis)<>'' AND
            TRIM(d.cultural_control)<>'' AND TRIM(d.biological_control)<>'' AND TRIM(d.chemical_control)<>'' AND TRIM(d.sources)<>''"""
        if mode == "complete": where = " AND " + complete_condition
        elif mode == "incomplete": where = " AND NOT (" + complete_condition + ")"
        order = " ORDER BY d.updated_at DESC, d.scientific_name COLLATE NOCASE"
        return self.conn.execute(self._dashboard_base_sql()+where+order+" LIMIT ?", (int(limit),)).fetchall()

    def super_search(self, query, limit=100):
        query = (query or "").strip()
        if not query: return self.dashboard_records("recent", limit)
        like = "%" + query + "%"
        fields = ["d.group_name","d.scientific_name","d.synonyms","d.disease_name","d.hosts",
                  "d.affected_organs","d.symptoms","d.pathogen_features","d.disease_cycle","d.epidemiology",
                  "d.differential_diagnosis","d.cultural_control","d.biological_control","d.chemical_control",
                  "d.distribution_turkey","d.distribution_world","d.climate_notes","d.sources","d.notes"]
        clause = " OR ".join(field+" LIKE ?" for field in fields)
        clause += " OR EXISTS (SELECT 1 FROM attachments ax WHERE ax.disease_id=d.id AND (ax.title LIKE ? OR ax.description LIKE ? OR ax.source LIKE ? OR ax.relative_path LIKE ?))"
        params = [like]*len(fields) + [like]*4 + [int(limit)]
        sql = self._dashboard_base_sql()+" AND ("+clause+") ORDER BY d.updated_at DESC LIMIT ?"
        return self.conn.execute(sql, params).fetchall()

    def workspace_note(self):
        row = self.conn.execute("SELECT note_text FROM workspace_notes WHERE id=1").fetchone()
        return row[0] if row else ""

    def save_workspace_note(self, text):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT OR REPLACE INTO workspace_notes(id,note_text,updated_at) VALUES(1,?,?)", (text or "", now))
        self.conn.commit()

    def tasks(self):
        return self.conn.execute("""SELECT t.*, d.disease_name FROM disease_tasks t
            LEFT JOIN diseases d ON d.id=t.disease_id ORDER BY t.is_done ASC, t.updated_at DESC""").fetchall()

    def add_task(self, disease_id, task_text):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT INTO disease_tasks(disease_id,task_text,is_done,created_at,updated_at) VALUES(?,?,0,?,?)",
                          (disease_id, task_text, now, now)); self.conn.commit()

    def toggle_task(self, task_id):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("UPDATE disease_tasks SET is_done=CASE is_done WHEN 0 THEN 1 ELSE 0 END, updated_at=? WHERE id=?", (now, task_id)); self.conn.commit()

    def delete_task(self, task_id):
        self.conn.execute("DELETE FROM disease_tasks WHERE id=?", (task_id,)); self.conn.commit()

    def monograph_projects(self):
        return self.conn.execute("SELECT * FROM monograph_projects ORDER BY updated_at DESC").fetchall()

    def save_monograph_project(self, name, config):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT OR REPLACE INTO monograph_projects (id,name,config_json,created_at,updated_at) VALUES ((SELECT id FROM monograph_projects WHERE name=?),?,?,COALESCE((SELECT created_at FROM monograph_projects WHERE name=?),?),?)", (name,name,json.dumps(config,ensure_ascii=False),name,now,now))
        self.conn.commit()

    def delete_monograph_project(self, project_id):
        self.conn.execute("DELETE FROM monograph_projects WHERE id=?", (project_id,)); self.conn.commit()

    def save_monograph_export(self, title, output_path, disease_count):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT INTO monograph_exports (title,output_path,disease_count,created_at) VALUES (?,?,?,?)", (title,output_path,int(disease_count),now)); self.conn.commit()

    def backup_to(self, destination_db):
        target = sqlite3.connect(destination_db)
        try:
            self.conn.backup(target)
        finally:
            target.close()



