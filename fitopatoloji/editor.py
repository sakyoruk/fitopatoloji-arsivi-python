# -*- coding: utf-8 -*-
from .common import *
from .richtext import RichTextEditor
from .catalogs import AGENT_GROUPS, TAXON_RANKS, HostCatalog
from .scientific import scientific_name_suggestion


def merge_host_ids(existing, added):
    """Return host ids in stable order without duplicates."""
    result = []
    seen = set()
    for value in list(existing or []) + list(added or []):
        try:
            host_id = int(value)
        except (TypeError, ValueError):
            continue
        if host_id not in seen:
            seen.add(host_id)
            result.append(host_id)
    return result


class DiseaseEditor(tk.Toplevel):
    """Kayıt girişini hızlandıran, tamamlanma ve değişiklik takibi yapan düzenleyici."""
    IMPORTANT_FIELDS = [
        "group_name", "scientific_name", "disease_name", "hosts", "content_body",
    ]

    def __init__(self, master, groups, initial=None, rich_initial=None, on_save=None, on_draft=None, draft_key=None, on_saved=None, database=None):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.title("Kayıt düzenle" if initial else "Yeni kayıt")
        self.transient(master)
        self.grab_set()
        self.initial = dict(initial) if initial else {}
        self.on_save = on_save
        self.rich_initial = rich_initial or {}
        self.on_draft = on_draft
        self.draft_key = draft_key
        self.on_saved = on_saved
        self.db = database
        self.selected_host_relations = list(self.initial.get("_host_relations", [])) if isinstance(self.initial, dict) else []
        if not self.selected_host_relations:
            self.selected_host_relations = [{"host_id": int(x), "relation_type": "Doğal konukçu", "scope_type": "Doğrudan", "relation_note": "", "is_excluded": 0} for x in self.initial.get("_host_ids", [])]
        self.selected_host_ids = [int(r.get("host_id")) for r in self.selected_host_relations]
        self._draft_job = None
        self.vars = {}
        self.texts = {}
        self.dirty = False
        self._loading = True

        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(980, max(720, screen_w - 80))
        win_h = min(760, max(520, screen_h - 120))
        self.geometry("{}x{}+{}+{}".format(
            win_w, win_h, max(0, (screen_w-win_w)//2), max(0, (screen_h-win_h)//2)
        ))
        self.minsize(min(720, win_w), min(520, win_h))

        self._build_header()
        self._build_footer()
        self._build_form(groups)
        self._bind_change_tracking()
        self._loading = False
        self.update_completion()

        self.bind("<Escape>", lambda _e: self.request_close())
        self.bind("<Control-s>", lambda _e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.request_close)

    def _build_header(self):
        header = ttk.Frame(self, padding=(12, 10, 12, 8))
        header.pack(side="top", fill="x")
        left = ttk.Frame(header)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Akıllı Kayıt Düzenleyici", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.completion_var = tk.StringVar(value="Kayıt tamamlanma durumu: %0")
        ttk.Label(left, textvariable=self.completion_var).pack(anchor="w", pady=(2, 0))
        self.progress = ttk.Progressbar(header, maximum=100, length=220)
        self.progress.pack(side="right", padx=(12, 0))

    def _build_footer(self):
        footer = ttk.Frame(self, padding=(10, 8, 10, 10))
        footer.pack(side="bottom", fill="x")
        self.change_var = tk.StringVar(value="Değişiklik yok")
        ttk.Label(footer, textvariable=self.change_var).pack(side="left")
        ttk.Button(footer, text="İptal", command=self.request_close).pack(side="right", padx=(6, 0))
        ttk.Button(footer, text="Kaydet", style="Primary.TButton", command=self.save).pack(side="right")

    def _build_form(self, groups):
        # RC10.9: Sekmeli ve parçalı kayıt formu yerine tek akışlı temel bilgiler + birleşik zengin metin.
        outer = ttk.Frame(self, padding=(10, 0, 10, 0))
        outer.pack(side="top", fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        basic = ttk.LabelFrame(outer, text="Temel bilgiler", padding=10)
        basic.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        basic.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(basic, text="Taksonomik grup  •").grid(row=row, column=0, sticky="w", pady=4)
        self.vars["group_name"] = tk.StringVar(value=self.initial.get("group_name", "ASCOMYCOTA"))
        ttk.Combobox(basic, textvariable=self.vars["group_name"], values=groups, state="normal").grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        for field, label in (("scientific_name", "Bilimsel ad  *"), ("synonyms", "Sinonimler / eski adlar"), ("disease_name", "Hastalık adı  *")):
            ttk.Label(basic, text=label).grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=self.initial.get(field, "") or "")
            entry = tk.Entry(basic, textvariable=var, font=("Segoe UI", 9, "italic")) if field == "scientific_name" else ttk.Entry(basic, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.vars[field] = var
            row += 1

        ttk.Label(basic, text="Konukçular  •").grid(row=row, column=0, sticky="nw", pady=4)
        host_box = ttk.Frame(basic)
        host_box.grid(row=row, column=1, sticky="nsew", pady=4)
        host_box.columnconfigure(0, weight=1); host_box.rowconfigure(1, weight=1)
        host_toolbar = ttk.Frame(host_box); host_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(host_toolbar, text="Konukçu ekle", style="Primary.TButton", command=self._select_hosts).pack(side="left")
        ttk.Button(host_toolbar, text="İlişkiyi düzenle", command=self._edit_selected_host_relation).pack(side="left", padx=(5, 0))
        ttk.Button(host_toolbar, text="Seçileni kaldır", command=self._remove_selected_hosts).pack(side="left", padx=(5, 0))
        self.host_count_var = tk.StringVar(value="0 konukçu"); ttk.Label(host_toolbar, textvariable=self.host_count_var).pack(side="right")
        self.host_tree = ttk.Treeview(host_box, columns=("common", "scientific", "level", "relation", "scope", "excluded"), show="headings", height=3, selectmode="extended")
        for key, text, width in (("common", "Türkçe ad", 125), ("scientific", "Bilimsel ad", 180), ("level", "Düzey", 65), ("relation", "İlişki", 115), ("scope", "Kapsam", 95), ("excluded", "Durum", 60)):
            self.host_tree.heading(key, text=text); self.host_tree.column(key, width=width, anchor="w")
        host_scroll = ttk.Scrollbar(host_box, orient="vertical", command=self.host_tree.yview)
        self.host_tree.configure(yscrollcommand=host_scroll.set)
        self.host_tree.grid(row=1, column=0, sticky="nsew"); host_scroll.grid(row=1, column=1, sticky="ns")
        self.hosts_var = tk.StringVar(value=self.initial.get("hosts", "") or "")
        self._refresh_selected_hosts()
        row += 1
        ttk.Label(basic, text="Etiketler").grid(row=row, column=0, sticky="w", pady=4)
        self.vars["_tags"] = tk.StringVar(value=self.initial.get("_tags", "") or "")
        ttk.Entry(basic, textvariable=self.vars["_tags"]).grid(row=row, column=1, sticky="ew", pady=4)

        content = ttk.LabelFrame(outer, text="Hastalık bilgileri", padding=8)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1); content.rowconfigure(1, weight=1)
        ttk.Label(content, text="Belirti, etmenin özellikleri, hastalık döngüsü, epidemiyoloji, ayırıcı teşhis, mücadele, dağılım ve çevre koşullarını tek metin içinde düzenleyin.", wraplength=900).grid(row=0, column=0, sticky="w", pady=(0, 5))
        editor = RichTextEditor(content, value=self.initial.get("content_body", "") or "", formatting=self.rich_initial.get("content_body", {}), height=18)
        editor.grid(row=1, column=0, sticky="nsew")
        self.texts["content_body"] = editor

    def _bind_change_tracking(self):
        for var in self.vars.values():
            var.trace_add("write", lambda *_args: self.mark_dirty())
        for editor in self.texts.values():
            try:
                editor.text.bind("<<Modified>>", self._text_modified, add="+")
                editor.text.edit_modified(False)
            except Exception:
                pass

    def _text_modified(self, event):
        try:
            if event.widget.edit_modified():
                event.widget.edit_modified(False)
                self.mark_dirty()
        except Exception:
            self.mark_dirty()

    def mark_dirty(self):
        if self._loading:
            return
        self.dirty = True
        self.change_var.set("Kaydedilmemiş değişiklikler var • Taslak hazırlanıyor")
        self.update_completion()
        if self.on_draft:
            if self._draft_job:
                try: self.after_cancel(self._draft_job)
                except Exception: pass
            self._draft_job = self.after(1200, self._autosave_draft)


    def _autosave_draft(self):
        self._draft_job = None
        if not self.dirty or not self.on_draft: return
        data = self._collect(); rich = data.pop("_rich_text", {})
        disease_id = self.initial.get("id") if isinstance(self.initial, dict) else None
        if disease_id is None and isinstance(self.draft_key, str) and self.draft_key.startswith("edit:"):
            try:
                disease_id = int(self.draft_key.split(":", 1)[1])
            except (TypeError, ValueError):
                disease_id = None
        self.on_draft(self.draft_key, disease_id, data, rich)
        self.change_var.set("Taslak otomatik kaydedildi")

    def _collect(self):
        data = {field: var.get().strip() for field, var in self.vars.items()}
        data["hosts"] = self.hosts_var.get().strip() if hasattr(self, "hosts_var") else data.get("hosts", "")
        data["_host_ids"] = list(self.selected_host_ids)
        data["_host_relations"] = [dict(r) for r in self.selected_host_relations]
        rich_data = {}
        for field, editor in self.texts.items():
            data[field] = editor.get_value().strip()
            formatting = editor.serialize()
            if formatting:
                rich_data[field] = formatting
        data["_rich_text"] = rich_data
        return data

    def update_completion(self):
        data = self._collect()
        filled = sum(1 for field in self.IMPORTANT_FIELDS if (data.get(field) or "").strip())
        percent = int(round(100.0 * filled / len(self.IMPORTANT_FIELDS)))
        self.progress["value"] = percent
        self.completion_var.set("Kayıt tamamlanma durumu: %{}  (* zorunlu, • önerilen)".format(percent))

    def request_close(self):
        if self.dirty:
            answer = messagebox.askyesnocancel(
                APP_NAME,
                "Kaydedilmemiş değişiklikler var. Kaydetmek ister misiniz?",
                parent=self,
            )
            if answer is None:
                return
            if answer:
                if not self.save(close_after=False):
                    return
        self.destroy()

    def save(self, close_after=True):
        data = self._collect()
        if not data.get("scientific_name"):
            messagebox.showwarning(APP_NAME, "Bilimsel ad boş bırakılamaz.", parent=self)
            return False
        if not data.get("disease_name"):
            messagebox.showwarning(APP_NAME, "Hastalık adı veya açıklama boş bırakılamaz.", parent=self)
            return False
        suggested, notes = scientific_name_suggestion(data.get("scientific_name"))
        if notes and suggested != data.get("scientific_name"):
            message = "Bilimsel ad için yazım önerisi:\n\n{}\n\n{}\n\nÖneri uygulansın mı?".format("\n".join("• "+x for x in notes), suggested)
            if messagebox.askyesno(APP_NAME, message, parent=self):
                data["scientific_name"] = suggested
                if "scientific_name" in self.vars: self.vars["scientific_name"].set(suggested)
        if self.on_save:
            self.on_save(data)
        if self.on_saved: self.on_saved(self.draft_key)
        self.dirty = False
        self.change_var.set("Kayıt kaydedildi")
        if close_after:
            self.destroy()
        return True
