# -*- coding: utf-8 -*-
from .common import *
import random

QUESTION_TYPES = ("Çoktan seçmeli", "Doğru / Yanlış", "Kısa cevap")
DIFFICULTIES = ("Kolay", "Orta", "Zor")

class QuestionEditor(tk.Toplevel):
    def __init__(self, master, db, question_id=None, disease_id=None, on_saved=None):
        tk.Toplevel.__init__(self, master); self.db=db; self.question_id=question_id; self.on_saved=on_saved
        self.title("Soru düzenleyici"); self.geometry("720x650"); self.transient(master); self.grab_set()
        row=db.quiz_question_get(question_id) if question_id else None
        frm=ttk.Frame(self,padding=14); frm.pack(fill="both",expand=True)
        self.vars={}
        fields=[("Soru türü","question_type",QUESTION_TYPES),("Zorluk","difficulty",DIFFICULTIES)]
        for label,key,values in fields:
            line=ttk.Frame(frm); line.pack(fill="x",pady=3); ttk.Label(line,text=label,width=15).pack(side="left")
            v=tk.StringVar(value=(row[key] if row else values[0])); self.vars[key]=v
            ttk.Combobox(line,textvariable=v,values=values,state="readonly").pack(side="left",fill="x",expand=True)
        line=ttk.Frame(frm); line.pack(fill="x",pady=3); ttk.Label(line,text="Hastalık",width=15).pack(side="left")
        diseases=db.search(); self.disease_map={"Genel / ilişkisiz":None}
        for d in diseases: self.disease_map["{} — {}".format(d["disease_name"],d["scientific_name"])]=int(d["id"])
        initial="Genel / ilişkisiz"
        target=disease_id if disease_id is not None else (row["disease_id"] if row else None)
        for text,did in self.disease_map.items():
            if did==target: initial=text; break
        self.disease_var=tk.StringVar(value=initial); ttk.Combobox(line,textvariable=self.disease_var,values=list(self.disease_map.keys()),state="readonly").pack(side="left",fill="x",expand=True)
        for label,key in (("Konu etiketi","topic_tag"),("Kaynak","source_text")):
            line=ttk.Frame(frm); line.pack(fill="x",pady=3); ttk.Label(line,text=label,width=15).pack(side="left")
            v=tk.StringVar(value=(row[key] if row else "")); self.vars[key]=v; ttk.Entry(line,textvariable=v).pack(side="left",fill="x",expand=True)
        ttk.Label(frm,text="Soru").pack(anchor="w",pady=(8,2)); self.q=tk.Text(frm,height=5,wrap="word",undo=True); self.q.pack(fill="x"); self.q.insert("1.0",row["question_text"] if row else "")
        optbox=ttk.LabelFrame(frm,text="Seçenekler (A–D)",padding=8); optbox.pack(fill="x",pady=8)
        self.opts=[]
        for i,key in enumerate(("option_a","option_b","option_c","option_d")):
            line=ttk.Frame(optbox); line.pack(fill="x",pady=2); ttk.Label(line,text=chr(65+i)+")",width=3).pack(side="left")
            v=tk.StringVar(value=(row[key] if row else "")); self.opts.append(v); ttk.Entry(line,textvariable=v).pack(side="left",fill="x",expand=True)
        line=ttk.Frame(frm); line.pack(fill="x",pady=3); ttk.Label(line,text="Doğru cevap",width=15).pack(side="left")
        self.answer=tk.StringVar(value=(row["correct_answer"] if row else "A")); ttk.Entry(line,textvariable=self.answer).pack(side="left",fill="x",expand=True)
        ttk.Label(frm,text="Açıklama / öğrenme notu").pack(anchor="w",pady=(8,2)); self.expl=tk.Text(frm,height=5,wrap="word"); self.expl.pack(fill="both",expand=True); self.expl.insert("1.0",row["explanation"] if row else "")
        bar=ttk.Frame(frm); bar.pack(fill="x",pady=(10,0)); ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(bar,text="Kaydet",command=self.save).pack(side="right",padx=6)
    def save(self):
        q=self.q.get("1.0","end-1c").strip()
        if not q: messagebox.showwarning("Eksik bilgi","Soru metnini yazın.",parent=self); return
        qtype=self.vars["question_type"].get(); ans=self.answer.get().strip()
        if qtype=="Çoktan seçmeli" and ans.upper() not in ("A","B","C","D"):
            messagebox.showwarning("Doğru cevap","Çoktan seçmeli sorularda A, B, C veya D yazın.",parent=self); return
        if qtype=="Doğru / Yanlış" and ans.lower() not in ("doğru","yanlış","d","y"):
            messagebox.showwarning("Doğru cevap","Doğru veya Yanlış yazın.",parent=self); return
        self.db.quiz_question_save(self.question_id,disease_id=self.disease_map.get(self.disease_var.get()),question_type=qtype,
            question_text=q,difficulty=self.vars["difficulty"].get(),topic_tag=self.vars["topic_tag"].get(),
            option_a=self.opts[0].get(),option_b=self.opts[1].get(),option_c=self.opts[2].get(),option_d=self.opts[3].get(),
            correct_answer=ans,explanation=self.expl.get("1.0","end-1c").strip(),source_text=self.vars["source_text"].get())
        if self.on_saved: self.on_saved()
        self.destroy()

