# -*- coding: utf-8 -*-
from .common import *

AGENT_GROUPS = [
    "Mantar", "Oomycete", "Bakteri", "Fitoplazma", "Spiroplazma",
    "Virüs", "Viroid", "Nematod", "Parazitik bitki",
    "Etmeni bilinmeyen hastalık", "Fizyolojik / abiyotik bozukluk",
]
TAXON_RANKS = [
    ("domain_name", "Üst âlem"), ("kingdom_name", "Âlem"),
    ("phylum_name", "Şube"), ("subphylum_name", "Alt şube"),
    ("class_name", "Sınıf"), ("order_name", "Takım"),
    ("family_name", "Familya"), ("genus_name", "Cins"),
    ("species_name", "Tür"), ("subspecies_name", "Alt tür"),
    ("pathovar", "Patovar"), ("forma_specialis", "Forma specialis"),
    ("strain_name", "Irk / strain"), ("isolate_name", "İzolat"),
]

class TaxonomyCatalog(tk.Toplevel):
    def __init__(self, master, db):
        tk.Toplevel.__init__(self, master)
        self.db = db
        self.title("Taksonomi Kataloğu")
        self.geometry("920x600")
        self.minsize(760, 480)
        self.transient(master)
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self, padding=12); top.pack(fill="x")
        ttk.Label(top, text="Taksonomi Kataloğu", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(top, text="Yeni takson", style="Primary.TButton", command=self.add_taxon).pack(side="right")
        body = ttk.Frame(self, padding=(12,0,12,12)); body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=("rank","name","parent","synonyms"), show="headings")
        for key, text, width in [("rank","Basamak",130),("name","Ad",230),("parent","Üst takson",220),("synonyms","Eş adlar",260)]:
            self.tree.heading(key, text=text); self.tree.column(key, width=width, anchor="w")
        y = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=y.set)
        self.tree.pack(side="left", fill="both", expand=True); y.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e:self.edit_taxon())
        bottom = ttk.Frame(self, padding=(12,0,12,12)); bottom.pack(fill="x")
        ttk.Button(bottom, text="Düzenle", command=self.edit_taxon).pack(side="right")
        ttk.Button(bottom, text="Sil", style="Danger.TButton", command=self.delete_taxon).pack(side="right", padx=6)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.taxonomy_list():
            self.tree.insert("","end",iid=str(row["id"]),values=(row["rank"],row["name"],row["parent_name"] or "",row["synonyms"] or ""))

    def _dialog(self, row=None):
        dlg=tk.Toplevel(self); dlg.title("Takson düzenle" if row else "Yeni takson"); dlg.transient(self); dlg.grab_set(); dlg.geometry("520x310")
        frm=ttk.Frame(dlg,padding=14); frm.pack(fill="both",expand=True); frm.columnconfigure(1,weight=1)
        rank=tk.StringVar(value=(row["rank"] if row else "Familya")); name=tk.StringVar(value=(row["name"] if row else "")); parent=tk.StringVar(value=(row["parent_name"] if row else "")); synonyms=tk.StringVar(value=(row["synonyms"] if row else ""))
        ranks=[label for _,label in TAXON_RANKS]
        for i,(label,var,widget) in enumerate([
            ("Basamak",rank,"combo"),("Ad",name,"entry"),("Üst takson",parent,"entry"),("Eş adlar",synonyms,"entry")]):
            ttk.Label(frm,text=label).grid(row=i,column=0,sticky="w",pady=6,padx=(0,10))
            w=ttk.Combobox(frm,textvariable=var,values=ranks,state="readonly") if widget=="combo" else ttk.Entry(frm,textvariable=var)
            w.grid(row=i,column=1,sticky="ew",pady=6)
        def save():
            if not name.get().strip(): messagebox.showwarning(APP_NAME,"Takson adı boş olamaz.",parent=dlg); return
            self.db.taxonomy_save(row["id"] if row else None,rank.get(),name.get(),parent.get(),synonyms.get()); dlg.destroy(); self.refresh()
        ttk.Button(frm,text="Kaydet",style="Primary.TButton",command=save).grid(row=5,column=1,sticky="e",pady=(18,0))
    def add_taxon(self): self._dialog()
    def edit_taxon(self):
        sel=self.tree.selection();
        if sel: self._dialog(self.db.taxonomy_get(int(sel[0])))
    def delete_taxon(self):
        sel=self.tree.selection();
        if sel and messagebox.askyesno(APP_NAME,"Seçili takson silinsin mi?",parent=self): self.db.taxonomy_delete(int(sel[0])); self.refresh()

