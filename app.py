# -*- coding: utf-8 -*-
"""Fitopatoloji Arşivi - Windows 7 uyumlu yerel masaüstü arşivi.

Yalnızca Python standart kütüphanesini kullanır: tkinter + sqlite3.
PyInstaller ile paketlendiğinde hedef bilgisayarda Python kurulumu gerekmez.
"""
from __future__ import print_function

import csv
import datetime as dt
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
import zipfile

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import ttk

APP_NAME = "Fitopatoloji Arşivi"
APP_VERSION = "0.2.0"

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

    def search(self, query="", group_name=""):
        query = (query or "").strip()
        group_name = (group_name or "").strip()
        clauses = []
        params = []
        if group_name and group_name != "TÜMÜ":
            clauses.append("group_name = ?")
            params.append(group_name)
        if query:
            like = "%" + query + "%"
            clauses.append(
                "(" + " OR ".join([
                    "scientific_name LIKE ?", "synonyms LIKE ?", "disease_name LIKE ?",
                    "hosts LIKE ?", "symptoms LIKE ?", "notes LIKE ?"
                ]) + ")"
            )
            params.extend([like] * 6)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = (
            "SELECT id, group_name, scientific_name, disease_name "
            "FROM diseases" + where +
            " ORDER BY scientific_name COLLATE NOCASE, disease_name COLLATE NOCASE"
        )
        return self.conn.execute(sql, params).fetchall()

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
        ttk.Button(toolbar, text="CSV dışa aktar", command=self.export_csv).pack(side="left", padx=4)

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
        ttk.Button(attach_buttons, text="Dosya ekle", command=self.add_attachment).pack(fill="x")
        ttk.Button(attach_buttons, text="Aç", command=self.open_attachment).pack(fill="x", pady=3)
        ttk.Button(attach_buttons, text="Kaldır", command=self.remove_attachment).pack(fill="x")
        self.attach_tree.bind("<Double-1>", lambda _e: self.open_attachment())

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
        rows = self.db.search(self.search_var.get(), self.group_var.get())
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
                values=(row["file_type"], os.path.basename(row["relative_path"]), row["description"]),
            )

    def add_attachment(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        filename = filedialog.askopenfilename(title="Fotoğraf veya belge seç")
        if not filename:
            return
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}
        ext = os.path.splitext(filename)[1].lower()
        file_type = "image" if ext in image_exts else "document"
        target_dir = self.paths.images if file_type == "image" else self.paths.documents
        safe_name = "{}_{}".format(uuid.uuid4().hex[:10], os.path.basename(filename))
        destination = os.path.join(target_dir, safe_name)
        try:
            shutil.copy2(filename, destination)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Dosya kopyalanamadı:\n{}".format(exc), parent=self)
            return
        description = ""
        relative = os.path.relpath(destination, self.paths.base)
        self.db.add_attachment(self.selected_id, file_type, relative, description)
        self.refresh_attachments()

    def selected_attachment(self):
        selection = self.attach_tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Önce bir dosya seçin.", parent=self)
            return None
        return self.db.get_attachment(int(selection[0]))

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

    def create_backup(self):
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_path = os.path.join(self.paths.backups, "Fitopatoloji_Yedek_{}.zip".format(stamp))
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
            messagebox.showinfo(APP_NAME, "Yedek oluşturuldu:\n{}".format(zip_path), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Yedek oluşturulamadı:\n{}".format(exc), parent=self)
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
        db = Database(paths.database, seed)
        assert db.count() == 283, "Beklenen başlangıç kayıt sayısı 283, bulunan: {}".format(db.count())
        new_id = db.add({"group_name": "TEST", "scientific_name": "Testus exemplum", "disease_name": "Test hastalığı"})
        assert db.get(new_id)["scientific_name"] == "Testus exemplum"
        db.update(new_id, {"group_name": "TEST", "scientific_name": "Testus exemplum", "disease_name": "Güncel test hastalığı"})
        assert db.get(new_id)["disease_name"] == "Güncel test hastalığı"
        db.delete(new_id)
        assert db.get(new_id) is None
        backup = os.path.join(root, "backup.db")
        db.backup_to(backup)
        assert os.path.exists(backup)
        db.close()
        print("SELF-TEST OK: 283 seed kayıt, CRUD ve SQLite yedekleme başarılı.")
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