class ExamWindow(tk.Toplevel):
    def __init__(self, master, db, questions, mode="Sınav", on_open_disease=None):
        tk.Toplevel.__init__(self,master); self.db=db; self.questions=list(questions); self.mode=mode; self.on_open_disease=on_open_disease
        self.index=0; self.answers={}; self.started=dt.datetime.now(); self.title("{} — Bilgi Modülü".format(mode)); self.geometry("820x650")
        top=ttk.Frame(self,padding=12); top.pack(fill="x"); self.progress=tk.StringVar(); ttk.Label(top,textvariable=self.progress,style="Title.TLabel").pack(side="left")
        self.card=ttk.Frame(self,padding=20); self.card.pack(fill="both",expand=True)
        self.q_label=ttk.Label(self.card,text="",wraplength=740,justify="left",font=("Segoe UI",13,"bold")); self.q_label.pack(fill="x",pady=(0,14))
        self.answer_var=tk.StringVar(); self.answer_box=ttk.Frame(self.card); self.answer_box.pack(fill="both",expand=True)
        self.feedback=tk.Text(self.card,height=8,wrap="word",state="disabled"); self.feedback.pack(fill="x",pady=10)
        bar=ttk.Frame(self,padding=12); bar.pack(fill="x"); ttk.Button(bar,text="Bitir",command=self.finish).pack(side="left"); self.next_btn=ttk.Button(bar,text="Sonraki",command=self.next); self.next_btn.pack(side="right")
        self.show_question()
    def show_question(self):
        for w in self.answer_box.winfo_children(): w.destroy()
        self.feedback.configure(state="normal"); self.feedback.delete("1.0","end"); self.feedback.configure(state="disabled")
        q=self.questions[self.index]; self.progress.set("Soru {} / {}   •   {}   •   {}".format(self.index+1,len(self.questions),q["difficulty"],q["topic_tag"] or "Genel")); self.q_label.configure(text=q["question_text"])
        self.answer_var.set(self.answers.get(int(q["id"]),"")); typ=q["question_type"]
        if typ=="Çoktan seçmeli":
            for code,key in zip("ABCD",("option_a","option_b","option_c","option_d")):
                if q[key]: ttk.Radiobutton(self.answer_box,text="{}) {}".format(code,q[key]),value=code,variable=self.answer_var).pack(anchor="w",fill="x",pady=4)
        elif typ=="Doğru / Yanlış":
            for value in ("Doğru","Yanlış"): ttk.Radiobutton(self.answer_box,text=value,value=value,variable=self.answer_var).pack(anchor="w",pady=5)
        else: ttk.Entry(self.answer_box,textvariable=self.answer_var,font=("Segoe UI",12)).pack(fill="x",pady=8)
        if self.mode=="Çalışma": ttk.Button(self.answer_box,text="Cevabı kontrol et",command=self.check_now).pack(anchor="w",pady=12)
        self.next_btn.configure(text="Sonuçları göster" if self.index==len(self.questions)-1 else "Sonraki")
    def normalized(self,s): return " ".join((s or "").strip().lower().split())
    def is_correct(self,q,a):
        aa=self.normalized(a); correct=self.normalized(q["correct_answer"])
        aliases={"d":"doğru","y":"yanlış"}; aa=aliases.get(aa,aa); correct=aliases.get(correct,correct)
        return aa==correct
    def check_now(self):
        q=self.questions[self.index]; ans=self.answer_var.get(); self.answers[int(q["id"])]=ans; ok=self.is_correct(q,ans)
        text=("Doğru.\n\n" if ok else "Yanlış. Doğru cevap: {}\n\n".format(q["correct_answer"]))+(q["explanation"] or "Açıklama eklenmemiş.")
        self.feedback.configure(state="normal"); self.feedback.delete("1.0","end"); self.feedback.insert("1.0",text); self.feedback.configure(state="disabled")
    def next(self):
        self.answers[int(self.questions[self.index]["id"])]=self.answer_var.get()
        if self.index==len(self.questions)-1: self.finish(); return
        self.index+=1; self.show_question()
    def finish(self):
        if not self.questions: self.destroy(); return
        self.answers[int(self.questions[self.index]["id"])]=self.answer_var.get()
        correct=0; wrong=[]; blank=0
        details=[]
        for q in self.questions:
            a=self.answers.get(int(q["id"]),"")
            if not a.strip(): blank+=1
            elif self.is_correct(q,a): correct+=1
            else: wrong.append(q)
            details.append({"question_id":int(q["id"]),"answer":a,"correct":self.is_correct(q,a)})
        total=len(self.questions); score=round(100.0*correct/total,1); seconds=int((dt.datetime.now()-self.started).total_seconds())
        sid=self.db.quiz_session_save(self.mode,total,correct,len(wrong),blank,score,seconds,details)
        ResultWindow(self,self.db,sid,total,correct,len(wrong),blank,score,wrong,self.on_open_disease)

