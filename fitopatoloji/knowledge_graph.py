# -*- coding: utf-8 -*-
from .common import *

_SPLIT = re.compile(r"[,;\n/|]+")
def terms(value):
    return [" ".join(x.strip().split()) for x in _SPLIT.split(value or "") if x.strip()]

def related(db, disease_id, limit=20):
    base = db.get(disease_id)
    if not base: return []
    bh=set(x.lower() for x in terms(base['hosts'])); bo=set(x.lower() for x in terms(base['affected_organs']))
    bs=set(x.lower() for x in terms(base['symptoms'])); sci=(base['scientific_name'] or '').strip().lower()
    out=[]
    for row in db.conn.execute("SELECT * FROM diseases WHERE id<>? AND COALESCE(deleted_at,'')=''",(disease_id,)).fetchall():
        reasons=[]; score=0
        h=bh & set(x.lower() for x in terms(row['hosts'])); o=bo & set(x.lower() for x in terms(row['affected_organs'])); s=bs & set(x.lower() for x in terms(row['symptoms']))
        if h: score+=4*len(h); reasons.append('Aynı konukçu: '+', '.join(sorted(h)[:3]))
        if o: score+=2*len(o); reasons.append('Aynı organ: '+', '.join(sorted(o)[:3]))
        if s: score+=len(s); reasons.append('Benzer belirti: '+', '.join(sorted(s)[:3]))
        if sci and sci==(row['scientific_name'] or '').strip().lower(): score+=8; reasons.append('Aynı etmen')
        if score: out.append((score,row,' • '.join(reasons)))
    return sorted(out,key=lambda x:(-x[0],x[1]['disease_name'].lower()))[:limit]

