# -*- coding: utf-8 -*-
from .common import *


class RichTextEditor(ttk.Frame):
    """Birleşik biçimleri koruyan, Windows 7 uyumlu bilimsel zengin metin editörü."""
    SYMBOLS = ["α", "β", "γ", "δ", "Δ", "µ", "°", "±", "≤", "≥", "×", "→", "♀", "♂", "®", "©"]
    FONT_FAMILIES = ["Segoe UI", "Arial", "Calibri", "Times New Roman", "Courier New", "Cambria"]
    FONT_SIZES = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32"]
    SEMANTIC_PREFIXES = ("fontfamily_", "fontsize_", "color_", "highlight_")

    def __init__(self, master, value="", formatting=None, height=6):
        ttk.Frame.__init__(self, master)
        self.color_tags = {}
        self._visual_tags = set()
        self._refresh_job = None

        toolbar1 = ttk.Frame(self); toolbar1.pack(fill="x", pady=(0, 2))
        self.font_family_var = tk.StringVar(value="Segoe UI")
        self.font_size_var = tk.StringVar(value="9")
        family = ttk.Combobox(toolbar1, textvariable=self.font_family_var, values=self.FONT_FAMILIES, width=17, state="readonly")
        size = ttk.Combobox(toolbar1, textvariable=self.font_size_var, values=self.FONT_SIZES, width=4, state="readonly")
        family.pack(side="left", padx=(0, 3)); size.pack(side="left", padx=(0, 5))
        family.bind("<<ComboboxSelected>>", lambda _e: self.apply_font_family())
        size.bind("<<ComboboxSelected>>", lambda _e: self.apply_font_size())
        for text, cmd, width in [
            ("B", lambda:self.toggle_tag("bold"),3), ("I", lambda:self.toggle_tag("italic"),3),
            ("U", lambda:self.toggle_tag("underline"),3), ("abc̶", lambda:self.toggle_tag("strikethrough"),4),
            ("x²", lambda:self.toggle_tag("superscript"),4), ("x₂", lambda:self.toggle_tag("subscript"),4),
            ("Bilimsel ad", self.scientific_name_style,10),
        ]:
            ttk.Button(toolbar1,text=text,width=width,command=cmd).pack(side="left",padx=(0,2))
        ttk.Button(toolbar1,text="Geri al",command=self.undo).pack(side="right",padx=2)
        ttk.Button(toolbar1,text="Yinele",command=self.redo).pack(side="right",padx=2)

        toolbar2 = ttk.Frame(self); toolbar2.pack(fill="x", pady=(0,3))
        for text,cmd,width in [
            ("• Liste",self.bullet_list,7),("1. Liste",self.numbered_list,7),
            ("Girinti +",lambda:self.indent(1),8),("Girinti −",lambda:self.indent(-1),8),
            ("Tablo",self.insert_table,6),("Sembol",self.symbol_menu,7),
        ]:
            ttk.Button(toolbar2,text=text,width=width,command=cmd).pack(side="left",padx=(0,2))
        ttk.Button(toolbar2,text="Renk",command=self.choose_color).pack(side="left",padx=(4,2))
        ttk.Button(toolbar2,text="Vurgu",command=self.choose_highlight).pack(side="left",padx=2)
        ttk.Button(toolbar2,text="Sol",width=4,command=lambda:self.align("left")).pack(side="left",padx=(5,1))
        ttk.Button(toolbar2,text="Orta",width=5,command=lambda:self.align("center")).pack(side="left",padx=1)
        ttk.Button(toolbar2,text="Sağ",width=4,command=lambda:self.align("right")).pack(side="left",padx=1)
        ttk.Button(toolbar2,text="İki yana",width=7,command=lambda:self.align("justify")).pack(side="left",padx=1)
        ttk.Button(toolbar2,text="Biçimi temizle",command=self.clear_formatting).pack(side="right")

        body=ttk.Frame(self); body.pack(fill="both",expand=True)
        self.text=tk.Text(body,height=height,wrap="word",undo=True,maxundo=-1,autoseparators=True,font=("Segoe UI",9),tabs=(40,80,120,160))
        scroll=ttk.Scrollbar(body,orient="vertical",command=self.text.yview); self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        self._configure_builtin_tags(); self.text.insert("1.0",value or ""); self.apply_formatting(formatting or {})
        self.text.bind("<Control-b>",lambda e:(self.toggle_tag("bold"),"break")[1])
        self.text.bind("<Control-i>",lambda e:(self.toggle_tag("italic"),"break")[1])
        self.text.bind("<Control-u>",lambda e:(self.toggle_tag("underline"),"break")[1])
        self.text.bind("<Control-z>",lambda e:(self.undo(),"break")[1])
        self.text.bind("<Control-y>",lambda e:(self.redo(),"break")[1])
        self.text.bind("<Control-equal>",lambda e:(self.toggle_tag("subscript"),"break")[1])
        self.text.bind("<Control-Shift-plus>",lambda e:(self.toggle_tag("superscript"),"break")[1])
        self.text.bind("<KeyRelease>",lambda _e:self._schedule_visual_refresh())
        self.text.bind("<ButtonRelease-1>",lambda _e:self._update_toolbar_state())

    def _configure_builtin_tags(self):
        # Font tags semantiktir; gerçek font birleşimleri _refresh_visual_fonts ile çizilir.
        self.text.tag_configure("bold")
        self.text.tag_configure("italic")
        self.text.tag_configure("underline",underline=True)
        self.text.tag_configure("strikethrough",overstrike=True)
        self.text.tag_configure("superscript",offset=4)
        self.text.tag_configure("subscript",offset=-3)
        self.text.tag_configure("align_left",justify="left")
        self.text.tag_configure("align_center",justify="center")
        self.text.tag_configure("align_right",justify="right")
        self.text.tag_configure("align_justify",justify="left")  # Tk tam iki yana yaslamayı desteklemez.
        self.text.tag_configure("indent_1",lmargin1=24,lmargin2=24)
        self.text.tag_configure("indent_2",lmargin1=48,lmargin2=48)
        self.text.tag_configure("indent_3",lmargin1=72,lmargin2=72)

    def _selection(self):
        try:return self.text.index("sel.first"),self.text.index("sel.last")
        except tk.TclError:return None

    def _target_range(self):
        return self._selection()

    def toggle_tag(self,tag):
        sel=self._target_range()
        if not sel:return
        start,end=sel
        # Seçimin tamamında tag varsa kaldır, aksi halde tüm seçime ekle.
        ranges=self.text.tag_ranges(tag)
        covered=False
        for i in range(0,len(ranges),2):
            if self.text.compare(ranges[i],"<=",start) and self.text.compare(ranges[i+1],">=",end): covered=True; break
        if covered:self.text.tag_remove(tag,start,end)
        else:
            if tag=="superscript":self.text.tag_remove("subscript",start,end)
            if tag=="subscript":self.text.tag_remove("superscript",start,end)
            self.text.tag_add(tag,start,end)
        self._refresh_visual_fonts()

    def apply_font_family(self):
        sel=self._selection()
        if not sel:return
        for tag in list(self.text.tag_names()):
            if tag.startswith("fontfamily_"):self.text.tag_remove(tag,*sel)
        tag="fontfamily_"+self.font_family_var.get().replace(" ","~")
        self.text.tag_configure(tag); self.text.tag_add(tag,*sel); self._refresh_visual_fonts()

    def apply_font_size(self):
        sel=self._selection()
        if not sel:return
        for tag in list(self.text.tag_names()):
            if tag.startswith("fontsize_"):self.text.tag_remove(tag,*sel)
        tag="fontsize_"+self.font_size_var.get()
        self.text.tag_configure(tag); self.text.tag_add(tag,*sel); self._refresh_visual_fonts()

    def scientific_name_style(self):
        sel=self._selection()
        if not sel:return
        self.text.tag_add("italic",*sel); self._refresh_visual_fonts()

    def _schedule_visual_refresh(self):
        if self._refresh_job:
            try:self.after_cancel(self._refresh_job)
            except Exception:pass
        self._refresh_job=self.after(80,self._refresh_visual_fonts)

    def _refresh_visual_fonts(self):
        self._refresh_job=None
        for tag in list(self._visual_tags):
            try:self.text.tag_delete(tag)
            except tk.TclError:pass
        self._visual_tags.clear()
        text_value=self.text.get("1.0","end-1c")
        if not text_value:return
        relevant=[]
        for tag in self.text.tag_names():
            if tag in ("bold","italic","superscript","subscript") or tag.startswith(("fontfamily_","fontsize_")):
                ranges=self.text.tag_ranges(tag)
                for i in range(0,len(ranges),2): relevant.append((str(ranges[i]),str(ranges[i+1]),tag))
        boundaries={"1.0","end-1c"}
        for a,b,_ in relevant:boundaries.add(a);boundaries.add(b)
        points=sorted(boundaries,key=lambda idx:int(self.text.count("1.0",idx,"chars")[0]))
        for i in range(len(points)-1):
            a,b=points[i],points[i+1]
            if self.text.compare(a,">=",b):continue
            active={tag for sa,sb,tag in relevant if self.text.compare(sa,"<=",a) and self.text.compare(sb,">=",b)}
            family="Segoe UI"; size=9
            fam=next((t for t in active if t.startswith("fontfamily_")),None)
            siz=next((t for t in active if t.startswith("fontsize_")),None)
            if fam:family=fam.split("_",1)[1].replace("~"," ")
            if siz:
                try:size=int(siz.split("_",1)[1])
                except ValueError:size=9
            if "superscript" in active or "subscript" in active:size=max(6,size-2)
            style=[]
            if "bold" in active:style.append("bold")
            if "italic" in active:style.append("italic")
            tag="__visual_{}_{}_{}".format(abs(hash(family))%100000,size,"_".join(style) or "normal")
            if tag not in self._visual_tags:
                self.text.tag_configure(tag,font=(family,size," ".join(style) if style else "normal")); self._visual_tags.add(tag)
            self.text.tag_add(tag,a,b); self.text.tag_raise(tag)
        for semantic in ("underline","strikethrough","superscript","subscript"):
            try:self.text.tag_raise(semantic)
            except tk.TclError:pass

    def _update_toolbar_state(self):
        idx=self.text.index("insert")
        tags=self.text.tag_names(idx)
        fam=next((t.split("_",1)[1].replace("~"," ") for t in tags if t.startswith("fontfamily_")),"Segoe UI")
        siz=next((t.split("_",1)[1] for t in tags if t.startswith("fontsize_")),"9")
        self.font_family_var.set(fam); self.font_size_var.set(siz)

    def _selected_lines(self):
        sel=self._selection()
        if sel:return self.text.index(sel[0]+" linestart"),self.text.index(sel[1]+" lineend")
        return self.text.index("insert linestart"),self.text.index("insert lineend")
    def bullet_list(self):self._prefix_lines("• ")
    def numbered_list(self):
        start,end=self._selected_lines(); lines=self.text.get(start,end).split("\n")
        self.text.delete(start,end); self.text.insert(start,"\n".join("{}. {}".format(i+1,line.lstrip("• ").strip()) for i,line in enumerate(lines)))
    def _prefix_lines(self,prefix):
        start,end=self._selected_lines(); lines=self.text.get(start,end).split("\n")
        self.text.delete(start,end); self.text.insert(start,"\n".join(prefix+line.lstrip("• ") for line in lines))
    def align(self,where):
        start,end=self._selected_lines()
        for tag in ("align_left","align_center","align_right","align_justify"):self.text.tag_remove(tag,start,end)
        self.text.tag_add("align_"+where,start,end)
    def indent(self,direction):
        start,end=self._selected_lines(); current=0
        for level in (1,2,3):
            tag="indent_{}".format(level)
            if tag in self.text.tag_names(start):current=level
            self.text.tag_remove(tag,start,end)
        target=max(0,min(3,current+direction))
        if target:self.text.tag_add("indent_{}".format(target),start,end)
    def insert_table(self):
        rows=simpledialog.askinteger(APP_NAME,"Satır sayısı:",initialvalue=3,minvalue=1,maxvalue=20,parent=self.winfo_toplevel())
        if not rows:return
        cols=simpledialog.askinteger(APP_NAME,"Sütun sayısı:",initialvalue=2,minvalue=1,maxvalue=8,parent=self.winfo_toplevel())
        if not cols:return
        table="\n".join("\t".join("[{}-{}]".format(r+1,c+1) for c in range(cols)) for r in range(rows))
        self.text.insert("insert",table+"\n")
    def symbol_menu(self):
        win=tk.Toplevel(self); win.title("Bilimsel semboller"); win.transient(self.winfo_toplevel()); win.resizable(False,False)
        frame=ttk.Frame(win,padding=8); frame.pack()
        for i,symbol in enumerate(self.SYMBOLS):
            ttk.Button(frame,text=symbol,width=4,command=lambda s=symbol:(self.text.insert("insert",s),win.destroy())).grid(row=i//8,column=i%8,padx=2,pady=2)
    def choose_color(self):self._choose_style("foreground","color_")
    def choose_highlight(self):self._choose_style("background","highlight_")
    def _choose_style(self,option,prefix):
        sel=self._selection()
        if not sel:return
        color=colorchooser.askcolor(parent=self.winfo_toplevel())[1]
        if not color:return
        for old in list(self.text.tag_names()):
            if old.startswith(prefix):self.text.tag_remove(old,*sel)
        tag=prefix+color.replace("#",""); self.text.tag_configure(tag,**{option:color}); self.color_tags[tag]=color; self.text.tag_add(tag,*sel)
    def clear_formatting(self):
        sel=self._selection()
        if not sel:return
        for tag in self.text.tag_names():
            if tag!="sel" and not tag.startswith("__visual_"):self.text.tag_remove(tag,*sel)
        self._refresh_visual_fonts()
    def undo(self):
        try:self.text.edit_undo(); self._refresh_visual_fonts()
        except tk.TclError:pass
    def redo(self):
        try:self.text.edit_redo(); self._refresh_visual_fonts()
        except tk.TclError:pass
    def get_value(self):return self.text.get("1.0","end-1c").strip()
    def serialize(self):
        result={"version":2,"tags":[]}
        for tag in self.text.tag_names():
            if tag=="sel" or tag.startswith("__visual_"):continue
            ranges=self.text.tag_ranges(tag)
            if not ranges:continue
            item={"name":tag,"ranges":[]}
            if tag.startswith(("color_","highlight_")):item["color"]="#"+tag.split("_",1)[1]
            for i in range(0,len(ranges),2):item["ranges"].append([str(ranges[i]),str(ranges[i+1])])
            result["tags"].append(item)
        return result if result["tags"] else {}
    def apply_formatting(self,formatting):
        for item in (formatting or {}).get("tags",[]):
            tag=item.get("name",""); color=item.get("color")
            if not tag:continue
            if tag.startswith("color_"):self.text.tag_configure(tag,foreground=color or "#"+tag.split("_",1)[1])
            elif tag.startswith("highlight_"):self.text.tag_configure(tag,background=color or "#"+tag.split("_",1)[1])
            elif tag.startswith(("fontfamily_","fontsize_")):self.text.tag_configure(tag)
            for start,end in item.get("ranges",[]):
                try:self.text.tag_add(tag,start,end)
                except tk.TclError:pass
        self._refresh_visual_fonts()
