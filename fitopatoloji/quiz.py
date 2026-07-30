# -*- coding: utf-8 -*-
from .common import *
import random

QUESTION_TYPES = ("Çoktan seçmeli", "Doğru / Yanlış", "Kısa cevap")
DIFFICULTIES = ("Kolay", "Orta", "Zor")
OPTION_KEYS = ("option_a", "option_b", "option_c", "option_d", "option_e")
FORMAT_KEYS = ("option_a_format_json", "option_b_format_json", "option_c_format_json", "option_d_format_json", "option_e_format_json")


def center_window(win, width=None, height=None):
    """Pencereyi ana pencerenin veya ekranın ortasında açar."""
    def _center():
        try:
            win.update_idletasks()
            w = int(width or win.winfo_width() or win.winfo_reqwidth())
            h = int(height or win.winfo_height() or win.winfo_reqheight())
            parent = win.master
            if parent is not None and parent.winfo_exists() and parent.winfo_viewable():
                x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
                y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
            else:
                x = max(0, (win.winfo_screenwidth() - w) // 2)
                y = max(0, (win.winfo_screenheight() - h) // 2)
            win.geometry("{}x{}+{}+{}".format(w, h, x, y))
        except tk.TclError:
            pass
    win.after_idle(_center)


def _loads_format(value):
    try:
        obj = json.loads(value or "{}")
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _quiz_image_root(db):
    root = os.path.abspath(os.path.join(os.path.dirname(db.db_path), os.pardir, "Images", "Quiz"))
    if not os.path.isdir(root):
        os.makedirs(root)
    return root


def _resolve_quiz_image(db, stored_path):
    value = (stored_path or "").strip()
    if not value:
        return ""
    if os.path.isabs(value):
        return value
    return os.path.join(_quiz_image_root(db), value)


def _load_preview(path, max_size):
    if not path or not os.path.exists(path):
        return None
    try:
        if PIL_AVAILABLE:
            image = Image.open(path)
            image.thumbnail(max_size, Image.LANCZOS if hasattr(Image, "LANCZOS") else Image.ANTIALIAS)
            return ImageTk.PhotoImage(image)
        return tk.PhotoImage(file=path)
    except Exception:
        return None


class QuizImagePreview(tk.Toplevel):
    def __init__(self, master, path, caption=""):
        tk.Toplevel.__init__(self, master)
        self.title("Soru görseli")
        self.geometry("900x680")
        self.transient(master)
        center_window(self, 900, 680)
        frame = ttk.Frame(self, padding=12); frame.pack(fill="both", expand=True)
        self.photo = _load_preview(path, (840, 570))
        if self.photo:
            ttk.Label(frame, image=self.photo, anchor="center").pack(fill="both", expand=True)
        else:
            ttk.Label(frame, text="Görsel açılamadı veya desteklenmeyen bir dosya biçimi.", anchor="center").pack(fill="both", expand=True)
        if caption:
            ttk.Label(frame, text=caption, wraplength=820, style="Muted.TLabel").pack(fill="x", pady=(8, 0))
        ttk.Button(frame, text="Kapat", command=self.destroy).pack(anchor="e", pady=(8, 0))


class MiniRichText(ttk.Frame):
    """Kalın/italik/birleşik biçimleri saklayan küçük metin düzenleyici."""
    def __init__(self, master, value="", formatting=None, height=3):
        ttk.Frame.__init__(self, master)
        bar = ttk.Frame(self); bar.pack(fill="x", pady=(0, 1))
        ttk.Button(bar, text="B", width=2, command=self.toggle_bold).pack(side="left")
        ttk.Button(bar, text="I", width=2, command=self.toggle_italic).pack(side="left", padx=(1, 0))
        body = ttk.Frame(self); body.pack(fill="both", expand=True)
        self.text = tk.Text(body, height=height, wrap="word", undo=True, font=("Segoe UI", 10))
        sb = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
        self.text.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.text.tag_configure("italic", font=("Segoe UI", 10, "italic"))
        self.text.tag_configure("bolditalic", font=("Segoe UI", 10, "bold italic"))
        self.text.insert("1.0", value or "")
        self.apply_formatting(formatting or {})
        self.text.bind("<Control-b>", self._key_bold)
        self.text.bind("<Control-i>", self._key_italic)
    def _key_bold(self, event): self.toggle_bold(); return "break"
    def _key_italic(self, event): self.toggle_italic(); return "break"
    def _selection(self):
        try: return self.text.index("sel.first"), self.text.index("sel.last")
        except tk.TclError: return None
    def _has_full(self, tag, start, end):
        ranges = self.text.tag_ranges(tag)
        for i in range(0, len(ranges), 2):
            if self.text.compare(ranges[i], "<=", start) and self.text.compare(ranges[i+1], ">=", end): return True
        return False
    def _apply_combined(self, start, end, bold, italic):
        for tag in ("bold", "italic", "bolditalic"): self.text.tag_remove(tag, start, end)
        if bold and italic: self.text.tag_add("bolditalic", start, end)
        elif bold: self.text.tag_add("bold", start, end)
        elif italic: self.text.tag_add("italic", start, end)
    def toggle_bold(self):
        sel = self._selection()
        if not sel: return
        start, end = sel
        is_bold = self._has_full("bold", start, end) or self._has_full("bolditalic", start, end)
        is_italic = self._has_full("italic", start, end) or self._has_full("bolditalic", start, end)
        self._apply_combined(start, end, not is_bold, is_italic)
    def toggle_italic(self):
        sel = self._selection()
        if not sel: return
        start, end = sel
        is_bold = self._has_full("bold", start, end) or self._has_full("bolditalic", start, end)
        is_italic = self._has_full("italic", start, end) or self._has_full("bolditalic", start, end)
        self._apply_combined(start, end, is_bold, not is_italic)
    def get_value(self): return self.text.get("1.0", "end-1c").strip()
    def serialize(self):
        result = {"bold": [], "italic": [], "bolditalic": []}
        for tag in result:
            ranges = self.text.tag_ranges(tag)
            result[tag] = [[str(ranges[i]), str(ranges[i+1])] for i in range(0, len(ranges), 2)]
        return {k:v for k,v in result.items() if v}
    def apply_formatting(self, fmt):
        for tag in ("bold", "italic", "bolditalic"):
            for start, end in (fmt or {}).get(tag, []):
                try: self.text.tag_add(tag, start, end)
                except tk.TclError: pass


def render_formatted_text(widget, value, formatting, base_font=("Segoe UI", 11), base_bold=False):
    widget.configure(state="normal"); widget.delete("1.0", "end")
    family, size = base_font[0], base_font[1]
    widget.tag_configure("base", font=(family, size, "bold" if base_bold else "normal"))
    widget.tag_configure("bold", font=(family, size, "bold"))
    widget.tag_configure("italic", font=(family, size, "italic"))
    widget.tag_configure("bolditalic", font=(family, size, "bold italic"))
    widget.insert("1.0", value or "", ("base",))
    for tag in ("bold", "italic", "bolditalic"):
        for start, end in (formatting or {}).get(tag, []):
            try: widget.tag_add(tag, start, end)
            except tk.TclError: pass
    widget.configure(state="disabled")


class DiseasePicker(tk.Toplevel):
    def __init__(self, master, db, selected_ids=None, on_apply=None):
        tk.Toplevel.__init__(self, master); self.db=db; self.on_apply=on_apply
        self.selected=set(int(x) for x in (selected_ids or [])); self._search_job=None
        self.title("İlişkili hastalıkları seç"); self.geometry("840x580"); self.transient(master); self.grab_set(); center_window(self,840,580)
        root=ttk.Frame(self,padding=12); root.pack(fill="both",expand=True)
        top=ttk.Frame(root); top.pack(fill="x"); self.query=tk.StringVar()
        ent=ttk.Entry(top,textvariable=self.query); ent.pack(side="left",fill="x",expand=True); ent.focus_set()
        ttk.Button(top,text="Seçimi temizle",command=self.clear).pack(side="left",padx=(6,0))
        self.query.trace_add("write", self._schedule_refresh)
        ttk.Label(root,text="Arama sonuçları yazdıkça güncellenir. Birden fazla hastalık seçebilirsiniz.",style="Muted.TLabel").pack(anchor="w",pady=(6,4))
        self.tree=ttk.Treeview(root,columns=("selected","scientific","group"),show="tree headings",selectmode="extended")
        self.tree.heading("#0",text="Hastalık"); self.tree.heading("selected",text="Seçili"); self.tree.heading("scientific",text="Bilimsel ad"); self.tree.heading("group",text="Grup")
        self.tree.column("#0",width=270); self.tree.column("selected",width=65,anchor="center"); self.tree.column("scientific",width=275); self.tree.column("group",width=150)
        self.tree.pack(fill="both",expand=True); self.tree.bind("<Double-1>",lambda e:self.toggle())
        bar=ttk.Frame(root); bar.pack(fill="x",pady=(10,0)); ttk.Button(bar,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(bar,text="Uygula",style="Primary.TButton",command=self.apply).pack(side="right",padx=6)
        self.refresh()
    def _schedule_refresh(self,*args):
        if self._search_job:
            try:self.after_cancel(self._search_job)
            except tk.TclError:pass
        self._search_job=self.after(180,self.refresh)
    def refresh(self):
        self._search_job=None; self.tree.delete(*self.tree.get_children())
        for d in self.db.search(query=self.query.get().strip()):
            did=int(d["id"]); self.tree.insert("","end",iid=str(did),text=d["disease_name"],values=("✓" if did in self.selected else "",d["scientific_name"],d["group_name"] or ""))
    def toggle(self):
        for iid in self.tree.selection():
            did=int(iid)
            if did in self.selected:self.selected.remove(did)
            else:self.selected.add(did)
        self.refresh()
    def clear(self):self.selected.clear();self.refresh()
    def apply(self):
        if self.on_apply:self.on_apply(sorted(self.selected))
        self.destroy()


class QuestionEditor(tk.Toplevel):
    """Her soru türünü ayrı sekmede düzenler; tür değiştirmek veriyi dönüştürmez."""
    def __init__(self, master, db, question_id=None, disease_id=None, on_saved=None, initial_type=None):
        tk.Toplevel.__init__(self, master); self.db=db; self.question_id=question_id; self.on_saved=on_saved
        self.title("Soru düzenleyici"); self.geometry("1040x760"); self.minsize(900,650); self.transient(master); self.grab_set(); center_window(self,1040,760)
        self.row=db.quiz_question_get(question_id) if question_id else None
        self.selected_disease_ids=db.quiz_question_disease_ids(question_id) if question_id else ([int(disease_id)] if disease_id else [])
        self.current_type=(self.row["question_type"] if self.row else (initial_type or QUESTION_TYPES[0]))
        self.image_path = (self.row["image_path"] if self.row and "image_path" in self.row.keys() else "")
        self.pending_image_path = ""
        self.image_caption = tk.StringVar(value=(self.row["image_caption"] if self.row and "image_caption" in self.row.keys() else ""))
        self.image_source = tk.StringVar(value=(self.row["image_source"] if self.row and "image_source" in self.row.keys() else ""))
        self.image_copyright = tk.StringVar(value=(self.row["image_copyright"] if self.row and "image_copyright" in self.row.keys() else ""))
        footer=ttk.Frame(self,padding=(12,6)); footer.pack(fill="x",side="bottom")
        ttk.Button(footer,text="İptal",command=self.destroy).pack(side="right"); ttk.Button(footer,text="Kaydet",style="Primary.TButton",command=self.save).pack(side="right",padx=6)
        body=ttk.Frame(self,padding=(10,5)); body.pack(fill="both",expand=True)
        common=ttk.Frame(body); common.pack(fill="x")
        self.difficulty=tk.StringVar(value=(self.row["difficulty"] if self.row else "Orta")); self.topic=tk.StringVar(value=(self.row["topic_tag"] if self.row else "")); self.source=tk.StringVar(value=(self.row["source_text"] if self.row else ""))
        for col,(label,var,values) in enumerate((("Zorluk",self.difficulty,DIFFICULTIES),("Konu etiketleri",self.topic,self.db.quiz_topic_tags()),("Kaynak / dayanak",self.source,()))):
            box=ttk.Frame(common); box.grid(row=0,column=col,sticky="ew",padx=(0,8)); ttk.Label(box,text=label).pack(anchor="w")
            if values:ttk.Combobox(box,textvariable=var,values=values).pack(fill="x")
            else:ttk.Entry(box,textvariable=var).pack(fill="x")
            common.columnconfigure(col,weight=1)
        rel=ttk.LabelFrame(body,text="İlişkili hastalıklar",padding=4); rel.pack(fill="x",pady=(3,2))
        self.disease_summary=tk.StringVar(); ttk.Label(rel,textvariable=self.disease_summary,wraplength=720).pack(side="left",fill="x",expand=True)
        ttk.Button(rel,text="Ara ve seç…",command=lambda:DiseasePicker(self,self.db,self.selected_disease_ids,self.set_diseases)).pack(side="right")
        ttk.Label(body,text="Konu etiketi test filtrelerinde; kaynak alanı bilimsel dayanağı gösterir.",style="Muted.TLabel").pack(anchor="w",pady=(0,3))
        image_box=ttk.LabelFrame(body,text="Soru görseli (isteğe bağlı)",padding=4); image_box.pack(fill="x",pady=(1,2))
        self.image_status=tk.StringVar(); ttk.Label(image_box,textvariable=self.image_status,wraplength=480).pack(side="left",fill="x",expand=True)
        ttk.Button(image_box,text="Görsel seç…",command=self.choose_image).pack(side="left",padx=2)
        ttk.Button(image_box,text="Bilgiler…",command=self.edit_image_metadata).pack(side="left",padx=2)
        ttk.Button(image_box,text="Önizle",command=self.preview_image).pack(side="left",padx=2)
        ttk.Button(image_box,text="Kaldır",command=self.remove_image).pack(side="left",padx=2)
        self._refresh_image_status()
        self.tabs=ttk.Notebook(body); self.tabs.pack(fill="both",expand=True)
        self.type_frames={}; self.editors={}
        for typ in QUESTION_TYPES:
            frame=ttk.Frame(self.tabs,padding=10); self.tabs.add(frame,text=typ); self.type_frames[typ]=frame
            self._build_type_tab(typ,frame)
        self.tabs.bind("<<NotebookTabChanged>>",self._tab_changed)
        self.tabs.select(QUESTION_TYPES.index(self.current_type)); self.set_diseases(self.selected_disease_ids)
    def _current_image_file(self):
        return self.pending_image_path or _resolve_quiz_image(self.db, self.image_path)
    def _refresh_image_status(self):
        path=self._current_image_file()
        self.image_status.set(os.path.basename(path) if path else "Bu soruya görsel eklenmedi.")
    def choose_image(self):
        path=filedialog.askopenfilename(parent=self,title="Soru görseli seç",filetypes=[("Görsel dosyaları","*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tif;*.tiff"),("Tüm dosyalar","*.*")])
        if path:
            self.pending_image_path=path; self._refresh_image_status()
    def edit_image_metadata(self):
        win=tk.Toplevel(self); win.title("Soru görseli bilgileri"); win.geometry("620x245"); win.transient(self); win.grab_set(); center_window(win,620,245)
        f=ttk.Frame(win,padding=12); f.pack(fill="both",expand=True); f.columnconfigure(1,weight=1)
        for row,(label,var) in enumerate((("Görsel açıklaması",self.image_caption),("Kaynak / URL",self.image_source),("Telif / kullanım",self.image_copyright))):
            ttk.Label(f,text=label).grid(row=row,column=0,sticky="w",padx=(0,10),pady=6); ttk.Entry(f,textvariable=var).grid(row=row,column=1,sticky="ew",pady=6)
        ttk.Label(f,text="Bu bilgiler soruyla birlikte saklanır ve büyük önizlemede gösterilir.",style="Muted.TLabel").grid(row=3,column=0,columnspan=2,sticky="w",pady=(8,4))
        ttk.Button(f,text="Kapat",command=win.destroy).grid(row=4,column=1,sticky="e",pady=(10,0))
    def preview_image(self):
        path=self._current_image_file()
        if not path or not os.path.exists(path):
            messagebox.showinfo("Soru görseli","Önizlenecek bir görsel seçilmedi.",parent=self); return
        QuizImagePreview(self,path,self.image_caption.get().strip())
    def remove_image(self):
        self.pending_image_path=""; self.image_path=""; self.image_caption.set(""); self.image_source.set(""); self.image_copyright.set(""); self._refresh_image_status()
    def _store_pending_image(self):
        if not self.pending_image_path:
            return self.image_path
        ext=os.path.splitext(self.pending_image_path)[1].lower() or ".img"
        name="quiz_{}{}".format(uuid.uuid4().hex,ext)
        shutil.copy2(self.pending_image_path,os.path.join(_quiz_image_root(self.db),name))
        self.image_path=name; self.pending_image_path=""
        return name
    def _fmt(self,key): return _loads_format(self.row[key]) if self.row and key in self.row.keys() else {}
    def _val(self,key): return self.row[key] if self.row and key in self.row.keys() else ""
    def _build_type_tab(self,typ,frame):
        active=(self.current_type==typ)
        frame.columnconfigure(0,weight=1)
        frame.rowconfigure(5,weight=1)
        ttk.Label(frame,text="Soru kökü").grid(row=0,column=0,sticky="w")
        q=MiniRichText(frame,self._val("question_text") if active else "",self._fmt("question_format_json") if active else {},height=2)
        q.grid(row=1,column=0,sticky="ew",pady=(1,3)); self.editors[(typ,"question")]=q
        if typ=="Çoktan seçmeli":
            opts=[]
            option_area=ttk.LabelFrame(frame,text="Seçenekler (A–E)",padding=3)
            option_area.grid(row=2,column=0,sticky="ew",pady=(0,3))
            option_area.columnconfigure(0,weight=1); option_area.columnconfigure(1,weight=1)
            for i,(key,fkey) in enumerate(zip(OPTION_KEYS,FORMAT_KEYS)):
                row=i//2; col=i%2
                cell=ttk.Frame(option_area); cell.grid(row=row,column=col,sticky="nsew",padx=(0 if col==0 else 4,4 if col==0 else 0),pady=0)
                ttk.Label(cell,text=chr(65+i)+")",width=2).pack(side="left",anchor="n",pady=17)
                ed=MiniRichText(cell,self._val(key) if active else "",self._fmt(fkey) if active else {},height=1)
                ed.pack(side="left",fill="both",expand=True);opts.append(ed)
            ans=ttk.LabelFrame(option_area,text="Doğru cevap",padding=5)
            ans.grid(row=2,column=1,sticky="nsew",padx=(4,0),pady=0)
            var=tk.StringVar(value=(self._val("correct_answer") if active else "A"))
            ttk.Label(ans,text="Seçenek:").pack(side="left",padx=(0,5))
            ttk.Combobox(ans,textvariable=var,values=tuple("ABCDE"),state="readonly",width=5).pack(side="left")
            self.editors[(typ,"options")]=opts; self.editors[(typ,"answer_var")]=var
        elif typ=="Doğru / Yanlış":
            ans=ttk.LabelFrame(frame,text="Doğru cevap",padding=6);ans.grid(row=2,column=0,sticky="ew",pady=(0,4))
            var=tk.StringVar(value=(self._val("correct_answer") if active else "Doğru"))
            ttk.Radiobutton(ans,text="Doğru",value="Doğru",variable=var).pack(side="left",padx=8);ttk.Radiobutton(ans,text="Yanlış",value="Yanlış",variable=var).pack(side="left",padx=8);self.editors[(typ,"answer_var")]=var
        else:
            answer_frame=ttk.Frame(frame); answer_frame.grid(row=2,column=0,sticky="ew",pady=(0,3))
            ttk.Label(answer_frame,text="Kabul edilecek doğru cevap").pack(anchor="w")
            ed=MiniRichText(answer_frame,self._val("correct_answer") if active else "",self._fmt("correct_answer_format_json") if active else {},height=2);ed.pack(fill="x",pady=(1,1));self.editors[(typ,"answer")]=ed
            ttk.Label(answer_frame,text="Birden fazla kabul edilen cevap için | kullanın.",style="Muted.TLabel").pack(anchor="w")
        ttk.Label(frame,text="Doğru cevabın açıklaması").grid(row=4,column=0,sticky="w",pady=(2,0))
        exp=MiniRichText(frame,self._val("explanation") if active else "",self._fmt("explanation_format_json") if active else {},height=4)
        exp.grid(row=5,column=0,sticky="nsew",pady=(1,0));self.editors[(typ,"explanation")]=exp
    def _tab_changed(self,event=None):
        self.current_type=QUESTION_TYPES[self.tabs.index(self.tabs.select())]
    def set_diseases(self,ids):
        self.selected_disease_ids=list(ids); names=[]
        for did in self.selected_disease_ids:
            d=self.db.get(int(did))
            if d:names.append(d["disease_name"])
        self.disease_summary.set("; ".join(names) if names else "İlişkili hastalık seçilmedi.")
    def save(self):
        typ=QUESTION_TYPES[self.tabs.index(self.tabs.select())]; q=self.editors[(typ,"question")]
        question=q.get_value()
        if not question:messagebox.showwarning("Eksik bilgi","Soru kökü boş bırakılamaz.",parent=self);return
        data=dict(disease_ids=self.selected_disease_ids,question_type=typ,question_text=question,difficulty=self.difficulty.get(),topic_tag=self.topic.get().strip(),source_text=self.source.get().strip(),question_format_json=json.dumps(q.serialize(),ensure_ascii=False),option_a="",option_b="",option_c="",option_d="",option_e="",option_a_format_json="{}",option_b_format_json="{}",option_c_format_json="{}",option_d_format_json="{}",option_e_format_json="{}",correct_answer="",correct_answer_format_json="{}")
        if typ=="Çoktan seçmeli":
            opts=self.editors[(typ,"options")]
            for key,fkey,ed in zip(OPTION_KEYS,FORMAT_KEYS,opts):data[key]=ed.get_value();data[fkey]=json.dumps(ed.serialize(),ensure_ascii=False)
            if any(not data[k] for k in OPTION_KEYS):messagebox.showwarning("Eksik seçenek","Çoktan seçmeli sorularda A–E seçeneklerinin tamamı doldurulmalıdır.",parent=self);return
            data["correct_answer"]=self.editors[(typ,"answer_var")].get()
            if not data["correct_answer"]:
                messagebox.showwarning("Eksik doğru cevap", "Çoktan seçmeli sorularda doğru seçenek seçilmelidir.", parent=self); return
        elif typ=="Doğru / Yanlış":data["correct_answer"]=self.editors[(typ,"answer_var")].get()
        else:
            ans=self.editors[(typ,"answer")];data["correct_answer"]=ans.get_value();data["correct_answer_format_json"]=json.dumps(ans.serialize(),ensure_ascii=False)
            if not data["correct_answer"]:messagebox.showwarning("Eksik cevap","Kısa cevap sorusunda kabul edilecek doğru cevabı yazın.",parent=self);return
        exp=self.editors[(typ,"explanation")];data["explanation"]=exp.get_value();data["explanation_format_json"]=json.dumps(exp.serialize(),ensure_ascii=False)
        data["image_path"]=self._store_pending_image(); data["image_caption"]=self.image_caption.get().strip(); data["image_source"]=self.image_source.get().strip(); data["image_copyright"]=self.image_copyright.get().strip()
        self.question_id=self.db.quiz_question_save(self.question_id,**data)
        if self.on_saved:self.on_saved()
        self.destroy()


class ExamWindow(tk.Toplevel):
    def __init__(self,master,db,questions,mode,on_open_disease=None,show_feedback=False):
        tk.Toplevel.__init__(self,master);self.db=db;self.questions=list(questions);self.mode=mode;self.on_open_disease=on_open_disease;self.show_feedback=bool(show_feedback or mode=="Çalışma")
        self.index=0;self.answers={};self.feedback_seen=set();self.started=dt.datetime.now();self.finished=False
        self.title("{} — Bilgi Sınavı".format(mode));self.geometry("900x690");self.minsize(780,590);self.transient(master);center_window(self,900,690)
        self.protocol("WM_DELETE_WINDOW",self.request_finish)
        root=ttk.Frame(self,padding=10);root.pack(fill="both",expand=True)
        top=ttk.Frame(root);top.pack(fill="x");self.progress=tk.StringVar();ttk.Label(top,textvariable=self.progress,font=("Segoe UI",11,"bold")).pack(side="left");ttk.Button(top,text="Testi Sonlandır",command=self.request_finish).pack(side="right")
        footer=ttk.Frame(root);footer.pack(fill="x",side="bottom",pady=(8,0))
        self.prev_btn=ttk.Button(footer,text="Önceki",command=self.previous);self.prev_btn.pack(side="left")
        self.next_btn=ttk.Button(footer,text="Sonraki",style="Primary.TButton",command=self.next);self.next_btn.pack(side="right")
        self.check_btn=ttk.Button(footer,text="Cevabı ve açıklamayı göster",command=self.check_now);self.check_btn.pack(side="right",padx=8)
        viewport=ttk.Frame(root);viewport.pack(fill="both",expand=True,pady=(8,0))
        self.exam_canvas=tk.Canvas(viewport,highlightthickness=0,borderwidth=0)
        self.exam_scroll=ttk.Scrollbar(viewport,orient="vertical",command=self.exam_canvas.yview)
        self.exam_canvas.configure(yscrollcommand=self.exam_scroll.set)
        self.exam_scroll.pack(side="right",fill="y");self.exam_canvas.pack(side="left",fill="both",expand=True)
        self.content=ttk.Frame(self.exam_canvas,padding=(4,0,4,4))
        self.content_window=self.exam_canvas.create_window((0,0),window=self.content,anchor="nw")
        self.content.bind("<Configure>",lambda e:self.exam_canvas.configure(scrollregion=self.exam_canvas.bbox("all")))
        self.exam_canvas.bind("<Configure>",lambda e:self.exam_canvas.itemconfigure(self.content_window,width=e.width))
        self.exam_canvas.bind("<MouseWheel>",self._on_exam_wheel)
        self.content.bind("<MouseWheel>",self._on_exam_wheel)
        self.image_frame=ttk.Frame(self.content); self.image_label=ttk.Label(self.image_frame,anchor="center",cursor="hand2"); self.image_label.pack()
        self.image_caption_label=ttk.Label(self.image_frame,style="Muted.TLabel",wraplength=760,anchor="center"); self.image_caption_label.pack(fill="x",pady=(3,0))
        self.exam_image_ref=None; self.exam_image_path=""; self.image_label.bind("<Button-1>",lambda e:self.open_image_preview())
        self.q_text=tk.Text(self.content,height=4,wrap="word",relief="flat",font=("Segoe UI",13));self.q_text.pack(fill="x",pady=(6,6))
        self.answer_box=ttk.LabelFrame(self.content,text="Cevabınız",padding=8);self.answer_box.pack(fill="x")
        self.answer_var=tk.StringVar()
        self.feedback=tk.Text(self.content,height=8,wrap="word",state="disabled",font=("Segoe UI",10));self.feedback.pack(fill="x",pady=(8,0))
        self.q_text.bind("<MouseWheel>",self._on_exam_wheel); self.feedback.bind("<MouseWheel>",self._on_exam_wheel)
        self.show_question()
    def _on_exam_wheel(self,event):
        try:
            delta=-1 if event.delta>0 else 1
            self.exam_canvas.yview_scroll(delta,"units")
        except tk.TclError:
            pass
        return "break"
    @staticmethod
    def _option_height(value):
        text=value or ""
        logical=sum(max(1,(len(line)+69)//70) for line in text.splitlines() or [""])
        return max(2,min(8,logical))
    def _save_current(self):
        if self.questions:self.answers[int(self.questions[self.index]["id"])]=self.answer_var.get()
    def show_question(self):
        for w in self.answer_box.winfo_children():w.destroy()
        self.feedback.configure(state="normal");self.feedback.delete("1.0","end");self.feedback.configure(state="disabled")
        q=self.questions[self.index];qid=int(q["id"]);self.progress.set("Soru {} / {}   •   {}   •   {}".format(self.index+1,len(self.questions),q["difficulty"],q["topic_tag"] or "Genel"))
        render_formatted_text(self.q_text,q["question_text"],_loads_format(q["question_format_json"]),("Segoe UI",13),True)
        self.exam_image_path=_resolve_quiz_image(self.db,q["image_path"] if "image_path" in q.keys() else "")
        self.exam_image_ref=_load_preview(self.exam_image_path,(640,230))
        if self.exam_image_ref:
            self.image_label.configure(image=self.exam_image_ref); self.image_caption_label.configure(text=(q["image_caption"] or "") if "image_caption" in q.keys() else "")
            self.image_frame.pack(fill="x",pady=(8,4),before=self.q_text)
        else:
            self.image_frame.pack_forget()
        self.answer_var.set(self.answers.get(qid,""));typ=q["question_type"]
        if typ=="Çoktan seçmeli":
            for code,key,fkey in zip("ABCDE",OPTION_KEYS,FORMAT_KEYS):
                row=ttk.Frame(self.answer_box);row.pack(fill="x",pady=2);ttk.Radiobutton(row,value=code,variable=self.answer_var).pack(side="left",anchor="n",pady=5)
                t=tk.Text(row,height=self._option_height(q[key]),wrap="word",relief="flat",cursor="arrow");t.pack(side="left",fill="x",expand=True);render_formatted_text(t,"{}) {}".format(code,q[key]),_offset_format(_loads_format(q[fkey]),3));t.bind("<Button-1>",lambda e,c=code:self.answer_var.set(c));t.bind("<MouseWheel>",self._on_exam_wheel)
        elif typ=="Doğru / Yanlış":
            for value in ("Doğru","Yanlış"):ttk.Radiobutton(self.answer_box,text=value,value=value,variable=self.answer_var).pack(anchor="w",pady=7)
        else:ttk.Entry(self.answer_box,textvariable=self.answer_var,font=("Segoe UI",12)).pack(fill="x",pady=8)
        self.prev_btn.configure(state="normal" if self.index>0 else "disabled");self.next_btn.configure(text="Sonuçları Göster" if self.index==len(self.questions)-1 else "Sonraki");self.check_btn.configure(state="normal" if self.show_feedback else "disabled")
        if qid in self.feedback_seen:self.check_now()
        self.after_idle(lambda:self.exam_canvas.yview_moveto(0.0))
    def open_image_preview(self):
        if self.exam_image_path:
            q=self.questions[self.index]; QuizImagePreview(self,self.exam_image_path,(q["image_caption"] or "") if "image_caption" in q.keys() else "")
    def normalized(self,s):return " ".join((s or "").strip().casefold().split())
    def is_correct(self,q,a):
        aa=self.normalized(a); answers=[self.normalized(x) for x in (q["correct_answer"] or "").split("|")];aliases={"d":"doğru","y":"yanlış"};aa=aliases.get(aa,aa);answers=[aliases.get(x,x) for x in answers];return aa in answers
    def check_now(self):
        if not self.questions:return
        q=self.questions[self.index];ans=self.answer_var.get();self.answers[int(q["id"])]=ans;self.feedback_seen.add(int(q["id"]));ok=self.is_correct(q,ans)
        prefix="Doğru.\n\n" if ok else "Yanlış. Doğru cevap: {}\n\n".format(q["correct_answer"])
        self.feedback.configure(state="normal");self.feedback.delete("1.0","end");self.feedback.insert("1.0",prefix);start=self.feedback.index("end-1c");self.feedback.insert("end",q["explanation"] or "Açıklama eklenmemiş.")
        fmt=_loads_format(q["explanation_format_json"])
        for tag in ("bold","italic","bolditalic"):
            self.feedback.tag_configure(tag,font=("Segoe UI",10,"bold italic" if tag=="bolditalic" else tag))
            for a,b in fmt.get(tag,[]):
                try:self.feedback.tag_add(tag,_add_index(start,a),_add_index(start,b))
                except tk.TclError:pass
        self.feedback.configure(state="disabled")
        self.after_idle(lambda:self.exam_canvas.yview_moveto(1.0))
    def previous(self):self._save_current();self.index=max(0,self.index-1);self.show_question()
    def next(self):
        self._save_current()
        if self.index>=len(self.questions)-1:self.finish();return
        self.index+=1;self.show_question()
    def request_finish(self):
        if self.finished:return
        if messagebox.askyesno("Testi sonlandır","Test şimdi sonlandırılsın mı? Verilen cevaplar değerlendirilir.",parent=self):self.finish()
    def finish(self):
        if self.finished:return
        self._save_current();self.finished=True
        correct=0;wrong=[];blank=0;details=[]
        for q in self.questions:
            a=self.answers.get(int(q["id"]),"");ok=self.is_correct(q,a)
            if not a.strip():blank+=1
            elif ok:correct+=1
            else:wrong.append(q)
            details.append({"question_id":int(q["id"]),"answer":a,"correct":ok})
        total=len(self.questions);score=round(100.0*correct/total,1) if total else 0;seconds=int((dt.datetime.now()-self.started).total_seconds());sid=self.db.quiz_session_save(self.mode,total,correct,len(wrong),blank,score,seconds,details)
        self.withdraw();result=ResultWindow(self.master,self.db,sid,total,correct,len(wrong),blank,score,wrong,self.on_open_disease);result.protocol("WM_DELETE_WINDOW",lambda:(result.destroy(),self.destroy()))


def _offset_format(fmt,prefix_len):
    result={}
    for tag in ("bold","italic","bolditalic"):
        result[tag]=[[_shift_index(a,prefix_len),_shift_index(b,prefix_len)] for a,b in (fmt or {}).get(tag,[])]
    return result

def _shift_index(index,amount):
    try:line,col=index.split(".");return "{}.{}".format(line,int(col)+amount if int(line)==1 else col)
    except Exception:return index

def _add_index(base,relative):
    try:line,col=relative.split(".");return "{} + {} lines + {} chars".format(base,int(line)-1,int(col))
    except Exception:return base


class ResultWindow(tk.Toplevel):
    def __init__(self,master,db,session_id,total,correct,wrong,blank,score,wrong_rows,on_open_disease):
        tk.Toplevel.__init__(self,master);self.db=db;self.on_open_disease=on_open_disease;self.title("Sınav sonucu");self.geometry("700x530");self.transient(master);center_window(self,700,530)
        footer=ttk.Frame(self,padding=(18,8));footer.pack(fill="x",side="bottom")
        f=ttk.Frame(self,padding=(18,14));f.pack(fill="both",expand=True);ttk.Label(f,text="Başarı: %{}".format(score),font=("Segoe UI",22,"bold")).pack(anchor="w");ttk.Label(f,text="{} soru • {} doğru • {} yanlış • {} boş".format(total,correct,wrong,blank)).pack(anchor="w",pady=(4,12))
        tree=ttk.Treeview(f,columns=("topic","disease"),show="tree headings",height=10);tree.heading("#0",text="Yanlış yapılan soru");tree.heading("topic",text="Konu");tree.heading("disease",text="Hastalık");tree.column("#0",width=340);tree.column("topic",width=110);tree.column("disease",width=160);tree.pack(fill="both",expand=True)
        for q in wrong_rows:tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["topic_tag"],q["disease_name"] or ""))
        def open_related():
            sel=tree.selection();ids=db.quiz_question_disease_ids(int(sel[0])) if sel else []
            if ids and on_open_disease:on_open_disease(ids[0])
        ttk.Button(footer,text="İlgili hastalığı aç",command=open_related).pack(side="left");ttk.Button(footer,text="Kapat",command=self.destroy).pack(side="right")


class QuizCenter(tk.Toplevel):
    def __init__(self,master,db,selected_disease_id=None,on_open_disease=None):
        tk.Toplevel.__init__(self,master);self.db=db;self.selected_disease_id=selected_disease_id;self.on_open_disease=on_open_disease
        self.title("Bilgi Sınavı ve Öğrenme Merkezi");self.geometry("1080x720");self.minsize(900,620);center_window(self,1080,720)
        nb=ttk.Notebook(self);nb.pack(fill="both",expand=True,padx=10,pady=10);self.bank=ttk.Frame(nb,padding=10);self.start=ttk.Frame(nb,padding=16);self.history=ttk.Frame(nb,padding=10)
        nb.add(self.bank,text="Soru Bankası");nb.add(self.start,text="Test Başlat");nb.add(self.history,text="Geçmiş ve İstatistik");self.build_bank();self.build_start();self.build_history();self.refresh_bank();self.refresh_history()
    def build_bank(self):
        bar=ttk.Frame(self.bank);bar.pack(fill="x");self.query=tk.StringVar();self.type_filter=tk.StringVar(value="Tümü");ent=ttk.Entry(bar,textvariable=self.query);ent.pack(side="left",fill="x",expand=True);ent.bind("<KeyRelease>",lambda e:self.refresh_bank())
        ttk.Combobox(bar,textvariable=self.type_filter,values=("Tümü",)+QUESTION_TYPES,state="readonly",width=18).pack(side="left",padx=5);self.type_filter.trace_add("write",lambda *a:self.refresh_bank())
        for typ,label in (("Çoktan seçmeli","+ Çoktan Seçmeli"),("Doğru / Yanlış","+ D/Y"),("Kısa cevap","+ Kısa Cevap")):ttk.Button(bar,text=label,command=lambda t=typ:QuestionEditor(self,self.db,disease_id=self.selected_disease_id,on_saved=self.refresh_bank,initial_type=t)).pack(side="left",padx=2)
        self.tree=ttk.Treeview(self.bank,columns=("type","difficulty","topic","disease"),show="tree headings");self.tree.heading("#0",text="Soru")
        for c,t,w in (("type","Tür",125),("difficulty","Zorluk",75),("topic","Konu",120),("disease","İlişkili hastalıklar",240)):self.tree.heading(c,text=t);self.tree.column(c,width=w)
        self.tree.column("#0",width=390);self.tree.pack(fill="both",expand=True,pady=8);self.tree.bind("<Double-1>",lambda e:self.edit_question())
        b=ttk.Frame(self.bank);b.pack(fill="x");ttk.Button(b,text="Düzenle",command=self.edit_question).pack(side="left");ttk.Button(b,text="Sil",command=self.delete_question).pack(side="left",padx=4)
    def refresh_bank(self):
        if not hasattr(self,"tree"):return
        self.tree.delete(*self.tree.get_children());typ="" if self.type_filter.get()=="Tümü" else self.type_filter.get()
        for q in self.db.quiz_questions(query=self.query.get(),question_type=typ):self.tree.insert("","end",iid=str(q["id"]),text=q["question_text"],values=(q["question_type"],q["difficulty"],q["topic_tag"],q["disease_name"] or ""))
    def edit_question(self):
        s=self.tree.selection()
        if s:QuestionEditor(self,self.db,int(s[0]),on_saved=self.refresh_bank)
    def delete_question(self):
        s=self.tree.selection()
        if s and messagebox.askyesno("Soru sil","Seçili soru silinsin mi?",parent=self):self.db.quiz_question_delete(int(s[0]));self.refresh_bank()
    def build_start(self):
        card=ttk.LabelFrame(self.start,text="Test ayarları",padding=20);card.pack(anchor="n",fill="x",padx=80,pady=25);card.columnconfigure(1,weight=1)
        self.mode=tk.StringVar(value="Sınav");self.exam_type=tk.StringVar(value="Çoktan seçmeli");self.count_var=tk.IntVar(value=10);self.diff=tk.StringVar(value="Tümü");self.topic=tk.StringVar(value="");self.only_selected=tk.BooleanVar(value=bool(self.selected_disease_id));self.feedback_option=tk.BooleanVar(value=False);self.mode_help=tk.StringVar()
        rows=(("Test türü",ttk.Combobox(card,textvariable=self.exam_type,values=QUESTION_TYPES,state="readonly")),("Mod",ttk.Combobox(card,textvariable=self.mode,values=("Sınav","Çalışma"),state="readonly")),("Soru sayısı",ttk.Spinbox(card,from_=1,to=100,textvariable=self.count_var)),("Zorluk",ttk.Combobox(card,textvariable=self.diff,values=("Tümü",)+DIFFICULTIES,state="readonly")),("Konu etiketi",ttk.Combobox(card,textvariable=self.topic,values=self.db.quiz_topic_tags())))
        ttk.Label(card,text="Kişiselleştirilmiş test oluştur",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,14))
        for i,(label,widget) in enumerate(rows,1):ttk.Label(card,text=label).grid(row=i,column=0,sticky="w",padx=(0,20),pady=6);widget.grid(row=i,column=1,sticky="ew",pady=6)
        ttk.Checkbutton(card,text="Yalnız seçili hastalığın soruları",variable=self.only_selected,state="normal" if self.selected_disease_id else "disabled").grid(row=6,column=0,columnspan=2,sticky="w",pady=(12,4))
        self.feedback_check=ttk.Checkbutton(card,text="Sınav sırasında cevap ve açıklama düğmesini etkinleştir",variable=self.feedback_option);self.feedback_check.grid(row=7,column=0,columnspan=2,sticky="w",pady=4)
        ttk.Label(card,textvariable=self.mode_help,style="Muted.TLabel",wraplength=650).grid(row=8,column=0,columnspan=2,sticky="w",pady=(4,2))
        ttk.Button(card,text="Testi başlat",style="Primary.TButton",command=self.start_exam).grid(row=9,column=0,columnspan=2,sticky="w",pady=(14,0))
        self.mode.trace_add("write",lambda *a:self._update_mode_help());self._update_mode_help()
    def _update_mode_help(self):
        if self.mode.get()=="Çalışma":
            self.mode_help.set("Çalışma modunda her soruda doğru cevap ve açıklama görüntülenebilir; bu düğme otomatik olarak etkindir. Sonuç yine geçmişe kaydedilir.")
            self.feedback_check.configure(state="disabled")
        else:
            self.mode_help.set("Sınav modunda cevaplar değerlendirme sonuna kadar gizli tutulur. İsterseniz yukarıdaki seçeneği açarak geri bildirim düğmesini etkinleştirebilirsiniz.")
            self.feedback_check.configure(state="normal")

    def start_exam(self):
        disease_id=self.selected_disease_id if self.only_selected.get() else None;diff="" if self.diff.get()=="Tümü" else self.diff.get()
        try:count=max(1,int(self.count_var.get()))
        except Exception:count=10
        rows=list(self.db.quiz_questions(disease_id=disease_id,difficulty=diff,topic=self.topic.get(),question_type=self.exam_type.get(),active_only=True));random.shuffle(rows);rows=rows[:count]
        if not rows:messagebox.showinfo("Soru bulunamadı","Seçilen tür ve ölçütlerde etkin soru yok.",parent=self);return
        ExamWindow(self,self.db,rows,self.mode.get(),self.on_open_disease,self.feedback_option.get())
    def build_history(self):
        top=ttk.Frame(self.history);top.pack(fill="x",pady=(0,8));self.stats=tk.StringVar();ttk.Label(top,textvariable=self.stats,font=("Segoe UI",12,"bold")).pack(side="left");ttk.Button(top,text="Tüm geçmişi temizle",command=self.clear_history).pack(side="right");ttk.Button(top,text="Seçili kaydı sil",command=self.delete_history).pack(side="right",padx=6)
        self.hist=ttk.Treeview(self.history,columns=("date","mode","total","score","duration"),show="headings")
        for c,t,w in (("date","Tarih",170),("mode","Mod",100),("total","Soru",70),("score","Puan",80),("duration","Süre",80)):self.hist.heading(c,text=t);self.hist.column(c,width=w)
        self.hist.pack(fill="both",expand=True)
    def delete_history(self):
        s=self.hist.selection()
        if s and messagebox.askyesno("Geçmiş kaydını sil","Seçili sınav kaydı silinsin mi?",parent=self):self.db.quiz_session_delete(int(s[0]));self.refresh_history()
    def clear_history(self):
        if messagebox.askyesno("Geçmişi temizle","Tüm sınav geçmişi ve istatistikleri kalıcı olarak silinsin mi?",parent=self):self.db.quiz_sessions_clear();self.refresh_history()
    def refresh_history(self):
        self.hist.delete(*self.hist.get_children());rows=self.db.quiz_sessions()
        for r in rows:self.hist.insert("","end",iid=str(r["id"]),values=(r["started_at"],r["mode"],r["total_questions"],"%{}".format(r["score"]),"{} sn".format(r["duration_seconds"])))
        st=self.db.quiz_stats();self.stats.set("{} sınav • {} soru • genel başarı %{}".format(st["sessions"],st["questions"],st["average_score"]))
