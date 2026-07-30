# -*- coding: utf-8 -*-
"""Bakım, tanılama, ayarlar ve yardım merkezi."""
from __future__ import print_function

from .common import *
import traceback


def _human_size(value):
    value = float(value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return "{:.1f} {}".format(value, unit)
        value /= 1024.0


class SettingsStore(object):
    DEFAULTS = {
        "theme": "Açık",
        "font_scale": "Normal",
        "open_dashboard": True,
        "remember_window": True,
        "auto_backup_days": 1,
        "thumbnail_size": "Orta",
        "default_export_dir": "",
        "window_geometry": "",
    }

    def __init__(self, paths):
        self.path = os.path.join(paths.data, "settings.json")
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                self.data.update(raw)
        except Exception:
            pass
        return self.data

    def save(self):
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
        if os.path.exists(self.path):
            os.remove(self.path)
        os.rename(temp, self.path)


class MaintenanceCenter(tk.Toplevel):
    def __init__(self, parent, db, paths):
        tk.Toplevel.__init__(self, parent); center_toplevel(self)
        self.parent = parent; self.db = db; self.paths = paths
        self.title("Bakım ve Tanılama Merkezi")
        self.geometry("850x590"); self.minsize(720, 480); self.transient(parent)
        self.status = tk.StringVar(value="Hazır")
        self._build(); self.refresh()

    def _build(self):
        shell = ttk.Frame(self, padding=16); shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Bakım ve Tanılama Merkezi", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Veritabanı, dosya bağlantıları ve önbellek durumunu denetleyin.", style="Muted.TLabel").pack(anchor="w", pady=(2, 12))
        self.tree = ttk.Treeview(shell, columns=("value", "state"), show="tree headings", height=14)
        self.tree.heading("#0", text="Denetim"); self.tree.heading("value", text="Değer"); self.tree.heading("state", text="Durum")
        self.tree.column("#0", width=390); self.tree.column("value", width=180); self.tree.column("state", width=120)
        self.tree.pack(fill="both", expand=True)
        bar = ttk.Frame(shell); bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text="Yeniden denetle", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Veritabanını doğrula", command=self.integrity_check).pack(side="left", padx=5)
        ttk.Button(bar, text="Optimize et", command=self.optimize).pack(side="left", padx=5)
        ttk.Button(bar, text="Eksik dosyaları bul", command=self.show_missing).pack(side="left", padx=5)
        ttk.Button(bar, text="Tanılama raporu", command=self.export_report).pack(side="left", padx=5)
        ttk.Label(shell, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

    def _stats(self):
        conn = self.db.conn
        disease_count = conn.execute("SELECT COUNT(*) FROM diseases WHERE COALESCE(deleted_at,'')='' ").fetchone()[0]
        photo_count = conn.execute("SELECT COUNT(*) FROM attachments WHERE file_type='image'").fetchone()[0]
        doc_count = conn.execute("SELECT COUNT(*) FROM attachments WHERE file_type<>'image'").fetchone()[0]
        history_count = conn.execute("SELECT COUNT(*) FROM disease_history").fetchone()[0]
        draft_count = conn.execute("SELECT COUNT(*) FROM disease_drafts").fetchone()[0]
        missing = self._missing_files()
        db_size = os.path.getsize(self.paths.database) if os.path.exists(self.paths.database) else 0
        backups = []
        if os.path.isdir(self.paths.backups):
            backups = [os.path.join(self.paths.backups, x) for x in os.listdir(self.paths.backups) if x.lower().endswith((".zip", ".db"))]
        latest = max((os.path.getmtime(x) for x in backups), default=0)
        latest_text = dt.datetime.fromtimestamp(latest).strftime("%d.%m.%Y %H:%M") if latest else "Yok"
        return [
            ("Veritabanı", _human_size(db_size), "Sağlıklı"),
            ("Aktif hastalık kaydı", disease_count, "Bilgi"),
            ("Fotoğraf", photo_count, "Bilgi"),
            ("Belge", doc_count, "Bilgi"),
            ("Kayıt geçmişi sürümü", history_count, "Bilgi"),
            ("Kurtarılabilir taslak", draft_count, "Dikkat" if draft_count else "Temiz"),
            ("Eksik dosya bağlantısı", len(missing), "Dikkat" if missing else "Temiz"),
            ("Son yedek", latest_text, "Bilgi" if latest else "Dikkat"),
            ("SQLite journal modu", conn.execute("PRAGMA journal_mode").fetchone()[0].upper(), "Bilgi"),
            ("Veritabanı şema sürümü", self.db.schema_version() if hasattr(self.db, "schema_version") else "—", "Bilgi"),
        ]

    def _missing_files(self):
        missing = []
        for row in self.db.conn.execute("SELECT id, relative_path FROM attachments ORDER BY id"):
            rel = row["relative_path"] or ""
            candidates = [os.path.join(self.paths.base, rel), os.path.join(self.paths.images, rel), os.path.join(self.paths.documents, rel)]
            if rel and not any(os.path.exists(p) for p in candidates):
                missing.append((row["id"], rel))
        return missing

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        try:
            for label, value, state in self._stats():
                self.tree.insert("", "end", text=label, values=(value, state))
            self.status.set("Denetim tamamlandı: {}".format(dt.datetime.now().strftime("%H:%M:%S")))
        except Exception as exc:
            self.status.set("Denetim başarısız: {}".format(exc))

    def integrity_check(self):
        try:
            result = self.db.conn.execute("PRAGMA integrity_check").fetchone()[0]
            if str(result).lower() == "ok": messagebox.showinfo(APP_NAME, "Veritabanı bütünlük kontrolü başarılı.", parent=self)
            else: messagebox.showwarning(APP_NAME, "SQLite denetim sonucu:\n{}".format(result), parent=self)
        except Exception as exc: messagebox.showerror(APP_NAME, str(exc), parent=self)

    def optimize(self):
        try:
            self.status.set("Veritabanı optimize ediliyor..."); self.update_idletasks()
            self.db.conn.execute("ANALYZE"); self.db.conn.commit(); self.db.conn.execute("VACUUM")
            self.refresh(); messagebox.showinfo(APP_NAME, "Veritabanı indeksleri analiz edildi ve dosya optimize edildi.", parent=self)
        except Exception as exc: messagebox.showerror(APP_NAME, "Optimizasyon başarısız:\n{}".format(exc), parent=self)

    def show_missing(self):
        missing = self._missing_files()
        win = tk.Toplevel(self); win.title("Eksik dosya bağlantıları"); win.geometry("720x420"); win.transient(self)
        tree = ttk.Treeview(win, columns=("id", "path"), show="headings")
        tree.heading("id", text="Ek ID"); tree.heading("path", text="Kayıtlı yol"); tree.column("id", width=80); tree.column("path", width=590)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for item in missing: tree.insert("", "end", values=item)
        if not missing: ttk.Label(win, text="Eksik dosya bağlantısı bulunmadı.", padding=20).place(relx=.5, rely=.5, anchor="center")

    def export_report(self):
        out = filedialog.asksaveasfilename(parent=self, title="Tanılama raporu", initialdir=self.paths.exports,
            initialfile="Fitopatoloji_Tanilama_{}.txt".format(dt.datetime.now().strftime("%Y%m%d_%H%M")), defaultextension=".txt", filetypes=[("Metin", "*.txt")])
        if not out: return
        try:
            lines = ["{} {} - Tanılama Raporu".format(APP_NAME, APP_VERSION), "Oluşturma: {}".format(dt.datetime.now()), ""]
            for label, value, state in self._stats(): lines.append("{}: {} [{}]".format(label, value, state))
            lines.extend(["", "SQLite integrity_check: {}".format(self.db.conn.execute("PRAGMA integrity_check").fetchone()[0])])
            with open(out, "w", encoding="utf-8") as handle: handle.write("\n".join(lines))
            messagebox.showinfo(APP_NAME, "Tanılama raporu oluşturuldu:\n{}".format(out), parent=self)
        except Exception as exc: messagebox.showerror(APP_NAME, str(exc), parent=self)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, paths, store):
        tk.Toplevel.__init__(self, parent); center_toplevel(self); self.parent=parent; self.paths=paths; self.store=store
        self.title("Ayarlar Merkezi"); self.geometry("600x470"); self.transient(parent); self.grab_set()
        d=store.data
        self.theme=tk.StringVar(value=d.get("theme","Açık")); self.font=tk.StringVar(value=d.get("font_scale","Normal"))
        self.dashboard=tk.BooleanVar(value=bool(d.get("open_dashboard",True))); self.remember=tk.BooleanVar(value=bool(d.get("remember_window",True)))
        self.backup=tk.IntVar(value=int(d.get("auto_backup_days",1))); self.thumb=tk.StringVar(value=d.get("thumbnail_size","Orta")); self.export=tk.StringVar(value=d.get("default_export_dir","") or paths.exports)
        self._build()

    def _row(self, parent, label, widget, row):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",padx=(0,14),pady=7); widget.grid(row=row,column=1,sticky="ew",pady=7)

    def _build(self):
        f=ttk.Frame(self,padding=18); f.pack(fill="both",expand=True); f.columnconfigure(1,weight=1)
        ttk.Label(f,text="Ayarlar Merkezi",style="Title.TLabel").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,12))
        self._row(f,"Tema",ttk.Combobox(f,textvariable=self.theme,values=("Açık","Koyu"),state="readonly"),1)
        self._row(f,"Yazı ölçeği",ttk.Combobox(f,textvariable=self.font,values=("Küçük","Normal","Büyük"),state="readonly"),2)
        self._row(f,"Thumbnail boyutu",ttk.Combobox(f,textvariable=self.thumb,values=("Küçük","Orta","Büyük"),state="readonly"),3)
        self._row(f,"Otomatik yedek aralığı (gün)",ttk.Spinbox(f,from_=1,to=30,textvariable=self.backup,width=8),4)
        exp=ttk.Frame(f); ttk.Entry(exp,textvariable=self.export).pack(side="left",fill="x",expand=True); ttk.Button(exp,text="Seç",command=self.choose_export).pack(side="left",padx=(5,0))
        self._row(f,"Varsayılan dışa aktarma klasörü",exp,5)
        ttk.Checkbutton(f,text="Program açıldığında Çalışma Merkezini göster",variable=self.dashboard).grid(row=6,column=0,columnspan=2,sticky="w",pady=7)
        ttk.Checkbutton(f,text="Ana pencere boyutunu ve konumunu hatırla",variable=self.remember).grid(row=7,column=0,columnspan=2,sticky="w",pady=7)
        ttk.Label(f,text="Tema ve yazı ölçeği değişiklikleri uygulama yeniden açıldığında tam olarak uygulanır.",style="Muted.TLabel",wraplength=530).grid(row=8,column=0,columnspan=2,sticky="w",pady=(12,0))
        bar=ttk.Frame(f); bar.grid(row=9,column=0,columnspan=2,sticky="e",pady=(22,0)); ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(bar,text="Kaydet",command=self.save).pack(side="right",padx=6)

    def choose_export(self):
        value=filedialog.askdirectory(parent=self,initialdir=self.export.get() or self.paths.exports)
        if value:self.export.set(value)

    def save(self):
        self.store.data.update({"theme":self.theme.get(),"font_scale":self.font.get(),"thumbnail_size":self.thumb.get(),"auto_backup_days":max(1,int(self.backup.get())),"default_export_dir":self.export.get().strip(),"open_dashboard":bool(self.dashboard.get()),"remember_window":bool(self.remember.get())})
        try:self.store.save(); messagebox.showinfo(APP_NAME,"Ayarlar kaydedildi.",parent=self); self.destroy()
        except Exception as exc:messagebox.showerror(APP_NAME,"Ayarlar kaydedilemedi:\n{}".format(exc),parent=self)


