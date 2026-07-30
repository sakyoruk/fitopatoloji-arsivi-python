# -*- coding: utf-8 -*-
from .common import *

FIELDS = [
    ("publication_type", "Yayın türü"), ("authors", "Yazar(lar)"),
    ("year_text", "Yıl"), ("title", "Başlık"), ("journal", "Dergi / Kitap"),
    ("volume", "Cilt"), ("issue", "Sayı"), ("pages", "Sayfalar"),
    ("doi", "DOI"), ("isbn", "ISBN"), ("url", "URL"),
    ("language_name", "Dil"), ("keywords", "Anahtar kelimeler"), ("notes", "Notlar")]

class LiteratureCatalog(tk.Toplevel):
    def __init__(self, master, db, disease_id=None):
        tk.Toplevel.__init__(self, master)
        self.db=db; self.disease_id=disease_id; self.selected_id=None
        self.title("Literatür Kataloğu")
        self.geometry("1040x680"); self.minsize(850,560); self.transient(master)
        self.query=tk.StringVar(); self.status=tk.StringVar()
        self.vars={name:tk.StringVar() for name,_ in FIELDS}
        self._build(); self.refresh()

    def _build(self):
        top=ttk.Frame(self,padding=10); top.pack(fill="x")
        ttk.Label(top,text="Literatür Kataloğu",style="Title.TLabel").pack(side="left")
        ttk.Entry(top,textvariable=self.query,width=32).pack(side="left",padx=(24,6))
        ttk.Button(top,text="Ara",command=self.refresh).pack(side="left")
        ttk.Button(top,text="Yeni",command=self.clear_form).pack(side="right")
        body=ttk.Panedwindow(self,orient="horizontal"); body.pack(fill="both",expand=True,padx=10,pady=(0,8))
        left=ttk.Frame(body); right=ttk.Frame(body,padding=10); body.add(left,weight=3); body.add(right,weight=2)
        cols=("year","authors","title","type")
        self.tree=ttk.Treeview(left,columns=cols,show="headings",selectmode="browse")
        for c,t,w in [("year","Yıl",60),("authors","Yazar(lar)",190),("title","Başlık",330),("type","Tür",90)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w,anchor="w")
        self.tree.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(left,orient="vertical",command=self.tree.yview); sb.pack(side="right",fill="y"); self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>",self.on_select); self.tree.bind("<Double-1>",lambda e:self.link_selected())
        form=ttk.Frame(right); form.pack(fill="both",expand=True)
        for i,(name,label) in enumerate(FIELDS):
            ttk.Label(form,text=label).grid(row=i,column=0,sticky="w",pady=2)
            if name=="publication_type":
                w=ttk.Combobox(form,textvariable=self.vars[name],values=("Makale","Kitap","Kitap bölümü","Tez","Bildiri","Rapor","Web kaynağı","Diğer"),state="readonly")
            else: w=ttk.Entry(form,textvariable=self.vars[name])
            w.grid(row=i,column=1,sticky="ew",padx=(8,0),pady=2)
        form.columnconfigure(1,weight=1)
        buttons=ttk.Frame(right); buttons.pack(fill="x",pady=(10,0))
        ttk.Button(buttons,text="Kaydet",style="Primary.TButton",command=self.save).pack(side="left")
        ttk.Button(buttons,text="Sil",command=self.delete).pack(side="left",padx=6)
        if self.disease_id:
            ttk.Button(buttons,text="Hastalığa bağla",command=self.link_selected).pack(side="right")
            ttk.Button(buttons,text="Bağı kaldır",command=self.unlink_selected).pack(side="right",padx=6)
        ttk.Label(self,textvariable=self.status,style="Muted.TLabel",padding=(10,4)).pack(fill="x")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        linked=set()
        if self.disease_id: linked={r["id"] for r in self.db.disease_literature(self.disease_id)}
        for r in self.db.literature_list(self.query.get()):
            mark="✓ " if r["id"] in linked else ""
            self.tree.insert("","end",iid=str(r["id"]),values=(r["year_text"],mark+(r["authors"] or ""),r["title"],r["publication_type"]))
        self.status.set("{} kaynak".format(len(self.tree.get_children())))

    def on_select(self,_e=None):
        sel=self.tree.selection()
        if not sel:return
        self.selected_id=int(sel[0]); r=self.db.literature_get(self.selected_id)
        for name,_ in FIELDS:self.vars[name].set(r[name] or "")

    def clear_form(self):
        self.selected_id=None
        for v in self.vars.values():v.set("")
        self.vars["publication_type"].set("Makale")

    def save(self):
        if not self.vars["title"].get().strip():
            messagebox.showwarning("Eksik bilgi","Başlık alanı zorunludur.",parent=self); return
        data={k:v.get() for k,v in self.vars.items()}
        self.selected_id=self.db.literature_save(self.selected_id,**data); self.refresh(); self.tree.selection_set(str(self.selected_id))

    def delete(self):
        if self.selected_id and messagebox.askyesno("Sil","Bu kaynak ve tüm hastalık bağlantıları silinsin mi?",parent=self):
            self.db.literature_delete(self.selected_id); self.clear_form(); self.refresh()

    def link_selected(self):
        if not self.disease_id:
            messagebox.showinfo("Bilgi","Kaynak bağlantısı için bu pencere bir hastalık kaydından açılmalıdır.",parent=self); return
        if not self.selected_id:
            messagebox.showwarning("Seçim","Bir kaynak seçin.",parent=self); return
        self.db.link_literature(self.disease_id,self.selected_id); self.refresh()

    def unlink_selected(self):
        if self.disease_id and self.selected_id:
            self.db.unlink_literature(self.disease_id,self.selected_id); self.refresh()

class PrivateNoteDialog(tk.Toplevel):
    def __init__(self, master, db, disease_id, title_text=""):
        tk.Toplevel.__init__(self,master); self.db=db; self.disease_id=disease_id
        self.title("Bilimsel Özel Notlar"); self.geometry("650x450"); self.transient(master); self.grab_set()
        frame=ttk.Frame(self,padding=14); frame.pack(fill="both",expand=True)
        ttk.Label(frame,text=title_text or "Hastalık notu",style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame,text="Bu notlar rapor, PDF, HTML ve monografi çıktılarına eklenmez.",style="Muted.TLabel").pack(anchor="w",pady=(2,8))
        self.text=tk.Text(frame,wrap="word",undo=True); self.text.pack(fill="both",expand=True)
        self.text.insert("1.0",db.private_note(disease_id))
        bar=ttk.Frame(frame); bar.pack(fill="x",pady=(8,0))
        ttk.Button(bar,text="Kaydet",style="Primary.TButton",command=self.save).pack(side="right")
        ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right",padx=6)
    def save(self):
        self.db.save_private_note(self.disease_id,self.text.get("1.0","end-1c")); self.destroy()
