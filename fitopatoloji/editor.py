# -*- coding: utf-8 -*-
from .common import *
from .richtext import RichTextEditor


class DiseaseEditor(tk.Toplevel):
    """Kayıt girişini hızlandıran, tamamlanma ve değişiklik takibi yapan düzenleyici."""
    IMPORTANT_FIELDS = [
        "group_name", "scientific_name", "disease_name", "hosts",
        "affected_organs", "symptoms", "pathogen_features",
        "epidemiology", "differential_diagnosis", "cultural_control",
        "sources",
    ]

    def __init__(self, master, groups, initial=None, rich_initial=None, on_save=None):
        tk.Toplevel.__init__(self, master)
        self.title("Kayıt düzenle" if initial else "Yeni kayıt")
        self.transient(master)
        self.grab_set()
        self.initial = dict(initial) if initial else {}
        self.on_save = on_save
        self.rich_initial = rich_initial or {}
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
        notebook = ttk.Notebook(self)
        notebook.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 0))
        basic = ttk.Frame(notebook, padding=12)
        biology = ttk.Frame(notebook, padding=12)
        control = ttk.Frame(notebook, padding=12)
        distribution = ttk.Frame(notebook, padding=12)
        references = ttk.Frame(notebook, padding=12)
        notebook.add(basic, text="Temel bilgiler")
        notebook.add(biology, text="Belirti ve biyoloji")
        notebook.add(control, text="Mücadele")
        notebook.add(distribution, text="Dağılım")
        notebook.add(references, text="Kaynak ve not")

        basic.columnconfigure(1, weight=1)
        row = 0
        ttk.Label(basic, text="Taksonomik grup  •").grid(row=row, column=0, sticky="w", pady=5)
        self.vars["group_name"] = tk.StringVar(value=self.initial.get("group_name", "ASCOMYCOTA"))
        ttk.Combobox(basic, textvariable=self.vars["group_name"], values=groups, state="normal").grid(row=row, column=1, sticky="ew", pady=5)
        row += 1
        for field, label in [
            ("scientific_name", "Bilimsel ad  *"),
            ("synonyms", "Sinonimler / eski adlar"),
            ("disease_name", "Hastalık adı  *"),
            ("hosts", "Konukçular  •"),
            ("affected_organs", "Etkilenen organlar  •"),
        ]:
            ttk.Label(basic, text=label).grid(row=row, column=0, sticky="nw", pady=5)
            if field in ("hosts", "affected_organs"):
                editor = RichTextEditor(basic, value=self.initial.get(field, "") or "", formatting=self.rich_initial.get(field, {}), height=4)
                editor.grid(row=row, column=1, sticky="nsew", pady=5)
                self.texts[field] = editor
                basic.rowconfigure(row, weight=1)
            else:
                var = tk.StringVar(value=self.initial.get(field, "") or "")
                entry = tk.Entry(basic, textvariable=var, font=("Segoe UI", 9, "italic")) if field == "scientific_name" else ttk.Entry(basic, textvariable=var)
                entry.grid(row=row, column=1, sticky="ew", pady=5)
                self.vars[field] = var
            row += 1

        for frame, fields in [
            (biology, [("symptoms", "Belirtiler  •"), ("pathogen_features", "Etmenin özellikleri  •"), ("disease_cycle", "Hastalık döngüsü"), ("epidemiology", "Epidemiyoloji / uygun çevre koşulları  •"), ("differential_diagnosis", "Ayırıcı teşhis  •")]),
            (control, [("cultural_control", "Kültürel mücadele  •"), ("biological_control", "Biyolojik mücadele"), ("chemical_control", "Kimyasal mücadele / prensipler")]),
            (distribution, [("distribution_turkey", "Türkiye dağılımı"), ("distribution_world", "Dünya dağılımı"), ("climate_notes", "İklim / çevre notları")]),
            (references, [("sources", "Kaynaklar  •"), ("notes", "Kişisel notlar")]),
        ]:
            frame.columnconfigure(0, weight=1)
            for idx, (field, label) in enumerate(fields):
                frame.rowconfigure(idx*2+1, weight=1)
                ttk.Label(frame, text=label).grid(row=idx*2, column=0, sticky="w", pady=(5,2))
                editor = RichTextEditor(frame, value=self.initial.get(field, "") or "", formatting=self.rich_initial.get(field, {}), height=6)
                editor.grid(row=idx*2+1, column=0, sticky="nsew", pady=(0,7))
                self.texts[field] = editor

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
        self.change_var.set("Kaydedilmemiş değişiklikler var")
        self.update_completion()

    def _collect(self):
        data = {field: var.get().strip() for field, var in self.vars.items()}
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
        if self.on_save:
            self.on_save(data)
        self.dirty = False
        self.change_var.set("Kayıt kaydedildi")
        if close_after:
            self.destroy()
        return True