class HelpCenter(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent); center_toplevel(self); self.title("Yardım Merkezi"); self.geometry("820x590"); self.transient(parent)
        shell=ttk.Frame(self,padding=14); shell.pack(fill="both",expand=True)
        ttk.Label(shell,text="Yardım Merkezi",style="Title.TLabel").pack(anchor="w")
        book=ttk.Notebook(shell); book.pack(fill="both",expand=True,pady=(10,0))
        topics=[
            ("Başlangıç","Yeni kayıt için sol menüdeki ‘Yeni kayıt’ düğmesini kullanın. Kayıt seçildiğinde İncele, Hastalık Dosyası, Fotoğraf Yöneticisi ve PDF işlemleri etkinleşir."),
            ("Kayıt ve editör","Ctrl+S kaydeder. Kalın, italik, altı çizili, üst/alt simge, listeler ve bilimsel semboller editör araç çubuğundan uygulanabilir. Kaydedilmemiş taslaklar otomatik kurtarılır."),
            ("Fotoğraflar","Fotoğraf Yöneticisi çoklu ekleme, thumbnail kataloğu, ana fotoğraf, sıralama, açıklama ve anotasyon işlemlerini bir araya getirir."),
            ("Rapor ve monografi","İncele ekranı tek kayıt önizlemesidir. Monografi Oluşturucu birden çok hastalığı kapak, içindekiler, ortak kaynakça ve indekslerle PDF/HTML kitap haline getirir."),
            ("Güvenlik","Yedekleri düzenli oluşturun. Kayıt geçmişi eski sürümlere dönüş sağlar; silinen kayıtlar önce Çöp Kutusuna taşınır. Bakım Merkezi veritabanı bütünlüğünü ve eksik dosyaları denetler."),
            ("Kısayollar","Ctrl+K: Komut paleti\nCtrl+S: Kaydet\nCtrl+N: Yeni kayıt\nCtrl+F: Arama\nCtrl+W: Çalışma alanı sekmesini kapat\nCtrl+B/I/U: Kalın / İtalik / Altı çizili"),
        ]
        for title,text in topics:
            frame=ttk.Frame(book,padding=18); book.add(frame,text=title)
            box=tk.Text(frame,wrap="word",font=("Segoe UI",11),relief="flat",padx=10,pady=10); box.pack(fill="both",expand=True); box.insert("1.0",text); box.configure(state="disabled")
