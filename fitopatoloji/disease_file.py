# -*- coding: utf-8 -*-
"""Dijital Hastalık Dosyası görünümü."""
from .common import *
from .rich_utils import apply_to_text_widget

CARD_FIELDS = [
    ("GENEL BİLGİLER", [("Etmen grubu", "group_name"), ("Sinonimler", "synonyms")]),
    ("KONUKÇU VE ORGANLAR", [("Konukçular", "hosts"), ("Etkilenen organlar", "affected_organs")]),
    ("BELİRTİLER VE ETMEN", [("Belirtiler", "symptoms"), ("Etmenin özellikleri", "pathogen_features")]),
    ("HASTALIK DÖNGÜSÜ VE EPİDEMİYOLOJİ", [("Hastalık döngüsü", "disease_cycle"), ("Epidemiyoloji", "epidemiology")]),
    ("TANI VE MÜCADELE", [("Ayırıcı teşhis", "differential_diagnosis"), ("Kültürel mücadele", "cultural_control"),
                           ("Biyolojik mücadele", "biological_control"), ("Kimyasal mücadele", "chemical_control")]),
    ("DAĞILIM VE ÇEVRE", [("Türkiye dağılımı", "distribution_turkey"), ("Dünya dağılımı", "distribution_world"),
                           ("İklim / çevre notları", "climate_notes")]),
    ("KAYNAKLAR VE NOTLAR", [("Kaynaklar", "sources"), ("Kişisel notlar", "notes")]),
]

