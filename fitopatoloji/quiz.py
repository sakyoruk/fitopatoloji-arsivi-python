# -*- coding: utf-8 -*-
from .common import *
import random

QUESTION_TYPES = ("Çoktan seçmeli", "Doğru / Yanlış", "Kısa cevap")
DIFFICULTIES = ("Kolay", "Orta", "Zor")
OPTION_KEYS = ("option_a", "option_b", "option_c", "option_d", "option_e")
FORMAT_KEYS = ("option_a_format_json", "option_b_format_json", "option_c_format_json", "option_d_format_json", "option_e_format_json")


def _loads_format(value):
    try:
        obj=json.loads(value or "{}")
        return obj if isinstance(obj,dict) else {}
    except Exception:
        return {}


class ItalicTextEditor(ttk.Frame):
    """Soru alanları için sade, bilimsel adları italikleyebilen metin düzenleyici."""
    def __init__(self, master, value="", formatting=None, height=3):
        ttk.Frame.__init__(self,master)
        bar=ttk.Frame(self); bar.pack(fill="x",pady=(0,2))
        ttk.Button(bar,text="İtalik",width=8,command=self.toggle_italic).pack(side="left")
        ttk.Label(bar,text="Cins/tür adını seçip İtalik'e basın.",style="Muted.TLabel").pack(side="left",padx=8)
        body=ttk.Frame(self); body.pack(fill="both",expand=True)
        self.text=tk.Text(body,height=height,wrap="word",undo=True,font=("Segoe UI",10))
        sb=ttk.Scrollbar(body,orient="vertical",command=self.text.yview); self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        self.text.tag_configure("italic",font=("Segoe UI",10,"italic"))
        self.text.insert("1.0",value or "")
        self.apply_formatting(formatting or {})
        self.text.bind("<Control-i>",lambda e:(self.toggle_italic(),"break")[1])
    def toggle_italic(self):
        try:start,end=self.text.index("sel.first"),self.text.index("sel.last")
        except tk.TclError:return
        covered=False
        ranges=self.text.tag_ranges("italic")
        for i in range(0,len(ranges),2):
            if self.text.compare(ranges[i],"<=",start) and self.text.compare(ranges[i+1],">=",end):covered=True;break
        if covered:self.text.tag_remove("italic",start,end)
        else:self.text.tag_add("italic",start,end)
    def get_value(self):return self.text.get("1.0","end-1c").strip()
    def serialize(self):
        ranges=self.text.tag_ranges("italic")
        return {"italic":[[str(ranges[i]),str(ranges[i+1])] for i in range(0,len(ranges),2)]} if ranges else {}
    def apply_formatting(self,fmt):
        for start,end in (fmt or {}).get("italic",[]):
            try:self.text.tag_add("italic",start,end)
            except tk.TclError:pass


def render_formatted_text(widget, value, formatting, base_font=("Segoe UI",11), bold=False):
    widget.configure(state="normal")
    widget.delete("1.0","end")
    widget.tag_configure("italic",font=(base_font[0],base_font[1],"bold italic" if bold else "italic"))
    if bold:widget.tag_configure("base",font=(base_font[0],base_font[1],"bold"))
    widget.insert("1.0",value or "",("base",) if bold else ())
    for start,end in (formatting or {}).get("italic",[]):
        try:widget.tag_add("italic",start,end)
        except tk.TclError:pass
    widget.configure(state="disabled")


