# -*- coding: utf-8 -*-
"""Hastalık kaydını tek sayfada, salt okunur olarak inceleme penceresi."""
from .common import *
import html
import webbrowser


PREVIEW_FIELDS = [
    ("Etmen grubu", "group_name"),
    ("Sinonimler / eski adlar", "synonyms"),
    ("Konukçular", "hosts"),
    ("Etkilenen organlar", "affected_organs"),
    ("Belirtiler", "symptoms"),
    ("Etmenin özellikleri", "pathogen_features"),
    ("Hastalık döngüsü", "disease_cycle"),
    ("Epidemiyoloji / uygun çevre koşulları", "epidemiology"),
    ("Ayırıcı teşhis", "differential_diagnosis"),
    ("Türkiye dağılımı", "distribution_turkey"),
    ("Dünya dağılımı", "distribution_world"),
    ("İklim / çevre notları", "climate_notes"),
    ("Kültürel mücadele", "cultural_control"),
    ("Biyolojik mücadele", "biological_control"),
    ("Kimyasal mücadele / prensipler", "chemical_control"),
    ("Kaynaklar", "sources"),
    ("Kişisel notlar", "notes"),
]


class DiseasePreview(tk.Toplevel):
    def __init__(self, master, db, paths, disease_id, pdf_callback=None):
        tk.Toplevel.__init__(self, master)
        self.db = db
        self.paths = paths
        self.disease_id = disease_id
        self.pdf_callback = pdf_callback
        self.record = db.get(disease_id)
        self.photo_refs = []
        self.font_size = 10
        self.show_photos_var = tk.BooleanVar(value=True)

        if not self.record:
            self.destroy()
            return

        self.title("İncele — {}".format(self.record["scientific_name"] or self.record["disease_name"]))
        self.geometry("980x760")
        self.minsize(720, 520)
        self.transient(master)
        self._build_ui()
        self.render()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="PDF olarak kaydet", command=self.save_pdf).pack(side="left")
        ttk.Button(toolbar, text="HTML olarak kaydet", command=self.save_html).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Yazdır", command=self.print_preview).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Checkbutton(
            toolbar, text="Fotoğrafları göster", variable=self.show_photos_var,
            command=self.render
        ).pack(side="left")
        ttk.Button(toolbar, text="A−", width=4, command=self.font_smaller).pack(side="right")
        ttk.Button(toolbar, text="A+", width=4, command=self.font_larger).pack(side="right", padx=(0, 4))
        ttk.Button(toolbar, text="Kapat", command=self.destroy).pack(side="right", padx=(0, 12))

        frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            frame, wrap="word", relief="flat", borderwidth=0,
            padx=34, pady=24, background="#ffffff", foreground="#17202a",
            cursor="arrow"
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.text.bind("<Control-mousewheel>", self._ctrl_wheel)
        self.bind("<Control-plus>", lambda _e: self.font_larger())
        self.bind("<Control-minus>", lambda _e: self.font_smaller())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _ctrl_wheel(self, event):
        if event.delta > 0:
            self.font_larger()
        else:
            self.font_smaller()
        return "break"

    def _configure_tags(self):
        size = self.font_size
        self.text.tag_configure("title", font=("Segoe UI", size + 8, "bold"), spacing3=4)
        self.text.tag_configure("subtitle", font=("Segoe UI", size + 2, "italic"), foreground="#52606d", spacing3=14)
        self.text.tag_configure("meta", font=("Segoe UI", max(8, size - 1)), foreground="#6b7785", spacing3=12)
        self.text.tag_configure("heading", font=("Segoe UI", size + 1, "bold"), foreground="#1f6b4f", spacing1=14, spacing3=5)
        self.text.tag_configure("body", font=("Segoe UI", size), lmargin1=4, lmargin2=4, spacing2=3, spacing3=5)
        self.text.tag_configure("reference", font=("Segoe UI", max(8, size - 1)), lmargin1=18, lmargin2=18, spacing2=2)
        self.text.tag_configure("divider", foreground="#cbd5df", spacing1=6, spacing3=6)

    def render(self):
        self.photo_refs = []
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self._configure_tags()
        r = self.record
        self.text.insert("end", (r["scientific_name"] or "Adsız kayıt") + "\n", "title")
        if r["disease_name"]:
            self.text.insert("end", r["disease_name"] + "\n", "subtitle")
        meta = "Son güncelleme: {}".format(r["updated_at"] or "—")
        self.text.insert("end", meta + "\n", "meta")
        self.text.insert("end", "─" * 90 + "\n", "divider")

        if self.show_photos_var.get():
            self._insert_photos()

        for title, field in PREVIEW_FIELDS:
            value = (r[field] or "").strip()
            if not value:
                continue
            self.text.insert("end", title.upper() + "\n", "heading")
            self.text.insert("end", value + "\n", "body")

        refs = list(self.db.references(self.disease_id))
        if refs:
            self.text.insert("end", "YAPILANDIRILMIŞ KAYNAKÇA\n", "heading")
            for idx, ref in enumerate(refs, 1):
                line = "[{}] {}: {}".format(idx, ref["source_type"], ref["citation"])
                if ref["identifier"]:
                    line += " — " + ref["identifier"]
                self.text.insert("end", line + "\n", "reference")

        self.text.insert("end", "\nBu görünüm salt okunurdur; veritabanındaki kayıt değiştirilmemiştir.\n", "meta")
        self.text.configure(state="disabled")

    def _insert_photos(self):
        if not PIL_AVAILABLE:
            return
        photos = list(self.db.image_attachments(self.disease_id))[:4]
        inserted = False
        for row in photos:
            path = os.path.join(self.paths.base, row["relative_path"])
            if not os.path.isfile(path):
                continue
            try:
                image = Image.open(path).convert("RGB")
                image.thumbnail((720, 360), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.photo_refs.append(photo)
                self.text.image_create("end", image=photo)
                self.text.insert("end", "\n")
                description = (row["description"] or "").strip()
                if description:
                    self.text.insert("end", description + "\n", "meta")
                inserted = True
            except Exception:
                pass
        if inserted:
            self.text.insert("end", "\n")

    def font_larger(self):
        self.font_size = min(18, self.font_size + 1)
        self.render()

    def font_smaller(self):
        self.font_size = max(8, self.font_size - 1)
        self.render()

    def save_pdf(self):
        if self.pdf_callback:
            self.pdf_callback()

    def _html_document(self):
        r = self.record
        chunks = [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<title>{}</title>".format(html.escape(r["scientific_name"] or APP_NAME)),
            "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;color:#17202a;line-height:1.55;padding:0 24px}h1{margin-bottom:0;color:#194f3b}h2{font-size:16px;color:#1f6b4f;border-bottom:1px solid #d9e2e8;padding-bottom:5px;margin-top:26px}.subtitle{font-size:18px;color:#52606d;margin-top:4px}.meta{color:#6b7785;font-size:12px}.photo{max-width:100%;max-height:420px;margin:14px 0;border-radius:8px}.caption{color:#6b7785;font-size:12px;margin-top:-8px}pre{white-space:pre-wrap;font-family:inherit}</style>",
            "</head><body>",
            "<h1><i>{}</i></h1>".format(html.escape(r["scientific_name"] or "Adsız kayıt")),
            "<div class='subtitle'>{}</div>".format(html.escape(r["disease_name"] or "")),
            "<div class='meta'>Son güncelleme: {}</div>".format(html.escape(r["updated_at"] or "—")),
        ]
        if self.show_photos_var.get():
            for row in list(self.db.image_attachments(self.disease_id))[:4]:
                path = os.path.join(self.paths.base, row["relative_path"])
                if os.path.isfile(path):
                    try:
                        uri = "file:///" + os.path.abspath(path).replace("\\", "/")
                        chunks.append("<img class='photo' src='{}'>".format(html.escape(uri, quote=True)))
                        if row["description"]:
                            chunks.append("<div class='caption'>{}</div>".format(html.escape(row["description"])))
                    except Exception:
                        pass
        for title, field in PREVIEW_FIELDS:
            value = (r[field] or "").strip()
            if value:
                chunks.append("<h2>{}</h2><pre>{}</pre>".format(html.escape(title), html.escape(value)))
        refs = list(self.db.references(self.disease_id))
        if refs:
            chunks.append("<h2>Yapılandırılmış kaynakça</h2><ol>")
            for ref in refs:
                line = "{}: {}".format(ref["source_type"], ref["citation"])
                if ref["identifier"]:
                    line += " — " + ref["identifier"]
                chunks.append("<li>{}</li>".format(html.escape(line)))
            chunks.append("</ol>")
        chunks.append("<p class='meta'>Bu görünüm {} {} ile oluşturuldu.</p></body></html>".format(APP_NAME, APP_VERSION))
        return "".join(chunks)

    def save_html(self):
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", self.record["scientific_name"] or "hastalik").strip("_")
        output = filedialog.asksaveasfilename(
            title="HTML önizlemeyi kaydet", initialdir=self.paths.exports,
            initialfile=(safe_name or "hastalik") + ".html",
            defaultextension=".html", filetypes=[("HTML dosyası", "*.html")], parent=self
        )
        if not output:
            return
        try:
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(self._html_document())
            messagebox.showinfo(APP_NAME, "HTML dosyası oluşturuldu:\n{}".format(output), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "HTML oluşturulamadı:\n{}".format(exc), parent=self)

    def print_preview(self):
        try:
            fd, path = tempfile.mkstemp(prefix="fitopatoloji_onizleme_", suffix=".html")
            os.close(fd)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._html_document())
            webbrowser.open("file:///" + path.replace("\\", "/"))
            messagebox.showinfo(
                APP_NAME,
                "Önizleme tarayıcıda açıldı. Tarayıcının Yazdır komutunu kullanabilirsiniz.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Yazdırma önizlemesi açılamadı:\n{}".format(exc), parent=self)
