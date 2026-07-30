# -*- coding: utf-8 -*-
"""2.0 RC2 arayüz bileşenleri.

Windows 7 uyumluluğu için yalnızca tkinter/ttk kullanır.
"""
from .common import tk, ttk, APP_NAME, APP_VERSION
from .theme import COLORS


class RibbonBar(ttk.Frame):
    """Office-benzeri, sekmeli fakat hafif bir komut şeridi."""
    def __init__(self, master, commands):
        ttk.Frame.__init__(self, master, style="Ribbon.TFrame")
        self.commands = commands
        self.notebook = ttk.Notebook(self, style="Ribbon.TNotebook")
        self.notebook.pack(fill="x", expand=True)
        self._build()

    def _button(self, parent, text, command, primary=False, width=None):
        style = "RibbonPrimary.TButton" if primary else "Ribbon.TButton"
        btn = ttk.Button(parent, text=text, command=command, style=style, width=width)
        btn.pack(side="left", padx=3, pady=5)
        return btn

    def _group(self, tab, title):
        outer = ttk.Frame(tab, style="Ribbon.TFrame")
        outer.pack(side="left", fill="y", padx=(5, 2), pady=3)
        body = ttk.Frame(outer, style="Ribbon.TFrame")
        body.pack(fill="both", expand=True)
        ttk.Label(outer, text=title, style="RibbonGroup.TLabel").pack(side="bottom", fill="x")
        return body

    def _build(self):
        specs = [
            ("DOSYA", [
                ("Kayıt", [("＋ Yeni", "new", True), ("✎ Düzenle", "edit", False), ("▣ Dosyayı Aç", "file", False)]),
                ("Çıktı", [("▣ PDF", "pdf", False), ("▤ Excel", "excel", False), ("▧ Monografi", "monograph", False)]),
                ("Güvenlik", [("⛁ Yedekle", "backup", False), ("⚙ Bakım", "maintenance", False)]),
            ]),
            ("KAYIT", [
                ("Görünüm", [("▤ İncele", "preview", True), ("◷ Geçmiş", "history", False), ("★ Favori", "favorite", False)]),
                ("Gezinme", [("◀ Önceki", "previous", False), ("Sonraki ▶", "next", False), ("⌕ Filtre", "filter", False)]),
                ("Düzen", [("✓ Toplu İşlem", "bulk", False), ("♲ Çöp Kutusu", "trash", False)]),
            ]),
            ("FOTOĞRAF", [
                ("Katalog", [("▦ Fotoğraf Yöneticisi", "photos", True), ("＋ Fotoğraf Ekle", "add_photo", False), ("▥ Galeri", "gallery", False)]),
                ("Araçlar", [("◉ Görsel Koleksiyon", "knowledge", False)]),
            ]),
            ("ANALİZ", [
                ("Bilimsel", [("⇄ Karşılaştır", "compare", True), ("✓ Teşhis", "diagnose", False), ("◉ Bilgi Ağı", "knowledge", False)]),
                ("Çalışma", [("⌂ Merkez", "dashboard", False), ("▦ Çalışma Alanı", "workspace", False), ("▥ İstatistik", "statistics", False)]),
            ]),
            ("YARDIM", [
                ("Uygulama", [("? Yardım", "help", True), ("! Sorun Bildir", "issue", False), ("⚙ Ayarlar", "settings", False), ("ⓘ Hakkında", "about", False)]),
                ("Hızlı Erişim", [("Ctrl+K Komut Paleti", "palette", False)]),
            ]),
        ]
        for tab_name, groups in specs:
            tab = ttk.Frame(self.notebook, style="Ribbon.TFrame")
            self.notebook.add(tab, text=tab_name)
            for group_name, buttons in groups:
                holder = self._group(tab, group_name)
                for label, key, primary in buttons:
                    command = self.commands.get(key)
                    if command:
                        self._button(holder, label, command, primary)