class DiseasePicker(tk.Toplevel):
    def __init__(self,master,db,selected_ids=None,on_apply=None):
        tk.Toplevel.__init__(self,master); self.db=db; self.on_apply=on_apply; self.selected=set(int(x) for x in (selected_ids or []))
        self.title("İlişkili hastalıkları seç"); self.geometry("820x560"); self.transient(master); self.grab_set()
        root=ttk.Frame(self,padding=12); root.pack(fill="both",expand=True)
        top=ttk.Frame(root); top.pack(fill="x"); self.query=tk.StringVar(); ttk.Entry(top,textvariable=self.query).pack(side="left",fill="x",expand=True)
        ttk.Button(top,text="Ara",command=self.refresh).pack(side="left",padx=4); ttk.Button(top,text="Seçimi temizle",command=self.clear).pack(side="left")
        ttk.Label(root,text="Bir soru birden fazla hastalıkla ilişkilendirilebilir. Arayın ve satırlara çift tıklayarak seçin.",style="Muted.TLabel").pack(anchor="w",pady=(6,4))
        self.tree=ttk.Treeview(root,columns=("selected","scientific","group"),show="tree headings",selectmode="extended")
        self.tree.heading("#0",text="Hastalık"); self.tree.heading("selected",text="Seçili"); self.tree.heading("scientific",text="Bilimsel ad"); self.tree.heading("group",text="Grup")
        self.tree.column("#0",width=260); self.tree.column("selected",width=70,anchor="center"); self.tree.column("scientific",width=260); self.tree.column("group",width=150)
        self.tree.pack(fill="both",expand=True); self.tree.bind("<Double-1>",lambda e:self.toggle())
        bar=ttk.Frame(root); bar.pack(fill="x",pady=(10,0)); ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(bar,text="Uygula",style="Primary.TButton",command=self.apply).pack(side="right",padx=6)
        self.refresh()
    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for d in self.db.search(query=self.query.get().strip()):
            did=int(d["id"]); self.tree.insert("","end",iid=str(did),text=d["disease_name"],values=("✓" if did in self.selected else "",d["scientific_name"],d["group_name"] or ""))
    def toggle(self):
        for iid in self.tree.selection():
            did=int(iid)
            if did in self.selected:self.selected.remove(did)
            else:self.selected.add(did)
        self.refresh()
    def clear(self):self.selected.clear(); self.refresh()
    def apply(self):
        if self.on_apply:self.on_apply(sorted(self.selected))
        self.destroy()


