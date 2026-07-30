# -*- coding: utf-8 -*-
"""1.8.0 Akıllı Ana Sayfa, Arşiv Denetimi ve Süper Arama."""
from .common import *
from .theme import COLORS

QUALITY_FIELDS = (
    "scientific_name", "disease_name", "hosts", "affected_organs", "symptoms",
    "pathogen_features", "disease_cycle", "epidemiology",
    "differential_diagnosis", "cultural_control", "biological_control",
    "chemical_control", "sources"
)


def record_quality(row, photo_count=0):
    filled = sum(1 for field in QUALITY_FIELDS if (row[field] or "").strip())
    percent = int(round(100.0 * filled / len(QUALITY_FIELDS)))
    missing = []
    if not (row["scientific_name"] or "").strip(): missing.append("etmen")
    if not (row["hosts"] or "").strip(): missing.append("konukçu")
    if not (row["symptoms"] or "").strip(): missing.append("belirti")
    if not (row["sources"] or "").strip(): missing.append("kaynakça")
    if not photo_count: missing.append("fotoğraf")
    if percent >= 85 and not missing:
        label = "Tam kayıt"
    elif not (row["sources"] or "").strip():
        label = "Kaynakça eksik"
    elif not photo_count:
        label = "Fotoğraf eksik"
    elif percent >= 60:
        label = "Gözden geçirilmeli"
    elif percent >= 30:
        label = "Temel bilgiler tamamlanıyor"
    else:
        label = "Taslak"
    return percent, label, missing