class HostCatalog(tk.Toplevel):
    def __init__(self, master, db, select_mode=False, disease_id=None, on_change=None, on_select=None, preselected_ids=None):
        tk.Toplevel.__init__(self, master)
        self.db=db; self.select_mode=select_mode; self.disease_id=disease_id; self.on_change=on_change; self.on_select=on_select; self.preselected_ids=set(int(x) for x in (preselected_ids or []))
        self.title("Konukçu Kataloğu")
        self.geometry("980x650"); self.minsize(780,500); self.transient(master)
        self._build(); self.refresh()

    def _build(self):
        top=ttk.Frame(self,padding=12); top.pack(fill="x")
        ttk.Label(top,text="Konukçu Kataloğu",font=("Segoe UI",14,"bold")).pack(side="left")
        ttk.Button(top,text="Yeni konukçu",style="Primary.TButton",command=self.add_host).pack(side="right")
        self.query=tk.StringVar(); entry=ttk.Entry(top,textvariable=self.query,width=28); entry.pack(side="right",padx=8); entry.bind("<KeyRelease>",lambda _e:self.refresh())
        body=ttk.Frame(self,padding=(12,0,12,8)); body.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(body,columns=("common","scientific","family","genus","rank"),show="headings",selectmode="extended")
        for key,text,width in [("common","Türkçe ad",170),("scientific","Bilimsel ad",250),("family","Familya",170),("genus","Cins",150),("rank","Düzey",90)]: self.tree.heading(key,text=text); self.tree.column(key,width=width,anchor="w")
        y=ttk.Scrollbar(body,orient="vertical",command=self.tree.yview); self.tree.configure(yscrollcommand=y.set); self.tree.pack(side="left",fill="both",expand=True); y.pack(side="right",fill="y")
        self.tree.bind("<Double-1>",lambda _e:self.choose() if self.select_mode else self.edit_host())
        bottom=ttk.Frame(self,padding=(12,0,12,12)); bottom.pack(fill="x")
        ttk.Button(bottom,text="Sil",style="Danger.TButton",command=self.delete_host).pack(side="right")
        ttk.Button(bottom,text="Düzenle",command=self.edit_host).pack(side="right",padx=6)
        if self.select_mode:
            ttk.Button(bottom,text="Seçili konukçuları hastalığa ekle",style="Primary.TButton",command=self.choose).pack(side="left")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.host_list(self.query.get()):
            iid=str(r["id"]); self.tree.insert("","end",iid=iid,values=(r["common_name"],r["scientific_name"],r["family_name"],r["genus_name"],r["taxon_level"]))
            if int(r["id"]) in self.preselected_ids: self.tree.selection_add(iid)
    def _dialog(self,row=None):
        dlg=tk.Toplevel(self); dlg.title("Konukçu düzenle" if row else "Yeni konukçu"); dlg.transient(self); dlg.grab_set(); dlg.geometry("560x470")
        frm=ttk.Frame(dlg,padding=14); frm.pack(fill="both",expand=True); frm.columnconfigure(1,weight=1)
        fields=[("common_name","Türkçe ad"),("scientific_name","Bilimsel ad"),("family_name","Familya"),("genus_name","Cins"),("species_name","Tür epiteti"),("alternative_names","Alternatif adlar"),("notes","Notlar")]
        vars={k:tk.StringVar(value=(row[k] if row else "")) for k,_ in fields}; level=tk.StringVar(value=(row["taxon_level"] if row else "Tür"))
        ttk.Label(frm,text="Düzey").grid(row=0,column=0,sticky="w",pady=5); ttk.Combobox(frm,textvariable=level,values=["Familya","Cins","Tür","Çeşit","Grup"],state="readonly").grid(row=0,column=1,sticky="ew",pady=5)
        for i,(k,label) in enumerate(fields,1): ttk.Label(frm,text=label).grid(row=i,column=0,sticky="w",pady=5,padx=(0,10)); ttk.Entry(frm,textvariable=vars[k]).grid(row=i,column=1,sticky="ew",pady=5)
        def save():
            if not (vars["common_name"].get().strip() or vars["scientific_name"].get().strip()): messagebox.showwarning(APP_NAME,"Türkçe veya bilimsel ad girilmelidir.",parent=dlg); return
            data={k:v.get().strip() for k,v in vars.items()}; data["taxon_level"]=level.get(); self.db.host_save(row["id"] if row else None,data); dlg.destroy(); self.refresh()
        ttk.Button(frm,text="Kaydet",style="Primary.TButton",command=save).grid(row=len(fields)+2,column=1,sticky="e",pady=(18,0))
    def add_host(self): self._dialog()
    def edit_host(self):
        s=self.tree.selection();
        if s:self._dialog(self.db.host_get(int(s[0])))
    def delete_host(self):
        s=self.tree.selection();
        if s and messagebox.askyesno(APP_NAME,"Seçili konukçu kayıtları silinsin mi?",parent=self):
            for iid in s:self.db.host_delete(int(iid))
            self.refresh()
    def choose(self):
        ids=[int(x) for x in self.tree.selection()]
        if not ids:return
        if self.on_select:
            self.on_select([self.db.host_get(host_id) for host_id in ids])
            self.destroy(); return
        if self.disease_id:
            for host_id in ids:self.db.disease_host_add(self.disease_id,host_id,"Doğal konukçu","Doğrudan","")
            if self.on_change:self.on_change()
            self.destroy()