class QuestionEditor(tk.Toplevel):
    def __init__(self, master, db, question_id=None, disease_id=None, on_saved=None):
        tk.Toplevel.__init__(self, master); self.db=db; self.question_id=question_id; self.on_saved=on_saved
        self.title("Soru düzenleyici"); self.geometry("860x760"); self.minsize(760,620); self.transient(master); self.grab_set()
        row=db.quiz_question_get(question_id) if question_id else None
        self.selected_disease_ids=db.quiz_question_disease_ids(question_id) if question_id else ([int(disease_id)] if disease_id else [])
        footer=ttk.Frame(self,padding=(14,8)); footer.pack(fill="x",side="bottom")
        ttk.Button(footer,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(footer,text="Kaydet",style="Primary.TButton",command=self.save).pack(side="right",padx=6)
        outer=ttk.Frame(self); outer.pack(fill="both",expand=True)
        canvas=tk.Canvas(outer,highlightthickness=0); scroll=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview); canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y"); canvas.pack(side="left",fill="both",expand=True)
        self.frm=ttk.Frame(canvas,padding=14); win=canvas.create_window((0,0),window=self.frm,anchor="nw")
        self.frm.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(win,width=e.width))
        self.vars={}
        head=ttk.Frame(self.frm); head.pack(fill="x")
        for label,key,values in (("Soru türü","question_type",QUESTION_TYPES),("Zorluk","difficulty",DIFFICULTIES)):
            box=ttk.Frame(head); box.pack(side="left",fill="x",expand=True,padx=(0,8)); ttk.Label(box,text=label).pack(anchor="w")
            v=tk.StringVar(value=(row[key] if row else values[0])); self.vars[key]=v
            cb=ttk.Combobox(box,textvariable=v,values=values,state="readonly"); cb.pack(fill="x")
            if key=="question_type":cb.bind("<<ComboboxSelected>>",lambda e:self.update_type_ui())
        rel=ttk.LabelFrame(self.frm,text="İlişkili hastalıklar",padding=8); rel.pack(fill="x",pady=8)
        self.disease_summary=tk.StringVar(); ttk.Label(rel,textvariable=self.disease_summary,wraplength=650).pack(side="left",fill="x",expand=True)
        ttk.Button(rel,text="Ara ve seç…",command=lambda:DiseasePicker(self,self.db,self.selected_disease_ids,self.set_diseases)).pack(side="right")
        meta=ttk.Frame(self.frm); meta.pack(fill="x",pady=4)
        left=ttk.Frame(meta); left.pack(side="left",fill="x",expand=True,padx=(0,8)); ttk.Label(left,text="Konu etiketleri").pack(anchor="w")
        self.vars["topic_tag"]=tk.StringVar(value=(row["topic_tag"] if row else "")); ttk.Combobox(left,textvariable=self.vars["topic_tag"],values=db.quiz_topic_tags()).pack(fill="x")
        ttk.Label(left,text="Arama ve test filtreleri için virgülle ayırın: Taksonomi, Belirti, Mücadele…",style="Muted.TLabel",wraplength=350).pack(anchor="w")
        right=ttk.Frame(meta); right.pack(side="left",fill="x",expand=True); ttk.Label(right,text="Kaynak / dayanak").pack(anchor="w")
        self.vars["source_text"]=tk.StringVar(value=(row["source_text"] if row else "")); ttk.Entry(right,textvariable=self.vars["source_text"]).pack(fill="x")
        ttk.Label(right,text="Kitap/makale künyesi, DOI, URL veya sayfa numarası. Sorunun doğrulanmasını sağlar.",style="Muted.TLabel",wraplength=350).pack(anchor="w")
        ttk.Label(self.frm,text="Soru kökü").pack(anchor="w",pady=(8,2)); self.q=ItalicTextEditor(self.frm,row["question_text"] if row else "",_loads_format(row["question_format_json"]) if row else {},height=5); self.q.pack(fill="x")
        self.optbox=ttk.LabelFrame(self.frm,text="Seçenekler (A–E)",padding=8); self.optbox.pack(fill="x",pady=8)
        self.opts=[]
        for i,(key,fkey) in enumerate(zip(OPTION_KEYS,FORMAT_KEYS)):
            line=ttk.Frame(self.optbox); line.pack(fill="x",pady=3); ttk.Label(line,text=chr(65+i)+")",width=3).pack(side="left",anchor="n",pady=28)
            ed=ItalicTextEditor(line,row[key] if row else "",_loads_format(row[fkey]) if row else {},height=2); ed.pack(side="left",fill="x",expand=True); self.opts.append(ed)
        self.answer_frame=ttk.Frame(self.frm); self.answer_frame.pack(fill="x",pady=4); ttk.Label(self.answer_frame,text="Doğru cevap",width=15).pack(side="left")
        self.answer=tk.StringVar(value=(row["correct_answer"] if row else "A")); self.answer_widget=None
        ttk.Label(self.frm,text="Doğru cevabın açıklaması / öğrenme notu").pack(anchor="w",pady=(8,2)); self.expl=ItalicTextEditor(self.frm,row["explanation"] if row else "",_loads_format(row["explanation_format_json"]) if row else {},height=5); self.expl.pack(fill="x")
        self.set_diseases(self.selected_disease_ids); self.update_type_ui()
    def set_diseases(self,ids):
        self.selected_disease_ids=list(ids); names=[]
        for did in self.selected_disease_ids:
            d=self.db.get(did)
            if d:names.append(d["disease_name"])
        self.disease_summary.set("Genel / ilişkisiz" if not names else "{} hastalık: {}".format(len(names),", ".join(names[:5])+("…" if len(names)>5 else "")))
    def update_type_ui(self):
        qtype=self.vars["question_type"].get()
        for w in self.answer_frame.winfo_children()[1:]:w.destroy()
        state="normal" if qtype=="Çoktan seçmeli" else "disabled"
        for ed in self.opts:
            ed.text.configure(state=state)
        if qtype=="Çoktan seçmeli":
            if self.answer.get().upper() not in "ABCDE":self.answer.set("A")
            self.answer_widget=ttk.Combobox(self.answer_frame,textvariable=self.answer,values=tuple("ABCDE"),state="readonly")
        elif qtype=="Doğru / Yanlış":
            if self.answer.get().lower() not in ("doğru","yanlış","d","y"):self.answer.set("Doğru")
            self.answer_widget=ttk.Combobox(self.answer_frame,textvariable=self.answer,values=("Doğru","Yanlış"),state="readonly")
        else:
            if self.answer.get().upper() in "ABCDE":self.answer.set("")
            self.answer_widget=ttk.Entry(self.answer_frame,textvariable=self.answer)
        self.answer_widget.pack(side="left",fill="x",expand=True)
    def save(self):
        q=self.q.get_value(); qtype=self.vars["question_type"].get(); ans=self.answer.get().strip()
        if not q:messagebox.showwarning("Eksik bilgi","Soru metnini yazın.",parent=self);return
        opts=[ed.get_value() for ed in self.opts]
        if qtype=="Çoktan seçmeli":
            if any(not x for x in opts):messagebox.showwarning("Eksik seçenek","Çoktan seçmeli sorularda A–E seçeneklerinin tamamını doldurun.",parent=self);return
            if ans.upper() not in tuple("ABCDE"):messagebox.showwarning("Doğru cevap","A, B, C, D veya E seçin.",parent=self);return
            ans=ans.upper()
        elif qtype=="Doğru / Yanlış":
            if ans.lower() not in ("doğru","yanlış","d","y"):messagebox.showwarning("Doğru cevap","Doğru veya Yanlış seçin.",parent=self);return
            ans="Doğru" if ans.lower() in ("doğru","d") else "Yanlış"; opts=["","","","",""]
        else:
            if not ans:messagebox.showwarning("Doğru cevap","Kısa cevap için kabul edilecek doğru cevabı yazın.",parent=self);return
            opts=["","","","",""]
        data=dict(question_type=qtype,question_text=q,difficulty=self.vars["difficulty"].get(),topic_tag=self.vars["topic_tag"].get().strip(),source_text=self.vars["source_text"].get().strip(),correct_answer=ans,explanation=self.expl.get_value(),
            question_format_json=json.dumps(self.q.serialize(),ensure_ascii=False),explanation_format_json=json.dumps(self.expl.serialize(),ensure_ascii=False))
        for key,value,ed,fkey in zip(OPTION_KEYS,opts,self.opts,FORMAT_KEYS):data[key]=value;data[fkey]=json.dumps(ed.serialize(),ensure_ascii=False)
        self.db.quiz_question_save(self.question_id,disease_ids=self.selected_disease_ids,**data)
        if self.on_saved:self.on_saved()
        self.destroy()


