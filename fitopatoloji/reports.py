# -*- coding: utf-8 -*-
"""RC9 bilimsel raporlar ve arşiv istatistikleri."""
from .common import *
import csv

class ReportsCenter(tk.Toplevel):
    def __init__(self, master, db, paths):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.db, self.paths = db, paths
        self.title("Bilimsel raporlar")
        self.geometry("980x650"); self.minsize(780,520); self.transient(master)
        top=ttk.Frame(self,padding=10); top.pack(fill='x')
        ttk.Label(top,text="Bilimsel raporlar",style="Title.TLabel").pack(side='left')
        ttk.Button(top,text="CSV dışa aktar",command=self.export_csv).pack(side='right')
        self.report_var=tk.StringVar(value="Etmen gruplarına göre hastalık sayısı")
        cb=ttk.Combobox(top,textvariable=self.report_var,state='readonly',width=40,values=(
            "Etmen gruplarına göre hastalık sayısı","Konukçu familyalarına göre hastalık sayısı",
            "En fazla konukçuya sahip hastalıklar","Literatür yoğunluğu","Fotoğraf istatistikleri","Soru bankası istatistikleri"))
        cb.pack(side='right',padx=8); cb.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.tree=ttk.Treeview(self,columns=('label','value','detail'),show='headings')
        for c,t,w in [('label','Başlık',430),('value','Sayı',90),('detail','Açıklama',380)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(fill='both',expand=True,padx=10,pady=(0,10)); self.rows=[]; self.refresh()
    def refresh(self):
        name=self.report_var.get(); q=[]
        if name.startswith('Etmen'):
            q=self.db.conn.execute("SELECT COALESCE(NULLIF(TRIM(agent_group),''),NULLIF(TRIM(group_name),''),'(Belirtilmemiş)') label, COUNT(*) n FROM diseases WHERE COALESCE(deleted_at,'')='' GROUP BY label ORDER BY n DESC,label").fetchall()
            self.rows=[(r['label'],r['n'],'hastalık') for r in q]
        elif name.startswith('Konukçu family'):
            q=self.db.conn.execute("SELECT COALESCE(NULLIF(TRIM(hc.family_name),''),'(Belirtilmemiş)') label,COUNT(DISTINCT dh.disease_id) n FROM disease_hosts dh JOIN host_catalog hc ON hc.id=dh.host_id WHERE dh.is_excluded=0 GROUP BY label ORDER BY n DESC,label").fetchall()
            self.rows=[(r['label'],r['n'],'ilişkili hastalık') for r in q]
        elif name.startswith('En fazla'):
            q=self.db.conn.execute("SELECT d.disease_name label,COUNT(DISTINCT dh.host_id) n,d.scientific_name detail FROM diseases d LEFT JOIN disease_hosts dh ON dh.disease_id=d.id AND dh.is_excluded=0 WHERE COALESCE(d.deleted_at,'')='' GROUP BY d.id ORDER BY n DESC,label LIMIT 100").fetchall()
            self.rows=[(r['label'],r['n'],r['detail']) for r in q]
        elif name.startswith('Literatür'):
            q=self.db.conn.execute("SELECT d.disease_name label,COUNT(DISTINCT dl.literature_id) n,d.scientific_name detail FROM diseases d LEFT JOIN disease_literature dl ON dl.disease_id=d.id WHERE COALESCE(d.deleted_at,'')='' GROUP BY d.id ORDER BY n DESC,label LIMIT 100").fetchall(); self.rows=[(r['label'],r['n'],r['detail']) for r in q]
        elif name.startswith('Fotoğraf'):
            q=self.db.conn.execute("SELECT COALESCE(NULLIF(TRIM(image_category),''),'Genel') label,COUNT(*) n FROM attachments WHERE file_type='image' GROUP BY label ORDER BY n DESC,label").fetchall(); self.rows=[(r['label'],r['n'],'fotoğraf') for r in q]
        else:
            q=self.db.conn.execute("SELECT difficulty label,COUNT(*) n,SUM(CASE WHEN is_active=1 THEN 1 ELSE 0 END) active FROM quiz_questions GROUP BY difficulty ORDER BY n DESC").fetchall(); self.rows=[(r['label'],r['n'],'{} etkin'.format(r['active'])) for r in q]
        self.tree.delete(*self.tree.get_children())
        for i,row in enumerate(self.rows): self.tree.insert('','end',iid=str(i),values=row)
    def export_csv(self):
        if not self.rows:return
        out=filedialog.asksaveasfilename(parent=self,initialdir=self.paths.exports,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='bilimsel_rapor.csv')
        if not out:return
        with open(out,'w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f,delimiter=';'); w.writerow(['Başlık','Sayı','Açıklama']); w.writerows(self.rows)
        messagebox.showinfo(APP_NAME,'Rapor kaydedildi:\n'+out,parent=self)
