# -*- coding: utf-8 -*-
from .common import *
from .gallery import PhotoGallery

try:
    from PIL import ImageGrab, ImageOps
except Exception:
    ImageGrab = None
    ImageOps = None

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}


class PhotoImportDialog(tk.Toplevel):
    """Çoklu fotoğraf eklemeden önce seçimleri küçük resimlerle gözden geçirir."""
    def __init__(self, master, paths):
        tk.Toplevel.__init__(self, master)
        self.paths = paths
        self.result = None
        self.files = []
        self.refs = []
        self.title("Fotoğraf ekleme")
        self.geometry("900x610")
        self.minsize(720, 480)
        self.transient(master)
        self.grab_set()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Eklenecek fotoğraflar", font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(top, text="Dosya seç", command=self.choose_files).pack(side="right")

        self.count_var = tk.StringVar(value="Henüz fotoğraf seçilmedi")
        ttk.Label(self, textvariable=self.count_var, padding=(10, 0, 10, 7)).pack(fill="x")

        body = ttk.Frame(self, padding=(10, 0, 10, 0))
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, highlightthickness=0, background="#ffffff")
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=7)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        options = ttk.LabelFrame(self, text="Ortak bilgiler", padding=10)
        options.pack(fill="x", padx=10, pady=8)
        ttk.Label(options, text="Açıklama:").grid(row=0, column=0, sticky="w")
        self.description = ttk.Entry(options)
        self.description.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.optimize = tk.BooleanVar(value=True)
        ttk.Checkbutton(options, text="Çok büyük fotoğrafları arşiv için optimize et (azami 3000 px)", variable=self.optimize).grid(row=1, column=1, sticky="w", pady=(7, 0))
        options.columnconfigure(1, weight=1)

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="İptal", command=self.destroy).pack(side="right")
        ttk.Button(bottom, text="Seçilenleri ekle", command=self.accept).pack(side="right", padx=(0, 7))

        self.choose_files()
        self.wait_window(self)

    def choose_files(self):
        chosen = filedialog.askopenfilenames(
            parent=self, title="Bir veya daha fazla fotoğraf seç",
            filetypes=[("Fotoğraf dosyaları", "*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tif;*.tiff"), ("Tüm dosyalar", "*.*")],
        )
        for filename in chosen:
            if os.path.splitext(filename)[1].lower() in IMAGE_EXTS and filename not in self.files:
                self.files.append(filename)
        self.refresh()

    def refresh(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.refs = []
        self.count_var.set("{} fotoğraf seçildi".format(len(self.files)) if self.files else "Henüz fotoğraf seçilmedi")
        for index, filename in enumerate(list(self.files)):
            card = ttk.Frame(self.inner, padding=5, relief="solid")
            card.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="nsew")
            preview = None
            if PIL_AVAILABLE:
                try:
                    with Image.open(filename) as src:
                        im = src.convert("RGB")
                        im.thumbnail((160, 105), Image.LANCZOS)
                        tile = Image.new("RGB", (164, 109), "white")
                        tile.paste(im, ((164-im.width)//2, (109-im.height)//2))
                    preview = ImageTk.PhotoImage(tile)
                    self.refs.append(preview)
                except Exception:
                    preview = None
            ttk.Label(card, image=preview, text="Önizleme yok" if preview is None else "", compound="center", anchor="center").pack()
            ttk.Label(card, text=os.path.basename(filename), width=24, anchor="center").pack(pady=(4, 2))
            ttk.Button(card, text="Listeden çıkar", command=lambda f=filename: self.remove(f)).pack(fill="x")
        for col in range(4):
            self.inner.columnconfigure(col, weight=1)

    def remove(self, filename):
        if filename in self.files:
            self.files.remove(filename)
        self.refresh()

    def accept(self):
        if not self.files:
            messagebox.showinfo(APP_NAME, "En az bir fotoğraf seçin.", parent=self)
            return
        self.result = {
            "files": list(self.files),
            "description": self.description.get().strip(),
            "optimize": bool(self.optimize.get()),
        }
        self.destroy()


class PhotoManager(tk.Toplevel):
    """Hastalığa bağlı fotoğraflar için katalog, metadata ve toplu işlem ekranı."""
    def __init__(self, master, db, paths, disease_id, refresh_callback=None):
        tk.Toplevel.__init__(self, master)
        self.db, self.paths, self.disease_id = db, paths, disease_id
        self.refresh_callback = refresh_callback
        self.photos = []
        self.selected_ids = set()
        self.refs = []
        self.preview_ref = None
        self.card_widgets = {}
        self.thumb_size = tk.StringVar(value="Orta")
        self.sort_var = tk.StringVar(value="Sıra")
        self.info_var = tk.StringVar(value="")
        self.title("Fotoğraf yöneticisi")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._build()
        self.refresh()

    def _build(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Fotoğraf ekle", command=self.import_photos).pack(side="left")
        ttk.Button(toolbar, text="Panodan yapıştır", command=self.paste_clipboard).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Galeride aç", command=self.open_gallery).pack(side="left")
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Label(toolbar, text="Küçük resim:").pack(side="left")
        size = ttk.Combobox(toolbar, textvariable=self.thumb_size, values=("Küçük", "Orta", "Büyük"), width=8, state="readonly")
        size.pack(side="left", padx=(4, 10)); size.bind("<<ComboboxSelected>>", lambda _e: self.draw_catalog())
        ttk.Label(toolbar, text="Sırala:").pack(side="left")
        sort = ttk.Combobox(toolbar, textvariable=self.sort_var, values=("Sıra", "Eklenme tarihi", "Dosya adı", "Başlık"), width=15, state="readonly")
        sort.pack(side="left", padx=4); sort.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Button(toolbar, text="Seçileni sil", command=self.delete_selected).pack(side="right")

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(paned)
        right = ttk.Frame(paned, padding=10)
        paned.add(left, weight=3); paned.add(right, weight=2)

        self.canvas = tk.Canvas(left, background="#ffffff", highlightthickness=0)
        sy = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.catalog = ttk.Frame(self.canvas, padding=7)
        self.catalog_window = self.canvas.create_window((0,0), window=self.catalog, anchor="nw")
        self.catalog.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._catalog_resize)
        self.canvas.configure(yscrollcommand=sy.set)
        self.canvas.pack(side="left", fill="both", expand=True); sy.pack(side="right", fill="y")

        self.preview_label = ttk.Label(right, text="Bir fotoğraf seçin", anchor="center", relief="solid")
        self.preview_label.pack(fill="x")
        ttk.Label(right, textvariable=self.info_var, anchor="center").pack(fill="x", pady=(5, 9))

        form = ttk.LabelFrame(right, text="Fotoğraf bilgileri", padding=9)
        form.pack(fill="x")
        self.title_entry = ttk.Entry(form)
        self.description_entry = ttk.Entry(form)
        self.date_entry = ttk.Entry(form)
        self.source_entry = ttk.Entry(form)
        for row, (label, widget) in enumerate((("Başlık", self.title_entry), ("Açıklama", self.description_entry), ("Çekim tarihi", self.date_entry), ("Kaynak / fotoğrafçı", self.source_entry))):
            ttk.Label(form, text=label+":").grid(row=row, column=0, sticky="w", pady=4)
            widget.grid(row=row, column=1, sticky="ew", padx=(8,0), pady=4)
        form.columnconfigure(1, weight=1)
        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Bilgileri kaydet", command=self.save_metadata).pack(side="left")
        ttk.Button(actions, text="Ana fotoğraf yap", command=self.make_primary).pack(side="left", padx=5)
        ttk.Button(actions, text="Dışarıda aç", command=self.open_external).pack(side="left")

        order = ttk.LabelFrame(right, text="Katalog sırası", padding=8)
        order.pack(fill="x")
        ttk.Button(order, text="◀ Önceye taşı", command=lambda: self.move_selected(-1)).pack(side="left", expand=True, fill="x")
        ttk.Button(order, text="Sonraya taşı ▶", command=lambda: self.move_selected(1)).pack(side="left", expand=True, fill="x", padx=(5,0))
        ttk.Label(right, text="Ctrl tuşuyla birden fazla fotoğraf seçebilirsiniz. Çift tıklama galeriyi açar.", wraplength=390).pack(fill="x", pady=(12,0))

    def _catalog_resize(self, event):
        self.canvas.itemconfigure(self.catalog_window, width=event.width)
        self.after_idle(self.draw_catalog)

    def _sorted_photos(self):
        rows = list(self.db.image_attachments(self.disease_id))
        key = self.sort_var.get()
        if key == "Eklenme tarihi": rows.sort(key=lambda r: (r["created_at"], r["id"]), reverse=True)
        elif key == "Dosya adı": rows.sort(key=lambda r: os.path.basename(r["relative_path"]).lower())
        elif key == "Başlık": rows.sort(key=lambda r: ((r["title"] or "").lower(), r["id"]))
        else: rows.sort(key=lambda r: (0 if r["is_primary"] else 1, r["sort_order"], r["id"]))
        return rows

    def refresh(self):
        self.photos = self._sorted_photos()
        valid = {int(r["id"]) for r in self.photos}
        self.selected_ids.intersection_update(valid)
        self.draw_catalog()
        self.show_selected()
        if self.refresh_callback:
            self.refresh_callback()

    def draw_catalog(self):
        for child in self.catalog.winfo_children(): child.destroy()
        self.refs=[]; self.card_widgets={}
        sizes={"Küçük":(110,74), "Orta":(155,104), "Büyük":(210,140)}
        w,h=sizes.get(self.thumb_size.get(),(155,104))
        available=max(500, self.canvas.winfo_width()-25)
        cols=max(1, available//(w+28))
        for idx,row in enumerate(self.photos):
            aid=int(row["id"]); selected=aid in self.selected_ids
            card=tk.Frame(self.catalog, bd=2, relief="solid", background="#dbeafe" if selected else "#ffffff", padx=5, pady=5)
            card.grid(row=idx//cols,column=idx%cols,padx=5,pady=5,sticky="n")
            photo=None; path=os.path.join(self.paths.base,row["relative_path"])
            if PIL_AVAILABLE and os.path.isfile(path):
                try:
                    with Image.open(path) as src:
                        im=src.convert("RGB"); im.thumbnail((w,h),Image.LANCZOS)
                        tile=Image.new("RGB",(w,h),"white"); tile.paste(im,((w-im.width)//2,(h-im.height)//2))
                    photo=ImageTk.PhotoImage(tile); self.refs.append(photo)
                except Exception: pass
            label=tk.Label(card,image=photo,text="Önizleme yok" if photo is None else "",compound="center",background=card["background"],width=w,height=h)
            label.pack()
            caption=("★ " if row["is_primary"] else "") + (row["title"] or os.path.basename(row["relative_path"]).split("_",1)[-1])
            text=tk.Label(card,text=caption[:28],background=card["background"],wraplength=w,justify="center")
            text.pack(pady=(4,0))
            for widget in (card,label,text):
                widget.bind("<Button-1>",lambda e,x=aid:self.select(x, bool(e.state & 0x0004)))
                widget.bind("<Double-1>",lambda _e,x=aid:self.open_gallery(x))
            self.card_widgets[aid]=card
        for col in range(cols): self.catalog.columnconfigure(col,weight=1)

    def select(self, attachment_id, additive=False):
        if additive:
            if attachment_id in self.selected_ids: self.selected_ids.remove(attachment_id)
            else: self.selected_ids.add(attachment_id)
        else:
            self.selected_ids={attachment_id}
        self.draw_catalog(); self.show_selected()

    def selected_row(self):
        if len(self.selected_ids)!=1: return None
        return self.db.get_attachment(next(iter(self.selected_ids)))

    def show_selected(self):
        row=self.selected_row()
        for entry in (self.title_entry,self.description_entry,self.date_entry,self.source_entry):
            entry.delete(0,"end")
        self.preview_ref=None
        if not row:
            self.preview_label.configure(image="",text="{} fotoğraf seçili".format(len(self.selected_ids)) if self.selected_ids else "Bir fotoğraf seçin")
            self.info_var.set("Toplam {} fotoğraf".format(len(self.photos)))
            return
        path=os.path.join(self.paths.base,row["relative_path"])
        if PIL_AVAILABLE and os.path.isfile(path):
            try:
                with Image.open(path) as src:
                    im=src.convert("RGB"); original=im.size; im.thumbnail((390,260),Image.LANCZOS)
                    tile=Image.new("RGB",(400,270),"white"); tile.paste(im,((400-im.width)//2,(270-im.height)//2))
                self.preview_ref=ImageTk.PhotoImage(tile); self.preview_label.configure(image=self.preview_ref,text="")
                self.info_var.set("{} × {} piksel  •  {}".format(original[0],original[1],os.path.basename(path).split("_",1)[-1]))
            except Exception:
                self.preview_label.configure(image="",text="Fotoğraf önizlenemedi")
        self.title_entry.insert(0,row["title"] or "")
        self.description_entry.insert(0,row["description"] or "")
        self.date_entry.insert(0,row["captured_at"] or "")
        self.source_entry.insert(0,row["source"] or "")

    def import_photos(self):
        dialog=PhotoImportDialog(self,self.paths)
        if not dialog.result: return
        added, skipped, failed = self._add_files(dialog.result["files"], dialog.result["description"], dialog.result["optimize"])
        self.refresh()
        msg="{} fotoğraf eklendi.".format(added)
        if skipped: msg += "\n{} yinelenen fotoğraf atlandı.".format(skipped)
        if failed: msg += "\n{} fotoğraf eklenemedi.".format(failed)
        messagebox.showinfo(APP_NAME,msg,parent=self)

    def _existing_hashes(self):
        result=set()
        for row in self.db.image_attachments(self.disease_id):
            path=os.path.join(self.paths.base,row["relative_path"])
            if os.path.isfile(path):
                try:
                    h=hashlib.sha256()
                    with open(path,"rb") as f:
                        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
                    result.add(h.hexdigest())
                except Exception: pass
        return result

    def _add_files(self, files, description="", optimize=True):
        hashes=self._existing_hashes(); added=skipped=failed=0
        target_dir=os.path.join(self.paths.images,str(self.disease_id))
        if not os.path.isdir(target_dir): os.makedirs(target_dir)
        for filename in files:
            try:
                with open(filename,"rb") as f: digest=hashlib.sha256(f.read()).hexdigest()
                if digest in hashes: skipped+=1; continue
                ext=os.path.splitext(filename)[1].lower() or ".jpg"
                destination=os.path.join(target_dir,"{}_{}".format(uuid.uuid4().hex[:10],os.path.basename(filename)))
                if optimize and PIL_AVAILABLE:
                    with Image.open(filename) as src:
                        im=ImageOps.exif_transpose(src) if ImageOps else src.copy()
                        if max(im.size)>3000:
                            im.thumbnail((3000,3000),Image.LANCZOS)
                            if im.mode not in ("RGB","L") and ext in (".jpg",".jpeg"): im=im.convert("RGB")
                            save_kwargs={"quality":92,"optimize":True} if ext in (".jpg",".jpeg") else {}
                            im.save(destination,**save_kwargs)
                        else: shutil.copy2(filename,destination)
                else: shutil.copy2(filename,destination)
                relative=os.path.relpath(destination,self.paths.base)
                self.db.add_attachment(self.disease_id,"image",relative,description,title=os.path.splitext(os.path.basename(filename))[0])
                hashes.add(digest); added+=1
            except Exception: failed+=1
        return added,skipped,failed

    def paste_clipboard(self):
        if not ImageGrab:
            messagebox.showwarning(APP_NAME,"Panodan fotoğraf alma bu sistemde kullanılamıyor.",parent=self); return
        try: data=ImageGrab.grabclipboard()
        except Exception: data=None
        if data is None:
            messagebox.showinfo(APP_NAME,"Panoda bir fotoğraf bulunamadı.",parent=self); return
        if isinstance(data,list):
            files=[f for f in data if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
            if files:
                self._add_files(files,"Panodan eklendi",True); self.refresh(); return
        if PIL_AVAILABLE and hasattr(data,"save"):
            target_dir=os.path.join(self.paths.images,str(self.disease_id))
            if not os.path.isdir(target_dir): os.makedirs(target_dir)
            destination=os.path.join(target_dir,"{}_pano.png".format(uuid.uuid4().hex[:10]))
            data.save(destination,"PNG")
            self.db.add_attachment(self.disease_id,"image",os.path.relpath(destination,self.paths.base),"Panodan eklendi",title="Pano görüntüsü")
            self.refresh(); return
        messagebox.showinfo(APP_NAME,"Panodaki içerik fotoğraf olarak eklenemedi.",parent=self)

    def save_metadata(self):
        row=self.selected_row()
        if not row:
            messagebox.showinfo(APP_NAME,"Bilgilerini düzenlemek için tek bir fotoğraf seçin.",parent=self); return
        self.db.update_attachment_metadata(row["id"],self.title_entry.get(),self.description_entry.get(),self.date_entry.get(),self.source_entry.get())
        self.refresh()

    def make_primary(self):
        row=self.selected_row()
        if not row: return
        self.db.set_primary_attachment(self.disease_id,row["id"]); self.refresh()

    def move_selected(self,direction):
        row=self.selected_row()
        if not row: return
        ordered=list(self.db.image_attachments(self.disease_id))
        ordered.sort(key=lambda r:(r["sort_order"],r["id"]))
        ids=[int(r["id"]) for r in ordered]; idx=ids.index(int(row["id"])); target=idx+direction
        if target<0 or target>=len(ids): return
        ids[idx],ids[target]=ids[target],ids[idx]
        self.db.set_attachment_order(ids); self.refresh()

    def delete_selected(self):
        if not self.selected_ids: return
        if not messagebox.askyesno(APP_NAME,"Seçili {} fotoğraf katalogdan kaldırılsın mı?".format(len(self.selected_ids)),parent=self): return
        for aid in list(self.selected_ids):
            row=self.db.get_attachment(aid)
            if row:
                path=os.path.join(self.paths.base,row["relative_path"])
                self.db.delete_attachment(aid)
                try:
                    if os.path.isfile(path): os.remove(path)
                except Exception: pass
        self.selected_ids.clear(); self.refresh()

    def open_gallery(self, attachment_id=None):
        aid=attachment_id or (next(iter(self.selected_ids)) if self.selected_ids else None)
        PhotoGallery(self,self.db,self.paths,self.disease_id,aid)

    def open_external(self):
        row=self.selected_row()
        if row:
            path=os.path.join(self.paths.base,row["relative_path"])
            try: os.startfile(path)
            except Exception as exc: messagebox.showerror(APP_NAME,str(exc),parent=self)

    def close(self):
        if self.refresh_callback: self.refresh_callback()
        self.destroy()
