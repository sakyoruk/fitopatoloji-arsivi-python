# -*- coding: utf-8 -*-
"""Fitopatoloji Arşivi - Windows 7 uyumlu yerel masaüstü arşivi.

Yalnızca Python standart kütüphanesini kullanır: tkinter + sqlite3.
PyInstaller ile paketlendiğinde hedef bilgisayarda Python kurulumu gerekmez.
"""
from __future__ import print_function

import csv
import datetime as dt
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:  # pragma: no cover
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import tkSimpleDialog as simpledialog
    import ttk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False

APP_NAME = "Fitopatoloji Arşivi"
APP_VERSION = "0.8.0"

LONG_FIELDS = [
    ("hosts", "Konukçular"),
    ("affected_organs", "Etkilenen organlar"),
    ("symptoms", "Belirtiler"),
    ("pathogen_features", "Etmenin özellikleri"),
    ("disease_cycle", "Hastalık döngüsü"),
    ("epidemiology", "Epidemiyoloji / uygun çevre koşulları"),
    ("differential_diagnosis", "Ayırıcı teşhis"),
    ("cultural_control", "Kültürel mücadele"),
    ("biological_control", "Biyolojik mücadele"),
    ("chemical_control", "Kimyasal mücadele / prensipler"),
    ("sources", "Kaynaklar"),
    ("notes", "Kişisel notlar"),
]

ALL_DB_FIELDS = [
    "id", "group_name", "scientific_name", "synonyms", "disease_name",
    "hosts", "affected_organs", "symptoms", "pathogen_features",
    "disease_cycle", "epidemiology", "differential_diagnosis",
    "cultural_control", "biological_control", "chemical_control",
    "sources", "notes", "created_at", "updated_at",
]


def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    """Paket içindeki salt-okunur kaynaklara ulaşır."""
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS, *parts))
    candidates.append(os.path.join(app_base_dir(), *parts))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