class DiseaseFile(tk.Toplevel):
    def __init__(self, master, db, paths, disease_id, on_edit=None, on_preview=None, on_pdf=None, on_photos=None):
        tk.Toplevel.__init__(self, master)
        self.db, self.paths, self.disease_id = db, paths, disease_id
        self.on_edit, self.on_preview, self.on_pdf, self.on_photos = on_edit, on_preview, on_pdf, on_photos
        self.record = db.get(disease_id)
        self.rich = db.rich_text(disease_id)
        self.photo_refs = []
        self.title("Dijital Hastalık Dosyası")
        self.geometry("1280x800")
        self.minsize(980, 620)
        self.transient(master)
        self._build()
        self.after_idle(self.render)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build(self):
        top = ttk.Frame(self, padding=(18, 14)); top.pack(fill="x")
        titlebox = ttk.Frame(top); titlebox.pack(side="left", fill="x", expand=True)
        self.title_var = tk.StringVar(); self.subtitle_var = tk.StringVar(); self.meta_var = tk.StringVar()
        ttk.Label(titlebox, textvariable=self.title_var, font=("Segoe UI", 20, "bold italic")).pack(anchor="w")
        ttk.Label(titlebox, textvariable=self.subtitle_var, font=("Segoe UI", 12)).pack(anchor="w", pady=(2,0))
        ttk.Label(titlebox, textvariable=self.meta_var, style="Muted.TLabel").pack(anchor="w", pady=(5,0))
        buttons = ttk.Frame(top); buttons.pack(side="right", anchor="n")
        ttk.Button(buttons, text="Düzenle", style="Primary.TButton", command=self._edit).pack(side="left", padx=3)
        ttk.Button(buttons, text="İncele", command=self._preview).pack(side="left", padx=3)
        ttk.Button(buttons, text="PDF", command=self._pdf).pack(side="left", padx=3)
        ttk.Button(buttons, text="Fotoğraflar", command=self._photos).pack(side="left", padx=3)

        body = ttk.Panedwindow(self, orient="horizontal"); body.pack(fill="both", expand=True, padx=14, pady=(0,10))
        center = ttk.Frame(body, padding=6); side = ttk.Frame(body, padding=(12,8))
        body.add(center, weight=5); body.add(side, weight=2)

        canvas = tk.Canvas(center, highlightthickness=0, background="#f4f7f5")
        scroll = ttk.Scrollbar(center, orient="vertical", command=canvas.yview)
        self.cards = ttk.Frame(canvas, padding=(8,4,12,12))
        self.cards.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.card_window = canvas.create_window((0,0), window=self.cards, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(self.card_window, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        self.card_canvas = canvas
        # Mouse wheel binding belongs to this window, not to the whole application.
        # bind_all left a callback behind after the DiseaseFile window was closed,
        # causing TclError when it tried to scroll a destroyed canvas.
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")

        ttk.Label(side, text="DOSYA ÖZETİ", style="Section.TLabel").pack(anchor="w")
        self.summary = tk.Text(side, height=9, wrap="word", relief="flat", padx=8, pady=8, cursor="arrow")
        self.summary.pack(fill="x", pady=(6,16)); self.summary.configure(state="disabled")
        ttk.Label(side, text="ZAMAN ÇİZELGESİ", style="Section.TLabel").pack(anchor="w")
        self.timeline = tk.Text(side, wrap="word", relief="flat", padx=8, pady=8, cursor="arrow")
        self.timeline.pack(fill="both", expand=True, pady=(6,0)); self.timeline.configure(state="disabled")

        bottom = ttk.Frame(self, padding=(18,8,18,14)); bottom.pack(fill="x")
        ttk.Label(bottom, text="FOTOĞRAF ŞERİDİ", style="Section.TLabel").pack(anchor="w")
        strip_wrap = ttk.Frame(bottom); strip_wrap.pack(fill="x", pady=(6,0))
        self.strip_canvas = tk.Canvas(strip_wrap, height=118, highlightthickness=0, background="#eef3f0")
        xscroll = ttk.Scrollbar(strip_wrap, orient="horizontal", command=self.strip_canvas.xview)
        self.strip = ttk.Frame(self.strip_canvas, padding=5)
        self.strip.bind("<Configure>", lambda _e: self.strip_canvas.configure(scrollregion=self.strip_canvas.bbox("all")))
        self.strip_canvas.create_window((0,0), window=self.strip, anchor="nw")
        self.strip_canvas.configure(xscrollcommand=xscroll.set)
        self.strip_canvas.pack(fill="x"); xscroll.pack(fill="x")


    def _on_mousewheel(self, event):
        """Scroll the card canvas only while the pointer is over it.

        The existence checks are intentionally defensive for delayed Tk events
        during window destruction on older Windows/Tk builds.
        """
        canvas = getattr(self, "card_canvas", None)
        if canvas is None:
            return
        try:
            if not self.winfo_exists() or not canvas.winfo_exists():
                return
            x, y = self.winfo_pointerxy()
            left, top = canvas.winfo_rootx(), canvas.winfo_rooty()
            right = left + canvas.winfo_width()
            bottom = top + canvas.winfo_height()
            if left <= x < right and top <= y < bottom:
                delta = int(-1 * (event.delta / 120)) if event.delta else 0
                if delta:
                    canvas.yview_scroll(delta, "units")
                    return "break"
        except (tk.TclError, AttributeError):
            return

    def _completion(self):
        fields = ["scientific_name","disease_name","hosts","affected_organs","symptoms","pathogen_features","epidemiology","differential_diagnosis","cultural_control","sources"]
        return int(round(100.0 * sum(bool((self.record[f] or '').strip()) for f in fields) / len(fields)))

    def render(self):
        if not self.record: return
        r = self.record
        self.title_var.set(r["scientific_name"] or "Adsız kayıt")
        self.subtitle_var.set(r["disease_name"] or "")
        tags = self.db.tags(self.disease_id)
        self.meta_var.set("{}  •  Tamamlanma %{}  •  {}  •  Son güncelleme {}".format(
            r["group_name"] or "Grup belirtilmemiş", self._completion(), "★ Favori" if r["favorite"] else "Normal kayıt", r["updated_at"] or "—"))
        for child in self.cards.winfo_children(): child.destroy()
        for card_title, fields in CARD_FIELDS:
            available = [(label, field, (r[field] or '').strip()) for label, field in fields if (r[field] or '').strip()]
            if not available: continue
            card = ttk.LabelFrame(self.cards, text=card_title, padding=(14,10))
            card.pack(fill="x", pady=(0,10))
            for label, field, value in available:
                ttk.Label(card, text=label, font=("Segoe UI",9,"bold")).pack(anchor="w", pady=(3,1))
                txt = tk.Text(card, wrap="word", height=max(2, min(8, value.count('\n')+2)), relief="flat", padx=6, pady=4, cursor="arrow")
                txt.pack(fill="x", pady=(0,6)); txt.insert("1.0", value)
                apply_to_text_widget(txt, value, self.rich.get(field, {}), "1.0", 9)
                txt.configure(state="disabled")
        self._render_summary(tags); self._render_timeline(); self._render_strip()

    def _render_summary(self, tags):
        photos = list(self.db.image_attachments(self.disease_id)); refs = list(self.db.references(self.disease_id))
        lines = ["Fotoğraflar: {}".format(len(photos)), "Kaynakça kayıtları: {}".format(len(refs)),
                 "Etiketler: {}".format(", ".join(tags) if tags else "—"), "Oluşturulma: {}".format(self.record["created_at"] or "—")]
        self.summary.configure(state="normal"); self.summary.delete("1.0","end"); self.summary.insert("1.0","\n\n".join(lines)); self.summary.configure(state="disabled")

    def _render_timeline(self):
        rows = list(self.db.history(self.disease_id))[:20]
        self.timeline.configure(state="normal"); self.timeline.delete("1.0","end")
        self.timeline.tag_configure("date", font=("Segoe UI",9,"bold"), foreground="#1f6b4f")
        self.timeline.tag_configure("event", lmargin1=10, lmargin2=10, spacing3=8)
        self.timeline.insert("end", "{}\n".format(self.record["updated_at"] or "—"), "date")
        self.timeline.insert("end", "Güncel sürüm\n\n", "event")
        for row in rows:
            self.timeline.insert("end", "{}\n".format(row["created_at"] or "—"), "date")
            changed = row["changed_fields"] or "Kayıt güncellendi"
            self.timeline.insert("end", changed.replace(",", " •") + "\n\n", "event")
        if not rows: self.timeline.insert("end", "Henüz geçmiş kaydı yok.")
        self.timeline.configure(state="disabled")

    def _render_strip(self):
        for child in self.strip.winfo_children(): child.destroy()
        self.photo_refs = []
        photos = list(self.db.image_attachments(self.disease_id))
        if not photos:
            ttk.Label(self.strip, text="Bu dosyada henüz fotoğraf yok.", style="Muted.TLabel").pack(side="left", padx=12, pady=38); return
        for row in photos:
            card = ttk.Frame(self.strip, padding=3); card.pack(side="left", padx=4)
            path = os.path.join(self.paths.base, row["relative_path"])
            photo = None
            if PIL_AVAILABLE and os.path.isfile(path):
                try:
                    with Image.open(path) as src:
                        im=src.convert("RGB"); im.thumbnail((120,78), Image.LANCZOS)
                        tile=Image.new("RGB",(124,82),"white"); tile.paste(im,((124-im.width)//2,(82-im.height)//2))
                    photo=ImageTk.PhotoImage(tile); self.photo_refs.append(photo)
                except Exception: pass
            lbl=ttk.Label(card, image=photo, text="Önizleme yok" if photo is None else "", compound="center", relief="solid")
            lbl.pack(); ttk.Label(card, text=("★ " if row["is_primary"] else "")+(row["title"] or os.path.basename(row["relative_path"]))[:18], width=19, anchor="center").pack()
            lbl.bind("<Double-1>", lambda _e: self._photos())

    def _edit(self):
        if self.on_edit: self.on_edit(); self.after(250, self._reload)
    def _preview(self):
        if self.on_preview: self.on_preview()
    def _pdf(self):
        if self.on_pdf: self.on_pdf()
    def _photos(self):
        if self.on_photos: self.on_photos()
    def _reload(self):
        if not self.winfo_exists(): return
        self.record=self.db.get(self.disease_id); self.rich=self.db.rich_text(self.disease_id); self.render()
