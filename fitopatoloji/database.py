# -*- coding: utf-8 -*-
from .common import *

class Database(object):
    SCHEMA_VERSION = 20012

    def __init__(self, db_path, seed_csv=None):
        self.db_path = db_path
        self.seed_csv = seed_csv
        self._create_pre_migration_backup()
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.create_schema()
        self.seed_if_empty()


    def _create_pre_migration_backup(self):
        """Mevcut bir veritabanını RC2 şema yükseltmesinden önce bir kez yedekler."""
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0:
            return
        try:
            probe = sqlite3.connect(self.db_path)
            current = int(probe.execute("PRAGMA user_version").fetchone()[0] or 0)
            probe.close()
            if current >= self.SCHEMA_VERSION:
                return
            backup_dir = os.path.abspath(os.path.join(os.path.dirname(self.db_path), os.pardir, "Backups"))
            if not os.path.isdir(backup_dir):
                os.makedirs(backup_dir)
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            target = os.path.join(backup_dir, "PreMigration_RC2_{}.db".format(stamp))
            shutil.copy2(self.db_path, target)
        except Exception:
            # Yedekleme denemesi uygulamanın açılmasını engellememelidir.
            pass

    def schema_version(self):
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0] or 0)

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
            CREATE INDEX IF NOT EXISTS idx_diseases_name ON diseases(disease_name);
            CREATE INDEX IF NOT EXISTS idx_diseases_updated ON diseases(updated_at DESC);
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

            CREATE TABLE IF NOT EXISTS taxonomy_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rank TEXT NOT NULL, name TEXT NOT NULL, parent_name TEXT NOT NULL DEFAULT '',
                synonyms TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                agent_group TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', accessed_at TEXT NOT NULL DEFAULT '',
                UNIQUE(rank, name)
            );
            CREATE INDEX IF NOT EXISTS idx_taxonomy_rank_name ON taxonomy_catalog(rank, name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS host_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                taxon_level TEXT NOT NULL DEFAULT 'Tür',
                common_name TEXT NOT NULL DEFAULT '', scientific_name TEXT NOT NULL DEFAULT '',
                family_name TEXT NOT NULL DEFAULT '', genus_name TEXT NOT NULL DEFAULT '',
                species_name TEXT NOT NULL DEFAULT '', subspecies_name TEXT NOT NULL DEFAULT '',
                variety_name TEXT NOT NULL DEFAULT '', cultivar_name TEXT NOT NULL DEFAULT '', host_group TEXT NOT NULL DEFAULT '',
                alternative_names TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_host_scientific_unique ON host_catalog(scientific_name COLLATE NOCASE) WHERE TRIM(scientific_name)<>'';
            CREATE INDEX IF NOT EXISTS idx_host_common ON host_catalog(common_name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_host_family ON host_catalog(family_name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS disease_hosts (
                disease_id INTEGER NOT NULL, host_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'Doğal konukçu',
                scope_type TEXT NOT NULL DEFAULT 'Doğrudan',
                relation_note TEXT NOT NULL DEFAULT '', is_excluded INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(disease_id, host_id, relation_type, is_excluded),
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE,
                FOREIGN KEY(host_id) REFERENCES host_catalog(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_disease_hosts_host ON disease_hosts(host_id, disease_id);

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

            CREATE TABLE IF NOT EXISTS literature_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publication_type TEXT NOT NULL DEFAULT 'Makale',
                authors TEXT NOT NULL DEFAULT '', year_text TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '', journal TEXT NOT NULL DEFAULT '',
                volume TEXT NOT NULL DEFAULT '', issue TEXT NOT NULL DEFAULT '', pages TEXT NOT NULL DEFAULT '',
                doi TEXT NOT NULL DEFAULT '', isbn TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '',
                language_name TEXT NOT NULL DEFAULT '', keywords TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_literature_title ON literature_catalog(title COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_literature_authors ON literature_catalog(authors COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_literature_doi ON literature_catalog(doi COLLATE NOCASE);
            CREATE TABLE IF NOT EXISTS disease_literature (
                disease_id INTEGER NOT NULL, literature_id INTEGER NOT NULL,
                relation_note TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(disease_id, literature_id),
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE,
                FOREIGN KEY(literature_id) REFERENCES literature_catalog(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_disease_literature_lit ON disease_literature(literature_id, disease_id);
            CREATE TABLE IF NOT EXISTS disease_private_notes (
                disease_id INTEGER PRIMARY KEY, note_text TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS disease_synonyms (
                id INTEGER PRIMARY KEY AUTOINCREMENT, disease_id INTEGER NOT NULL,
                synonym_name TEXT NOT NULL, synonym_type TEXT NOT NULL DEFAULT 'Bilimsel eş ad',
                is_preferred INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE,
                UNIQUE(disease_id, synonym_name COLLATE NOCASE)
            );
            CREATE INDEX IF NOT EXISTS idx_disease_synonyms_name ON disease_synonyms(synonym_name COLLATE NOCASE);

            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disease_id INTEGER,
                question_type TEXT NOT NULL DEFAULT 'Çoktan seçmeli',
                question_text TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT 'Orta',
                topic_tag TEXT NOT NULL DEFAULT '',
                option_a TEXT NOT NULL DEFAULT '', option_b TEXT NOT NULL DEFAULT '',
                option_c TEXT NOT NULL DEFAULT '', option_d TEXT NOT NULL DEFAULT '', option_e TEXT NOT NULL DEFAULT '',
                question_format_json TEXT NOT NULL DEFAULT '{}',
                option_a_format_json TEXT NOT NULL DEFAULT '{}', option_b_format_json TEXT NOT NULL DEFAULT '{}',
                option_c_format_json TEXT NOT NULL DEFAULT '{}', option_d_format_json TEXT NOT NULL DEFAULT '{}',
                option_e_format_json TEXT NOT NULL DEFAULT '{}', explanation_format_json TEXT NOT NULL DEFAULT '{}', correct_answer_format_json TEXT NOT NULL DEFAULT '{}',
                correct_answer TEXT NOT NULL DEFAULT '', explanation TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL DEFAULT '', is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_quiz_questions_disease ON quiz_questions(disease_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_quiz_questions_topic ON quiz_questions(topic_tag COLLATE NOCASE);
            CREATE TABLE IF NOT EXISTS quiz_question_diseases (
                question_id INTEGER NOT NULL, disease_id INTEGER NOT NULL,
                PRIMARY KEY(question_id, disease_id),
                FOREIGN KEY(question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
                FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_quiz_qd_disease ON quiz_question_diseases(disease_id, question_id);
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT NOT NULL,
                started_at TEXT NOT NULL, total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL, wrong_count INTEGER NOT NULL, blank_count INTEGER NOT NULL,
                score REAL NOT NULL, duration_seconds INTEGER NOT NULL DEFAULT 0,
                details_json TEXT NOT NULL DEFAULT '[]'
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
            ("agent_group", "TEXT NOT NULL DEFAULT ''"),
            ("domain_name", "TEXT NOT NULL DEFAULT ''"),
            ("kingdom_name", "TEXT NOT NULL DEFAULT ''"),
            ("phylum_name", "TEXT NOT NULL DEFAULT ''"),
            ("subphylum_name", "TEXT NOT NULL DEFAULT ''"),
            ("class_name", "TEXT NOT NULL DEFAULT ''"),
            ("order_name", "TEXT NOT NULL DEFAULT ''"),
            ("family_name", "TEXT NOT NULL DEFAULT ''"),
            ("genus_name", "TEXT NOT NULL DEFAULT ''"),
            ("species_name", "TEXT NOT NULL DEFAULT ''"),
            ("subspecies_name", "TEXT NOT NULL DEFAULT ''"),
            ("pathovar", "TEXT NOT NULL DEFAULT ''"),
            ("forma_specialis", "TEXT NOT NULL DEFAULT ''"),
            ("strain_name", "TEXT NOT NULL DEFAULT ''"),
            ("isolate_name", "TEXT NOT NULL DEFAULT ''"),
            ("taxonomy_source", "TEXT NOT NULL DEFAULT ''"),
            ("taxonomy_accessed_at", "TEXT NOT NULL DEFAULT ''"),
            ("taxonomy_notes", "TEXT NOT NULL DEFAULT ''"),
        ]:
            if column_name not in disease_columns:
                self.conn.execute("ALTER TABLE diseases ADD COLUMN {} {}".format(column_name, definition))

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_diseases_deleted ON diseases(deleted_at)")

        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(attachments)").fetchall()]
        for column_name, definition in [
            ("is_primary", "INTEGER NOT NULL DEFAULT 0"),
            ("title", "TEXT NOT NULL DEFAULT ''"),
            ("captured_at", "TEXT NOT NULL DEFAULT ''"),
            ("source", "TEXT NOT NULL DEFAULT ''"),
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
            ("image_category", "TEXT NOT NULL DEFAULT 'Genel'"),
            ("photographer", "TEXT NOT NULL DEFAULT ''"),
            ("copyright_owner", "TEXT NOT NULL DEFAULT ''"),
            ("license_text", "TEXT NOT NULL DEFAULT ''"),
            ("scale_info", "TEXT NOT NULL DEFAULT ''"),
            ("location_text", "TEXT NOT NULL DEFAULT ''"),
        ]:
            if column_name not in columns:
                self.conn.execute("ALTER TABLE attachments ADD COLUMN {} {}".format(column_name, definition))
        self.conn.execute("UPDATE attachments SET sort_order = id WHERE sort_order = 0")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_type ON attachments(file_type, disease_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_diseases_agent_group ON diseases(agent_group COLLATE NOCASE)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_diseases_taxonomy_order ON diseases(order_name COLLATE NOCASE)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_active_disease ON quiz_questions(is_active, disease_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_literature_year ON literature_catalog(year_text COLLATE NOCASE)")

        taxonomy_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(taxonomy_catalog)").fetchall()]
        for column_name in ("agent_group", "source", "accessed_at"):
            if column_name not in taxonomy_columns:
                self.conn.execute("ALTER TABLE taxonomy_catalog ADD COLUMN {} TEXT NOT NULL DEFAULT ''".format(column_name))
        host_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(host_catalog)").fetchall()]
        for column_name in ("subspecies_name", "variety_name", "cultivar_name", "host_group"):
            if column_name not in host_columns:
                self.conn.execute("ALTER TABLE host_catalog ADD COLUMN {} TEXT NOT NULL DEFAULT ''".format(column_name))
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_host_genus ON host_catalog(genus_name COLLATE NOCASE)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_host_group ON host_catalog(host_group COLLATE NOCASE)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_taxonomy_agent ON taxonomy_catalog(agent_group COLLATE NOCASE)")
        # RC10.2 — sınav modülü genişletmeleri
        quiz_columns = [row[1] for row in self.conn.execute("PRAGMA table_info(quiz_questions)").fetchall()]
        for column_name, definition in [
            ("option_e", "TEXT NOT NULL DEFAULT ''"),
            ("question_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("option_a_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("option_b_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("option_c_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("option_d_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("option_e_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("explanation_format_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("correct_answer_format_json", "TEXT NOT NULL DEFAULT '{}'")
        ]:
            if column_name not in quiz_columns:
                self.conn.execute("ALTER TABLE quiz_questions ADD COLUMN {} {}".format(column_name, definition))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS quiz_question_diseases (
            question_id INTEGER NOT NULL, disease_id INTEGER NOT NULL,
            PRIMARY KEY(question_id, disease_id),
            FOREIGN KEY(question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE,
            FOREIGN KEY(disease_id) REFERENCES diseases(id) ON DELETE CASCADE)""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_quiz_qd_disease ON quiz_question_diseases(disease_id, question_id)")
        self.conn.execute("""INSERT OR IGNORE INTO quiz_question_diseases(question_id,disease_id)
            SELECT id,disease_id FROM quiz_questions WHERE disease_id IS NOT NULL""")
        self.conn.execute("PRAGMA user_version = {}".format(self.SCHEMA_VERSION))
        self.conn.commit()
        # Eski serbest metin sinonimlerini normalize edilmiş kataloğa taşı.
        for row in self.conn.execute("SELECT id, synonyms FROM diseases WHERE TRIM(COALESCE(synonyms,''))<>''").fetchall():
            self.sync_disease_synonyms(int(row["id"]), row["synonyms"] or "")

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
            clauses.append("((" + " OR ".join([field + " LIKE ?" for field in searchable]) + ") OR EXISTS (SELECT 1 FROM disease_synonyms ds WHERE ds.disease_id=diseases.id AND ds.synonym_name LIKE ?))")
            params.extend([like] * (len(searchable)+1))
        if host:
            clauses.append("EXISTS (SELECT 1 FROM disease_hosts dh JOIN host_catalog hc ON hc.id=dh.host_id WHERE dh.disease_id=diseases.id AND dh.is_excluded=0 AND (hc.common_name LIKE ? OR hc.scientific_name LIKE ? OR hc.family_name LIKE ? OR hc.genus_name LIKE ? OR hc.alternative_names LIKE ?))")
            params.extend(["%" + host + "%"] * 5)
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

    def taxonomy_list(self, rank="", agent_group="", query=""):
        clauses=[]; params=[]
        if rank:
            clauses.append("rank=?"); params.append(rank)
        if agent_group:
            clauses.append("agent_group=?"); params.append(agent_group)
        if query:
            like="%"+query.strip()+"%"
            clauses.append("(name LIKE ? OR parent_name LIKE ? OR synonyms LIKE ? OR notes LIKE ?)")
            params.extend([like]*4)
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        return self.conn.execute("SELECT * FROM taxonomy_catalog"+where+" ORDER BY rank COLLATE NOCASE, name COLLATE NOCASE",params).fetchall()

    def taxonomy_get(self, taxon_id):
        return self.conn.execute("SELECT * FROM taxonomy_catalog WHERE id=?", (taxon_id,)).fetchone()

    def taxonomy_save(self, taxon_id, rank, name, parent_name="", synonyms="", notes="", agent_group="", source="", accessed_at=""):
        values=(rank.strip(),name.strip(),parent_name.strip(),synonyms.strip(),notes.strip(),agent_group.strip(),source.strip(),accessed_at.strip())
        if taxon_id:
            self.conn.execute("UPDATE taxonomy_catalog SET rank=?, name=?, parent_name=?, synonyms=?, notes=?, agent_group=?, source=?, accessed_at=? WHERE id=?", values+(taxon_id,))
        else:
            self.conn.execute("INSERT INTO taxonomy_catalog(rank,name,parent_name,synonyms,notes,agent_group,source,accessed_at) VALUES(?,?,?,?,?,?,?,?)", values)
        self.conn.commit()

    def taxonomy_delete(self, taxon_id):
        self.conn.execute("DELETE FROM taxonomy_catalog WHERE id=?", (taxon_id,)); self.conn.commit()

    def host_list(self, query=""):
        q=(query or "").strip()
        if q:
            like="%"+q+"%"
            return self.conn.execute("SELECT * FROM host_catalog WHERE common_name LIKE ? OR scientific_name LIKE ? OR family_name LIKE ? OR genus_name LIKE ? OR alternative_names LIKE ? OR host_group LIKE ? ORDER BY scientific_name COLLATE NOCASE, common_name COLLATE NOCASE", (like,like,like,like,like,like)).fetchall()
        return self.conn.execute("SELECT * FROM host_catalog ORDER BY scientific_name COLLATE NOCASE, common_name COLLATE NOCASE").fetchall()

    def host_get(self, host_id):
        return self.conn.execute("SELECT * FROM host_catalog WHERE id=?", (host_id,)).fetchone()

    def host_save(self, host_id, data):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields=("taxon_level","common_name","scientific_name","family_name","genus_name","species_name","subspecies_name","variety_name","cultivar_name","host_group","alternative_names","notes")
        vals=[data.get(k,"") for k in fields]
        if host_id:
            self.conn.execute("UPDATE host_catalog SET "+", ".join(k+"=?" for k in fields)+", updated_at=? WHERE id=?", vals+[now,host_id])
        else:
            self.conn.execute("INSERT INTO host_catalog("+", ".join(fields)+",created_at,updated_at) VALUES("+", ".join(["?"]*(len(fields)+2))+")", vals+[now,now])
        self.conn.commit()

    def host_delete(self, host_id):
        self.conn.execute("DELETE FROM host_catalog WHERE id=?", (host_id,)); self.conn.commit()

    def disease_host_add(self, disease_id, host_id, relation_type="Doğal konukçu", scope_type="Doğrudan", note="", excluded=0):
        self.conn.execute("INSERT OR REPLACE INTO disease_hosts(disease_id,host_id,relation_type,scope_type,relation_note,is_excluded) VALUES(?,?,?,?,?,?)", (disease_id,host_id,relation_type,scope_type,note,int(bool(excluded))))
        self.conn.commit()

    def disease_host_remove(self, disease_id, host_id):
        self.conn.execute("DELETE FROM disease_hosts WHERE disease_id=? AND host_id=?", (disease_id,host_id)); self.conn.commit()

    def replace_disease_hosts(self, disease_id, relations):
        self.conn.execute("DELETE FROM disease_hosts WHERE disease_id=?", (disease_id,))
        for relation in relations or []:
            self.conn.execute("INSERT OR REPLACE INTO disease_hosts(disease_id,host_id,relation_type,scope_type,relation_note,is_excluded) VALUES(?,?,?,?,?,?)",
                (disease_id, int(relation.get("host_id")), relation.get("relation_type", "Doğal konukçu"),
                 relation.get("scope_type", "Doğrudan"), relation.get("relation_note", ""), int(bool(relation.get("is_excluded", 0)))))
        self.conn.commit()

    def disease_hosts(self, disease_id):
        return self.conn.execute("SELECT hc.*, dh.relation_type, dh.scope_type, dh.relation_note, dh.is_excluded FROM disease_hosts dh JOIN host_catalog hc ON hc.id=dh.host_id WHERE dh.disease_id=? ORDER BY dh.is_excluded, hc.scientific_name COLLATE NOCASE, hc.common_name COLLATE NOCASE", (disease_id,)).fetchall()

    def disease_hosts_text(self, disease_id):
        rows=self.disease_hosts(disease_id)
        included=[]; excluded=[]
        for r in rows:
            name=r["common_name"] or r["scientific_name"]
            item="{} ({})".format(name,r["scientific_name"]) if r["common_name"] and r["scientific_name"] else name
            (excluded if r["is_excluded"] else included).append(item)
        text=", ".join(included)
        if excluded: text += ("; " if text else "") + "Hariç: " + ", ".join(excluded)
        return text

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
        disease_id = cur.lastrowid
        self.sync_disease_synonyms(disease_id, data.get("synonyms", ""))
        return disease_id

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
        self.sync_disease_synonyms(disease_id, data.get("synonyms", ""))

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

    def literature_list(self, query=""):
        query=(query or "").strip()
        if not query:
            return self.conn.execute("SELECT * FROM literature_catalog ORDER BY year_text DESC, authors COLLATE NOCASE, title COLLATE NOCASE").fetchall()
        like="%"+query+"%"
        return self.conn.execute("""SELECT * FROM literature_catalog WHERE authors LIKE ? OR title LIKE ? OR journal LIKE ? OR doi LIKE ? OR isbn LIKE ? OR keywords LIKE ? ORDER BY year_text DESC, authors COLLATE NOCASE""", (like,like,like,like,like,like)).fetchall()

    def literature_get(self, literature_id):
        return self.conn.execute("SELECT * FROM literature_catalog WHERE id=?", (literature_id,)).fetchone()

    def literature_save(self, literature_id=None, **data):
        fields=("publication_type","authors","year_text","title","journal","volume","issue","pages","doi","isbn","url","language_name","keywords","notes")
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values=[(data.get(f) or "").strip() for f in fields]
        if literature_id:
            self.conn.execute("UPDATE literature_catalog SET "+", ".join(f+"=?" for f in fields)+", updated_at=? WHERE id=?", values+[now,literature_id])
            result=literature_id
        else:
            cur=self.conn.execute("INSERT INTO literature_catalog ("+", ".join(fields)+",created_at,updated_at) VALUES ("+", ".join(["?"]*(len(fields)+2))+")", values+[now,now])
            result=cur.lastrowid
        self.conn.commit(); return result

    def literature_delete(self, literature_id):
        self.conn.execute("DELETE FROM literature_catalog WHERE id=?", (literature_id,)); self.conn.commit()

    def disease_literature(self, disease_id):
        return self.conn.execute("""SELECT l.*, dl.relation_note FROM disease_literature dl JOIN literature_catalog l ON l.id=dl.literature_id WHERE dl.disease_id=? ORDER BY l.year_text DESC, l.authors COLLATE NOCASE""", (disease_id,)).fetchall()

    def link_literature(self, disease_id, literature_id, relation_note=""):
        self.conn.execute("INSERT OR REPLACE INTO disease_literature(disease_id,literature_id,relation_note) VALUES(?,?,?)", (disease_id,literature_id,(relation_note or "").strip())); self.conn.commit()

    def unlink_literature(self, disease_id, literature_id):
        self.conn.execute("DELETE FROM disease_literature WHERE disease_id=? AND literature_id=?", (disease_id,literature_id)); self.conn.commit()

    def disease_synonyms(self, disease_id):
        return self.conn.execute("SELECT * FROM disease_synonyms WHERE disease_id=? ORDER BY is_preferred DESC, synonym_name COLLATE NOCASE", (disease_id,)).fetchall()

    def sync_disease_synonyms(self, disease_id, synonyms_text):
        from .scientific import split_synonyms
        names=split_synonyms(synonyms_text)
        current={r["synonym_name"].casefold():r for r in self.disease_synonyms(disease_id)}
        keep=set(n.casefold() for n in names)
        for key,row in current.items():
            if key not in keep:
                self.conn.execute("DELETE FROM disease_synonyms WHERE id=?", (row["id"],))
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for name in names:
            self.conn.execute("INSERT OR IGNORE INTO disease_synonyms(disease_id,synonym_name,created_at) VALUES(?,?,?)", (disease_id,name,now))
        self.conn.commit()

    def save_disease_synonym(self, disease_id, synonym_name, synonym_type="Bilimsel eş ad", is_preferred=0, notes=""):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT OR REPLACE INTO disease_synonyms(id,disease_id,synonym_name,synonym_type,is_preferred,notes,created_at) VALUES((SELECT id FROM disease_synonyms WHERE disease_id=? AND synonym_name=? COLLATE NOCASE),?,?,?,?,?,COALESCE((SELECT created_at FROM disease_synonyms WHERE disease_id=? AND synonym_name=? COLLATE NOCASE),?))", (disease_id,synonym_name,disease_id,synonym_name.strip(),synonym_type.strip(),int(bool(is_preferred)),notes.strip(),disease_id,synonym_name,now))
        row=self.get(disease_id)
        names=[r["synonym_name"] for r in self.disease_synonyms(disease_id)]
        if row:
            self.conn.execute("UPDATE diseases SET synonyms=?, updated_at=? WHERE id=?", ("; ".join(names),now,disease_id))
        self.conn.commit()

    def delete_disease_synonym(self, synonym_id):
        row=self.conn.execute("SELECT disease_id FROM disease_synonyms WHERE id=?", (synonym_id,)).fetchone()
        if not row:return
        disease_id=row[0]; self.conn.execute("DELETE FROM disease_synonyms WHERE id=?", (synonym_id,))
        names=[r["synonym_name"] for r in self.disease_synonyms(disease_id)]
        self.conn.execute("UPDATE diseases SET synonyms=? WHERE id=?", ("; ".join(names),disease_id)); self.conn.commit()

    def private_note(self, disease_id):
        row=self.conn.execute("SELECT note_text FROM disease_private_notes WHERE disease_id=?", (disease_id,)).fetchone()
        return row[0] if row else ""

    def save_private_note(self, disease_id, note_text):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("INSERT OR REPLACE INTO disease_private_notes(disease_id,note_text,updated_at) VALUES(?,?,?)", (disease_id,note_text or "",now)); self.conn.commit()

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



    def update_attachment_metadata(self, attachment_id, title, description, captured_at, source, image_category="Genel", photographer="", copyright_owner="", license_text="", scale_info="", location_text=""):
        self.conn.execute(
            """UPDATE attachments
               SET title = ?, description = ?, captured_at = ?, source = ?, image_category = ?,
                   photographer = ?, copyright_owner = ?, license_text = ?, scale_info = ?, location_text = ?
               WHERE id = ?""",
            ((title or "").strip(), (description or "").strip(),
             (captured_at or "").strip(), (source or "").strip(), (image_category or "Genel").strip(),
             (photographer or "").strip(), (copyright_owner or "").strip(), (license_text or "").strip(),
             (scale_info or "").strip(), (location_text or "").strip(), attachment_id),
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
        clause += " OR EXISTS (SELECT 1 FROM disease_synonyms ds WHERE ds.disease_id=d.id AND ds.synonym_name LIKE ?)"
        params = [like]*len(fields) + [like]*5 + [int(limit)]
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


    # RC8/RC10.2 — Bilgi Sınavı ve Öğrenme Modülü
    def quiz_questions(self, query="", disease_id=None, difficulty="", topic="", question_type="", active_only=False):
        clauses=[]; params=[]
        if query:
            like="%"+query.strip()+"%"; clauses.append("(q.question_text LIKE ? OR q.topic_tag LIKE ? OR q.explanation LIKE ? OR q.source_text LIKE ?)"); params.extend([like]*4)
        if disease_id is not None:
            clauses.append("EXISTS (SELECT 1 FROM quiz_question_diseases qd WHERE qd.question_id=q.id AND qd.disease_id=?)"); params.append(int(disease_id))
        if difficulty: clauses.append("q.difficulty=?"); params.append(difficulty)
        if question_type: clauses.append("q.question_type=?"); params.append(question_type)
        if topic: clauses.append("q.topic_tag LIKE ?"); params.append("%"+topic.strip()+"%")
        if active_only: clauses.append("q.is_active=1")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        return self.conn.execute("""SELECT q.*,
            (SELECT GROUP_CONCAT(d.disease_name, '; ') FROM quiz_question_diseases qd JOIN diseases d ON d.id=qd.disease_id WHERE qd.question_id=q.id) disease_name,
            (SELECT GROUP_CONCAT(d.scientific_name, '; ') FROM quiz_question_diseases qd JOIN diseases d ON d.id=qd.disease_id WHERE qd.question_id=q.id) scientific_name
            FROM quiz_questions q"""+where+" ORDER BY q.updated_at DESC, q.id DESC",params).fetchall()

    def quiz_question_get(self, question_id):
        return self.conn.execute("""SELECT q.*,
            (SELECT GROUP_CONCAT(d.disease_name, '; ') FROM quiz_question_diseases qd JOIN diseases d ON d.id=qd.disease_id WHERE qd.question_id=q.id) disease_name,
            (SELECT GROUP_CONCAT(d.scientific_name, '; ') FROM quiz_question_diseases qd JOIN diseases d ON d.id=qd.disease_id WHERE qd.question_id=q.id) scientific_name
            FROM quiz_questions q WHERE q.id=?""",(int(question_id),)).fetchone()

    def quiz_question_disease_ids(self, question_id):
        return [int(r[0]) for r in self.conn.execute("SELECT disease_id FROM quiz_question_diseases WHERE question_id=? ORDER BY disease_id",(int(question_id),)).fetchall()]

    def quiz_question_save(self, question_id=None, disease_ids=None, **data):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields=("disease_id","question_type","question_text","difficulty","topic_tag","option_a","option_b","option_c","option_d","option_e",
            "question_format_json","option_a_format_json","option_b_format_json","option_c_format_json","option_d_format_json","option_e_format_json","explanation_format_json","correct_answer_format_json",
            "correct_answer","explanation","source_text")
        supplied_ids = list(disease_ids or [])
        if not supplied_ids and data.get("disease_id") is not None:
            supplied_ids = [data.get("disease_id")]
        disease_ids=list(dict.fromkeys(int(x) for x in supplied_ids if x is not None))
        primary=disease_ids[0] if disease_ids else None
        data["disease_id"]=primary
        values=[data.get(f) if f=="disease_id" else (data.get(f,"") or "") for f in fields]
        if question_id:
            self.conn.execute("UPDATE quiz_questions SET "+", ".join(f+"=?" for f in fields)+", updated_at=? WHERE id=?",values+[now,int(question_id)])
            result=int(question_id)
        else:
            cur=self.conn.execute("INSERT INTO quiz_questions ("+", ".join(fields)+",is_active,created_at,updated_at) VALUES ("+", ".join(["?"]*len(fields))+",1,?,?)",values+[now,now]); result=cur.lastrowid
        self.conn.execute("DELETE FROM quiz_question_diseases WHERE question_id=?",(result,))
        for did in disease_ids:
            self.conn.execute("INSERT OR IGNORE INTO quiz_question_diseases(question_id,disease_id) VALUES(?,?)",(result,did))
        self.conn.commit(); return result

    def quiz_question_delete(self, question_id):
        self.conn.execute("DELETE FROM quiz_questions WHERE id=?",(int(question_id),)); self.conn.commit()

    def quiz_question_count(self, disease_id=None):
        if disease_id is None: return int(self.conn.execute("SELECT COUNT(*) FROM quiz_questions WHERE is_active=1").fetchone()[0])
        return int(self.conn.execute("SELECT COUNT(DISTINCT q.id) FROM quiz_questions q JOIN quiz_question_diseases qd ON qd.question_id=q.id WHERE q.is_active=1 AND qd.disease_id=?",(int(disease_id),)).fetchone()[0])

    def quiz_topic_tags(self):
        tags=[]
        for row in self.conn.execute("SELECT topic_tag FROM quiz_questions WHERE TRIM(topic_tag)<>''").fetchall():
            for tag in str(row[0]).replace(';',',').split(','):
                tag=tag.strip()
                if tag and tag not in tags: tags.append(tag)
        return sorted(tags,key=lambda x:x.lower())

    def quiz_session_save(self, mode,total,correct,wrong,blank,score,duration_seconds,details):
        now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur=self.conn.execute("INSERT INTO quiz_sessions(mode,started_at,total_questions,correct_count,wrong_count,blank_count,score,duration_seconds,details_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (mode,now,int(total),int(correct),int(wrong),int(blank),float(score),int(duration_seconds),json.dumps(details,ensure_ascii=False)))
        self.conn.commit(); return cur.lastrowid

    def quiz_sessions(self, limit=100):
        return self.conn.execute("SELECT * FROM quiz_sessions ORDER BY started_at DESC, id DESC LIMIT ?",(int(limit),)).fetchall()

    def quiz_session_delete(self, session_id):
        self.conn.execute("DELETE FROM quiz_sessions WHERE id=?",(int(session_id),)); self.conn.commit()

    def quiz_sessions_clear(self):
        self.conn.execute("DELETE FROM quiz_sessions"); self.conn.commit()

    def quiz_stats(self):
        row=self.conn.execute("SELECT COUNT(*) sessions, COALESCE(SUM(total_questions),0) questions, COALESCE(ROUND(AVG(score),1),0) average_score FROM quiz_sessions").fetchone()
        return dict(row)

    def backup_to(self, destination_db):
        target = sqlite3.connect(destination_db)
        try:
            self.conn.backup(target)
        finally:
            target.close()