class Dashboard(tk.Toplevel):
    def __init__(self, parent, database, open_callback, new_callback, command_callback=None):
        tk.Toplevel.__init__(self, parent); center_toplevel(self)
        self.parent = parent
        self.db = database
        self.open_callback = open_callback
        self.new_callback = new_callback
        self.command_callback = command_callback
        self.title("Çalışma Merkezi — {} {}".format(APP_NAME, APP_VERSION))
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.transient(parent)
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Arşiv özeti hazırlanıyor…")
        self.after_id = None
        self.build_ui()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Control-k>", lambda _e: self._commands())
        self.after_idle(self._focus_search)

    def _focus_search(self):
        self.search_entry.focus_set()

    def build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        head = ttk.Frame(root, style="Surface.TFrame", padding=(18, 14))
        head.pack(fill="x")
        left = ttk.Frame(head, style="Surface.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Çalışma Merkezi", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Arşivin durumunu görün, eksikleri tamamlayın ve kayıtlara hızla ulaşın.", style="Subtitle.TLabel").pack(anchor="w")
        actions = ttk.Frame(head, style="Surface.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Yeni kayıt", style="Primary.TButton", command=self._new).pack(side="left", padx=4)
        ttk.Button(actions, text="Komutlar  Ctrl+K", command=self._commands).pack(side="left", padx=4)
        ttk.Button(actions, text="Arşive dön", command=self.destroy).pack(side="left", padx=4)

        search_box = ttk.Frame(root, style="Surface.TFrame", padding=(18, 14))
        search_box.pack(fill="x", pady=(12, 0))
        ttk.Label(search_box, text="Süper arama", style="Section.TLabel").pack(anchor="w")
        self.search_entry = ttk.Entry(search_box, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.pack(fill="x", pady=(7, 0))
        self.search_entry.bind("<KeyRelease>", self._queue_search)
        self.search_entry.bind("<Return>", lambda _e: self.open_selected_search())
        ttk.Label(search_box, text="Etmen, hastalık, konukçu, belirti, organ, kaynakça ve fotoğraf açıklamalarında arar.", style="Muted.TLabel").pack(anchor="w", pady=(5, 0))

        cards = ttk.Frame(root)
        cards.pack(fill="x", pady=12)
        for column in range(4): cards.columnconfigure(column, weight=1)
        self.card_labels = {}
        metrics = (("total", "Toplam kayıt"), ("complete", "Tam kayıt"), ("favorites", "Favoriler"),
                   ("hosts", "Konukçular"), ("literature", "Literatür"), ("photos", "Fotoğraflar"),
                   ("questions", "Sorular"), ("no_sources", "Kaynakçasız"))
        for index, (key, title) in enumerate(metrics):
            card = ttk.Frame(cards, style="Card.TFrame", padding=(14, 10))
            card.grid(row=index // 4, column=index % 4, sticky="ew", padx=(0, 8) if index % 4 != 3 else 0, pady=(0, 8))
            value = ttk.Label(card, text="0", style="MetricValue.TLabel")
            value.pack(anchor="w")
            ttk.Label(card, text=title, style="MetricLabel.TLabel").pack(anchor="w")
            self.card_labels[key] = value

        panes = ttk.Panedwindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True)
        result_card = ttk.Frame(panes, style="Surface.TFrame", padding=12)
        side_card = ttk.Frame(panes, style="Surface.TFrame", padding=12)
        panes.add(result_card, weight=3)
        panes.add(side_card, weight=2)

        self.result_title = ttk.Label(result_card, text="Son düzenlenen kayıtlar", style="Section.TLabel")
        self.result_title.pack(anchor="w", pady=(0, 8))
        rf = ttk.Frame(result_card, style="Surface.TFrame")
        rf.pack(fill="both", expand=True)
        self.results = ttk.Treeview(rf, columns=("disease", "status", "updated"), show="headings", selectmode="browse")
        for col, title, width in (("disease", "Kayıt", 330), ("status", "Durum", 145), ("updated", "Güncelleme", 125)):
            self.results.heading(col, text=title); self.results.column(col, width=width, anchor="w")
        sy = ttk.Scrollbar(rf, orient="vertical", command=self.results.yview)
        self.results.configure(yscrollcommand=sy.set)
        self.results.pack(side="left", fill="both", expand=True); sy.pack(side="right", fill="y")
        self.results.bind("<Double-1>", lambda _e: self.open_selected_search())
        ttk.Button(result_card, text="Seçili kaydı aç", style="Primary.TButton", command=self.open_selected_search).pack(anchor="e", pady=(8, 0))

        ttk.Label(side_card, text="Arşiv denetimi", style="Section.TLabel").pack(anchor="w")
        ttk.Label(side_card, text="Bir başlığa çift tıklayarak ilgili kayıtları listeleyin.", style="Muted.TLabel").pack(anchor="w", pady=(2, 8))
        af = ttk.Frame(side_card, style="Surface.TFrame")
        af.pack(fill="both", expand=True)
        self.audit = ttk.Treeview(af, columns=("count",), show="tree headings", selectmode="browse")
        self.audit.heading("#0", text="Kontrol"); self.audit.heading("count", text="Sayı")
        self.audit.column("#0", width=260); self.audit.column("count", width=60, anchor="center")
        ay = ttk.Scrollbar(af, orient="vertical", command=self.audit.yview)
        self.audit.configure(yscrollcommand=ay.set)
        self.audit.pack(side="left", fill="both", expand=True); ay.pack(side="right", fill="y")
        self.audit.bind("<Double-1>", lambda _e: self.show_audit_selection())
        ttk.Button(side_card, text="Seçilen denetimi göster", command=self.show_audit_selection).pack(anchor="e", pady=(8, 0))

        ttk.Label(root, textvariable=self.status_var, style="Status.TLabel", anchor="w").pack(fill="x", pady=(12, 0))

    def _queue_search(self, _event=None):
        if self.after_id:
            try: self.after_cancel(self.after_id)
            except Exception: pass
        self.after_id = self.after(180, self.run_search)

    def refresh_all(self):
        stats = self.db.dashboard_stats()
        try:
            stats.update({
                "hosts": int(self.db.conn.execute("SELECT COUNT(*) FROM host_catalog").fetchone()[0]),
                "literature": int(self.db.conn.execute("SELECT COUNT(*) FROM literature_catalog").fetchone()[0]),
                "photos": int(self.db.conn.execute("SELECT COUNT(*) FROM attachments WHERE file_type='image'").fetchone()[0]),
                "questions": int(self.db.quiz_question_count()),
            })
        except Exception:
            pass
        for key, label in self.card_labels.items(): label.configure(text=str(stats.get(key, 0)))
        self.audit.delete(*self.audit.get_children())
        audit_rows = [
            ("no_photo", "Fotoğrafı olmayan kayıtlar", stats["no_photo"]),
            ("no_sources", "Kaynakçası olmayan kayıtlar", stats["no_sources"]),
            ("no_pathogen", "Etmeni belirtilmemiş kayıtlar", stats["no_pathogen"]),
            ("no_symptoms", "Belirtileri eksik kayıtlar", stats["no_symptoms"]),
            ("incomplete", "Tamamlanması gereken kayıtlar", stats["incomplete"]),
            ("complete", "Tamamlanmış kayıtlar", stats["complete"]),
            ("favorites", "Favori kayıtlar", stats["favorites"]),
        ]
        for iid, title, count in audit_rows: self.audit.insert("", "end", iid=iid, text=title, values=(count,))
        self.show_recent()

    def _fill_results(self, rows, title):
        self.results.delete(*self.results.get_children())
        self.result_title.configure(text=title)
        for row in rows:
            percent, status, _missing = record_quality(row, int(row["photo_count"] or 0))
            name = "{} — {}".format(row["scientific_name"] or "Etmen belirtilmemiş", row["disease_name"] or "Adsız kayıt")
            self.results.insert("", "end", iid=str(row["id"]), values=(name, "{} · %{}".format(status, percent), (row["updated_at"] or "")[:10]))
        self.status_var.set("{} kayıt gösteriliyor.".format(len(rows)))
        children = self.results.get_children()
        if children: self.results.selection_set(children[0])

    def show_recent(self):
        self._fill_results(self.db.dashboard_records("recent", limit=30), "Son düzenlenen kayıtlar")

    def run_search(self):
        query = self.search_var.get().strip()
        if not query:
            self.show_recent(); return
        self._fill_results(self.db.super_search(query, limit=100), "Arama sonuçları — “{}”".format(query))

    def show_audit_selection(self):
        selected = self.audit.selection()
        if not selected: return
        key = selected[0]
        titles = {
            "no_photo":"Fotoğrafı olmayan kayıtlar", "no_sources":"Kaynakçası olmayan kayıtlar",
            "no_pathogen":"Etmeni belirtilmemiş kayıtlar", "no_symptoms":"Belirtileri eksik kayıtlar",
            "incomplete":"Tamamlanması gereken kayıtlar", "complete":"Tamamlanmış kayıtlar", "favorites":"Favori kayıtlar"
        }
        self.search_var.set("")
        self._fill_results(self.db.dashboard_records(key, limit=500), titles.get(key, "Arşiv denetimi"))

    def open_selected_search(self):
        selection = self.results.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Önce bir kayıt seçin.", parent=self); return
        disease_id = int(selection[0])
        self.destroy()
        self.open_callback(disease_id)

    def _new(self):
        self.destroy(); self.new_callback()

    def _commands(self):
        if self.command_callback: self.command_callback()
