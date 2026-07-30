# -*- coding: utf-8 -*-
"""Araştırmacı çalışma alanı: sekmeler, bölünmüş görünüm, notlar ve görevler."""
from .common import *
from .rich_utils import apply_to_text_widget

VIEW_FIELDS = [
    ("Genel", [("Etmen grubu", "group_name"), ("Sinonimler", "synonyms")]),
    ("Konukçular", [("Konukçular", "hosts"), ("Etkilenen organlar", "affected_organs")]),
    ("Belirtiler", [("Belirtiler", "symptoms"), ("Etmenin özellikleri", "pathogen_features")]),
    ("Epidemiyoloji", [("Hastalık döngüsü", "disease_cycle"), ("Epidemiyoloji", "epidemiology")]),
    ("Tanı ve mücadele", [("Ayırıcı teşhis", "differential_diagnosis"), ("Kültürel mücadele", "cultural_control"),
                           ("Biyolojik mücadele", "biological_control"), ("Kimyasal mücadele", "chemical_control")]),
    ("Kaynakça ve notlar", [("Kaynaklar", "sources"), ("Kişisel notlar", "notes")]),
]

class Workspace(tk.Toplevel):
    def __init__(self, master, db, paths, initial_id=None, on_open=None, on_edit=None):
        tk.Toplevel.__init__(self, master)
        self.db, self.paths = db, paths
        self.on_open, self.on_edit = on_open, on_edit
        self.open_ids = []
        self.views = {}
        self.title("Araştırmacı Çalışma Alanı")
        self.geometry("1380x840")
        self.minsize(1050, 650)
        self.transient(master)
        self._build()
        self._load_note()
        self._refresh_tasks()
        if initial_id:
            self.open_disease(initial_id)
        self.bind("<Control-w>", lambda _e: self.close_current())
        self.bind("<Control-s>", lambda _e: self.save_note())
        self.bind("<Escape>", lambda _e: self.destroy())

    def _build(self):
        top = ttk.Frame(self, padding=(14,10)); top.pack(fill="x")
        ttk.Label(top, text="Araştırmacı Çalışma Alanı", font=("Segoe UI", 17, "bold")).pack(side="left")
        ttk.Button(top, text="Hastalık ekle", style="Primary.TButton", command=self.choose_disease).pack(side="right", padx=3)
        ttk.Button(top, text="Bölünmüş görünüm", command=self.split_view).pack(side="right", padx=3)
        ttk.Button(top, text="Sekmeyi kapat", command=self.close_current).pack(side="right", padx=3)

        outer = ttk.Panedwindow(self, orient="horizontal"); outer.pack(fill="both", expand=True, padx=12, pady=(0,12))
        main = ttk.Frame(outer); side = ttk.Frame(outer, padding=(10,4))
        outer.add(main, weight=5); outer.add(side, weight=2)
        self.tabs = ttk.Notebook(main); self.tabs.pack(fill="both", expand=True)

        side_tabs = ttk.Notebook(side); side_tabs.pack(fill="both", expand=True)
        note_tab = ttk.Frame(side_tabs, padding=8); task_tab = ttk.Frame(side_tabs, padding=8)
        side_tabs.add(note_tab, text="Not Defteri"); side_tabs.add(task_tab, text="Görevler")
        ttk.Label(note_tab, text="Çalışma notları", style="Section.TLabel").pack(anchor="w")
        self.note = tk.Text(note_tab, wrap="word", undo=True, font=("Segoe UI",10), padx=8, pady=8)
        self.note.pack(fill="both", expand=True, pady=(6,6))
        ttk.Button(note_tab, text="Notları kaydet", style="Primary.TButton", command=self.save_note).pack(fill="x")

        add = ttk.Frame(task_tab); add.pack(fill="x")
        self.task_var = tk.StringVar(); ttk.Entry(add, textvariable=self.task_var).pack(side="left", fill="x", expand=True)
        ttk.Button(add, text="Ekle", command=self.add_task).pack(side="left", padx=(5,0))
        self.task_tree = ttk.Treeview(task_tab, columns=("disease","status"), show="tree headings", selectmode="browse")
        self.task_tree.heading("#0", text="Görev"); self.task_tree.heading("disease", text="Hastalık"); self.task_tree.heading("status", text="Durum")
        self.task_tree.column("#0", width=230); self.task_tree.column("disease", width=150); self.task_tree.column("status", width=75, anchor="center")
        self.task_tree.pack(fill="both", expand=True, pady=7)
        row = ttk.Frame(task_tab); row.pack(fill="x")
        ttk.Button(row, text="Tamamlandı / Geri al", command=self.toggle_task).pack(side="left")
        ttk.Button(row, text="Sil", style="Danger.TButton", command=self.delete_task).pack(side="right")

    def choose_disease(self):
        rows = self.db.search("", "", "", "", "", False)
        dlg = tk.Toplevel(self); dlg.title("Hastalık seç"); dlg.geometry("620x500"); dlg.transient(self)
        q = tk.StringVar(); ttk.Entry(dlg, textvariable=q).pack(fill="x", padx=10, pady=10)
        tree = ttk.Treeview(dlg, columns=("disease",), show="tree headings")
        tree.heading("#0", text="Etmen"); tree.heading("disease", text="Hastalık"); tree.pack(fill="both", expand=True, padx=10)
        def fill(*_):
            text=q.get().lower().strip(); tree.delete(*tree.get_children())
            for r in rows:
                blob=((r["scientific_name"] or "")+" "+(r["disease_name"] or "")).lower()
                if not text or text in blob: tree.insert("","end",iid=str(r["id"]),text=r["scientific_name"],values=(r["disease_name"],))
        def open_it(_e=None):
            sel=tree.selection()
            if sel: self.open_disease(int(sel[0])); dlg.destroy()
        q.trace_add("write", fill) if hasattr(q,"trace_add") else q.trace("w",fill)
        fill(); tree.bind("<Double-1>",open_it); ttk.Button(dlg,text="Aç",style="Primary.TButton",command=open_it).pack(pady=8)

    def open_disease(self, disease_id):
        disease_id=int(disease_id)
        if disease_id in self.open_ids:
            self.tabs.select(self.views[disease_id]["frame"]); return
        r=self.db.get(disease_id)
        if not r: return
        frame=ttk.Frame(self.tabs, padding=8)
        self.tabs.add(frame, text=(r["disease_name"] or r["scientific_name"] or "Kayıt")[:28])
        self.open_ids.append(disease_id); self.views[disease_id]={"frame":frame}
        self._build_record_view(frame,disease_id)
        self.tabs.select(frame)

    def _build_record_view(self, parent, disease_id):
        r=self.db.get(disease_id); rich=self.db.rich_text(disease_id)
        head=ttk.Frame(parent); head.pack(fill="x", pady=(0,8))
        box=ttk.Frame(head); box.pack(side="left",fill="x",expand=True)
        ttk.Label(box,text=r["scientific_name"] or "Adsız",font=("Segoe UI",16,"bold italic")).pack(anchor="w")
        ttk.Label(box,text=r["disease_name"] or "",style="Muted.TLabel").pack(anchor="w")
        ttk.Button(head,text="Ana ekranda aç",command=lambda:self._open_main(disease_id)).pack(side="right",padx=3)
        ttk.Button(head,text="Düzenle",style="Primary.TButton",command=lambda:self._edit(disease_id)).pack(side="right",padx=3)
        canvas=tk.Canvas(parent,highlightthickness=0,background="#f4f7f5"); sb=ttk.Scrollbar(parent,orient="vertical",command=canvas.yview)
        holder=ttk.Frame(canvas,padding=(6,4,12,12)); win=canvas.create_window((0,0),window=holder,anchor="nw")
        holder.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(win,width=e.width)); canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        for section, fields in VIEW_FIELDS:
            vals=[(label,key,(r[key] or "").strip()) for label,key in fields if (r[key] or "").strip()]
            if not vals: continue
            card=ttk.LabelFrame(holder,text=section.upper(),padding=10); card.pack(fill="x",pady=(0,8))
            for label,key,value in vals:
                ttk.Label(card,text=label,font=("Segoe UI",9,"bold")).pack(anchor="w")
                txt=tk.Text(card,wrap="word",height=max(2,min(7,value.count("\n")+2)),relief="flat",padx=5,pady=4,cursor="arrow")
                txt.pack(fill="x",pady=(1,6)); txt.insert("1.0",value); apply_to_text_widget(txt,value,rich.get(key,{}),"1.0",9); txt.configure(state="disabled")

    def split_view(self):
        if len(self.open_ids)<2:
            messagebox.showinfo(APP_NAME,"Bölünmüş görünüm için en az iki hastalık sekmesi açın.",parent=self); return
        current=self.current_id(); other=next((x for x in self.open_ids if x!=current),None)
        if not current or not other:return
        dlg=tk.Toplevel(self); dlg.title("Bölünmüş görünüm"); dlg.geometry("1360x780"); dlg.transient(self)
        pane=ttk.Panedwindow(dlg,orient="horizontal"); pane.pack(fill="both",expand=True,padx=8,pady=8)
        for did in (current,other):
            f=ttk.Frame(pane,padding=5); pane.add(f,weight=1); self._build_record_view(f,did)

    def current_id(self):
        tab=self.tabs.select()
        for did,data in self.views.items():
            if str(data["frame"])==tab:return did
        return None

    def close_current(self):
        did=self.current_id()
        if did is None:return
        frame=self.views.pop(did)["frame"]; self.tabs.forget(frame); frame.destroy(); self.open_ids.remove(did)

    def _open_main(self,did):
        if self.on_open:self.on_open(did)
    def _edit(self,did):
        if self.on_open:self.on_open(did)
        if self.on_edit:self.after(20,self.on_edit)

    def _load_note(self):
        self.note.delete("1.0","end"); self.note.insert("1.0",self.db.workspace_note())
    def save_note(self):
        self.db.save_workspace_note(self.note.get("1.0","end-1c"));
        messagebox.showinfo(APP_NAME,"Çalışma notları kaydedildi.",parent=self)
    def add_task(self):
        text=self.task_var.get().strip()
        if not text:return
        self.db.add_task(self.current_id(),text); self.task_var.set(""); self._refresh_tasks()
    def _refresh_tasks(self):
        self.task_tree.delete(*self.task_tree.get_children())
        for row in self.db.tasks():
            self.task_tree.insert("","end",iid=str(row["id"]),text=row["task_text"],values=(row["disease_name"] or "Genel","Tamam" if row["is_done"] else "Açık"))
    def toggle_task(self):
        sel=self.task_tree.selection()
        if sel:self.db.toggle_task(int(sel[0])); self._refresh_tasks()
    def delete_task(self):
        sel=self.task_tree.selection()
        if sel:self.db.delete_task(int(sel[0])); self._refresh_tasks()