class AppPaths(object):
    def __init__(self, base_dir=None):
        self.base = os.path.abspath(base_dir or app_base_dir())
        self.data = os.path.join(self.base, "Data")
        self.images = os.path.join(self.base, "Images")
        self.documents = os.path.join(self.base, "Documents")
        self.backups = os.path.join(self.base, "Backups")
        self.exports = os.path.join(self.base, "Exports")
        self.database = os.path.join(self.data, "fitopatoloji.db")
        for folder in (self.data, self.images, self.documents, self.backups, self.exports):
            if not os.path.isdir(folder):
                os.makedirs(folder)


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
                sources TEXT NOT NULL DEFAULT '',
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
            CREATE INDEX IF NOT EXISTS idx_attachments_disease ON attachments(disease_id);
            """
        )
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(attachments)").fetchall()]
        if "is_primary" not in columns:
            self.conn.execute("ALTER TABLE attachments ADD COLUMN is_primary INTEGER NOT NULL DEFAULT 0")
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
        return self.conn.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]

    def list_groups(self):
        return [row[0] for row in self.conn.execute(
            "SELECT DISTINCT group_name FROM diseases WHERE group_name <> '' ORDER BY group_name COLLATE NOCASE"
        ).fetchall()]

    def search(self, query="", group_name="", host="", organ="", symptom=""):
        query = (query or "").strip()
        group_name = (group_name or "").strip()
        host = (host or "").strip()
        organ = (organ or "").strip()
        symptom = (symptom or "").strip()
        clauses = []
        params = []

        if group_name and group_name != "TÜMÜ":
            clauses.append("group_name = ?")
            params.append(group_name)

        searchable = [
            "group_name", "scientific_name", "synonyms", "disease_name",
            "hosts", "affected_organs", "symptoms", "pathogen_features",
            "disease_cycle", "epidemiology", "differential_diagnosis",
            "cultural_control", "biological_control", "chemical_control",
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
            "SELECT id, group_name, scientific_name, disease_name "
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

    def diagnose(self, host="", organ="", symptom=""):
        host = (host or "").strip().lower()
        organ = (organ or "").strip().lower()
        symptom_words = [w for w in re.split(r"\s+", (symptom or "").strip().lower()) if len(w) > 2]
        rows = self.conn.execute(
            """SELECT id, group_name, scientific_name, disease_name,
                      hosts, affected_organs, symptoms
               FROM diseases"""
        ).fetchall()
        results = []
        for row in rows:
            score = 0
            matched = []
            hosts = (row["hosts"] or "").lower()
            organs = (row["affected_organs"] or "").lower()
            symptoms = (row["symptoms"] or "").lower()
            if host:
                if host in hosts:
                    score += 4
                    matched.append("konukçu")
                else:
                    continue
            if organ:
                if organ in organs:
                    score += 3
                    matched.append("organ")
                else:
                    continue
            if symptom_words:
                hit_count = sum(1 for word in symptom_words if word in symptoms)
                if not hit_count:
                    continue
                score += hit_count * 2
                matched.append("{} belirti sözcüğü".format(hit_count))
            if score:
                results.append((score, row, ", ".join(matched)))
        results.sort(key=lambda item: (-item[0], item[1]["scientific_name"].lower()))
        return results[:100]

    def get(self, disease_id):
        return self.conn.execute("SELECT * FROM diseases WHERE id = ?", (disease_id,)).fetchone()

    def add(self, data):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [f for f in ALL_DB_FIELDS if f not in ("id", "created_at", "updated_at")]
        values = [data.get(f, "") for f in fields]
        sql = "INSERT INTO diseases ({}, created_at, updated_at) VALUES ({}, ?, ?)".format(
            ", ".join(fields), ", ".join(["?"] * len(fields))
        )
        cur = self.conn.execute(sql, values + [now, now])
        self.conn.commit()
        return cur.lastrowid

    def update(self, disease_id, data):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [f for f in ALL_DB_FIELDS if f not in ("id", "created_at", "updated_at")]
        assignments = ", ".join([f + " = ?" for f in fields])
        values = [data.get(f, "") for f in fields]
        self.conn.execute(
            "UPDATE diseases SET {}, updated_at = ? WHERE id = ?".format(assignments),
            values + [now, disease_id],
        )
        self.conn.commit()

    def delete(self, disease_id):
        self.conn.execute("DELETE FROM diseases WHERE id = ?", (disease_id,))
        self.conn.commit()

    def attachments(self, disease_id):
        return self.conn.execute(
            "SELECT * FROM attachments WHERE disease_id = ? ORDER BY created_at DESC, id DESC",
            (disease_id,),
        ).fetchall()

    def add_attachment(self, disease_id, file_type, relative_path, description=""):
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.execute(
            "INSERT INTO attachments (disease_id, file_type, relative_path, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (disease_id, file_type, relative_path, description, now),
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

    def image_attachments(self, disease_id):
        return self.conn.execute(
            """SELECT * FROM attachments
               WHERE disease_id = ? AND file_type = 'image'
               ORDER BY is_primary DESC, created_at, id""",
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

    def backup_to(self, destination_db):
        target = sqlite3.connect(destination_db)
        try:
            self.conn.backup(target)
        finally:
            target.close()


class DiseaseEditor(tk.Toplevel):
    def __init__(self, master, groups, initial=None, on_save=None):
        tk.Toplevel.__init__(self, master)
        self.title("Kayıt düzenle" if initial else "Yeni kayıt")
        self.transient(master)
        self.grab_set()

        # Windows 7 ve düşük çözünürlüklü ekranlarda pencerenin
        # görev çubuğunun altında kalmasını önle.
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(900, max(700, screen_w - 80))
        win_h = min(700, max(500, screen_h - 120))
        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)
        self.geometry("{}x{}+{}+{}".format(win_w, win_h, pos_x, pos_y))
        self.minsize(min(700, win_w), min(500, win_h))
        self.initial = dict(initial) if initial else {}
        self.on_save = on_save
        self.vars = {}
        self.texts = {}

        # Alt düğme çubuğunu önce paketle; böylece pencere küçülse bile
        # Kaydet ve İptal düğmeleri görünür kalır.
        footer = ttk.Frame(self, padding=(10, 8, 10, 10))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="İptal", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(footer, text="Kaydet", command=self.save).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))

        basic = ttk.Frame(notebook, padding=12)
        biology = ttk.Frame(notebook, padding=12)
        control = ttk.Frame(notebook, padding=12)
        references = ttk.Frame(notebook, padding=12)
        notebook.add(basic, text="Temel bilgiler")
        notebook.add(biology, text="Belirti ve biyoloji")
        notebook.add(control, text="Mücadele")
        notebook.add(references, text="Kaynak ve not")

        basic.columnconfigure(1, weight=1)
        row = 0
        ttk.Label(basic, text="Taksonomik grup").grid(row=row, column=0, sticky="w", pady=5)
        self.vars["group_name"] = tk.StringVar(value=self.initial.get("group_name", "ASCOMYCOTA"))
        combo = ttk.Combobox(basic, textvariable=self.vars["group_name"], values=groups, state="normal")
        combo.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1
        for field, label in [
            ("scientific_name", "Bilimsel ad"),
            ("synonyms", "Sinonimler / eski adlar"),
            ("disease_name", "Hastalık adı"),
            ("hosts", "Konukçular"),
            ("affected_organs", "Etkilenen organlar"),
        ]:
            ttk.Label(basic, text=label).grid(row=row, column=0, sticky="nw", pady=5)
            if field in ("hosts", "affected_organs"):
                widget = tk.Text(basic, height=4, wrap="word")
                widget.insert("1.0", self.initial.get(field, "") or "")
                widget.grid(row=row, column=1, sticky="nsew", pady=5)
                self.texts[field] = widget
                basic.rowconfigure(row, weight=1)
            else:
                var = tk.StringVar(value=self.initial.get(field, "") or "")
                ttk.Entry(basic, textvariable=var).grid(row=row, column=1, sticky="ew", pady=5)
                self.vars[field] = var
            row += 1

        for frame, fields in [
            (biology, [
                ("symptoms", "Belirtiler"),
                ("pathogen_features", "Etmenin özellikleri"),
                ("disease_cycle", "Hastalık döngüsü"),
                ("epidemiology", "Epidemiyoloji / uygun çevre koşulları"),
                ("differential_diagnosis", "Ayırıcı teşhis"),
            ]),
            (control, [
                ("cultural_control", "Kültürel mücadele"),
                ("biological_control", "Biyolojik mücadele"),
                ("chemical_control", "Kimyasal mücadele / prensipler"),
            ]),
            (references, [
                ("sources", "Kaynaklar"),
                ("notes", "Kişisel notlar"),
            ]),
        ]:
            frame.columnconfigure(0, weight=1)
            for idx, (field, label) in enumerate(fields):
                frame.rowconfigure(idx * 2 + 1, weight=1)
                ttk.Label(frame, text=label).grid(row=idx * 2, column=0, sticky="w", pady=(5, 2))
                text = tk.Text(frame, height=6, wrap="word", undo=True)
                text.insert("1.0", self.initial.get(field, "") or "")
                text.grid(row=idx * 2 + 1, column=0, sticky="nsew", pady=(0, 7))
                self.texts[field] = text

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-s>", lambda _e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def save(self):
        data = {}
        for field, var in self.vars.items():
            data[field] = var.get().strip()
        for field, text in self.texts.items():
            data[field] = text.get("1.0", "end-1c").strip()
        if not data.get("scientific_name"):
            messagebox.showwarning(APP_NAME, "Bilimsel ad boş bırakılamaz.", parent=self)
            return
        if not data.get("disease_name"):
            messagebox.showwarning(APP_NAME, "Hastalık adı veya açıklama boş bırakılamaz.", parent=self)
            return
        if self.on_save:
            self.on_save(data)
        self.destroy()



class PhotoGallery(tk.Toplevel):
    def __init__(self, master, db, paths, disease_id, start_attachment_id=None):
        tk.Toplevel.__init__(self, master)
        self.db = db
        self.paths = paths
        self.disease_id = disease_id
        self.photos = list(db.image_attachments(disease_id))
        self.index = 0
        self.zoom = 1.0
        self.rotation = 0
        self.original_image = None
        self.tk_image = None

        self.title("Fotoğraf galerisi")
        self.geometry("1000x720")
        self.minsize(700, 500)
        self.transient(master)

        if start_attachment_id is not None:
            for idx, row in enumerate(self.photos):
                if int(row["id"]) == int(start_attachment_id):
                    self.index = idx
                    break

        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="◀ Önceki", command=self.previous).pack(side="left")
        ttk.Button(toolbar, text="Sonraki ▶", command=self.next).pack(side="left", padx=4)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Küçült", command=self.zoom_out).pack(side="left")
        ttk.Button(toolbar, text="Büyüt", command=self.zoom_in).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Sığdır", command=self.fit).pack(side="left")
        ttk.Button(toolbar, text="Döndür", command=self.rotate).pack(side="left", padx=4)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Ana fotoğraf yap", command=self.make_primary).pack(side="left")
        ttk.Button(toolbar, text="Açıklamayı düzenle", command=self.edit_description).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Dışarıda aç", command=self.open_external).pack(side="right")

        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.render())

        self.info_var = tk.StringVar()
        ttk.Label(self, textvariable=self.info_var, anchor="center", padding=8).pack(fill="x")

        self.bind("<Left>", lambda _e: self.previous())
        self.bind("<Right>", lambda _e: self.next())
        self.bind("<plus>", lambda _e: self.zoom_in())
        self.bind("<minus>", lambda _e: self.zoom_out())
        self.bind("<Escape>", lambda _e: self.destroy())

        if not self.photos:
            messagebox.showinfo(APP_NAME, "Bu kayıtta fotoğraf yok.", parent=master)
            self.destroy()
            return
        self.load_current()

    def current_row(self):
        return self.photos[self.index] if self.photos else None

    def current_path(self):
        row = self.current_row()
        return os.path.join(self.paths.base, row["relative_path"]) if row else ""

    def load_current(self):
        path = self.current_path()
        if not os.path.exists(path):
            self.original_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                max(10, self.canvas.winfo_width() // 2),
                max(10, self.canvas.winfo_height() // 2),
                text="Dosya bulunamadı:\n{}".format(path),
                fill="white",
                justify="center",
            )
            return
        if not PIL_AVAILABLE:
            messagebox.showerror(
                APP_NAME,
                "Galeri için Pillow bileşeni gerekli.\nDerleme dosyasına 'pip install pillow' eklenmelidir.",
                parent=self,
            )
            self.destroy()
            return
        try:
            self.original_image = Image.open(path).convert("RGB")
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)
            return
        self.zoom = 1.0
        self.rotation = 0
        self.fit()

    def render(self):
        if self.original_image is None or not PIL_AVAILABLE:
            return
        image = self.original_image.rotate(self.rotation, expand=True)
        width = max(1, int(image.width * self.zoom))
        height = max(1, int(image.height * self.zoom))
        image = image.resize((width, height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self.tk_image,
            anchor="center",
        )
        row = self.current_row()
        primary = " · ANA FOTOĞRAF" if row["is_primary"] else ""
        self.info_var.set(
            "{} / {} · {} · Yakınlaştırma: %{}{} · {}".format(
                self.index + 1,
                len(self.photos),
                os.path.basename(row["relative_path"]).split("_", 1)[-1],
                int(self.zoom * 100),
                primary,
                row["description"] or "Açıklama yok",
            )
        )

    def fit(self):
        if self.original_image is None:
            return
        canvas_w = max(300, self.canvas.winfo_width() - 30)
        canvas_h = max(250, self.canvas.winfo_height() - 30)
        image = self.original_image.rotate(self.rotation, expand=True)
        self.zoom = min(float(canvas_w) / image.width, float(canvas_h) / image.height, 1.0)
        self.render()

    def zoom_in(self):
        self.zoom = min(4.0, self.zoom * 1.25)
        self.render()

    def zoom_out(self):
        self.zoom = max(0.1, self.zoom / 1.25)
        self.render()

    def rotate(self):
        self.rotation = (self.rotation - 90) % 360
        self.fit()

    def previous(self):
        if self.photos:
            self.index = (self.index - 1) % len(self.photos)
            self.load_current()

    def next(self):
        if self.photos:
            self.index = (self.index + 1) % len(self.photos)
            self.load_current()

    def make_primary(self):
        row = self.current_row()
        if not row:
            return
        self.db.set_primary_attachment(self.disease_id, row["id"])
        self.photos = list(self.db.image_attachments(self.disease_id))
        for idx, item in enumerate(self.photos):
            if item["id"] == row["id"]:
                self.index = idx
                break
        self.master.refresh_attachments()
        self.render()

    def edit_description(self):
        row = self.current_row()
        if not row:
            return
        value = simpledialog.askstring(
            APP_NAME,
            "Fotoğraf açıklaması:",
            initialvalue=row["description"] or "",
            parent=self,
        )
        if value is None:
            return
        self.db.update_attachment_description(row["id"], value)
        self.photos = list(self.db.image_attachments(self.disease_id))
        for idx, item in enumerate(self.photos):
            if item["id"] == row["id"]:
                self.index = idx
                break
        self.master.refresh_attachments()
        self.render()

    def open_external(self):
        path = self.current_path()
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)


class MainWindow(tk.Tk):
    def __init__(self, paths, database):
        tk.Tk.__init__(self)
        self.paths = paths
        self.db = database
        self.selected_id = None
        self.title("{} {}".format(APP_NAME, APP_VERSION))
        self.geometry("1220x760")
        self.minsize(960, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.search_var = tk.StringVar()
        self.group_var = tk.StringVar(value="TÜMÜ")
        self.host_filter = ""
        self.organ_filter = ""
        self.symptom_filter = ""
        self.status_var = tk.StringVar()
        self.header_scientific = tk.StringVar(value="Bir kayıt seçin")
        self.header_disease = tk.StringVar(value="")
        self.header_group = tk.StringVar(value="")
        self.detail_texts = {}

        self.build_ui()
        self.refresh_groups()
        self.refresh_list()

    def build_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Yeni kayıt", command=self.new_record).pack(side="left")
        ttk.Button(toolbar, text="Düzenle", command=self.edit_record).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Sil", command=self.delete_record).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Yedek oluştur", command=self.create_backup).pack(side="left")
        ttk.Button(toolbar, text="Yedeği geri yükle", command=self.restore_backup).pack(side="left", padx=4)
        ttk.Button(toolbar, text="CSV dışa aktar", command=self.export_csv).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Gelişmiş filtre", command=self.open_advanced_filter).pack(side="left")
        ttk.Button(toolbar, text="Teşhis sihirbazı", command=self.open_diagnosis_wizard).pack(side="left", padx=4)

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(paned, padding=6)
        right = ttk.Frame(paned, padding=6)
        paned.add(left, weight=2)
        paned.add(right, weight=5)

        filter_frame = ttk.Frame(left)
        filter_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(filter_frame, text="Ara").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(filter_frame, textvariable=self.search_var)
        search.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        ttk.Label(filter_frame, text="Grup").grid(row=0, column=1, sticky="w")
        self.group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var, state="readonly", width=22)
        self.group_combo.grid(row=1, column=1, sticky="ew")
        ttk.Button(filter_frame, text="Temizle", command=self.clear_filters).grid(row=1, column=2, padx=(5, 0))
        filter_frame.columnconfigure(0, weight=1)
        search.bind("<KeyRelease>", lambda _e: self.after_idle(self.refresh_list))
        self.group_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_list())

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("scientific", "disease"), show="headings", selectmode="browse")
        self.tree.heading("scientific", text="Etmen")
        self.tree.heading("disease", text="Hastalık")
        self.tree.column("scientific", width=215, anchor="w")
        self.tree.column("disease", width=260, anchor="w")
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda _e: self.edit_record())

        header = ttk.Frame(right)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, textvariable=self.header_scientific, font=("Segoe UI", 13, "bold"), wraplength=700).pack(anchor="w")
        ttk.Label(header, textvariable=self.header_disease, font=("Segoe UI", 10), wraplength=700).pack(anchor="w", pady=(2, 0))
        ttk.Label(header, textvariable=self.header_group).pack(anchor="w", pady=(2, 0))

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        tabs = [
            ("Temel", ["synonyms", "hosts", "affected_organs"]),
            ("Belirti ve biyoloji", ["symptoms", "pathogen_features", "disease_cycle", "epidemiology", "differential_diagnosis"]),
            ("Mücadele", ["cultural_control", "biological_control", "chemical_control"]),
            ("Kaynak ve not", ["sources", "notes"]),
        ]
        labels = dict(LONG_FIELDS)
        labels["synonyms"] = "Sinonimler / eski adlar"
        for tab_name, fields in tabs:
            outer = ttk.Frame(notebook)
            notebook.add(outer, text=tab_name)
            canvas = tk.Canvas(outer, highlightthickness=0)
            scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            inner = ttk.Frame(canvas, padding=10)
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scroll.set)
            canvas.pack(side="left", fill="both", expand=True)
            scroll.pack(side="right", fill="y")
            inner.columnconfigure(0, weight=1)
            for idx, field in enumerate(fields):
                ttk.Label(inner, text=labels[field], font=("Segoe UI", 9, "bold")).grid(row=idx * 2, column=0, sticky="w", pady=(6, 2))
                text = tk.Text(inner, height=5, wrap="word", relief="solid", borderwidth=1, background="#ffffff")
                text.grid(row=idx * 2 + 1, column=0, sticky="ew")
                text.configure(state="disabled")
                self.detail_texts[field] = text

        attachment_frame = ttk.LabelFrame(right, text="Fotoğraflar ve belgeler", padding=6)
        attachment_frame.pack(fill="x", pady=(8, 0))
        self.attach_tree = ttk.Treeview(attachment_frame, columns=("type", "name", "description"), show="headings", height=4)
        self.attach_tree.heading("type", text="Tür")
        self.attach_tree.heading("name", text="Dosya")
        self.attach_tree.heading("description", text="Açıklama")
        self.attach_tree.column("type", width=70)
        self.attach_tree.column("name", width=260)
        self.attach_tree.column("description", width=330)
        self.attach_tree.pack(side="left", fill="x", expand=True)
        attach_buttons = ttk.Frame(attachment_frame)
        attach_buttons.pack(side="right", fill="y", padx=(6, 0))
        ttk.Button(attach_buttons, text="Fotoğraf ekle", command=self.add_photo).pack(fill="x")
        ttk.Button(attach_buttons, text="Belge ekle", command=self.add_document).pack(fill="x", pady=(3, 0))
        ttk.Button(attach_buttons, text="Galeri", command=self.open_gallery).pack(fill="x", pady=(3, 0))
        ttk.Button(attach_buttons, text="Aç", command=self.open_attachment).pack(fill="x", pady=3)
        ttk.Button(attach_buttons, text="Kaldır", command=self.remove_attachment).pack(fill="x")
        self.attach_tree.bind("<Double-1>", self.on_attachment_double_click)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken", padding=(6, 3))
        status.pack(fill="x", side="bottom")

    def refresh_groups(self):
        groups = ["TÜMÜ"] + self.db.list_groups()
        self.group_combo["values"] = groups
        if self.group_var.get() not in groups:
            self.group_var.set("TÜMÜ")

    def refresh_list(self, select_id=None):
        current = select_id or self.selected_id
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.db.search(self.search_var.get(), self.group_var.get(), self.host_filter, self.organ_filter, self.symptom_filter)
        selected_item = None
        for row in rows:
            item = self.tree.insert("", "end", iid=str(row["id"]), values=(row["scientific_name"], row["disease_name"]))
            if current and int(row["id"]) == int(current):
                selected_item = item
        self.status_var.set("{} kayıt gösteriliyor · veritabanında toplam {} kayıt".format(len(rows), self.db.count()))
        if selected_item:
            self.tree.selection_set(selected_item)
            self.tree.focus(selected_item)
            self.tree.see(selected_item)
            self.load_record(int(selected_item))
        elif rows:
            first = str(rows[0]["id"])
            self.tree.selection_set(first)
            self.tree.focus(first)
            self.load_record(int(first))
        else:
            self.clear_detail()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if selected:
            self.load_record(int(selected[0]))

    def load_record(self, disease_id):
        record = self.db.get(disease_id)
        if not record:
            return
        self.selected_id = disease_id
        self.header_scientific.set(record["scientific_name"])
        self.header_disease.set(record["disease_name"])
        self.header_group.set(record["group_name"])
        for field, text in self.detail_texts.items():
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", record[field] or "")
            text.configure(state="disabled")
        self.refresh_attachments()

    def clear_detail(self):
        self.selected_id = None
        self.header_scientific.set("Kayıt bulunamadı")
        self.header_disease.set("")
        self.header_group.set("")
        for text in self.detail_texts.values():
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.configure(state="disabled")
        for item in self.attach_tree.get_children():
            self.attach_tree.delete(item)

    def new_record(self):
        groups = self.db.list_groups()
        DiseaseEditor(self, groups, on_save=self._save_new)

    def _save_new(self, data):
        new_id = self.db.add(data)
        self.refresh_groups()
        self.refresh_list(select_id=new_id)

    def edit_record(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir kayıt seçin.", parent=self)
            return
        record = self.db.get(self.selected_id)
        groups = self.db.list_groups()
        DiseaseEditor(self, groups, initial=record, on_save=self._save_edit)

    def _save_edit(self, data):
        self.db.update(self.selected_id, data)
        self.refresh_groups()
        self.refresh_list(select_id=self.selected_id)

    def delete_record(self):
        if not self.selected_id:
            return
        record = self.db.get(self.selected_id)
        answer = messagebox.askyesno(
            APP_NAME,
            "'{}' kaydı ve bağlı dosyaları veritabanından silinsin mi?\n\nDosyaların kopyaları klasörde kalır.".format(record["scientific_name"]),
            parent=self,
        )
        if answer:
            self.db.delete(self.selected_id)
            self.selected_id = None
            self.refresh_groups()
            self.refresh_list()

    def refresh_attachments(self):
        for item in self.attach_tree.get_children():
            self.attach_tree.delete(item)
        if not self.selected_id:
            return
        for row in self.db.attachments(self.selected_id):
            self.attach_tree.insert(
                "", "end", iid=str(row["id"]),
                values=(
                    ("★ Fotoğraf" if row["is_primary"] else "Fotoğraf") if row["file_type"] == "image" else "Belge",
                    os.path.basename(row["relative_path"]).split("_", 1)[-1],
                    row["description"],
                ),
            )

    def add_photo(self):
        self.add_attachment("image")

    def add_document(self):
        self.add_attachment("document")

    def add_attachment(self, requested_type=None):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return

        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}
        if requested_type == "image":
            filename = filedialog.askopenfilename(
                title="Fotoğraf seç",
                filetypes=[
                    ("Fotoğraf dosyaları", "*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tif;*.tiff"),
                    ("Tüm dosyalar", "*.*"),
                ],
            )
        else:
            filename = filedialog.askopenfilename(
                title="Belge seç",
                filetypes=[
                    ("Belgeler", "*.pdf;*.doc;*.docx;*.xls;*.xlsx;*.ppt;*.pptx;*.txt;*.rtf"),
                    ("Tüm dosyalar", "*.*"),
                ],
            )

        if not filename:
            return

        ext = os.path.splitext(filename)[1].lower()
        detected_type = "image" if ext in image_exts else "document"
        file_type = requested_type or detected_type

        if requested_type == "image" and detected_type != "image":
            messagebox.showwarning(
                APP_NAME,
                "Seçilen dosya desteklenen bir fotoğraf biçiminde değil.",
                parent=self,
            )
            return

        description = simpledialog.askstring(
            APP_NAME,
            "Dosya açıklaması (isteğe bağlı):",
            parent=self,
        )
        if description is None:
            return

        root_dir = self.paths.images if file_type == "image" else self.paths.documents
        target_dir = os.path.join(root_dir, str(self.selected_id))
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        original_name = os.path.basename(filename)
        safe_name = "{}_{}".format(uuid.uuid4().hex[:10], original_name)
        destination = os.path.join(target_dir, safe_name)

        try:
            shutil.copy2(filename, destination)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Dosya kopyalanamadı:\n{}".format(exc), parent=self)
            return

        relative = os.path.relpath(destination, self.paths.base)
        try:
            self.db.add_attachment(
                self.selected_id,
                file_type,
                relative,
                (description or "").strip(),
            )
        except Exception as exc:
            try:
                os.remove(destination)
            except Exception:
                pass
            messagebox.showerror(APP_NAME, "Dosya kaydedilemedi:\n{}".format(exc), parent=self)
            return

        self.refresh_attachments()
        self.status_var.set(
            "{} eklendi: {}".format(
                "Fotoğraf" if file_type == "image" else "Belge",
                original_name,
            )
        )

    def selected_attachment(self):
        selection = self.attach_tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Önce bir dosya seçin.", parent=self)
            return None
        return self.db.get_attachment(int(selection[0]))

    def clear_filters(self):
        self.search_var.set("")
        self.group_var.set("TÜMÜ")
        self.host_filter = ""
        self.organ_filter = ""
        self.symptom_filter = ""
        self.refresh_list()

    def open_advanced_filter(self):
        dialog = tk.Toplevel(self)
        dialog.title("Gelişmiş filtre")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        values = {
            "host": tk.StringVar(value=self.host_filter),
            "organ": tk.StringVar(value=self.organ_filter),
            "symptom": tk.StringVar(value=self.symptom_filter),
        }
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)
        fields = [
            ("Konukçu", "host", self.db.distinct_terms("hosts")),
            ("Etkilenen organ", "organ", self.db.distinct_terms("affected_organs")),
            ("Belirti sözcüğü", "symptom", self.db.distinct_terms("symptoms")),
        ]
        for row, (label, key, options) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5)
            combo = ttk.Combobox(frame, textvariable=values[key], values=options, width=48, state="normal")
            combo.grid(row=row, column=1, sticky="ew", pady=5)

        def apply_filter():
            self.host_filter = values["host"].get().strip()
            self.organ_filter = values["organ"].get().strip()
            self.symptom_filter = values["symptom"].get().strip()
            dialog.destroy()
            self.refresh_list()

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="İptal", command=dialog.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(buttons, text="Uygula", command=apply_filter).pack(side="right")
        frame.columnconfigure(1, weight=1)
        dialog.bind("<Return>", lambda _e: apply_filter())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.update_idletasks()
        dialog.geometry("+{}+{}".format(
            max(0, self.winfo_rootx() + 120),
            max(0, self.winfo_rooty() + 100),
        ))

    def open_diagnosis_wizard(self):
        dialog = tk.Toplevel(self)
        dialog.title("Teşhis sihirbazı")
        dialog.geometry("860x560")
        dialog.minsize(720, 450)
        dialog.transient(self)

        top = ttk.Frame(dialog, padding=10)
        top.pack(fill="x")
        host_var = tk.StringVar()
        organ_var = tk.StringVar()
        symptom_var = tk.StringVar()

        ttk.Label(top, text="Konukçu").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Organ").grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(top, text="Belirti / anahtar sözcükler").grid(row=0, column=2, sticky="w", padx=(6, 0))
        ttk.Combobox(top, textvariable=host_var, values=self.db.distinct_terms("hosts"), state="normal").grid(row=1, column=0, sticky="ew")
        ttk.Combobox(top, textvariable=organ_var, values=self.db.distinct_terms("affected_organs"), state="normal").grid(row=1, column=1, sticky="ew", padx=(6, 0))
        ttk.Entry(top, textvariable=symptom_var).grid(row=1, column=2, sticky="ew", padx=(6, 0))
        for col in range(3):
            top.columnconfigure(col, weight=1)

        result_frame = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        result_frame.pack(fill="both", expand=True)
        result_tree = ttk.Treeview(
            result_frame,
            columns=("score", "scientific", "disease", "match"),
            show="headings",
            selectmode="browse",
        )
        for column, title, width in [
            ("score", "Puan", 55),
            ("scientific", "Etmen", 230),
            ("disease", "Hastalık", 300),
            ("match", "Eşleşme", 180),
        ]:
            result_tree.heading(column, text=title)
            result_tree.column(column, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=result_tree.yview)
        result_tree.configure(yscrollcommand=scrollbar.set)
        result_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def run_diagnosis():
            for item in result_tree.get_children():
                result_tree.delete(item)
            results = self.db.diagnose(host_var.get(), organ_var.get(), symptom_var.get())
            for score, row, matched in results:
                result_tree.insert(
                    "", "end", iid=str(row["id"]),
                    values=(score, row["scientific_name"], row["disease_name"], matched),
                )
            if not results:
                messagebox.showinfo(APP_NAME, "Bu ölçütlerle eşleşen kayıt bulunamadı.", parent=dialog)

        def open_result(_event=None):
            selection = result_tree.selection()
            if not selection:
                return
            disease_id = int(selection[0])
            dialog.destroy()
            self.search_var.set("")
            self.group_var.set("TÜMÜ")
            self.host_filter = self.organ_filter = self.symptom_filter = ""
            self.refresh_list(select_id=disease_id)

        buttons = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Kapat", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Seçili kaydı aç", command=open_result).pack(side="right", padx=5)
        ttk.Button(buttons, text="Olası hastalıkları bul", command=run_diagnosis).pack(side="right")
        result_tree.bind("<Double-1>", open_result)
        dialog.bind("<Return>", lambda _e: run_diagnosis())

    def open_gallery(self):
        if not self.selected_id:
            return
        row = self.selected_attachment()
        start_id = row["id"] if row and row["file_type"] == "image" else None
        PhotoGallery(self, self.db, self.paths, self.selected_id, start_id)

    def on_attachment_double_click(self, _event=None):
        row = self.selected_attachment()
        if row and row["file_type"] == "image":
            self.open_gallery()
        else:
            self.open_attachment()

    def open_attachment(self):
        row = self.selected_attachment()
        if not row:
            return
        path = os.path.join(self.paths.base, row["relative_path"])
        if not os.path.exists(path):
            messagebox.showerror(APP_NAME, "Dosya bulunamadı:\n{}".format(path), parent=self)
            return
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Dosya açılamadı:\n{}".format(exc), parent=self)

    def remove_attachment(self):
        row = self.selected_attachment()
        if not row:
            return
        if messagebox.askyesno(APP_NAME, "Dosya bağlantısı kaldırılsın mı?\nKopyalanan dosya da silinecek.", parent=self):
            path = os.path.join(self.paths.base, row["relative_path"])
            self.db.delete_attachment(row["id"])
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass
            self.refresh_attachments()

    def _write_backup_zip(self, zip_path):
        temp_dir = tempfile.mkdtemp(prefix="fitopatoloji_backup_")
        try:
            db_copy = os.path.join(temp_dir, "fitopatoloji.db")
            self.db.backup_to(db_copy)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(db_copy, os.path.join("Data", "fitopatoloji.db"))
                for folder_name, folder_path in (("Images", self.paths.images), ("Documents", self.paths.documents)):
                    for root, _dirs, files in os.walk(folder_path):
                        for filename in files:
                            full = os.path.join(root, filename)
                            rel = os.path.relpath(full, folder_path)
                            archive.write(full, os.path.join(folder_name, rel))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_backup(self):
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_path = os.path.join(self.paths.backups, "Fitopatoloji_Yedek_{}.zip".format(stamp))
        try:
            self._write_backup_zip(zip_path)
            messagebox.showinfo(APP_NAME, "Yedek oluşturuldu:\n{}".format(zip_path), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Yedek oluşturulamadı:\n{}".format(exc), parent=self)

    def restore_backup(self):
        backup_path = filedialog.askopenfilename(
            title="Fitopatoloji yedeğini seç",
            initialdir=self.paths.backups,
            filetypes=[("ZIP yedeği", "*.zip")],
        )
        if not backup_path:
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Seçilen yedek geri yüklenecek.\n\nMevcut arşiv önce otomatik olarak güvenlik yedeğine alınacaktır. Devam edilsin mi?",
            parent=self,
        ):
            return

        temp_dir = tempfile.mkdtemp(prefix="fitopatoloji_restore_")
        safety_path = os.path.join(
            self.paths.backups,
            "Geri_Yukleme_Oncesi_{}.zip".format(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")),
        )
        try:
            self._write_backup_zip(safety_path)
            with zipfile.ZipFile(backup_path, "r") as archive:
                for member in archive.infolist():
                    target = os.path.abspath(os.path.join(temp_dir, member.filename))
                    if not target.startswith(os.path.abspath(temp_dir) + os.sep):
                        raise ValueError("Yedek içinde güvensiz dosya yolu bulundu.")
                archive.extractall(temp_dir)

            restored_db = os.path.join(temp_dir, "Data", "fitopatoloji.db")
            if not os.path.isfile(restored_db):
                raise ValueError("Yedekte Data/fitopatoloji.db bulunamadı.")

            test_conn = sqlite3.connect(restored_db)
            try:
                test_conn.execute("SELECT COUNT(*) FROM diseases").fetchone()
            finally:
                test_conn.close()

            self.db.close()
            shutil.copy2(restored_db, self.paths.database)

            for folder_name, target_folder in (("Images", self.paths.images), ("Documents", self.paths.documents)):
                source_folder = os.path.join(temp_dir, folder_name)
                if os.path.isdir(target_folder):
                    shutil.rmtree(target_folder)
                os.makedirs(target_folder)
                if os.path.isdir(source_folder):
                    for name in os.listdir(source_folder):
                        source = os.path.join(source_folder, name)
                        target = os.path.join(target_folder, name)
                        if os.path.isdir(source):
                            shutil.copytree(source, target)
                        else:
                            shutil.copy2(source, target)

            self.db = Database(self.paths.database, resource_path("seed", "diseases.csv"))
            self.selected_id = None
            self.clear_filters()
            self.refresh_groups()
            self.refresh_list()
            messagebox.showinfo(
                APP_NAME,
                "Yedek başarıyla geri yüklendi.\n\nGeri yükleme öncesi güvenlik yedeği:\n{}".format(safety_path),
                parent=self,
            )
        except Exception as exc:
            try:
                self.db = Database(self.paths.database, resource_path("seed", "diseases.csv"))
            except Exception:
                pass
            messagebox.showerror(
                APP_NAME,
                "Yedek geri yüklenemedi:\n{}\n\nMevcut veriler korunmaya çalışıldı.".format(exc),
                parent=self,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def export_csv(self):
        default_name = "fitopatoloji_{}.csv".format(dt.datetime.now().strftime("%Y-%m-%d"))
        output = filedialog.asksaveasfilename(
            title="CSV dışa aktar",
            initialdir=self.paths.exports,
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV dosyası", "*.csv")],
        )
        if not output:
            return
        try:
            self.db.export_csv(output)
            messagebox.showinfo(APP_NAME, "CSV oluşturuldu:\n{}".format(output), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "CSV oluşturulamadı:\n{}".format(exc), parent=self)

    def on_close(self):
        self.db.close()
        self.destroy()


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
        })
        assert db.get(new_id)["scientific_name"] == "Testus exemplum"

        db.update(new_id, {
            "group_name": "TEST",
            "scientific_name": "Testus exemplum",
            "disease_name": "Güncel test hastalığı",
            "hosts": "Test konukçusu",
            "affected_organs": "Test yaprağı",
            "symptoms": "Test lekesi ve solgunluk",
        })
        assert db.get(new_id)["disease_name"] == "Güncel test hastalığı"

        # Arama ve teşhis testleri gerçek seed içeriğine bağlı olmamalı.
        assert any(row["id"] == new_id for row in db.search("Testus exemplum"))
        assert any(row["id"] == new_id for row in db.search(host="Test konukçusu"))
        assert any(item[1]["id"] == new_id for item in db.diagnose(
            host="Test konukçusu",
            organ="Test yaprağı",
            symptom="leke",
        ))

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


def main():
    if "--self-test" in sys.argv:
        return self_test()
    paths = AppPaths()
    seed = resource_path("seed", "diseases.csv")
    try:
        db = Database(paths.database, seed)
    except Exception as exc:
        # GUI başlamadan önceki hatayı görünür kıl.
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_NAME, "Veritabanı açılamadı:\n{}\n\nUygulama klasörünün yazılabilir olduğundan emin olun.".format(exc))
        root.destroy()
        return 1
    app = MainWindow(paths, db)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
