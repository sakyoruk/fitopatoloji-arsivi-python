# -*- coding: utf-8 -*-
"""RC2 sorun bildirme ve gizlilik odaklı tanılama paketi."""
from __future__ import print_function
from .common import *
import platform
import traceback

class IssueReportDialog(tk.Toplevel):
    def __init__(self, parent, db, paths):
        tk.Toplevel.__init__(self, parent)
        self.parent=parent; self.db=db; self.paths=paths
        self.title("Sorun Bildir / Tanılama Paketi")
        self.geometry("720x560"); self.minsize(620,480); self.transient(parent); self.grab_set()
        self.include_logs=tk.BooleanVar(value=True)
        self._build()

    def _build(self):
        shell=ttk.Frame(self,padding=16); shell.pack(fill="both",expand=True)
        ttk.Label(shell,text="Sorun Bildir",style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell,text="Kişisel hastalık kayıtları, fotoğraflar ve belgeler pakete eklenmez.",style="Muted.TLabel").pack(anchor="w",pady=(2,10))
        ttk.Label(shell,text="Sorunu nasıl tekrar oluşturabiliriz?").pack(anchor="w")
        self.description=tk.Text(shell,height=10,wrap="word",font=("Segoe UI",10),padx=8,pady=8)
        self.description.pack(fill="both",expand=True,pady=(4,10))
        ttk.Checkbutton(shell,text="Son hata günlüklerini ekle",variable=self.include_logs).pack(anchor="w")
        ttk.Label(shell,text="Pakete sürüm, Python/Windows bilgisi, SQLite sağlık özeti ve isteğe bağlı hata günlükleri eklenir.",style="Muted.TLabel",wraplength=650).pack(anchor="w",pady=(5,12))
        bar=ttk.Frame(shell); bar.pack(fill="x")
        ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right")
        ttk.Button(bar,text="Tanılama paketi oluştur",style="Primary.TButton",command=self.create_package).pack(side="right",padx=6)

    def _health_text(self):
        conn=self.db.conn
        lines=["{} {}".format(APP_NAME,APP_VERSION),
               "Oluşturma: {}".format(dt.datetime.now().isoformat()),
               "Windows: {}".format(platform.platform()),
               "Python: {}".format(sys.version.replace("\n"," ")),
               "SQLite: {}".format(sqlite3.sqlite_version),
               "Şema sürümü: {}".format(self.db.schema_version() if hasattr(self.db,"schema_version") else "Bilinmiyor"),
               "Integrity check: {}".format(conn.execute("PRAGMA integrity_check").fetchone()[0]),
               "Aktif kayıt: {}".format(conn.execute("SELECT COUNT(*) FROM diseases WHERE COALESCE(deleted_at,'')='' ").fetchone()[0]),
               "Ek dosya: {}".format(conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0])]
        return "\n".join(lines)

    def create_package(self):
        out=filedialog.asksaveasfilename(parent=self,title="Tanılama paketini kaydet",initialdir=self.paths.exports,
            initialfile="Fitopatoloji_RC2_Tanilama_{}.zip".format(dt.datetime.now().strftime("%Y%m%d_%H%M")),
            defaultextension=".zip",filetypes=[("ZIP paketi","*.zip")])
        if not out:return
        try:
            with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("sorun_aciklamasi.txt",self.description.get("1.0","end-1c").strip())
                zf.writestr("sistem_ve_saglik.txt",self._health_text())
                zf.writestr("GIZLILIK.txt","Bu paket veritabanı, hastalık içerikleri, fotoğraflar veya belgeler içermez.\n")
                if self.include_logs.get():
                    log_dir=os.path.join(self.paths.data,"Logs")
                    if os.path.isdir(log_dir):
                        logs=sorted([os.path.join(log_dir,x) for x in os.listdir(log_dir) if x.lower().endswith('.log')],key=os.path.getmtime,reverse=True)[:5]
                        for path in logs: zf.write(path,os.path.join("logs",os.path.basename(path)))
            messagebox.showinfo(APP_NAME,"Tanılama paketi oluşturuldu:\n{}".format(out),parent=self); self.destroy()
        except Exception as exc:
            messagebox.showerror(APP_NAME,"Paket oluşturulamadı:\n{}".format(exc),parent=self)