class ResultWindow(tk.Toplevel):
    def __init__(self,master,db,session_id,total,correct,wrong,blank,score,wrong_rows,on_open_disease):
        tk.Toplevel.__init__(self,master); self.db=db; self.on_open_disease=on_open_disease; self.title("Sınav sonucu"); self.geometry("690x520"); self.transient(master)
        f=ttk.Frame(self,padding=18); f.pack(fill="both",expand=True); ttk.Label(f,text="Başarı: %{}".format(score),font=("Segoe UI",22,"bold")).pack(anchor="w")
        ttk.Label(f,text="{} soru • {} doğru • {} yanlış • {} boş".format(total,correct,wrong,blank)).pack(anchor="w",pady=(4,14))
        ttk.Label(f,text="Yanlış yapılan sorular").pack(anchor="w"); tree=ttk.Treeview(f,columns=("topic","disease"),show="tree headings",height=12); tree.heading("#0",text="Soru"); tree.heading("topic",text="Konu"); tree.heading("disease",text="Hastalık"); tree.column("#0",width=330); tree.column("topic",width=110); tree.column("disease",width=150); tree.pack(fill="both",expand=True,pady=6)
        for q in wrong_rows: tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["topic_tag"],q["disease_name"] or ""))
        def open_related():
            sel=tree.selection()
            if not sel:return
            q=db.quiz_question_get(int(sel[0])); did=q["disease_id"] if q else None
            if did and on_open_disease: on_open_disease(int(did))
        ttk.Button(f,text="İlgili hastalığı aç",command=open_related).pack(side="left",pady=8); ttk.Button(f,text="Kapat",command=self.destroy).pack(side="right",pady=8)

