# -*- coding: utf-8 -*-
from .common import *
from .editor import DiseaseEditor
from .gallery import PhotoGallery
from .comparison import DiseaseComparison
from .preview import DiseasePreview
from .photo_manager import PhotoManager, PhotoImportDialog
from .theme import apply_theme, COLORS
from .rich_utils import apply_to_text_widget, to_reportlab

class MainWindow(tk.Tk):
    def __init__(self, paths, database):
        tk.Tk.__init__(self)
        apply_theme(self)
        self.paths = paths
        self.db = database
        self.selected_id = None
        self.title("{} {}".format(APP_NAME, APP_VERSION))
        self.geometry("1220x760")
        self.minsize(960, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after_idle(self.maximize_window)
        self.after(1200, self.automatic_daily_backup)

        self.search_var = tk.StringVar()
        self.group_var = tk.StringVar(value="TÜMÜ")
        self.host_filter = ""
        self.organ_filter = ""
        self.symptom_filter = ""
        self.favorites_only_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar()
        self.header_scientific = tk.StringVar(value="Bir kayıt seçin")
        self.header_disease = tk.StringVar(value="")
        self.header_group = tk.StringVar(value="")
        self.detail_texts = {}
        self.summary_photo = None
        self.summary_photo_label = None
        self.summary_text = None
        self.attachment_thumbnail_refs = []
        self.thumbnail_items = {}

        self.build_ui()
        self.refresh_groups()
        self.refresh_list()

    def maximize_window(self):
        try:
            self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", True)
            except Exception:
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                self.geometry("{}x{}+0+0".format(screen_w, max(600, screen_h - 40)))

    def build_ui(self):
        # Sol gezinti + üst başlık + içerik düzeni. Tamamı ttk olduğu için
        # Windows 7 ve PyInstaller paketleriyle uyumludur.
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)

        nav = ttk.Frame(shell, style="Nav.TFrame", width=196)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        ttk.Label(nav, text="Fitopatoloji", style="NavTitle.TLabel").pack(anchor="w", padx=16, pady=(18, 0))
        ttk.Label(nav, text="ARŞİVİ  •  v{}".format(APP_VERSION), style="NavSub.TLabel").pack(anchor="w", padx=16, pady=(1, 18))

        ttk.Button(nav, text="＋  Yeni kayıt", style="Nav.TButton", command=self.new_record).pack(fill="x")
        ttk.Button(nav, text="✎  Kaydı düzenle", style="Nav.TButton", command=self.edit_record).pack(fill="x")
        ttk.Button(nav, text="▤  İncele", style="Nav.TButton", command=self.preview_record).pack(fill="x")
        ttk.Button(nav, text="★  Favori", style="Nav.TButton", command=self.toggle_favorite).pack(fill="x")
        ttk.Separator(nav, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Button(nav, text="⌕  Gelişmiş filtre", style="Nav.TButton", command=self.open_advanced_filter).pack(fill="x")
        ttk.Button(nav, text="✓  Teşhis sihirbazı", style="Nav.TButton", command=self.open_diagnosis_wizard).pack(fill="x")
        ttk.Button(nav, text="⇄  Karşılaştır", style="Nav.TButton", command=self.open_comparison).pack(fill="x")
        ttk.Button(nav, text="▥  İstatistik", style="Nav.TButton", command=self.open_statistics).pack(fill="x")
        ttk.Separator(nav, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Button(nav, text="▣  PDF raporu", style="Nav.TButton", command=self.export_pdf_report).pack(fill="x")
        ttk.Button(nav, text="▤  Excel aktar", style="Nav.TButton", command=self.export_excel).pack(fill="x")
        ttk.Button(nav, text="⛁  Yedekleme", style="Nav.TButton", command=self.create_backup).pack(fill="x")

        content = ttk.Frame(shell)
        content.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(content, style="Header.TFrame", padding=(18, 12))
        header.pack(fill="x")
        title_box = ttk.Frame(header, style="Header.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="Hastalık Arşivi", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Kayıtları ara, düzenle ve bilimsel bilgileri tek yerde yönet.", style="Subtitle.TLabel").pack(anchor="w", pady=(1, 0))
        actions = ttk.Frame(header, style="Header.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="◀", width=3, command=self.previous_record).pack(side="left", padx=(0, 4))
        ttk.Button(actions, text="▶", width=3, command=self.next_record).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Yeni kayıt", style="Primary.TButton", command=self.new_record).pack(side="left")

        body = ttk.Frame(content, padding=(14, 12, 14, 8))
        body.pack(fill="both", expand=True)

        paned = ttk.Panedwindow(body, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned, style="Surface.TFrame", padding=10)
        right = ttk.Frame(paned, style="Surface.TFrame", padding=12)
        paned.add(left, weight=2)
        paned.add(right, weight=5)

        ttk.Label(left, text="Kayıtlar", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        search_card = ttk.Frame(left, style="Surface.TFrame")
        search_card.pack(fill="x", pady=(0, 9))
        search = ttk.Entry(search_card, textvariable=self.search_var)
        search.pack(fill="x")
        search.insert(0, "")
        search.bind("<KeyRelease>", lambda _e: self.after_idle(self.refresh_list))

        filter_row = ttk.Frame(left, style="Surface.TFrame")
        filter_row.pack(fill="x", pady=(0, 9))
        self.group_combo = ttk.Combobox(filter_row, textvariable=self.group_var, state="readonly", width=18)
        self.group_combo.pack(side="left", fill="x", expand=True)
        self.group_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_list())
        ttk.Button(filter_row, text="Temizle", command=self.clear_filters).pack(side="left", padx=(6, 0))
        ttk.Checkbutton(left, text="Yalnız favoriler", variable=self.favorites_only_var, command=self.refresh_list).pack(anchor="w", pady=(0, 8))

        tree_frame = ttk.Frame(left, style="Surface.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("scientific", "disease"), show="headings", selectmode="browse")
        self.tree.heading("scientific", text="Etmen")
        self.tree.heading("disease", text="Hastalık")
        self.tree.column("scientific", width=195, anchor="w")
        self.tree.column("disease", width=215, anchor="w")
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda _e: self.edit_record())

        record_header = ttk.Frame(right, style="Surface.TFrame")
        record_header.pack(fill="x", pady=(0, 10))
        heading_box = ttk.Frame(record_header, style="Surface.TFrame")
        heading_box.pack(side="left", fill="x", expand=True)
        ttk.Label(heading_box, textvariable=self.header_scientific, style="Surface.TLabel", font=("Segoe UI", 14, "bold italic"), wraplength=650).pack(anchor="w")
        ttk.Label(heading_box, textvariable=self.header_disease, style="Muted.TLabel", font=("Segoe UI", 10), wraplength=650).pack(anchor="w", pady=(2, 0))
        ttk.Label(heading_box, textvariable=self.header_group, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        record_actions = ttk.Frame(record_header, style="Surface.TFrame")
        record_actions.pack(side="right")
        ttk.Button(record_actions, text="İncele", style="Primary.TButton", command=self.preview_record).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Düzenle", command=self.edit_record).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Sil", style="Danger.TButton", command=self.delete_record).pack(side="left")

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        summary_tab = ttk.Frame(notebook, style="Surface.TFrame", padding=12)
        notebook.add(summary_tab, text="Bilgi kartı")
        summary_tab.columnconfigure(1, weight=1)
        summary_tab.rowconfigure(0, weight=1)
        self.summary_photo_label = ttk.Label(summary_tab, text="Ana fotoğraf yok", anchor="center", relief="solid", style="Surface.TLabel")
        self.summary_photo_label.grid(row=0, column=0, sticky="n", padx=(0, 12))
        self.summary_text = tk.Text(summary_tab, width=60, height=24, wrap="word", relief="flat", borderwidth=0, background="#ffffff", foreground=COLORS["text"], padx=10, pady=10)
        self.summary_text.grid(row=0, column=1, sticky="nsew")
        self.summary_text.configure(state="disabled")

        tabs = [
            ("Temel", ["synonyms", "hosts", "affected_organs"]),
            ("Belirti ve biyoloji", ["symptoms", "pathogen_features", "disease_cycle", "epidemiology", "differential_diagnosis"]),
            ("Mücadele", ["cultural_control", "biological_control", "chemical_control"]),
            ("Dağılım", ["distribution_turkey", "distribution_world", "climate_notes"]),
            ("Kaynak ve not", ["sources", "notes"]),
        ]
        labels = dict(LONG_FIELDS)
        labels["synonyms"] = "Sinonimler / eski adlar"
        for tab_name, fields in tabs:
            outer = ttk.Frame(notebook, style="Surface.TFrame")
            notebook.add(outer, text=tab_name)
            canvas = tk.Canvas(outer, highlightthickness=0, background="#ffffff")
            scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            inner = ttk.Frame(canvas, style="Surface.TFrame", padding=12)
            inner.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scroll.set)
            canvas.pack(side="left", fill="both", expand=True)
            scroll.pack(side="right", fill="y")
            inner.columnconfigure(0, weight=1)
            for idx, field in enumerate(fields):
                ttk.Label(inner, text=labels[field], style="Section.TLabel").grid(row=idx * 2, column=0, sticky="w", pady=(7, 3))
                text = tk.Text(inner, height=5, wrap="word", relief="solid", borderwidth=1, background="#ffffff", foreground=COLORS["text"], padx=8, pady=7)
                text.grid(row=idx * 2 + 1, column=0, sticky="ew")
                text.configure(state="disabled")
                self.detail_texts[field] = text

        attachment_frame = ttk.LabelFrame(right, text="Fotoğraflar ve belgeler", padding=8)
        attachment_frame.pack(fill="x", pady=(10, 0))

        catalog = ttk.Frame(attachment_frame, style="Surface.TFrame")
        catalog.pack(fill="x", pady=(0, 7))
        self.thumbnail_canvas = tk.Canvas(catalog, height=116, highlightthickness=0, background="#ffffff")
        thumb_scroll = ttk.Scrollbar(catalog, orient="horizontal", command=self.thumbnail_canvas.xview)
        self.thumbnail_canvas.configure(xscrollcommand=thumb_scroll.set)
        self.thumbnail_canvas.pack(fill="x")
        thumb_scroll.pack(fill="x")
        self.thumbnail_inner = ttk.Frame(self.thumbnail_canvas, style="Surface.TFrame")
        self.thumbnail_window = self.thumbnail_canvas.create_window((0, 0), window=self.thumbnail_inner, anchor="nw")
        self.thumbnail_inner.bind("<Configure>", lambda _e: self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all")))

        self.attach_tree = ttk.Treeview(attachment_frame, columns=("type", "name", "description"), show="headings", height=3)
        self.attach_tree.heading("type", text="Tür")
        self.attach_tree.heading("name", text="Dosya")
        self.attach_tree.heading("description", text="Açıklama")
        self.attach_tree.column("type", width=70)
        self.attach_tree.column("name", width=250)
        self.attach_tree.column("description", width=310)
        self.attach_tree.pack(side="left", fill="x", expand=True)
        attach_buttons = ttk.Frame(attachment_frame, style="Surface.TFrame")
        attach_buttons.pack(side="right", fill="y", padx=(8, 0))
        ttk.Button(attach_buttons, text="Fotoğraf yöneticisi", style="Primary.TButton", command=self.open_photo_manager).pack(fill="x")
        ttk.Button(attach_buttons, text="Hızlı fotoğraf ekle", command=self.add_photo).pack(fill="x", pady=(4, 0))
        ttk.Button(attach_buttons, text="Belge ekle", command=self.add_document).pack(fill="x", pady=(4, 0))
        ttk.Button(attach_buttons, text="Galeri", command=self.open_gallery).pack(fill="x", pady=(4, 0))
        ttk.Button(attach_buttons, text="Aç", command=self.open_attachment).pack(fill="x", pady=4)
        ttk.Button(attach_buttons, text="Kaldır", style="Danger.TButton", command=self.remove_attachment).pack(fill="x")
        self.attach_tree.bind("<Double-1>", self.on_attachment_double_click)

        status = ttk.Label(content, textvariable=self.status_var, anchor="w", style="Status.TLabel")
        status.pack(fill="x", side="bottom")

    @staticmethod
    def apply_rich_to_text(text_widget, text_value, formatting, base_index="1.0", font_size=9):
        apply_to_text_widget(text_widget, text_value or "", formatting or {}, base_index, font_size)

    def previous_record(self):
        items = list(self.tree.get_children())
        if not items:
            return
        current = str(self.selected_id) if self.selected_id else items[0]
        try:
            index = items.index(current)
        except ValueError:
            index = 0
        target = items[(index - 1) % len(items)]
        self.tree.selection_set(target)
        self.tree.focus(target)
        self.tree.see(target)
        self.load_record(int(target))

    def next_record(self):
        items = list(self.tree.get_children())
        if not items:
            return
        current = str(self.selected_id) if self.selected_id else items[0]
        try:
            index = items.index(current)
        except ValueError:
            index = -1
        target = items[(index + 1) % len(items)]
        self.tree.selection_set(target)
        self.tree.focus(target)
        self.tree.see(target)
        self.load_record(int(target))

    def automatic_daily_backup(self):
        try:
            today = dt.datetime.now().strftime("%Y-%m-%d")
            marker = os.path.join(self.paths.backups, ".last_auto_backup")
            last_date = ""
            if os.path.isfile(marker):
                with open(marker, "r", encoding="utf-8") as handle:
                    last_date = handle.read().strip()
            if last_date == today:
                return
            output = os.path.join(self.paths.backups, "Otomatik_Yedek_{}.zip".format(today))
            self._write_backup_zip(output)
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write(today)
            self.status_var.set("Günlük otomatik yedek oluşturuldu: {}".format(os.path.basename(output)))
        except Exception as exc:
            self.status_var.set("Otomatik yedek oluşturulamadı: {}".format(exc))

    def export_excel(self):
        if not OPENPYXL_AVAILABLE:
            messagebox.showerror(APP_NAME, "Excel dışa aktarımı için openpyxl bileşeni bulunamadı.", parent=self)
            return
        output = filedialog.asksaveasfilename(
            title="Excel dışa aktar",
            initialdir=self.paths.exports,
            initialfile="fitopatoloji_{}.xlsx".format(dt.datetime.now().strftime("%Y-%m-%d")),
            defaultextension=".xlsx",
            filetypes=[("Excel dosyası", "*.xlsx")],
        )
        if not output:
            return
        try:
            self.db.export_excel(output)
            messagebox.showinfo(APP_NAME, "Excel dosyası oluşturuldu:\n{}".format(output), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Excel oluşturulamadı:\n{}".format(exc), parent=self)

    def find_duplicates(self):
        duplicates = self.db.duplicate_candidates()
        dialog = tk.Toplevel(self)
        dialog.title("Olası tekrar kayıtlar")
        dialog.geometry("850x520")
        dialog.transient(self)
        tree = ttk.Treeview(dialog, columns=("reason", "id", "scientific", "disease"), show="headings")
        for col, title, width in [
            ("reason", "Eşleşme", 110), ("id", "ID", 60),
            ("scientific", "Bilimsel ad", 280), ("disease", "Hastalık adı", 330)
        ]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for reason, rows in duplicates:
            for row in rows:
                tree.insert("", "end", iid="{}-{}-{}".format(reason, row["id"], len(tree.get_children())),
                            values=(reason, row["id"], row["scientific_name"], row["disease_name"]))
        ttk.Label(
            dialog,
            text="Bu ekran olası tekrarları gösterir; yanlış veri kaybını önlemek için otomatik birleştirme yapmaz.",
            padding=(10, 0, 10, 8),
        ).pack(fill="x")
        if not duplicates:
            ttk.Label(dialog, text="Olası tekrar kayıt bulunamadı.", padding=20).place(relx=.5, rely=.5, anchor="center")

    def refresh_groups(self):
        groups = ["TÜMÜ"] + self.db.list_groups()
        self.group_combo["values"] = groups
        if self.group_var.get() not in groups:
            self.group_var.set("TÜMÜ")

    def refresh_list(self, select_id=None):
        current = select_id or self.selected_id
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.db.search(self.search_var.get(), self.group_var.get(), self.host_filter, self.organ_filter, self.symptom_filter, self.favorites_only_var.get())
        selected_item = None
        for row in rows:
            item = self.tree.insert("", "end", iid=str(row["id"]), values=(("★ " if row["favorite"] else "") + row["scientific_name"], row["disease_name"]))
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
        self.header_group.set(("★ " if record["favorite"] else "") + record["group_name"])
        self.refresh_summary_card(record)
        rich_map = self.db.rich_text(disease_id)
        for field, text_widget in self.detail_texts.items():
            text_widget.configure(state="normal")
            text_widget.delete("1.0", "end")
            text_widget.insert("1.0", record[field] or "")
            self.apply_rich_to_text(text_widget, record[field] or "", rich_map.get(field, {}))
            text_widget.configure(state="disabled")
        self.refresh_attachments()

    def clear_detail(self):
        self.selected_id = None
        self.header_scientific.set("Kayıt bulunamadı")
        self.header_disease.set("")
        self.header_group.set("")
        self.summary_photo = None
        if self.summary_photo_label:
            self.summary_photo_label.configure(image="", text="Ana fotoğraf yok")
        if self.summary_text:
            self.summary_text.configure(state="normal")
            self.summary_text.delete("1.0", "end")
            self.summary_text.configure(state="disabled")
        for text in self.detail_texts.values():
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.configure(state="disabled")
        for item in self.attach_tree.get_children():
            self.attach_tree.delete(item)
        self.refresh_photo_catalog()

    def new_record(self):
        groups = self.db.list_groups()
        DiseaseEditor(self, groups, on_save=self._save_new)

    def _save_new(self, data):
        rich_data = data.pop("_rich_text", {})
        new_id = self.db.add(data)
        self.db.save_rich_text(new_id, rich_data)
        self.refresh_groups()
        self.refresh_list(select_id=new_id)

    def preview_record(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir kayıt seçin.", parent=self)
            return
        DiseasePreview(
            self, self.db, self.paths, self.selected_id,
            pdf_callback=self.export_pdf_report,
        )

    def edit_record(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir kayıt seçin.", parent=self)
            return
        record = self.db.get(self.selected_id)
        groups = self.db.list_groups()
        DiseaseEditor(self, groups, initial=record, rich_initial=self.db.rich_text(self.selected_id), on_save=self._save_edit)

    def _save_edit(self, data):
        rich_data = data.pop("_rich_text", {})
        self.db.update(self.selected_id, data)
        self.db.save_rich_text(self.selected_id, rich_data)
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
                values=(
                    ("★ Fotoğraf" if row["is_primary"] else "Fotoğraf") if row["file_type"] == "image" else "Belge",
                    os.path.basename(row["relative_path"]).split("_", 1)[-1],
                    row["description"],
                ),
            )
        self.refresh_photo_catalog()

    def add_photo(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        dialog = PhotoImportDialog(self, self.paths)
        if not dialog.result:
            return
        manager = PhotoManager(self, self.db, self.paths, self.selected_id, self.refresh_attachments)
        manager.withdraw()
        added, skipped, failed = manager._add_files(
            dialog.result["files"], dialog.result["description"], dialog.result["optimize"]
        )
        manager.destroy()
        self.refresh_attachments()
        text = "{} fotoğraf eklendi.".format(added)
        if skipped:
            text += " {} yinelenen fotoğraf atlandı.".format(skipped)
        if failed:
            text += " {} fotoğraf eklenemedi.".format(failed)
        self.status_var.set(text)

    def open_photo_manager(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        PhotoManager(self, self.db, self.paths, self.selected_id, self.refresh_attachments)

    def add_document(self):
        self.add_attachment("document")

    def add_attachment(self, requested_type=None):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff"}
        if requested_type == "image":
            filenames = list(filedialog.askopenfilenames(
                title="Bir veya daha fazla fotoğraf seç",
                filetypes=[("Fotoğraf dosyaları", "*.jpg;*.jpeg;*.png;*.gif;*.bmp;*.tif;*.tiff"), ("Tüm dosyalar", "*.*")],
            ))
        else:
            chosen = filedialog.askopenfilename(
                title="Belge seç",
                filetypes=[("Belgeler", "*.pdf;*.doc;*.docx;*.xls;*.xlsx;*.ppt;*.pptx;*.txt;*.rtf"), ("Tüm dosyalar", "*.*")],
            )
            filenames = [chosen] if chosen else []
        if not filenames:
            return
        valid=[]
        for filename in filenames:
            ext=os.path.splitext(filename)[1].lower()
            if requested_type == "image" and ext not in image_exts:
                continue
            valid.append(filename)
        if not valid:
            messagebox.showwarning(APP_NAME, "Desteklenen bir fotoğraf seçilmedi.", parent=self); return
        description = simpledialog.askstring(
            APP_NAME,
            "Seçilen dosyalar için ortak açıklama (isteğe bağlı):\nHer fotoğrafın açıklamasını galeriden ayrıca değiştirebilirsiniz.",
            parent=self,
        )
        if description is None:
            return
        added=[]; failed=[]
        for filename in valid:
            ext=os.path.splitext(filename)[1].lower()
            file_type = requested_type or ("image" if ext in image_exts else "document")
            root_dir=self.paths.images if file_type=="image" else self.paths.documents
            target_dir=os.path.join(root_dir,str(self.selected_id))
            if not os.path.isdir(target_dir): os.makedirs(target_dir)
            original_name=os.path.basename(filename)
            safe_name="{}_{}".format(uuid.uuid4().hex[:10],original_name)
            destination=os.path.join(target_dir,safe_name)
            try:
                shutil.copy2(filename,destination)
                relative=os.path.relpath(destination,self.paths.base)
                self.db.add_attachment(self.selected_id,file_type,relative,(description or "").strip())
                added.append(original_name)
            except Exception as exc:
                failed.append("{}: {}".format(original_name,exc))
                try:
                    if os.path.isfile(destination): os.remove(destination)
                except Exception: pass
        self.refresh_attachments()
        if added:
            self.status_var.set("{} dosya eklendi.".format(len(added)))
        if failed:
            messagebox.showwarning(APP_NAME, "Bazı dosyalar eklenemedi:\n" + "\n".join(failed[:8]), parent=self)

    def refresh_photo_catalog(self):
        if not hasattr(self, "thumbnail_inner"):
            return
        for child in self.thumbnail_inner.winfo_children(): child.destroy()
        self.attachment_thumbnail_refs=[]; self.thumbnail_items={}
        if not self.selected_id:
            return
        photos=list(self.db.image_attachments(self.selected_id))
        if not photos:
            ttk.Label(self.thumbnail_inner,text="Henüz fotoğraf yok. 'Fotoğraf(lar) ekle' ile toplu seçim yapabilirsiniz.",style="Muted.TLabel").pack(side="left",padx=8,pady=38)
            return
        for row in photos:
            card=ttk.Frame(self.thumbnail_inner,style="Surface.TFrame",padding=4)
            card.pack(side="left",padx=(0,7),pady=2)
            path=os.path.join(self.paths.base,row["relative_path"])
            photo=None
            if PIL_AVAILABLE and os.path.isfile(path):
                try:
                    with Image.open(path) as src:
                        im=src.convert("RGB"); im.thumbnail((104,72),Image.LANCZOS)
                        tile=Image.new("RGB",(108,76),"white")
                        tile.paste(im,((108-im.width)//2,(76-im.height)//2))
                    photo=ImageTk.PhotoImage(tile); self.attachment_thumbnail_refs.append(photo)
                except Exception: photo=None
            label=ttk.Label(card,image=photo,text="Önizleme yok" if photo is None else "",compound="center",relief="solid",anchor="center")
            label.pack()
            name=os.path.basename(row["relative_path"]).split("_",1)[-1]
            caption=("★ " if row["is_primary"] else "")+name
            ttk.Label(card,text=caption[:18],width=18,anchor="center",style="Muted.TLabel").pack(pady=(3,0))
            aid=int(row["id"])
            for widget in (card,label):
                widget.bind("<Button-1>",lambda _e,x=aid:self.select_thumbnail(x))
                widget.bind("<Double-1>",lambda _e,x=aid:self.open_gallery_at(x))

    def select_thumbnail(self, attachment_id):
        iid=str(attachment_id)
        if self.attach_tree.exists(iid):
            self.attach_tree.selection_set(iid); self.attach_tree.focus(iid); self.attach_tree.see(iid)

    def open_gallery_at(self, attachment_id):
        self.select_thumbnail(attachment_id)
        PhotoGallery(self,self.db,self.paths,self.selected_id,attachment_id)

    def selected_attachment(self):
        selection = self.attach_tree.selection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Önce bir dosya seçin.", parent=self)
            return None
        return self.db.get_attachment(int(selection[0]))

    def clear_filters(self):
        self.search_var.set("")
        self.group_var.set("TÜMÜ")
        self.host_filter = ""
        self.organ_filter = ""
        self.symptom_filter = ""
        self.favorites_only_var.set(False)
        self.refresh_list()

    def open_advanced_filter(self):
        dialog = tk.Toplevel(self)
        dialog.title("Gelişmiş filtre")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        values = {
            "host": tk.StringVar(value=self.host_filter),
            "organ": tk.StringVar(value=self.organ_filter),
            "symptom": tk.StringVar(value=self.symptom_filter),
        }
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)
        fields = [
            ("Konukçu", "host", self.db.distinct_terms("hosts")),
            ("Etkilenen organ", "organ", self.db.distinct_terms("affected_organs")),
            ("Belirti sözcüğü", "symptom", self.db.distinct_terms("symptoms")),
        ]
        for row, (label, key, options) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5)
            combo = ttk.Combobox(frame, textvariable=values[key], values=options, width=48, state="normal")
            combo.grid(row=row, column=1, sticky="ew", pady=5)

        def apply_filter():
            self.host_filter = values["host"].get().strip()
            self.organ_filter = values["organ"].get().strip()
            self.symptom_filter = values["symptom"].get().strip()
            dialog.destroy()
            self.refresh_list()

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="İptal", command=dialog.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(buttons, text="Uygula", command=apply_filter).pack(side="right")
        frame.columnconfigure(1, weight=1)
        dialog.bind("<Return>", lambda _e: apply_filter())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.update_idletasks()
        dialog.geometry("+{}+{}".format(
            max(0, self.winfo_rootx() + 120),
            max(0, self.winfo_rooty() + 100),
        ))

    def open_diagnosis_wizard(self):
        dialog = tk.Toplevel(self)
        dialog.title("Teşhis sihirbazı")
        dialog.geometry("860x560")
        dialog.minsize(720, 450)
        dialog.transient(self)

        top = ttk.Frame(dialog, padding=10)
        top.pack(fill="x")
        host_var = tk.StringVar()
        organ_var = tk.StringVar()
        symptom_var = tk.StringVar()
        group_diag_var = tk.StringVar(value="TÜMÜ")

        ttk.Label(top, text="Etmen grubu").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Konukçu").grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(top, text="Organ").grid(row=0, column=2, sticky="w", padx=(6, 0))
        ttk.Label(top, text="Belirti / anahtar sözcükler").grid(row=0, column=3, sticky="w", padx=(6, 0))
        ttk.Combobox(top, textvariable=group_diag_var, values=["TÜMÜ"] + self.db.list_groups(), state="readonly").grid(row=1, column=0, sticky="ew")
        ttk.Combobox(top, textvariable=host_var, values=self.db.distinct_terms("hosts"), state="normal").grid(row=1, column=1, sticky="ew", padx=(6, 0))
        ttk.Combobox(top, textvariable=organ_var, values=self.db.distinct_terms("affected_organs"), state="normal").grid(row=1, column=2, sticky="ew", padx=(6, 0))
        ttk.Entry(top, textvariable=symptom_var).grid(row=1, column=3, sticky="ew", padx=(6, 0))
        for col in range(4):
            top.columnconfigure(col, weight=1)

        result_frame = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        result_frame.pack(fill="both", expand=True)
        result_tree = ttk.Treeview(
            result_frame,
            columns=("score", "scientific", "disease", "match"),
            show="headings",
            selectmode="browse",
        )
        for column, title, width in [
            ("score", "Puan", 55),
            ("scientific", "Etmen", 230),
            ("disease", "Hastalık", 300),
            ("match", "Eşleşme", 180),
        ]:
            result_tree.heading(column, text=title)
            result_tree.column(column, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=result_tree.yview)
        result_tree.configure(yscrollcommand=scrollbar.set)
        result_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def run_diagnosis():
            for item in result_tree.get_children():
                result_tree.delete(item)
            results = self.db.diagnose(host_var.get(), organ_var.get(), symptom_var.get(), group_diag_var.get())
            for score, row, matched in results:
                result_tree.insert(
                    "", "end", iid=str(row["id"]),
                    values=(score, row["scientific_name"], row["disease_name"], matched),
                )
            if not results:
                messagebox.showinfo(APP_NAME, "Bu ölçütlerle eşleşen kayıt bulunamadı.", parent=dialog)

        def open_result(_event=None):
            selection = result_tree.selection()
            if not selection:
                return
            disease_id = int(selection[0])
            dialog.destroy()
            self.search_var.set("")
            self.group_var.set("TÜMÜ")
            self.host_filter = self.organ_filter = self.symptom_filter = ""
            self.refresh_list(select_id=disease_id)

        buttons = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Kapat", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Seçili kaydı aç", command=open_result).pack(side="right", padx=5)
        ttk.Button(buttons, text="Olası hastalıkları bul", command=run_diagnosis).pack(side="right")
        result_tree.bind("<Double-1>", open_result)
        dialog.bind("<Return>", lambda _e: run_diagnosis())

    def refresh_summary_card(self, record):
        if self.summary_text:
            sections = [("Hastalık", "disease_name"), ("Etmen grubu", "group_name"), ("Konukçular", "hosts"), ("Etkilenen organlar", "affected_organs"), ("Belirtiler", "symptoms"), ("Epidemiyoloji", "epidemiology"), ("Türkiye dağılımı", "distribution_turkey"), ("Dünya dağılımı", "distribution_world")]
            rich_map = self.db.rich_text(record["id"])
            self.summary_text.configure(state="normal")
            self.summary_text.delete("1.0", "end")
            for title, field in sections:
                value = (record[field] or "").strip()
                if value:
                    self.summary_text.insert("end", title + "\n", "heading")
                    start_index = self.summary_text.index("end-1c")
                    self.summary_text.insert("end", value)
                    self.apply_rich_to_text(self.summary_text, value, rich_map.get(field, {}), start_index)
                    self.summary_text.insert("end", "\n\n")
            controls = [record["cultural_control"], record["biological_control"], record["chemical_control"]]
            if any((value or "").strip() for value in controls):
                self.summary_text.insert("end", "Mücadele özeti\n", "heading")
                for field in ("cultural_control", "biological_control", "chemical_control"):
                    value = (record[field] or "").strip()
                    if value:
                        start_index = self.summary_text.index("end-1c")
                        self.summary_text.insert("end", value)
                        self.apply_rich_to_text(self.summary_text, value, rich_map.get(field, {}), start_index)
                        self.summary_text.insert("end", "\n")
            self.summary_text.tag_configure("heading", font=("Segoe UI", 9, "bold"))
            self.summary_text.configure(state="disabled")

        self.summary_photo = None
        if self.summary_photo_label:
            self.summary_photo_label.configure(image="", text="Ana fotoğraf yok")
        photos = self.db.image_attachments(record["id"])
        if not photos or not PIL_AVAILABLE or not self.summary_photo_label:
            return
        path = os.path.join(self.paths.base, photos[0]["relative_path"])
        if not os.path.isfile(path):
            return
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                image.thumbnail((300, 260), Image.LANCZOS)
            self.summary_photo = ImageTk.PhotoImage(image)
            self.summary_photo_label.configure(image=self.summary_photo, text="")
        except Exception:
            self.summary_photo_label.configure(image="", text="Fotoğraf önizlenemedi")
    def toggle_favorite(self):
        if not self.selected_id:
            return
        is_favorite = self.db.toggle_favorite(self.selected_id)
        self.refresh_list(select_id=self.selected_id)
        self.status_var.set("Kayıt favorilere eklendi." if is_favorite else "Kayıt favorilerden çıkarıldı.")

    def open_reference_manager(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        dialog = tk.Toplevel(self)
        dialog.title("Kaynak yönetimi")
        dialog.geometry("850x480")
        dialog.minsize(650, 380)
        dialog.transient(self)

        tree = ttk.Treeview(
            dialog,
            columns=("type", "citation", "identifier"),
            show="headings",
            selectmode="browse",
        )
        for column, title, width in [
            ("type", "Tür", 100),
            ("citation", "Kaynak künyesi", 480),
            ("identifier", "DOI / URL / ISBN", 220),
        ]:
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh():
            for item in tree.get_children():
                tree.delete(item)
            for row in self.db.references(self.selected_id):
                tree.insert("", "end", iid=str(row["id"]), values=(
                    row["source_type"], row["citation"], row["identifier"]
                ))

        def add():
            add_dialog = tk.Toplevel(dialog)
            add_dialog.title("Kaynak ekle")
            add_dialog.transient(dialog)
            add_dialog.grab_set()
            frame = ttk.Frame(add_dialog, padding=12)
            frame.pack(fill="both", expand=True)
            type_var = tk.StringVar(value="Makale")
            citation_var = tk.StringVar()
            identifier_var = tk.StringVar()
            ttk.Label(frame, text="Tür").grid(row=0, column=0, sticky="w", pady=4)
            ttk.Combobox(
                frame, textvariable=type_var,
                values=["Makale", "Kitap", "Tez", "Web", "Rapor", "Diğer"],
                state="readonly", width=18
            ).grid(row=0, column=1, sticky="ew", pady=4)
            ttk.Label(frame, text="Kaynak künyesi").grid(row=1, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=citation_var, width=70).grid(row=1, column=1, sticky="ew", pady=4)
            ttk.Label(frame, text="DOI / URL / ISBN").grid(row=2, column=0, sticky="w", pady=4)
            ttk.Entry(frame, textvariable=identifier_var).grid(row=2, column=1, sticky="ew", pady=4)

            def save():
                if not citation_var.get().strip():
                    messagebox.showwarning(APP_NAME, "Kaynak künyesi boş bırakılamaz.", parent=add_dialog)
                    return
                self.db.add_reference(
                    self.selected_id,
                    type_var.get(),
                    citation_var.get(),
                    identifier_var.get(),
                )
                add_dialog.destroy()
                refresh()

            buttons = ttk.Frame(frame)
            buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
            ttk.Button(buttons, text="İptal", command=add_dialog.destroy).pack(side="right", padx=(5, 0))
            ttk.Button(buttons, text="Kaydet", command=save).pack(side="right")
            frame.columnconfigure(1, weight=1)

        def remove():
            selection = tree.selection()
            if not selection:
                return
            if messagebox.askyesno(APP_NAME, "Seçili kaynak silinsin mi?", parent=dialog):
                self.db.delete_reference(int(selection[0]))
                refresh()

        def open_identifier(_event=None):
            selection = tree.selection()
            if not selection:
                return
            row = next((r for r in self.db.references(self.selected_id) if str(r["id"]) == selection[0]), None)
            if not row or not row["identifier"]:
                return
            identifier = row["identifier"].strip()
            if identifier.lower().startswith(("http://", "https://")):
                try:
                    os.startfile(identifier)
                except Exception as exc:
                    messagebox.showerror(APP_NAME, "Bağlantı açılamadı:\n{}".format(exc), parent=dialog)

        buttons = ttk.Frame(dialog, padding=(10, 0, 10, 10))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Kapat", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Sil", command=remove).pack(side="right", padx=5)
        ttk.Button(buttons, text="Yeni kaynak", command=add).pack(side="right")
        tree.bind("<Double-1>", open_identifier)
        refresh()

    def open_statistics(self):
        stats = self.db.statistics()
        dialog = tk.Toplevel(self)
        dialog.title("Arşiv istatistikleri")
        dialog.geometry("620x520")
        dialog.minsize(500, 400)
        dialog.transient(self)

        summary = ttk.LabelFrame(dialog, text="Genel", padding=10)
        summary.pack(fill="x", padx=10, pady=10)
        values = [
            ("Toplam hastalık kaydı", stats["total"]),
            ("Favori kayıt", stats["favorites"]),
            ("Fotoğraf", stats["photos"]),
            ("Belge", stats["documents"]),
            ("Yapılandırılmış kaynak", stats["references"]),
        ]
        for row, (label, value) in enumerate(values):
            ttk.Label(summary, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Label(summary, text=str(value), font=("Segoe UI", 9, "bold")).grid(row=row, column=1, sticky="e", padx=(20, 0))

        group_frame = ttk.LabelFrame(dialog, text="Etmen grupları", padding=8)
        group_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        group_tree = ttk.Treeview(group_frame, columns=("group", "count"), show="headings")
        group_tree.heading("group", text="Grup")
        group_tree.heading("count", text="Kayıt sayısı")
        group_tree.column("group", width=360)
        group_tree.column("count", width=100, anchor="e")
        group_tree.pack(fill="both", expand=True)
        for row in stats["groups"]:
            group_tree.insert("", "end", values=(row["label"], row["total"]))

    @staticmethod
    def _pdf_text(value):
        value = "" if value is None else str(value)
        return xml_escape(value).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")

    def _register_pdf_font(self):
        if not REPORTLAB_AVAILABLE:
            return "Helvetica", "Helvetica-Bold"
        try:
            fonts_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
            regular = os.path.join(fonts_dir, "Vera.ttf")
            bold = os.path.join(fonts_dir, "VeraBd.ttf")
            if os.path.isfile(regular):
                if "Vera" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("Vera", regular))
                if os.path.isfile(bold) and "Vera-Bold" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("Vera-Bold", bold))
                return "Vera", "Vera-Bold" if os.path.isfile(bold) else "Vera"
        except Exception:
            pass
        return "Helvetica", "Helvetica-Bold"

    def export_pdf_report(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(
                APP_NAME,
                "PDF raporu için ReportLab bileşeni bulunamadı.",
                parent=self,
            )
            return
        record = self.db.get(self.selected_id)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", record["scientific_name"]).strip("_") or "hastalik"
        output = filedialog.asksaveasfilename(
            title="PDF hastalık raporu",
            initialdir=self.paths.exports,
            initialfile=safe_name + ".pdf",
            defaultextension=".pdf",
            filetypes=[("PDF dosyası", "*.pdf")],
        )
        if not output:
            return
        try:
            font_name, bold_name = self._register_pdf_font()
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "FitoTitle", parent=styles["Title"], fontName=bold_name,
                fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=10
            )
            heading_style = ParagraphStyle(
                "FitoHeading", parent=styles["Heading2"], fontName=bold_name,
                fontSize=11, leading=14, spaceBefore=8, spaceAfter=4
            )
            body_style = ParagraphStyle(
                "FitoBody", parent=styles["BodyText"], fontName=font_name,
                fontSize=9, leading=13, spaceAfter=4
            )

            doc = SimpleDocTemplate(
                output, pagesize=A4,
                rightMargin=1.6 * cm, leftMargin=1.6 * cm,
                topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                title=record["scientific_name"],
                author=APP_NAME,
            )
            story = [
                Paragraph(self._pdf_text(record["scientific_name"]), title_style),
                Paragraph(self._pdf_text(record["disease_name"]), ParagraphStyle(
                    "Sub", parent=body_style, fontName=bold_name,
                    fontSize=12, alignment=TA_CENTER, spaceAfter=10
                )),
            ]

            photos = self.db.image_attachments(self.selected_id)

            rich_map = self.db.rich_text(self.selected_id)

            fields = [
                ("Etmen grubu", "group_name"),
                ("Sinonimler / eski adlar", "synonyms"),
                ("Konukçular", "hosts"),
                ("Etkilenen organlar", "affected_organs"),
                ("Belirtiler", "symptoms"),
                ("Etmenin özellikleri", "pathogen_features"),
                ("Hastalık döngüsü", "disease_cycle"),
                ("Epidemiyoloji", "epidemiology"),
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
            for title, field in fields:
                value = (record[field] or "").strip()
                if value:
                    story.append(Paragraph(title, heading_style))
                    story.append(Paragraph(to_reportlab(value, rich_map.get(field, {})), body_style))

            refs = self.db.references(self.selected_id)
            if refs:
                story.append(Paragraph("Yapılandırılmış kaynakça", heading_style))
                for ref in refs:
                    line = "{}: {}".format(ref["source_type"], ref["citation"])
                    if ref["identifier"]:
                        line += " - " + ref["identifier"]
                    story.append(Paragraph(self._pdf_text("• " + line), body_style))

            if photos:
                story.append(Paragraph("Fotoğraflar", heading_style))
                photo_cells = []
                for photo_row in photos:
                    image_path = os.path.join(self.paths.base, photo_row["relative_path"])
                    if not os.path.isfile(image_path):
                        continue
                    try:
                        image = RLImage(image_path)
                        image._restrictSize(5.2 * cm, 3.6 * cm)
                        caption = (photo_row["description"] or os.path.basename(photo_row["relative_path"]).split("_", 1)[-1]).strip()
                        cell = [image, Paragraph(self._pdf_text(caption), ParagraphStyle(
                            "PhotoCaption", parent=body_style, fontSize=7, leading=9, alignment=TA_CENTER
                        ))]
                        photo_cells.append(cell)
                    except Exception:
                        pass
                if photo_cells:
                    rows = []
                    for index in range(0, len(photo_cells), 3):
                        row = photo_cells[index:index + 3]
                        while len(row) < 3:
                            row.append("")
                        rows.append(row)
                    table = Table(rows, colWidths=[5.5 * cm] * 3, hAlign="CENTER")
                    table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]))
                    story.append(table)

            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph(
                self._pdf_text("{} {} tarafından {} tarihinde oluşturuldu.".format(
                    APP_NAME, APP_VERSION, dt.datetime.now().strftime("%d.%m.%Y %H:%M")
                )),
                ParagraphStyle("Footer", parent=body_style, fontSize=7, textColor=colors.grey)
            ))
            doc.build(story)
            if not os.path.isfile(output) or os.path.getsize(output) < 100:
                raise IOError("PDF dosyası oluşturulamadı veya boş oluştu.")
            messagebox.showinfo(APP_NAME, "PDF raporu oluşturuldu:\n{}".format(output), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "PDF raporu oluşturulamadı:\n{}".format(exc), parent=self)


    def open_comparison(self):
        DiseaseComparison(self, self.db, self.selected_id)

    def open_gallery(self):
        if not self.selected_id:
            return
        row = self.selected_attachment()
        start_id = row["id"] if row and row["file_type"] == "image" else None
        PhotoGallery(self, self.db, self.paths, self.selected_id, start_id)

    def on_attachment_double_click(self, _event=None):
        row = self.selected_attachment()
        if row and row["file_type"] == "image":
            self.open_gallery()
        else:
            self.open_attachment()

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

    def _write_backup_zip(self, zip_path):
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
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def create_backup(self):
        stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        zip_path = os.path.join(self.paths.backups, "Fitopatoloji_Yedek_{}.zip".format(stamp))
        try:
            self._write_backup_zip(zip_path)
            messagebox.showinfo(APP_NAME, "Yedek oluşturuldu:\n{}".format(zip_path), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Yedek oluşturulamadı:\n{}".format(exc), parent=self)

    def restore_backup(self):
        backup_path = filedialog.askopenfilename(
            title="Fitopatoloji yedeğini seç",
            initialdir=self.paths.backups,
            filetypes=[("ZIP yedeği", "*.zip")],
        )
        if not backup_path:
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Seçilen yedek geri yüklenecek.\n\nMevcut arşiv önce otomatik olarak güvenlik yedeğine alınacaktır. Devam edilsin mi?",
            parent=self,
        ):
            return

        temp_dir = tempfile.mkdtemp(prefix="fitopatoloji_restore_")
        safety_path = os.path.join(
            self.paths.backups,
            "Geri_Yukleme_Oncesi_{}.zip".format(dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")),
        )
        try:
            self._write_backup_zip(safety_path)
            with zipfile.ZipFile(backup_path, "r") as archive:
                for member in archive.infolist():
                    target = os.path.abspath(os.path.join(temp_dir, member.filename))
                    if not target.startswith(os.path.abspath(temp_dir) + os.sep):
                        raise ValueError("Yedek içinde güvensiz dosya yolu bulundu.")
                archive.extractall(temp_dir)

            restored_db = os.path.join(temp_dir, "Data", "fitopatoloji.db")
            if not os.path.isfile(restored_db):
                raise ValueError("Yedekte Data/fitopatoloji.db bulunamadı.")

            test_conn = sqlite3.connect(restored_db)
            try:
                test_conn.execute("SELECT COUNT(*) FROM diseases").fetchone()
            finally:
                test_conn.close()

            self.db.close()
            shutil.copy2(restored_db, self.paths.database)

            for folder_name, target_folder in (("Images", self.paths.images), ("Documents", self.paths.documents)):
                source_folder = os.path.join(temp_dir, folder_name)
                if os.path.isdir(target_folder):
                    shutil.rmtree(target_folder)
                os.makedirs(target_folder)
                if os.path.isdir(source_folder):
                    for name in os.listdir(source_folder):
                        source = os.path.join(source_folder, name)
                        target = os.path.join(target_folder, name)
                        if os.path.isdir(source):
                            shutil.copytree(source, target)
                        else:
                            shutil.copy2(source, target)

            self.db = Database(self.paths.database, resource_path("seed", "diseases.csv"))
            self.selected_id = None
            self.clear_filters()
            self.refresh_groups()
            self.refresh_list()
            messagebox.showinfo(
                APP_NAME,
                "Yedek başarıyla geri yüklendi.\n\nGeri yükleme öncesi güvenlik yedeği:\n{}".format(safety_path),
                parent=self,
            )
        except Exception as exc:
            try:
                self.db = Database(self.paths.database, resource_path("seed", "diseases.csv"))
            except Exception:
                pass
            messagebox.showerror(
                APP_NAME,
                "Yedek geri yüklenemedi:\n{}\n\nMevcut veriler korunmaya çalışıldı.".format(exc),
                parent=self,
            )
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


