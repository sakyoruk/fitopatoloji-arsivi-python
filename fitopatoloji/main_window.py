# -*- coding: utf-8 -*-
from .common import *
from .editor import DiseaseEditor
from .gallery import PhotoGallery
from .comparison import DiseaseComparison
from .preview import DiseasePreview
from .photo_manager import PhotoManager, PhotoImportDialog
from .file_manager import FileManager
from .dashboard import Dashboard
from .disease_file import DiseaseFile
from .knowledge_graph import KnowledgeCenter
from .workspace import Workspace
from .monograph import MonographBuilder
from .theme import apply_theme, COLORS
from .rich_utils import apply_to_text_widget, to_reportlab
from .maintenance import MaintenanceCenter, SettingsDialog, SettingsStore, HelpCenter
from .diagnostics import IssueReportDialog
from .rc_shell import ContextPanel, AboutDialog
from .catalogs import TaxonomyCatalog, HostCatalog
from .literature import LiteratureCatalog, PrivateNoteDialog
from .quiz import QuizCenter
from .reports import ReportsCenter

class MainWindow(tk.Tk):
    def __init__(self, paths, database):
        tk.Tk.__init__(self)
        apply_theme(self)
        self.paths = paths
        self.db = database
        self.settings = SettingsStore(paths)
        self.selected_id = None
        self.title("{} {}".format(APP_NAME, APP_VERSION))
        saved_geometry = self.settings.data.get("window_geometry", "")
        self.geometry(saved_geometry or "1220x760")
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
        self.nav_buttons = {}
        self.record_metric_vars = {key: tk.StringVar(value="0") for key in ("hosts", "literature", "photos", "questions")}

        self.dashboard_window = None
        self.workspace_window = None
        self.build_ui()
        self.refresh_groups()
        self.refresh_list()
        self.bind_all("<Control-k>", lambda _e: self.open_command_palette())
        # Uygulama doğrudan ana arşiv ekranında açılır. Çalışma Merkezi
        # sol menüdeki "Ana sayfa" komutuyla isteğe bağlı olarak açılır.

    def open_maintenance(self):
        MaintenanceCenter(self, self.db, self.paths)

    def open_settings(self):
        SettingsDialog(self, self.paths, self.settings)

    def open_help(self):
        HelpCenter(self)

    def open_about(self):
        AboutDialog(self)

    def open_issue_report(self):
        IssueReportDialog(self, self.db, self.paths)

    def open_taxonomy_catalog(self):
        TaxonomyCatalog(self, self.db)

    def open_literature_catalog(self):
        LiteratureCatalog(self, self.db, self.selected_id)

    def open_private_notes(self):
        if not self.selected_id:
            messagebox.showwarning("Seçim", "Özel not eklemek için bir hastalık seçin.", parent=self); return
        row=self.db.get(self.selected_id)
        PrivateNoteDialog(self, self.db, self.selected_id, (row["disease_name"] or row["scientific_name"]) if row else "")

    def open_host_catalog(self):
        HostCatalog(self, self.db)

    def open_dashboard(self):
        try:
            if self.dashboard_window and self.dashboard_window.winfo_exists():
                self.dashboard_window.lift(); self.dashboard_window.focus_force(); return
        except Exception:
            pass
        self.dashboard_window = Dashboard(self, self.db, self.open_record_by_id, self.new_record, self.open_command_palette)

    def open_workspace(self):
        try:
            if self.workspace_window and self.workspace_window.winfo_exists():
                self.workspace_window.lift(); self.workspace_window.focus_force()
                if self.selected_id: self.workspace_window.open_disease(self.selected_id)
                return
        except Exception:
            pass
        self.workspace_window = Workspace(self, self.db, self.paths, self.selected_id, self.open_record_by_id, self.edit_record)

    def open_quiz_center(self):
        QuizCenter(self, self.db, self.selected_id, self.open_record_by_id)

    def open_reports_center(self):
        ReportsCenter(self, self.db, self.paths)

    def open_monograph(self):
        selected = []
        if self.selected_id:
            selected.append(self.selected_id)
        try:
            selected.extend(int(x) for x in self.tree.selection() if int(x) not in selected)
        except Exception:
            pass
        MonographBuilder(self, self.db, self.paths, selected)

    def open_record_by_id(self, disease_id):
        self.search_var.set("")
        self.group_var.set("TÜMÜ")
        self.host_filter = self.organ_filter = self.symptom_filter = ""
        self.favorites_only_var.set(False)
        self.refresh_list(select_id=disease_id)
        self.lift(); self.focus_force()

    def open_command_palette(self):
        dialog = tk.Toplevel(self)
        dialog.title("Hızlı komutlar")
        dialog.geometry("520x430")
        dialog.transient(self)
        query = tk.StringVar()
        frame = ttk.Frame(dialog, padding=14); frame.pack(fill="both", expand=True)
        entry = ttk.Entry(frame, textvariable=query, font=("Segoe UI", 11)); entry.pack(fill="x")
        tree = ttk.Treeview(frame, columns=("hint",), show="tree headings", selectmode="extended")
        tree.heading("#0", text="Komut"); tree.heading("hint", text="İşlem")
        tree.column("#0", width=280); tree.column("hint", width=170)
        tree.pack(fill="both", expand=True, pady=(10, 0))
        commands = [
            ("dashboard", "Çalışma merkezini aç", "Arşiv özeti", self.open_dashboard),
            ("workspace", "Araştırmacı çalışma alanını aç", "Sekmeler, notlar ve görevler", self.open_workspace),
            ("monograph", "Dijital monografi oluştur", "Kitap düzeninde PDF ve HTML", self.open_monograph),
            ("new", "Yeni hastalık kaydı", "Kayıt oluştur", self.new_record),
            ("edit", "Seçili kaydı düzenle", "Düzenleyici", self.edit_record),
            ("file", "Dijital hastalık dosyasını aç", "Dosya görünümü", self.open_disease_file),
            ("knowledge", "Bilimsel bilgi ağını aç", "İlişkiler ve indeks", self.open_knowledge_center),
            ("taxonomy", "Taksonomi kataloğunu aç", "Etmen sınıflandırması", self.open_taxonomy_catalog),
            ("hosts", "Konukçu kataloğunu aç", "Yapılandırılmış konukçular", self.open_host_catalog),
            ("literature", "Literatür kataloğunu aç", "Kaynakları tek merkezde yönet", self.open_literature_catalog),
            ("quiz", "Bilgi sınavı merkezini aç", "Soru bankası ve öğrenme geçmişi", self.open_quiz_center),
            ("reports", "Bilimsel raporları aç", "İstatistikler ve CSV dışa aktarım", self.open_reports_center),
            ("preview", "Seçili kaydı incele", "Önizleme", self.preview_record),
            ("photos", "Fotoğraf yöneticisini aç", "Görsel katalog", self.open_photo_manager),
            ("compare", "Hastalıkları karşılaştır", "Karşılaştırma", self.open_comparison),
            ("diagnose", "Teşhis sihirbazını aç", "Tanı desteği", self.open_diagnosis_wizard),
            ("pdf", "PDF raporu oluştur", "Dışa aktar", self.export_pdf_report),
            ("backup", "Yedek oluştur", "Güvenlik", self.create_backup),
            ("duplicates", "Benzer kayıtları bul", "Arşiv denetimi", self.find_duplicates),
            ("maintenance", "Bakım ve tanılama merkezini aç", "Veritabanı sağlığı", self.open_maintenance),
            ("settings", "Ayarlar merkezini aç", "Uygulama tercihleri", self.open_settings),
            ("help", "Yardım merkezini aç", "Kullanım ve kısayollar", self.open_help),
            ("issue", "Sorun bildir", "Gizlilik odaklı tanılama paketi", self.open_issue_report),
            ("about", "Fitopatoloji Arşivi hakkında", "Sürüm ve uygulama bilgisi", self.open_about),
        ]
        def fill(*_args):
            text=query.get().strip().lower(); tree.delete(*tree.get_children())
            for key,title,hint,func in commands:
                if not text or text in title.lower() or text in hint.lower(): tree.insert("","end",iid=key,text=title,values=(hint,))
            kids=tree.get_children()
            if kids: tree.selection_set(kids[0])
        def run(_event=None):
            sel=tree.selection()
            if not sel:return
            key=sel[0]; dialog.destroy()
            for item in commands:
                if item[0]==key: self.after(20,item[3]); break
        query.trace_add("write",fill) if hasattr(query,"trace_add") else query.trace("w",fill)
        fill(); tree.bind("<Double-1>",run); dialog.bind("<Return>",run); dialog.bind("<Escape>",lambda _e:dialog.destroy())
        entry.focus_set()


    def open_knowledge_center(self):
        KnowledgeCenter(self, self.db, self.paths, self.selected_id, self._open_from_knowledge)

    def _open_from_knowledge(self, disease_id):
        self.selected_id = int(disease_id)
        self.refresh_list(select_id=self.selected_id)
        self.open_disease_file()

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

        nav = ttk.Frame(shell, style="Nav.TFrame", width=208)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        ttk.Label(nav, text="Fitopatoloji", style="NavTitle.TLabel").pack(anchor="w", padx=16, pady=(18, 0))
        ttk.Label(nav, text="ARŞİVİ  •  v{}".format(APP_VERSION), style="NavSub.TLabel").pack(anchor="w", padx=16, pady=(1, 18))

        def nav_item(key, text, command, active=False):
            button = ttk.Button(nav, text=text, style="NavActive.TButton" if active else "Nav.TButton", command=command)
            button.pack(fill="x")
            self.nav_buttons[key] = button
            return button

        ttk.Label(nav, text="ARŞİV", style="NavSection.TLabel").pack(anchor="w", padx=16, pady=(0, 4))
        nav_item("home", "  Ana sayfa", self.open_dashboard)
        nav_item("diseases", "  Hastalıklar", lambda: self.focus_force(), active=True)
        nav_item("taxonomy", "  Taksonomi", self.open_taxonomy_catalog)
        nav_item("hosts", "  Konukçular", self.open_host_catalog)
        nav_item("literature", "  Literatür", self.open_literature_catalog)
        nav_item("photos", "  Fotoğraflar", self.open_photo_manager)
        ttk.Separator(nav, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Label(nav, text="ÖĞRENME VE ANALİZ", style="NavSection.TLabel").pack(anchor="w", padx=16, pady=(0, 4))
        nav_item("search", "  Arama ve filtre", self.open_advanced_filter)
        nav_item("diagnosis", "  Teşhis sihirbazı", self.open_diagnosis_wizard)
        nav_item("compare", "  Karşılaştır", self.open_comparison)
        nav_item("network", "  Bilgi ağı", self.open_knowledge_center)
        nav_item("workspace", "  Çalışma alanı", self.open_workspace)
        nav_item("notes", "  Özel notlar", self.open_private_notes)
        nav_item("quiz", "  Bilgi sınavı", self.open_quiz_center)
        ttk.Separator(nav, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Label(nav, text="YAYIN", style="NavSection.TLabel").pack(anchor="w", padx=16, pady=(0, 4))
        nav_item("monograph", "  Monografi", self.open_monograph)
        nav_item("reports", "  Bilimsel raporlar", self.open_reports_center)
        ttk.Separator(nav, orient="horizontal").pack(fill="x", padx=14, pady=8)
        ttk.Label(nav, text="SİSTEM", style="NavSection.TLabel").pack(anchor="w", padx=16, pady=(0, 4))
        nav_item("backup", "  Yedekleme", self.create_backup)
        nav_item("maintenance", "  Bakım ve ayarlar", self.open_maintenance)
        nav_item("help", "  Yardım", self.open_help)

        content = ttk.Frame(shell)
        content.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(content, style="Header.TFrame", padding=(18, 10))
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
        insight_host = ttk.Frame(paned, style="Surface.TFrame")
        paned.add(left, weight=2)
        paned.add(right, weight=5)
        paned.add(insight_host, weight=1)
        self.context_panel = ContextPanel(insight_host, self.db, {"edit": self.edit_record, "preview": self.preview_record})
        self.context_panel.pack(fill="both", expand=True)

        list_head = ttk.Frame(left, style="Surface.TFrame")
        list_head.pack(fill="x", pady=(0, 8))
        ttk.Label(list_head, text="Kayıtlar", style="Section.TLabel").pack(side="left")
        self.list_count_label = ttk.Label(list_head, text="0 kayıt", style="Badge.TLabel")
        self.list_count_label.pack(side="right")
        search_card = ttk.Frame(left, style="Surface.TFrame")
        search_card.pack(fill="x", pady=(0, 9))
        ttk.Label(search_card, text="Arşivde ara", style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
        search = ttk.Entry(search_card, textvariable=self.search_var, font=("Segoe UI", 10))
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
        self.tree.tag_configure("odd", background="#f7f9f6")
        self.tree.tag_configure("even", background="#ffffff")

        record_header = ttk.Frame(right, style="Surface.TFrame")
        record_header.pack(fill="x", pady=(0, 10))
        heading_box = ttk.Frame(record_header, style="Surface.TFrame")
        heading_box.pack(side="left", fill="x", expand=True)
        ttk.Label(heading_box, textvariable=self.header_scientific, style="Surface.TLabel", font=("Segoe UI", 14, "bold italic"), wraplength=650).pack(anchor="w")
        ttk.Label(heading_box, textvariable=self.header_disease, style="Muted.TLabel", font=("Segoe UI", 10), wraplength=650).pack(anchor="w", pady=(2, 0))
        ttk.Label(heading_box, textvariable=self.header_group, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        metrics = ttk.Frame(record_header, style="Surface.TFrame")
        metrics.pack(side="left", padx=(18, 8))
        for idx, (key, label) in enumerate((("hosts", "Konukçu"), ("literature", "Kaynak"), ("photos", "Fotoğraf"), ("questions", "Soru"))):
            box = ttk.Frame(metrics, style="Card.TFrame", padding=(9, 5))
            box.grid(row=0, column=idx, padx=3)
            ttk.Label(box, textvariable=self.record_metric_vars[key], style="MetricValue.TLabel").pack()
            ttk.Label(box, text=label, style="MetricLabel.TLabel").pack()
        record_actions = ttk.Frame(record_header, style="Surface.TFrame")
        record_actions.pack(side="right")
        ttk.Button(record_actions, text="Dosyayı Aç", style="Primary.TButton", command=self.open_disease_file).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Fotoğraflar", command=self.open_photo_manager).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Dosyalar", command=self.open_file_manager).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="İncele", command=self.preview_record).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Düzenle", command=self.edit_record).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Geçmiş", command=self.open_history).pack(side="left", padx=(0, 5))
        ttk.Button(record_actions, text="Sil", style="Danger.TButton", command=self.delete_record).pack(side="left")

        # RC10.9: Hastalık bilgileri tek, büyük zengin metin alanında gösterilir.
        detail = ttk.LabelFrame(right, text="Hastalık bilgileri", padding=10)
        detail.pack(fill="both", expand=True)
        detail.columnconfigure(0, weight=1); detail.rowconfigure(0, weight=1)
        text = tk.Text(detail, wrap="word", relief="solid", borderwidth=1, background="#ffffff", foreground=COLORS["text"], padx=12, pady=10)
        scroll = ttk.Scrollbar(detail, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set, state="disabled")
        text.grid(row=0, column=0, sticky="nsew"); scroll.grid(row=0, column=1, sticky="ns")
        self.detail_texts["content_body"] = text

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
        for index, row in enumerate(rows):
            item = self.tree.insert("", "end", iid=str(row["id"]), values=(("★ " if row["favorite"] else "") + row["scientific_name"], row["disease_name"]), tags=(("even" if index % 2 == 0 else "odd"),))
            if current and int(row["id"]) == int(current):
                selected_item = item
        self.status_var.set("{} kayıt gösteriliyor · veritabanında toplam {} kayıt".format(len(rows), self.db.count()))
        try: self.list_count_label.configure(text="{} kayıt".format(len(rows)))
        except Exception: pass
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
        self.header_group.set(("Favori · " if record["favorite"] else "") + record["group_name"])
        try:
            self.record_metric_vars["hosts"].set(str(len(self.db.disease_hosts(disease_id))))
            self.record_metric_vars["literature"].set(str(len(self.db.disease_literature(disease_id))))
            self.record_metric_vars["photos"].set(str(sum(1 for a in self.db.attachments(disease_id) if a["file_type"] == "image")))
            self.record_metric_vars["questions"].set(str(self.db.quiz_question_count(disease_id)))
        except Exception:
            for value in self.record_metric_vars.values(): value.set("—")
        self.refresh_summary_card(record)
        try:
            self.context_panel.show_record(record)
        except Exception:
            pass
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
        for value in self.record_metric_vars.values(): value.set("0")
        try:
            self.context_panel.clear()
        except Exception:
            pass
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
        # Fotoğraf ve dosya listeleri artık kendi yöneticilerinde tutulur.

    def new_record(self):
        groups = self.db.list_groups(); key="new"
        draft=self.db.get_draft(key); initial=None; rich=None
        if draft and messagebox.askyesno(APP_NAME, "{} tarihli kaydedilmemiş yeni kayıt taslağı bulundu. Kurtarılsın mı?".format(draft["updated_at"]), parent=self): initial=draft["data"]; rich=draft["rich"]
        DiseaseEditor(self, groups, initial=initial, rich_initial=rich, on_save=self._save_new, on_draft=self.db.save_draft, draft_key=key, on_saved=self.db.delete_draft, database=self.db)

    def _save_new(self, data):
        rich_data = data.pop("_rich_text", {}); tags=[x.strip() for x in data.pop("_tags", "").replace(";", ",").split(",") if x.strip()]
        data.pop("_host_ids", None)
        host_relations = data.pop("_host_relations", [])
        new_id = self.db.add(data)
        self.db.replace_disease_hosts(new_id, host_relations)
        self.db.save_rich_text(new_id, rich_data); self.db.save_tags(new_id, tags)
        self.refresh_groups()
        self.refresh_list(select_id=new_id)

    def open_disease_file(self):
        if not self.selected_id:
            messagebox.showinfo(APP_NAME, "Önce bir hastalık kaydı seçin.", parent=self)
            return
        DiseaseFile(
            self, self.db, self.paths, self.selected_id,
            on_edit=self.edit_record, on_preview=self.preview_record,
            on_pdf=self.export_pdf_report, on_photos=self.open_photo_manager,
        )

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
        record = dict(self.db.get(self.selected_id)); record["_tags"] = ", ".join(self.db.tags(self.selected_id))
        host_rows = self.db.disease_hosts(self.selected_id)
        record["_host_ids"] = [int(r["id"]) for r in host_rows]
        record["_host_relations"] = [{"host_id":int(r["id"]),"relation_type":r["relation_type"],"scope_type":r["scope_type"],"relation_note":r["relation_note"],"is_excluded":int(r["is_excluded"])} for r in host_rows]
        record["hosts"] = self.db.disease_hosts_text(self.selected_id) or record.get("hosts", "")
        groups = self.db.list_groups(); key="edit:{}".format(self.selected_id)
        rich=self.db.rich_text(self.selected_id); draft=self.db.get_draft(key)
        if draft and messagebox.askyesno(APP_NAME, "{} tarihli kaydedilmemiş taslak bulundu. Kurtarılsın mı?".format(draft["updated_at"]), parent=self): record=draft["data"]; rich=draft["rich"]
        DiseaseEditor(self, groups, initial=record, rich_initial=rich, on_save=self._save_edit, on_draft=self.db.save_draft, draft_key=key, on_saved=self.db.delete_draft, database=self.db)

    def _save_edit(self, data):
        rich_data = data.pop("_rich_text", {}); tags=[x.strip() for x in data.pop("_tags", "").replace(";", ",").split(",") if x.strip()]
        data.pop("_host_ids", None)
        host_relations = data.pop("_host_relations", [])
        self.db.update(self.selected_id, data)
        self.db.replace_disease_hosts(self.selected_id, host_relations)
        self.db.save_rich_text(self.selected_id, rich_data); self.db.save_tags(self.selected_id, tags)
        self.refresh_groups()
        self.refresh_list(select_id=self.selected_id)

    def delete_record(self):
        if not self.selected_id:
            return
        record = self.db.get(self.selected_id)
        answer = messagebox.askyesno(
            APP_NAME,
            "'{}' kaydı Çöp Kutusu'na taşınsın mı?\n\nKayıt daha sonra geri yüklenebilir.".format(record["scientific_name"]),
            parent=self,
        )
        if answer:
            self.db.delete(self.selected_id)
            self.selected_id = None
            self.refresh_groups()
            self.refresh_list()

    def open_history(self):
        if not self.selected_id: messagebox.showinfo(APP_NAME,"Önce bir kayıt seçin.",parent=self); return
        win=tk.Toplevel(self); win.title("Kayıt geçmişi"); win.geometry("780x480"); win.transient(self)
        tree=ttk.Treeview(win,columns=("date","fields"),show="headings"); tree.heading("date",text="Tarih"); tree.heading("fields",text="Değişen alanlar"); tree.column("date",width=160); tree.column("fields",width=560); tree.pack(fill="both",expand=True,padx=12,pady=12)
        for r in self.db.history(self.selected_id): tree.insert("","end",iid=str(r["id"]),values=(r["created_at"],r["changed_fields"] or "Önceki sürüm"))
        def restore():
            sel=tree.selection()
            if not sel:return
            if messagebox.askyesno(APP_NAME,"Seçili eski sürüm geri yüklensin mi? Mevcut sürüm de geçmişe kaydedilecektir.",parent=win): self.db.restore_history(int(sel[0])); self.refresh_list(select_id=self.selected_id); win.destroy()
        ttk.Button(win,text="Seçili sürümü geri yükle",style="Primary.TButton",command=restore).pack(pady=(0,12))

    def open_trash(self):
        win=tk.Toplevel(self); win.title("Çöp Kutusu"); win.geometry("760x480"); win.transient(self)
        tree=ttk.Treeview(win,columns=("name","disease","date"),show="headings",selectmode="extended"); [tree.heading(c,text=t) for c,t in (("name","Etmen"),("disease","Hastalık"),("date","Silinme tarihi"))]; tree.pack(fill="both",expand=True,padx=12,pady=12)
        def fill():
            tree.delete(*tree.get_children())
            for r in self.db.trash(): tree.insert("","end",iid=str(r["id"]),values=(r["scientific_name"],r["disease_name"],r["deleted_at"]))
        def restore():
            for i in tree.selection(): self.db.restore_from_trash(int(i))
            fill(); self.refresh_groups(); self.refresh_list()
        def purge():
            ids=tree.selection()
            if ids and messagebox.askyesno(APP_NAME,"Seçili kayıtlar kalıcı olarak silinsin mi? Bu işlem geri alınamaz.",parent=win):
                for i in ids:self.db.permanent_delete(int(i))
                fill()
        bar=ttk.Frame(win); bar.pack(fill="x",padx=12,pady=(0,12)); ttk.Button(bar,text="Geri yükle",style="Primary.TButton",command=restore).pack(side="left"); ttk.Button(bar,text="Kalıcı sil",style="Danger.TButton",command=purge).pack(side="right"); fill()

    def bulk_actions(self):
        ids=[int(i) for i in self.tree.selection()]
        if not ids: messagebox.showinfo(APP_NAME,"Listeden bir veya daha fazla kayıt seçin. Çoklu seçim için Ctrl tuşunu kullanın.",parent=self); return
        win=tk.Toplevel(self); win.title("Toplu işlemler"); win.geometry("440x260"); win.transient(self); frame=ttk.Frame(win,padding=16); frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="{} kayıt seçildi".format(len(ids)),font=("Segoe UI",11,"bold")).pack(anchor="w")
        tag=tk.StringVar(); ttk.Label(frame,text="Eklenecek etiketler (virgülle):").pack(anchor="w",pady=(16,4)); ttk.Entry(frame,textvariable=tag).pack(fill="x")
        def add_tags(): self.db.add_tags_bulk(ids,[x.strip() for x in tag.get().replace(";",",").split(",") if x.strip()]); messagebox.showinfo(APP_NAME,"Etiketler eklendi.",parent=win); win.destroy()
        def favorite(value):
            for i in ids:
                r=dict(self.db.get(i)); r["favorite"]=value; self.db.update(i,r)
            self.refresh_list(); win.destroy()
        ttk.Button(frame,text="Etiketleri ekle",style="Primary.TButton",command=add_tags).pack(fill="x",pady=(12,4)); ttk.Button(frame,text="Favorilere ekle",command=lambda:favorite(1)).pack(fill="x",pady=4); ttk.Button(frame,text="Favorilerden çıkar",command=lambda:favorite(0)).pack(fill="x",pady=4)

    def refresh_attachments(self):
        if not self.selected_id: return
        try:
            self.record_metric_vars["photos"].set(str(len(self.db.image_attachments(self.selected_id))))
        except Exception:
            pass

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
        return

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

            if (record["content_body"] or "").strip():
                story.append(Paragraph("Hastalık bilgileri", heading_style))
                story.append(Paragraph(to_reportlab(record["content_body"], rich_map.get("content_body", {})), body_style))
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
        if self.settings.data.get("remember_window", True):
            try:
                self.settings.data["window_geometry"] = self.geometry()
                self.settings.save()
            except Exception:
                pass
        self.db.close()
        self.destroy()