class ExamWindow(tk.Toplevel):
    def __init__(self, master, db, questions, mode="Sınav", on_open_disease=None, show_feedback=False):
        tk.Toplevel.__init__(self,master); self.db=db; self.questions=list(questions); self.mode=mode; self.on_open_disease=on_open_disease; self.show_feedback=bool(show_feedback or mode=="Çalışma")
        self.index=0; self.answers={}; self.feedback_seen=set(); self.started=dt.datetime.now(); self.finished=False
        self.title("{} — Bilgi Modülü".format(mode)); self.geometry("900x700"); self.minsize(760,600); self.protocol("WM_DELETE_WINDOW",self.request_finish)
        top=ttk.Frame(self,padding=12); top.pack(fill="x"); self.progress=tk.StringVar(); ttk.Label(top,textvariable=self.progress,style="Title.TLabel").pack(side="left")
        self.card=ttk.Frame(self,padding=18); self.card.pack(fill="both",expand=True)
        self.q_text=tk.Text(self.card,height=6,wrap="word",relief="flat",font=("Segoe UI",13),cursor="arrow"); self.q_text.pack(fill="x",pady=(0,12))
        self.answer_var=tk.StringVar(); self.answer_box=ttk.Frame(self.card); self.answer_box.pack(fill="both",expand=True)
        self.feedback=tk.Text(self.card,height=8,wrap="word",state="disabled"); self.feedback.pack(fill="x",pady=10)
        bar=ttk.Frame(self,padding=12); bar.pack(fill="x")
        ttk.Button(bar,text="Testi sonlandır",command=self.request_finish).pack(side="left")
        self.prev_btn=ttk.Button(bar,text="Önceki",command=self.previous); self.prev_btn.pack(side="right",padx=(4,0))
        self.next_btn=ttk.Button(bar,text="Sonraki",command=self.next); self.next_btn.pack(side="right")
        self.check_btn=ttk.Button(bar,text="Cevabı ve açıklamayı göster",command=self.check_now); self.check_btn.pack(side="right",padx=8)
        self.show_question()
    def _save_current(self):
        if self.questions:self.answers[int(self.questions[self.index]["id"])]=self.answer_var.get()
    def show_question(self):
        for w in self.answer_box.winfo_children():w.destroy()
        self.feedback.configure(state="normal"); self.feedback.delete("1.0","end"); self.feedback.configure(state="disabled")
        q=self.questions[self.index]; qid=int(q["id"]); self.progress.set("Soru {} / {}   •   {}   •   {}".format(self.index+1,len(self.questions),q["difficulty"],q["topic_tag"] or "Genel"))
        render_formatted_text(self.q_text,q["question_text"],_loads_format(q["question_format_json"]),base_font=("Segoe UI",13),bold=True)
        self.answer_var.set(self.answers.get(qid,"")); typ=q["question_type"]
        if typ=="Çoktan seçmeli":
            for code,key,fkey in zip("ABCDE",OPTION_KEYS,FORMAT_KEYS):
                if not q[key]:continue
                row=ttk.Frame(self.answer_box); row.pack(fill="x",pady=3)
                ttk.Radiobutton(row,value=code,variable=self.answer_var).pack(side="left",anchor="n",pady=5)
                t=tk.Text(row,height=max(1,min(3,(len(q[key])//90)+1)),wrap="word",relief="flat",cursor="arrow",font=("Segoe UI",11)); t.pack(side="left",fill="x",expand=True)
                render_formatted_text(t,"{}) {}".format(code,q[key]),_offset_format(_loads_format(q[fkey]),3),base_font=("Segoe UI",11))
                t.bind("<Button-1>",lambda e,c=code:self.answer_var.set(c))
        elif typ=="Doğru / Yanlış":
            for value in ("Doğru","Yanlış"):ttk.Radiobutton(self.answer_box,text=value,value=value,variable=self.answer_var).pack(anchor="w",pady=6)
        else:ttk.Entry(self.answer_box,textvariable=self.answer_var,font=("Segoe UI",12)).pack(fill="x",pady=8)
        self.prev_btn.configure(state="normal" if self.index>0 else "disabled")
        self.next_btn.configure(text="Sonuçları göster" if self.index==len(self.questions)-1 else "Sonraki")
        self.check_btn.configure(state="normal" if self.show_feedback else "disabled")
        if qid in self.feedback_seen:self.check_now()
    def normalized(self,s):return " ".join((s or "").strip().lower().split())
    def is_correct(self,q,a):
        aa=self.normalized(a); correct=self.normalized(q["correct_answer"]); aliases={"d":"doğru","y":"yanlış"}; return aliases.get(aa,aa)==aliases.get(correct,correct)
    def check_now(self):
        q=self.questions[self.index]; ans=self.answer_var.get(); self.answers[int(q["id"])]=ans; self.feedback_seen.add(int(q["id"])); ok=self.is_correct(q,ans)
        prefix="Doğru.\n\n" if ok else "Yanlış. Doğru cevap: {}\n\n".format(q["correct_answer"])
        self.feedback.configure(state="normal"); self.feedback.delete("1.0","end"); self.feedback.insert("1.0",prefix)
        start=self.feedback.index("end-1c"); self.feedback.insert("end",q["explanation"] or "Açıklama eklenmemiş.")
        for a,b in _loads_format(q["explanation_format_json"]).get("italic",[]):
            try:self.feedback.tag_add("italic",_add_index(start,a),_add_index(start,b))
            except tk.TclError:pass
        self.feedback.tag_configure("italic",font=("Segoe UI",10,"italic")); self.feedback.configure(state="disabled")
    def previous(self):self._save_current(); self.index=max(0,self.index-1); self.show_question()
    def next(self):
        self._save_current()
        if self.index==len(self.questions)-1:self.finish();return
        self.index+=1;self.show_question()
    def request_finish(self):
        if messagebox.askyesno("Testi sonlandır","Test şimdi sonlandırılsın mı? Verilen cevaplar değerlendirilir.",parent=self):self.finish()
    def finish(self):
        if self.finished:return
        self.finished=True
        if not self.questions:self.destroy();return
        self._save_current(); correct=0; wrong=[]; blank=0; details=[]
        for q in self.questions:
            a=self.answers.get(int(q["id"]),""); ok=self.is_correct(q,a)
            if not a.strip():blank+=1
            elif ok:correct+=1
            else:wrong.append(q)
            details.append({"question_id":int(q["id"]),"answer":a,"correct":ok})
        total=len(self.questions); score=round(100.0*correct/total,1); seconds=int((dt.datetime.now()-self.started).total_seconds())
        sid=self.db.quiz_session_save(self.mode,total,correct,len(wrong),blank,score,seconds,details)
        ResultWindow(self,self.db,sid,total,correct,len(wrong),blank,score,wrong,self.on_open_disease)


def _offset_format(fmt,prefix_len):
    result={"italic":[]}
    for a,b in (fmt or {}).get("italic",[]):
        result["italic"].append([_shift_index(a,prefix_len),_shift_index(b,prefix_len)])
    return result

def _shift_index(index,amount):
    try:line,col=index.split("."); return "{}.{}".format(line,int(col)+amount if int(line)==1 else col)
    except Exception:return index

def _add_index(base,relative):
    try:line,col=relative.split("."); return "{} + {} lines + {} chars".format(base,int(line)-1,int(col))
    except Exception:return base


class ResultWindow(tk.Toplevel):
    def __init__(self,master,db,session_id,total,correct,wrong,blank,score,wrong_rows,on_open_disease):
        tk.Toplevel.__init__(self,master); self.db=db; self.on_open_disease=on_open_disease; self.title("Sınav sonucu"); self.geometry("690x520"); self.transient(master)
        f=ttk.Frame(self,padding=18); f.pack(fill="both",expand=True); ttk.Label(f,text="Başarı: %{}".format(score),font=("Segoe UI",22,"bold")).pack(anchor="w")
        ttk.Label(f,text="{} soru • {} doğru • {} yanlış • {} boş".format(total,correct,wrong,blank)).pack(anchor="w",pady=(4,14))
        ttk.Label(f,text="Yanlış yapılan sorular").pack(anchor="w"); tree=ttk.Treeview(f,columns=("topic","disease"),show="tree headings",height=12); tree.heading("#0",text="Soru"); tree.heading("topic",text="Konu"); tree.heading("disease",text="Hastalık"); tree.column("#0",width=330); tree.column("topic",width=110); tree.column("disease",width=150); tree.pack(fill="both",expand=True,pady=6)
        for q in wrong_rows:tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["topic_tag"],q["disease_name"] or ""))
        def open_related():
            sel=tree.selection()
            if not sel:return
            ids=db.quiz_question_disease_ids(int(sel[0])); did=ids[0] if ids else None
            if did and on_open_disease:on_open_disease(int(did))
        ttk.Button(f,text="İlgili hastalığı aç",command=open_related).pack(side="left",pady=8); ttk.Button(f,text="Kapat",command=self.destroy).pack(side="right",pady=8)


class QuizCenter(tk.Toplevel):
    def __init__(self, master, db, selected_disease_id=None, on_open_disease=None):
        tk.Toplevel.__init__(self,master); self.db=db; self.selected_disease_id=selected_disease_id; self.on_open_disease=on_open_disease
        self.title("Bilgi Sınavı ve Öğrenme Merkezi"); self.geometry("1050x700"); self.minsize(850,600)
        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=10,pady=10)
        self.bank=ttk.Frame(nb,padding=10); self.start=ttk.Frame(nb,padding=16); self.history=ttk.Frame(nb,padding=10)
        nb.add(self.bank,text="Soru Bankası"); nb.add(self.start,text="Test Başlat"); nb.add(self.history,text="Geçmiş ve İstatistik")
        self.build_bank(); self.build_start(); self.build_history(); self.refresh_bank(); self.refresh_history()
    def build_bank(self):
        bar=ttk.Frame(self.bank); bar.pack(fill="x"); self.query=tk.StringVar(); ttk.Entry(bar,textvariable=self.query).pack(side="left",fill="x",expand=True); ttk.Button(bar,text="Ara",command=self.refresh_bank).pack(side="left",padx=4); ttk.Button(bar,text="Yeni soru",command=lambda:QuestionEditor(self,self.db,disease_id=self.selected_disease_id,on_saved=self.refresh_bank)).pack(side="left")
        self.tree=ttk.Treeview(self.bank,columns=("type","difficulty","topic","disease"),show="tree headings"); self.tree.heading("#0",text="Soru")
        for c,t,w in (("type","Tür",120),("difficulty","Zorluk",80),("topic","Konu",120),("disease","İlişkili hastalıklar",220)):self.tree.heading(c,text=t);self.tree.column(c,width=w)
        self.tree.column("#0",width=380); self.tree.pack(fill="both",expand=True,pady=8); self.tree.bind("<Double-1>",lambda e:self.edit_question())
        b=ttk.Frame(self.bank); b.pack(fill="x"); ttk.Button(b,text="Düzenle",command=self.edit_question).pack(side="left"); ttk.Button(b,text="Sil",command=self.delete_question).pack(side="left",padx=4)
    def refresh_bank(self):
        self.tree.delete(*self.tree.get_children())
        for q in self.db.quiz_questions(query=self.query.get()):self.tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["question_type"],q["difficulty"],q["topic_tag"],q["disease_name"] or ""))
    def edit_question(self):
        s=self.tree.selection()
        if s:QuestionEditor(self,self.db,int(s[0]),on_saved=self.refresh_bank)
    def delete_question(self):
        s=self.tree.selection()
        if s and messagebox.askyesno("Soru sil","Seçili soru silinsin mi?",parent=self):self.db.quiz_question_delete(int(s[0]));self.refresh_bank()
    def build_start(self):
        wrap=ttk.Frame(self.start); wrap.pack(fill="both",expand=True)
        card=ttk.LabelFrame(wrap,text="Test ayarları",padding=18); card.pack(anchor="n",fill="x",padx=60,pady=30)
        ttk.Label(card,text="Kişiselleştirilmiş test oluştur",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,16))
        self.mode=tk.StringVar(value="Sınav"); self.count_var=tk.IntVar(value=10); self.diff=tk.StringVar(value="Tümü"); self.topic=tk.StringVar(value=""); self.only_selected=tk.BooleanVar(value=bool(self.selected_disease_id)); self.feedback_option=tk.BooleanVar(value=False)
        rows=(("Mod",ttk.Combobox(card,textvariable=self.mode,values=("Sınav","Çalışma"),state="readonly")),("Soru sayısı",ttk.Spinbox(card,from_=1,to=100,textvariable=self.count_var)),("Zorluk",ttk.Combobox(card,textvariable=self.diff,values=("Tümü",)+DIFFICULTIES,state="readonly")),("Konu etiketi",ttk.Combobox(card,textvariable=self.topic,values=self.db.quiz_topic_tags())))
        for i,(label,widget) in enumerate(rows,1):ttk.Label(card,text=label).grid(row=i,column=0,sticky="w",padx=(0,18),pady=6);widget.grid(row=i,column=1,sticky="ew",pady=6)
        card.columnconfigure(1,weight=1)
        ttk.Checkbutton(card,text="Yalnız seçili hastalığın soruları",variable=self.only_selected,state="normal" if self.selected_disease_id else "disabled").grid(row=5,column=0,columnspan=2,sticky="w",pady=(12,4))
        ttk.Checkbutton(card,text="İlerlerken doğru cevap ve açıklamayı gösterme düğmesini etkinleştir",variable=self.feedback_option).grid(row=6,column=0,columnspan=2,sticky="w",pady=4)
        ttk.Button(card,text="Testi başlat",style="Primary.TButton",command=self.start_exam).grid(row=7,column=0,columnspan=2,sticky="w",pady=(18,0))
    def start_exam(self):
        disease_id=self.selected_disease_id if self.only_selected.get() else None; diff="" if self.diff.get()=="Tümü" else self.diff.get()
        try:count=max(1,int(self.count_var.get()))
        except Exception:count=10
        rows=list(self.db.quiz_questions(disease_id=disease_id,difficulty=diff,topic=self.topic.get(),active_only=True));random.shuffle(rows);rows=rows[:count]
        if not rows:messagebox.showinfo("Soru bulunamadı","Seçilen ölçütlerde etkin soru yok.",parent=self);return
        ExamWindow(self,self.db,rows,self.mode.get(),self.on_open_disease,self.feedback_option.get())
    def build_history(self):
        top=ttk.Frame(self.history); top.pack(fill="x",pady=(0,8)); self.stats=tk.StringVar(); ttk.Label(top,textvariable=self.stats,font=("Segoe UI",12,"bold")).pack(side="left")
        ttk.Button(top,text="Tüm geçmişi temizle",command=self.clear_history).pack(side="right"); ttk.Button(top,text="Seçili kaydı sil",command=self.delete_history).pack(side="right",padx=6)
        self.hist=ttk.Treeview(self.history,columns=("date","mode","total","score","duration"),show="headings")
        for c,t,w in (("date","Tarih",170),("mode","Mod",100),("total","Soru",70),("score","Puan",80),("duration","Süre",80)):self.hist.heading(c,text=t);self.hist.column(c,width=w)
        self.hist.pack(fill="both",expand=True)
    def delete_history(self):
        s=self.hist.selection()
        if s and messagebox.askyesno("Geçmiş kaydını sil","Seçili sınav kaydı silinsin mi?",parent=self):self.db.quiz_session_delete(int(s[0]));self.refresh_history()
    def clear_history(self):
        if messagebox.askyesno("Geçmişi temizle","Tüm sınav geçmişi ve istatistikleri kalıcı olarak silinsin mi?",parent=self):self.db.quiz_sessions_clear();self.refresh_history()
    def refresh_history(self):
        self.hist.delete(*self.hist.get_children()); rows=self.db.quiz_sessions()
        for r in rows:self.hist.insert("","end",iid=str(r["id"]),values=(r["started_at"],r["mode"],r["total_questions"],"%{}".format(r["score"]),"{} sn".format(r["duration_seconds"])))
        st=self.db.quiz_stats();self.stats.set("{} sınav • {} soru • genel başarı %{}".format(st["sessions"],st["questions"],st["average_score"]))
