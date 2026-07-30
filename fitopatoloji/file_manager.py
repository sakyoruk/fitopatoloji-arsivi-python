# -*- coding: utf-8 -*-
from .common import *

class FileManager(tk.Toplevel):
    """Bir hastalığa bağlı fotoğraf dışındaki belgeleri yönetir."""
    def __init__(self, master, db, paths, disease_id, refresh_callback=None):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.db, self.paths, self.disease_id = db, paths, disease_id
        self.refresh_callback = refresh_callback
        self.title("Dosya yöneticisi"); self.geometry("760x440"); self.minsize(620, 360); self.transient(master)
        toolbar=ttk.Frame(self,padding=10); toolbar.pack(fill="x")
        ttk.Button(toolbar,text="Dosya ekle",style="Primary.TButton",command=self.add_file).pack(side="left")
        ttk.Button(toolbar,text="Aç",command=self.open_file).pack(side="left",padx=5)
        ttk.Button(toolbar,text="Kaldır",style="Danger.TButton",command=self.remove_file).pack(side="left")
        self.tree=ttk.Treeview(self,columns=("name","description","date"),show="headings",selectmode="browse")
        for col,title,width in (("name","Dosya",330),("description","Açıklama",260),("date","Eklenme",130)):
            self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor="w")
        self.tree.pack(fill="both",expand=True,padx=10,pady=(0,10)); self.tree.bind("<Double-1>",lambda _e:self.open_file())
        self.refresh()
    def refresh(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        for row in self.db.attachments(self.disease_id):
            if row["file_type"] == "image": continue
            self.tree.insert("","end",iid=str(row["id"]),values=(os.path.basename(row["relative_path"]).split("_",1)[-1],row["description"],row["created_at"]))
        if self.refresh_callback: self.refresh_callback()
    def selected(self):
        sel=self.tree.selection(); return self.db.get_attachment(int(sel[0])) if sel else None
    def add_file(self):
        files=filedialog.askopenfilenames(parent=self,title="Dosya ekle",filetypes=[("Tüm dosyalar","*.*")])
        if not files:return
        description=simpledialog.askstring(APP_NAME,"Dosya açıklaması (isteğe bağlı):",parent=self) or ""
        target=os.path.join(self.paths.documents,str(self.disease_id)); os.makedirs(target,exist_ok=True)
        for src in files:
            name="{}_{}".format(uuid.uuid4().hex[:10],os.path.basename(src)); dst=os.path.join(target,name); shutil.copy2(src,dst)
            rel=os.path.relpath(dst,self.paths.base); self.db.add_attachment(self.disease_id,"document",rel,description)
        self.refresh()
    def open_file(self):
        row=self.selected()
        if not row:return
        path=os.path.join(self.paths.base,row["relative_path"])
        try:
            if sys.platform.startswith("win"): os.startfile(path)
            elif sys.platform=="darwin": subprocess.Popen(["open",path])
            else: subprocess.Popen(["xdg-open",path])
        except Exception as exc: messagebox.showerror(APP_NAME,"Dosya açılamadı:\n{}".format(exc),parent=self)
    def remove_file(self):
        row=self.selected()
        if not row:return
        if not messagebox.askyesno(APP_NAME,"Seçili dosya arşivden kaldırılsın mı?",parent=self):return
        path=os.path.join(self.paths.base,row["relative_path"]); self.db.delete_attachment(row["id"])
        try:
            if os.path.isfile(path): os.remove(path)
        except Exception: pass
        self.refresh()