class KnowledgeCenter(tk.Toplevel):
    def __init__(self,parent,db,paths,disease_id=None,on_open=None):
        tk.Toplevel.__init__(self,parent); self.db=db; self.paths=paths; self.disease_id=disease_id; self.on_open=on_open
        self.title('Bilimsel Bilgi Ağı'); self.geometry('1120x720'); self.minsize(850,560); self.transient(parent)
        nb=ttk.Notebook(self); nb.pack(fill='both',expand=True,padx=10,pady=10)
        self.rel=ttk.Frame(nb,padding=10); self.graph=ttk.Frame(nb,padding=10); self.entities=ttk.Frame(nb,padding=10); self.index=ttk.Frame(nb,padding=10); self.images=ttk.Frame(nb,padding=10); self.refs=ttk.Frame(nb,padding=10)
        for f,t in [(self.rel,'İlgili hastalıklar'),(self.graph,'Bilgi haritası'),(self.entities,'Etmen ve konukçular'),(self.index,'Bilimsel indeks'),(self.images,'Görsel koleksiyon'),(self.refs,'Kaynak havuzu')]: nb.add(f,text=t)
        self._build_related(); self._build_graph(); self._build_entities(); self._build_index(); self._build_images(); self._build_refs()
    def _open(self,did):
        if self.on_open: self.on_open(int(did)); self.destroy()
    def _build_related(self):
        if not self.disease_id:
            ttk.Label(self.rel,text='İlgili hastalıkları görmek için ana ekrandan bir hastalık seçin.').pack(anchor='w'); return
        base=self.db.get(self.disease_id); ttk.Label(self.rel,text='{} için ilişkiler'.format(base['disease_name']),font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(0,8))
        tree=ttk.Treeview(self.rel,columns=('score','reason'),show='tree headings'); tree.heading('#0',text='Hastalık'); tree.heading('score',text='Puan'); tree.heading('reason',text='Neden ilgili?'); tree.column('#0',width=260); tree.column('score',width=60,anchor='center'); tree.column('reason',width=620)
        tree.pack(fill='both',expand=True)
        for score,row,why in related(self.db,self.disease_id): tree.insert('','end',iid=str(row['id']),text=row['disease_name'],values=(score,why))
        tree.bind('<Double-1>',lambda e: self._open(tree.selection()[0]) if tree.selection() else None)
    def _build_graph(self):
        c=tk.Canvas(self.graph,bg='white',highlightthickness=0); c.pack(fill='both',expand=True)
        if not self.disease_id: c.create_text(420,260,text='Bir hastalık seçildiğinde bilgi ağı burada oluşur.',font=('Segoe UI',13)); return
        base=self.db.get(self.disease_id); items=related(self.db,self.disease_id,8)
        def draw():
            c.delete('all'); w=max(c.winfo_width(),800); h=max(c.winfo_height(),500); cx=w/2; cy=h/2
            c.create_oval(cx-105,cy-42,cx+105,cy+42,fill='#dff3e7',outline='#2f855a',width=2); c.create_text(cx,cy,text=base['disease_name'],width=185,font=('Segoe UI',10,'bold'))
            import math
            for i,(score,row,why) in enumerate(items):
                a=(2*math.pi*i/max(len(items),1))-math.pi/2; x=cx+min(w,h)*.34*math.cos(a); y=cy+min(w,h)*.34*math.sin(a)
                c.create_line(cx,cy,x,y,fill='#94a3b8',width=max(1,min(4,score//4+1)))
                tag='d{}'.format(row['id']); c.create_oval(x-88,y-31,x+88,y+31,fill='#f8fafc',outline='#64748b',tags=(tag,)); c.create_text(x,y,text=row['disease_name'],width=155,tags=(tag,)); c.tag_bind(tag,'<Double-1>',lambda e,d=row['id']:self._open(d))
            for label,vals,dx,dy in [('Etmen',[base['scientific_name']],0,-135),('Konukçu',terms(base['hosts'])[:3],-220,105),('Organ',terms(base['affected_organs'])[:3],220,105)]:
                text=label+'\n'+'\n'.join(vals); c.create_rectangle(cx+dx-80,cy+dy-30,cx+dx+80,cy+dy+30,fill='#fff7ed',outline='#d97706'); c.create_text(cx+dx,cy+dy,text=text,width=145)
        c.bind('<Configure>',lambda e:draw()); self.after(100,draw)
    def _build_entities(self):
        panes=ttk.Panedwindow(self.entities,orient='horizontal'); panes.pack(fill='both',expand=True)
        for title,field in [('Etmenler','scientific_name'),('Konukçular','hosts')]:
            f=ttk.Frame(panes,padding=6); panes.add(f,weight=1); ttk.Label(f,text=title,font=('Segoe UI',12,'bold')).pack(anchor='w')
            tree=ttk.Treeview(f,columns=('count',),show='tree headings'); tree.heading('#0',text=title[:-3] if title.endswith('ler') else title); tree.heading('count',text='Kayıt'); tree.pack(fill='both',expand=True,pady=(6,0))
            counts={}
            for r in self.db.conn.execute("SELECT id,scientific_name,hosts FROM diseases WHERE COALESCE(deleted_at,'')='' "):
                vals=[r[field]] if field=='scientific_name' else terms(r[field])
                for v in vals:
                    v=(v or '').strip()
                    if v: counts.setdefault(v,[]).append(r['id'])
            for name,ids in sorted(counts.items(),key=lambda x:x[0].lower()): tree.insert('','end',text=name,values=(len(ids),),tags=('ids:'+','.join(map(str,ids)),))
            def open_entity(e,t=tree):
                sel=t.selection()
                if not sel:return
                tags=t.item(sel[0],'tags'); ids=[x for x in tags if x.startswith('ids:')][0][4:].split(','); self._entity_detail(t.item(sel[0],'text'),ids)
            tree.bind('<Double-1>',open_entity)
    def _entity_detail(self,name,ids):
        w=tk.Toplevel(self); w.title(name); w.geometry('620x430'); ttk.Label(w,text=name,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=12,pady=10)
        tree=ttk.Treeview(w,columns=('scientific',),show='tree headings'); tree.heading('#0',text='Hastalık'); tree.heading('scientific',text='Etmen'); tree.pack(fill='both',expand=True,padx=12,pady=(0,12))
        for did in ids:
            r=self.db.get(int(did));
            if r: tree.insert('','end',iid=str(did),text=r['disease_name'],values=(r['scientific_name'],))
        tree.bind('<Double-1>',lambda e:self._open(tree.selection()[0]) if tree.selection() else None)
    def _build_index(self):
        q=tk.StringVar(); ttk.Entry(self.index,textvariable=q).pack(fill='x',pady=(0,8)); tree=ttk.Treeview(self.index,columns=('type','detail'),show='tree headings'); tree.heading('#0',text='Terim'); tree.heading('type',text='Tür'); tree.heading('detail',text='Açıklama'); tree.pack(fill='both',expand=True)
        rows=[]
        for r in self.db.conn.execute("SELECT id,disease_name,scientific_name,hosts FROM diseases WHERE COALESCE(deleted_at,'')='' "):
            rows += [(r['disease_name'],'Hastalık',r['scientific_name'],r['id']),(r['scientific_name'],'Etmen',r['disease_name'],r['id'])]
            rows += [(h,'Konukçu',r['disease_name'],r['id']) for h in terms(r['hosts'])]
        def fill(*a):
            s=q.get().lower(); tree.delete(*tree.get_children())
            for term,kind,detail,did in sorted(rows,key=lambda x:(x[0] or '').lower()):
                if term and (not s or s in term.lower() or s in detail.lower()): tree.insert('','end',text=term,values=(kind,detail),tags=('did:'+str(did),))
        q.trace_add('write',fill) if hasattr(q,'trace_add') else q.trace('w',fill); fill()
        tree.bind('<Double-1>',lambda e:self._open(int([x for x in tree.item(tree.selection()[0],'tags') if x.startswith('did:')][0][4:])) if tree.selection() else None)
    def _build_images(self):
        tree=ttk.Treeview(self.images,columns=('disease','title','description'),show='headings');
        for c,t,w in [('disease','Hastalık',230),('title','Başlık / dosya',260),('description','Açıklama / kaynak',420)]: tree.heading(c,text=t); tree.column(c,width=w)
        tree.pack(fill='both',expand=True)
        for a in self.db.conn.execute("SELECT a.*,d.disease_name FROM attachments a JOIN diseases d ON d.id=a.disease_id WHERE a.file_type='image' AND COALESCE(d.deleted_at,'')='' ORDER BY d.disease_name,a.sort_order"):
            tree.insert('','end',iid=str(a['id']),values=(a['disease_name'],a['title'] or os.path.basename(a['relative_path']),((a['description'] or '')+' '+(a['source'] or '')).strip()),tags=('did:'+str(a['disease_id']),))
        tree.bind('<Double-1>',lambda e:self._open(int([x for x in tree.item(tree.selection()[0],'tags') if x.startswith('did:')][0][4:])) if tree.selection() else None)
    def _build_refs(self):
        tree=ttk.Treeview(self.refs,columns=('type','citation','used'),show='headings');
        for c,t,w in [('type','Tür',100),('citation','Kaynak',700),('used','Kullanım',80)]: tree.heading(c,text=t); tree.column(c,width=w)
        tree.pack(fill='both',expand=True)
        groups={}
        for r in self.db.conn.execute("SELECT source_type,citation,identifier,COUNT(DISTINCT disease_id) n FROM disease_references GROUP BY lower(trim(citation)),lower(trim(identifier)) ORDER BY citation"):
            key=(r['citation'] or r['identifier'] or '').strip()
            if key: tree.insert('','end',values=(r['source_type'],key,r['n']))
