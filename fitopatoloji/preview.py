# -*- coding: utf-8 -*-
"""Hastalık kaydını tek sayfada, salt okunur olarak inceleme penceresi."""
from .common import *
from .rich_utils import apply_to_text_widget, to_html
import html
import webbrowser

PREVIEW_FIELDS = [
    ("Etmen grubu", "group_name"), ("Sinonimler / eski adlar", "synonyms"),
    ("Konukçular", "hosts"), ("Etkilenen organlar", "affected_organs"),
    ("Belirtiler", "symptoms"), ("Etmenin özellikleri", "pathogen_features"),
    ("Hastalık döngüsü", "disease_cycle"),
    ("Epidemiyoloji / uygun çevre koşulları", "epidemiology"),
    ("Ayırıcı teşhis", "differential_diagnosis"),
    ("Türkiye dağılımı", "distribution_turkey"), ("Dünya dağılımı", "distribution_world"),
    ("İklim / çevre notları", "climate_notes"), ("Kültürel mücadele", "cultural_control"),
    ("Biyolojik mücadele", "biological_control"),
    ("Kimyasal mücadele / prensipler", "chemical_control"),
    ("Kaynaklar", "sources"), ("Kişisel notlar", "notes"),
]

class DiseasePreview(tk.Toplevel):
    def __init__(self, master, db, paths, disease_id, pdf_callback=None):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.db, self.paths, self.disease_id = db, paths, disease_id
        self.pdf_callback = pdf_callback
        self.record = db.get(disease_id)
        self.rich_map = db.rich_text(disease_id)
        self.photo_refs = []
        self.font_size = 10
        self.show_photos_var = tk.BooleanVar(value=True)
        if not self.record:
            self.destroy(); return
        self.title("İncele — {}".format(self.record["scientific_name"] or self.record["disease_name"]))
        self.geometry("980x760"); self.minsize(720, 520); self.transient(master)
        self._build_ui()
        # Windows/Tk ilk çiziminde boş görünme sorununu önlemek için pencere
        # yerleştikten sonra iki aşamalı çizim yapılır.
        self.after_idle(self.render)
        self.after(100, self.render)

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(10, 8)); toolbar.pack(fill="x")
        ttk.Button(toolbar, text="PDF olarak kaydet", command=self.save_pdf).pack(side="left")
        ttk.Button(toolbar, text="HTML olarak kaydet", command=self.save_html).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Yazdır", command=self.print_preview).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Checkbutton(toolbar, text="Fotoğrafları göster", variable=self.show_photos_var, command=self.render).pack(side="left")
        ttk.Button(toolbar, text="A−", width=4, command=self.font_smaller).pack(side="right")
        ttk.Button(toolbar, text="A+", width=4, command=self.font_larger).pack(side="right", padx=(0,4))
        ttk.Button(toolbar, text="Kapat", command=self.destroy).pack(side="right", padx=(0,12))
        frame = ttk.Frame(self, padding=(12,0,12,12)); frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, wrap="word", relief="flat", borderwidth=0, padx=34, pady=24,
                            background="#ffffff", foreground="#17202a", cursor="arrow")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        self.text.bind("<Control-MouseWheel>", self._ctrl_wheel)
        self.bind("<Control-plus>", lambda _e: self.font_larger())
        self.bind("<Control-minus>", lambda _e: self.font_smaller())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _ctrl_wheel(self, event):
        self.font_larger() if event.delta > 0 else self.font_smaller(); return "break"

    def _configure_tags(self):
        size = self.font_size
        self.text.tag_configure("title", font=("Segoe UI", size+8, "bold italic"), spacing3=4)
        self.text.tag_configure("subtitle", font=("Segoe UI", size+2), foreground="#52606d", spacing3=14)
        self.text.tag_configure("meta", font=("Segoe UI", max(8,size-1)), foreground="#6b7785", spacing3=12)
        self.text.tag_configure("heading", font=("Segoe UI", size+1, "bold"), foreground="#1f6b4f", spacing1=14, spacing3=5)
        self.text.tag_configure("body", font=("Segoe UI", size), lmargin1=4, lmargin2=4, spacing2=3, spacing3=5)
        self.text.tag_configure("reference", font=("Segoe UI", max(8,size-1)), lmargin1=18, lmargin2=18, spacing2=2)
        self.text.tag_configure("divider", foreground="#cbd5df", spacing1=6, spacing3=6)
        self.text.tag_configure("photo_heading", font=("Segoe UI", size+1, "bold"), foreground="#1f6b4f", spacing1=18, spacing3=8)

    def render(self):
        if not self.winfo_exists(): return
        self.photo_refs = []
        self.text.configure(state="normal"); self.text.delete("1.0", "end"); self._configure_tags()
        r = self.record
        self.text.insert("end", (r["scientific_name"] or "Adsız kayıt")+"\n", "title")
        if r["disease_name"]: self.text.insert("end", r["disease_name"]+"\n", "subtitle")
        self.text.insert("end", "Son güncelleme: {}\n".format(r["updated_at"] or "—"), "meta")
        self.text.insert("end", "─"*90+"\n", "divider")
        for title, field in PREVIEW_FIELDS:
            value = (r[field] or "").strip()
            if not value: continue
            self.text.insert("end", title.upper()+"\n", "heading")
            start = self.text.index("end-1c")
            self.text.insert("end", value, "body")
            apply_to_text_widget(self.text, value, self.rich_map.get(field, {}), start, self.font_size)
            self.text.insert("end", "\n")
        refs = list(self.db.references(self.disease_id))
        if refs:
            self.text.insert("end", "YAPILANDIRILMIŞ KAYNAKÇA\n", "heading")
            for idx, ref in enumerate(refs,1):
                line="[{}] {}: {}".format(idx,ref["source_type"],ref["citation"])
                if ref["identifier"]: line += " — "+ref["identifier"]
                self.text.insert("end", line+"\n", "reference")
        if self.show_photos_var.get(): self._insert_photos()
        self.text.insert("end", "\nBu görünüm salt okunurdur; veritabanındaki kayıt değiştirilmemiştir.\n", "meta")
        self.text.configure(state="disabled"); self.text.see("1.0")
        self.update_idletasks()

    def _insert_photos(self):
        if not PIL_AVAILABLE: return
        rows=[]
        for row in list(self.db.image_attachments(self.disease_id)):
            path=os.path.join(self.paths.base,row["relative_path"])
            if not os.path.isfile(path): continue
            try:
                with Image.open(path) as src:
                    image=src.convert("RGB")
                    # Nizami katalog görünümü: oran korunur, sabit 220x150 tuvale ortalanır.
                    image.thumbnail((210,140), Image.LANCZOS)
                    tile=Image.new("RGB",(220,150),"white")
                    tile.paste(image,((220-image.width)//2,(150-image.height)//2))
                rows.append((row,ImageTk.PhotoImage(tile)))
            except Exception: pass
        if not rows: return
        self.text.insert("end", "FOTOĞRAFLAR\n", "photo_heading")
        for i,(row,photo) in enumerate(rows):
            self.photo_refs.append(photo); self.text.image_create("end",image=photo)
            self.text.insert("end", "   " if i%3 != 2 else "\n")
        if len(rows)%3: self.text.insert("end","\n")
        captions=[(row["description"] or os.path.basename(row["relative_path"]).split("_",1)[-1]).strip() for row,_ in rows]
        if any(captions): self.text.insert("end", " • ".join(captions)+"\n", "meta")
        self.text.insert("end","\n")

    def font_larger(self): self.font_size=min(18,self.font_size+1); self.render()
    def font_smaller(self): self.font_size=max(8,self.font_size-1); self.render()
    def save_pdf(self):
        if self.pdf_callback: self.pdf_callback()

    def _html_document(self):
        r=self.record
        chunks=["<!doctype html><html><head><meta charset='utf-8'>",
        "<title>{}</title>".format(html.escape(r["scientific_name"] or APP_NAME)),
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:32px auto;color:#17202a;line-height:1.55;padding:0 24px}h1{margin-bottom:0;color:#194f3b}h2{font-size:16px;color:#1f6b4f;border-bottom:1px solid #d9e2e8;padding-bottom:5px;margin-top:26px}.subtitle{font-size:18px;color:#52606d;margin-top:4px}.meta{color:#6b7785;font-size:12px}.photos{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}.photo-card{border:1px solid #d9e2e8;padding:8px;border-radius:8px}.photo{width:100%;height:160px;object-fit:contain;background:white}.caption{color:#6b7785;font-size:12px;margin-top:6px}.section{white-space:normal}</style></head><body>",
        "<h1><i>{}</i></h1>".format(html.escape(r["scientific_name"] or "Adsız kayıt")),
        "<div class='subtitle'>{}</div>".format(html.escape(r["disease_name"] or "")),
        "<div class='meta'>Son güncelleme: {}</div>".format(html.escape(r["updated_at"] or "—"))]
        for title,field in PREVIEW_FIELDS:
            value=(r[field] or "").strip()
            if value: chunks.append("<h2>{}</h2><div class='section'>{}</div>".format(html.escape(title),to_html(value,self.rich_map.get(field,{}))))
        refs=list(self.db.references(self.disease_id))
        if refs:
            chunks.append("<h2>Yapılandırılmış kaynakça</h2><ol>")
            for ref in refs:
                line="{}: {}".format(ref["source_type"],ref["citation"])
                if ref["identifier"]: line+=" — "+ref["identifier"]
                chunks.append("<li>{}</li>".format(html.escape(line)))
            chunks.append("</ol>")
        if self.show_photos_var.get():
            cards=[]
            for row in self.db.image_attachments(self.disease_id):
                path=os.path.join(self.paths.base,row["relative_path"])
                if os.path.isfile(path):
                    uri="file:///"+os.path.abspath(path).replace("\\","/")
                    caption=html.escape(row["description"] or os.path.basename(row["relative_path"]).split("_",1)[-1])
                    cards.append("<div class='photo-card'><img class='photo' src='{}'><div class='caption'>{}</div></div>".format(html.escape(uri,quote=True),caption))
            if cards: chunks.append("<h2>Fotoğraflar</h2><div class='photos'>{}</div>".format("".join(cards)))
        chunks.append("<p class='meta'>Bu görünüm {} {} ile oluşturuldu.</p></body></html>".format(APP_NAME,APP_VERSION))
        return "".join(chunks)

    def save_html(self):
        safe_name=re.sub(r"[^A-Za-z0-9_-]+","_",self.record["scientific_name"] or "hastalik").strip("_")
        output=filedialog.asksaveasfilename(title="HTML olarak kaydet",initialdir=self.paths.exports,initialfile=safe_name+".html",defaultextension=".html",filetypes=[("HTML dosyası","*.html")])
        if not output:return
        try:
            with open(output,"w",encoding="utf-8") as h:h.write(self._html_document())
            messagebox.showinfo(APP_NAME,"HTML dosyası oluşturuldu:\n{}".format(output),parent=self)
        except Exception as exc: messagebox.showerror(APP_NAME,"HTML oluşturulamadı:\n{}".format(exc),parent=self)

    def print_preview(self):
        temp=os.path.join(tempfile.gettempdir(),"fitopatoloji_onizleme_{}.html".format(self.disease_id))
        try:
            with open(temp,"w",encoding="utf-8") as h:h.write(self._html_document())
            webbrowser.open("file:///"+temp.replace("\\","/"))
            messagebox.showinfo(APP_NAME,"Yazdırmak için tarayıcıda Ctrl+P kullanın.",parent=self)
        except Exception as exc: messagebox.showerror(APP_NAME,"Yazdırma önizlemesi açılamadı:\n{}".format(exc),parent=self)
