# -*- coding: utf-8 -*-
from .common import *
from .richtext import RichTextEditor

class DiseaseEditor(tk.Toplevel):
    def __init__(self, master, groups, initial=None, rich_initial=None, on_save=None):
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
        self.rich_initial = rich_initial or {}
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
        distribution = ttk.Frame(notebook, padding=12)
        references = ttk.Frame(notebook, padding=12)
        notebook.add(basic, text="Temel bilgiler")
        notebook.add(biology, text="Belirti ve biyoloji")
        notebook.add(control, text="Mücadele")
        notebook.add(distribution, text="Dağılım")
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
                editor = RichTextEditor(
                    basic,
                    value=self.initial.get(field, "") or "",
                    formatting=self.rich_initial.get(field, {}),
                    height=4,
                )
                editor.grid(row=row, column=1, sticky="nsew", pady=5)
                self.texts[field] = editor
                basic.rowconfigure(row, weight=1)
            else:
                var = tk.StringVar(value=self.initial.get(field, "") or "")
                if field == "scientific_name":
                    entry = tk.Entry(basic, textvariable=var, font=("Segoe UI", 9, "italic"))
                    entry.grid(row=row, column=1, sticky="ew", pady=5)
                else:
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
            (distribution, [
                ("distribution_turkey", "Türkiye dağılımı"),
                ("distribution_world", "Dünya dağılımı"),
                ("climate_notes", "İklim / çevre notları"),
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
                editor = RichTextEditor(
                    frame,
                    value=self.initial.get(field, "") or "",
                    formatting=self.rich_initial.get(field, {}),
                    height=6,
                )
                editor.grid(row=idx * 2 + 1, column=0, sticky="nsew", pady=(0, 7))
                self.texts[field] = editor

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-s>", lambda _e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def save(self):
        data = {}
        for field, var in self.vars.items():
            data[field] = var.get().strip()
        rich_data = {}
        for field, editor in self.texts.items():
            data[field] = editor.get_value()
            formatting = editor.serialize()
            if formatting:
                rich_data[field] = formatting
        data["_rich_text"] = rich_data
        if not data.get("scientific_name"):
            messagebox.showwarning(APP_NAME, "Bilimsel ad boş bırakılamaz.", parent=self)
            return
        if not data.get("disease_name"):
            messagebox.showwarning(APP_NAME, "Hastalık adı veya açıklama boş bırakılamaz.", parent=self)
            return
        if self.on_save:
            self.on_save(data)
        self.destroy()