class ContextPanel(ttk.Frame):
    """Seçili kayıt için küçük, bağlamsal kalite ve eylem paneli."""
    def __init__(self, master, db, actions):
        ttk.Frame.__init__(self, master, style="Surface.TFrame", padding=12)
        self.db = db
        self.actions = actions
        self.title_var = tk.StringVar(value="Kayıt seçilmedi")
        self.score_var = tk.StringVar(value="—")
        self.suggestion_var = tk.StringVar(value="Bir hastalık seçtiğinizde kalite önerileri burada görünür.")
        ttk.Label(self, text="AKILLI ÖNERİLER", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(self, textvariable=self.title_var, style="ContextTitle.TLabel", wraplength=235).pack(anchor="w", pady=(4, 2))
        ttk.Label(self, textvariable=self.score_var, style="Score.TLabel").pack(anchor="w", pady=(2, 8))
        ttk.Separator(self).pack(fill="x", pady=(0, 8))
        ttk.Label(self, textvariable=self.suggestion_var, style="Surface.TLabel", wraplength=235, justify="left").pack(anchor="w")
        ttk.Button(self, text="Kaydı düzenle", style="Primary.TButton", command=actions.get("edit")).pack(fill="x", pady=(14, 4))
        ttk.Button(self, text="İncele", command=actions.get("preview")).pack(fill="x")

    @staticmethod
    def _completion(record):
        fields = ("scientific_name", "disease_name", "hosts", "symptoms", "pathogen_features", "epidemiology", "differential_diagnosis", "cultural_control", "chemical_control", "sources")
        filled = sum(1 for field in fields if str(record[field] or "").strip())
        return int(round(100.0 * filled / len(fields)))

    def show_record(self, record):
        if not record:
            self.clear()
            return
        score = self._completion(record)
        self.title_var.set(record["disease_name"] or record["scientific_name"] or "Adsız kayıt")
        self.score_var.set("Kayıt bütünlüğü: %{}".format(score))
        suggestions = []
        if not str(record["sources"] or "").strip(): suggestions.append("• Kaynakça eklenmeli")
        if not str(record["symptoms"] or "").strip(): suggestions.append("• Belirtiler bölümü eksik")
        if not str(record["epidemiology"] or "").strip(): suggestions.append("• Epidemiyoloji bilgisi eksik")
        try:
            photos = [x for x in self.db.attachments(record["id"]) if x["file_type"] == "photo"]
            if not photos: suggestions.append("• Fotoğraf eklenmemiş")
        except Exception:
            pass
        if not suggestions:
            suggestions.append("✓ Temel bölümler tamamlanmış görünüyor")
        self.suggestion_var.set("\n".join(suggestions[:5]))

    def clear(self):
        self.title_var.set("Kayıt seçilmedi")
        self.score_var.set("—")
        self.suggestion_var.set("Bir hastalık seçtiğinizde kalite önerileri burada görünür.")


class AboutDialog(tk.Toplevel):
    def __init__(self, master):
        tk.Toplevel.__init__(self, master)
        self.title("{} Hakkında".format(APP_NAME))
        self.geometry("520x390")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        frame = ttk.Frame(self, padding=24, style="Surface.TFrame")
        frame.pack(fill="both", expand=True)
        mark = tk.Canvas(frame, width=76, height=76, background=COLORS["surface"], highlightthickness=0)
        mark.pack()
        mark.create_oval(10, 8, 66, 64, fill=COLORS["primary"], outline="")
        mark.create_line(38, 58, 38, 72, fill=COLORS["primary"], width=5)
        mark.create_arc(18, 19, 48, 55, start=280, extent=150, style="arc", outline="#ffffff", width=4)
        mark.create_arc(29, 15, 60, 52, start=110, extent=150, style="arc", outline="#ffffff", width=4)
        ttk.Label(frame, text=APP_NAME, style="AboutTitle.TLabel").pack(pady=(6, 2))
        ttk.Label(frame, text="Sürüm {} — Release Candidate 2".format(APP_VERSION), style="Muted.TLabel").pack()
        ttk.Label(frame, text="Bitki hastalıkları için yerel, çevrimdışı ve araştırmacı odaklı bilimsel arşiv.", style="Surface.TLabel", wraplength=430, justify="center").pack(pady=(18, 8))
        ttk.Label(frame, text="Python • Tkinter • SQLite\nWindows 7 SP1 x64 uyumlu masaüstü yapı", style="Muted.TLabel", justify="center").pack()
        ttk.Separator(frame).pack(fill="x", pady=18)
        ttk.Label(frame, text="2.0 RC2; yeni komut şeridi, akıllı kayıt önerileri, tutarlı uygulama kimliği ve sağlamlaştırılmış açılış deneyimini içerir.", style="Surface.TLabel", wraplength=430, justify="center").pack()
        ttk.Button(frame, text="Kapat", style="Primary.TButton", command=self.destroy).pack(pady=(18, 0))


class SplashScreen(tk.Toplevel):
    def __init__(self, master):
        tk.Toplevel.__init__(self, master)
        self.overrideredirect(True)
        self.configure(background=COLORS["nav"])
        width, height = 520, 280
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry("{}x{}+{}+{}".format(width, height, x, y))
        canvas = tk.Canvas(self, width=520, height=280, background=COLORS["nav"], highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_oval(54, 52, 132, 130, fill=COLORS["primary"], outline="")
        canvas.create_line(93, 120, 93, 154, fill="#ffffff", width=6)
        canvas.create_arc(65, 64, 105, 112, start=285, extent=140, style="arc", outline="#ffffff", width=5)
        canvas.create_arc(82, 58, 122, 108, start=105, extent=145, style="arc", outline="#ffffff", width=5)
        canvas.create_text(156, 75, text="Fitopatoloji Arşivi", anchor="w", fill="#ffffff", font=("Segoe UI", 23, "bold"))
        canvas.create_text(157, 112, text="Bilimsel Masaüstü • 2.0 RC2", anchor="w", fill="#b9cad8", font=("Segoe UI", 11))
        canvas.create_line(55, 178, 465, 178, fill="#35536c")
        canvas.create_text(55, 207, text="Arşiv hazırlanıyor…", anchor="w", fill="#dfe9f0", font=("Segoe UI", 10))
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=410)
        self.progress.place(x=55, y=232)
        self.progress.start(12)