class QuizCenter(tk.Toplevel):
    def __init__(self, master, db, selected_disease_id=None, on_open_disease=None):
        tk.Toplevel.__init__(self,master); self.db=db; self.selected_disease_id=selected_disease_id; self.on_open_disease=on_open_disease
        self.title("Bilgi Sınavı ve Öğrenme Merkezi"); self.geometry("1050x700")
        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=10,pady=10)
        self.bank=ttk.Frame(nb,padding=10); self.start=ttk.Frame(nb,padding=16); self.history=ttk.Frame(nb,padding=10)
        nb.add(self.bank,text="Soru Bankası"); nb.add(self.start,text="Test Başlat"); nb.add(self.history,text="Geçmiş ve İstatistik")
        self.build_bank(); self.build_start(); self.build_history(); self.refresh_bank(); self.refresh_history()
    def build_bank(self):
        bar=ttk.Frame(self.bank); bar.pack(fill="x"); self.query=tk.StringVar(); ttk.Entry(bar,textvariable=self.query).pack(side="left",fill="x",expand=True); ttk.Button(bar,text="Ara",command=self.refresh_bank).pack(side="left",padx=4); ttk.Button(bar,text="Yeni soru",command=lambda:QuestionEditor(self,self.db,disease_id=self.selected_disease_id,on_saved=self.refresh_bank)).pack(side="left")
        self.tree=ttk.Treeview(self.bank,columns=("type","difficulty","topic","disease"),show="tree headings"); self.tree.heading("#0",text="Soru");
        for c,t,w in (("type","Tür",120),("difficulty","Zorluk",80),("topic","Konu",120),("disease","Hastalık",180)): self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.column("#0",width=420); self.tree.pack(fill="both",expand=True,pady=8); self.tree.bind("<Double-1>",lambda e:self.edit_question())
        b=ttk.Frame(self.bank); b.pack(fill="x"); ttk.Button(b,text="Düzenle",command=self.edit_question).pack(side="left"); ttk.Button(b,text="Sil",command=self.delete_question).pack(side="left",padx=4)
    def refresh_bank(self):
        self.tree.delete(*self.tree.get_children())
        for q in self.db.quiz_questions(query=self.query.get()): self.tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["question_type"],q["difficulty"],q["topic_tag"],q["disease_name"] or ""))
    def edit_question(self):
        s=self.tree.selection();
        if s: QuestionEditor(self,self.db,int(s[0]),on_saved=self.refresh_bank)
    def delete_question(self):
        s=self.tree.selection();
        if s and messagebox.askyesno("Soru sil","Seçili soru silinsin mi?",parent=self): self.db.quiz_question_delete(int(s[0])); self.refresh_bank()
    def build_start(self):
        ttk.Label(self.start,text="Kişiselleştirilmiş test oluştur",font=("Segoe UI",16,"bold")).pack(anchor="w",pady=(0,12))
        self.mode=tk.StringVar(value="Sınav"); self.count_var=tk.IntVar(value=10); self.diff=tk.StringVar(value="Tümü"); self.topic=tk.StringVar(value=""); self.only_selected=tk.BooleanVar(value=bool(self.selected_disease_id))
        for label,widget in (("Mod",ttk.Combobox(self.start,textvariable=self.mode,values=("Sınav","Çalışma"),state="readonly")),("Soru sayısı",ttk.Spinbox(self.start,from_=1,to=100,textvariable=self.count_var)),("Zorluk",ttk.Combobox(self.start,textvariable=self.diff,values=("Tümü",)+DIFFICULTIES,state="readonly")),("Konu etiketi",ttk.Entry(self.start,textvariable=self.topic))):
            row=ttk.Frame(self.start); row.pack(fill="x",pady=5); ttk.Label(row,text=label,width=18).pack(side="left"); widget.pack(side="left",fill="x",expand=True)
        ttk.Checkbutton(self.start,text="Yalnız seçili hastalığın soruları",variable=self.only_selected,state="normal" if self.selected_disease_id else "disabled").pack(anchor="w",pady=8)
        ttk.Button(self.start,text="Testi başlat",style="Primary.TButton",command=self.start_exam).pack(anchor="w",pady=12)
    def start_exam(self):
        disease_id=self.selected_disease_id if self.only_selected.get() else None; diff="" if self.diff.get()=="Tümü" else self.diff.get()
        rows=list(self.db.quiz_questions(disease_id=disease_id,difficulty=diff,topic=self.topic.get(),active_only=True)); random.shuffle(rows); rows=rows[:max(1,int(self.count_var.get()))]
        if not rows: messagebox.showinfo("Soru bulunamadı","Seçilen ölçütlerde etkin soru yok.",parent=self); return
        ExamWindow(self,self.db,rows,self.mode.get(),self.on_open_disease)
    def build_history(self):
        self.stats=tk.StringVar(); ttk.Label(self.history,textvariable=self.stats,font=("Segoe UI",12,"bold")).pack(anchor="w",pady=(0,8))
        self.hist=ttk.Treeview(self.history,columns=("date","mode","total","score","duration"),show="headings")
        for c,t,w in (("date","Tarih",170),("mode","Mod",100),("total","Soru",70),("score","Puan",80),("duration","Süre",80)): self.hist.heading(c,text=t); self.hist.column(c,width=w)
        self.hist.pack(fill="both",expand=True)
    def refresh_history(self):
        self.hist.delete(*self.hist.get_children()); rows=self.db.quiz_sessions();
        for r in rows:self.hist.insert("","end",iid=str(r["id"]),values=(r["started_at"],r["mode"],r["total_questions"],"%{}".format(r["score"]),"{} sn".format(r["duration_seconds"])))
        st=self.db.quiz_stats(); self.stats.set("{} sınav • {} soru • genel başarı %{}".format(st["sessions"],st["questions"],st["average_score"]))
