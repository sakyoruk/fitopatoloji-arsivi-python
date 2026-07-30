# -*- coding: utf-8 -*-
from .common import *

class RichTextEditor(ttk.Frame):
    """Bilimsel metinler için genişletilmiş Tk tabanlı zengin metin editörü."""
    SYMBOLS = ["α", "β", "γ", "δ", "Δ", "µ", "°", "±", "≤", "≥", "×", "→", "♀", "♂"]

    def __init__(self, master, value="", formatting=None, height=6):
        ttk.Frame.__init__(self, master)
        self.color_tags = {}
        toolbar = ttk.Frame(self); toolbar.pack(fill="x", pady=(0,3))
        for text, cmd, width in [
            ("B", lambda:self.toggle_tag("bold"),3), ("I", lambda:self.toggle_tag("italic"),3),
            ("U", lambda:self.toggle_tag("underline"),3), ("x²", lambda:self.toggle_tag("superscript"),4),
            ("x₂", lambda:self.toggle_tag("subscript"),4), ("• Liste", self.bullet_list,7),
            ("1. Liste", self.numbered_list,7), ("Tablo", self.insert_table,6), ("Sembol", self.symbol_menu,7),
        ]:
            ttk.Button(toolbar,text=text,width=width,command=cmd).pack(side="left",padx=(0,2))
        ttk.Button(toolbar,text="Renk",command=self.choose_color).pack(side="left",padx=(4,2))
        ttk.Button(toolbar,text="Vurgu",command=self.choose_highlight).pack(side="left",padx=2)
        ttk.Button(toolbar,text="Sol",width=4,command=lambda:self.align("left")).pack(side="left",padx=(5,1))
        ttk.Button(toolbar,text="Orta",width=5,command=lambda:self.align("center")).pack(side="left",padx=1)
        ttk.Button(toolbar,text="Sağ",width=4,command=lambda:self.align("right")).pack(side="left",padx=1)
        ttk.Button(toolbar,text="Temizle",command=self.clear_formatting).pack(side="right")

        body=ttk.Frame(self); body.pack(fill="both",expand=True)
        self.text=tk.Text(body,height=height,wrap="word",undo=True,font=("Segoe UI",9),tabs=(80,160,240,320))
        scroll=ttk.Scrollbar(body,orient="vertical",command=self.text.yview); self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        self._configure_builtin_tags(); self.text.insert("1.0",value or ""); self.apply_formatting(formatting or {})
        self.text.bind("<Control-b>",lambda e:(self.toggle_tag("bold"),"break")[1])
        self.text.bind("<Control-i>",lambda e:(self.toggle_tag("italic"),"break")[1])
        self.text.bind("<Control-u>",lambda e:(self.toggle_tag("underline"),"break")[1])

    def _configure_builtin_tags(self):
        self.text.tag_configure("bold",font=("Segoe UI",9,"bold")); self.text.tag_configure("italic",font=("Segoe UI",9,"italic"))
        self.text.tag_configure("underline",underline=True); self.text.tag_configure("superscript",offset=4,font=("Segoe UI",7))
        self.text.tag_configure("subscript",offset=-3,font=("Segoe UI",7)); self.text.tag_configure("align_left",justify="left")
        self.text.tag_configure("align_center",justify="center"); self.text.tag_configure("align_right",justify="right")

    def _selection(self):
        try:return self.text.index("sel.first"),self.text.index("sel.last")
        except tk.TclError:return None
    def toggle_tag(self,tag):
        sel=self._selection()
        if not sel:return
        start,end=sel
        if tag in self.text.tag_names(start):self.text.tag_remove(tag,start,end)
        else:
            if tag=="superscript":self.text.tag_remove("subscript",start,end)
            if tag=="subscript":self.text.tag_remove("superscript",start,end)
            self.text.tag_add(tag,start,end)
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
        for tag in ("align_left","align_center","align_right"):self.text.tag_remove(tag,start,end)
        self.text.tag_add("align_"+where,start,end)
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
            ttk.Button(frame,text=symbol,width=4,command=lambda s=symbol:(self.text.insert("insert",s),win.destroy())).grid(row=i//7,column=i%7,padx=2,pady=2)
    def choose_color(self):self._choose_style("foreground","color_")
    def choose_highlight(self):self._choose_style("background","highlight_")
    def _choose_style(self,option,prefix):
        sel=self._selection()
        if not sel:return
        color=colorchooser.askcolor(parent=self.winfo_toplevel())[1]
        if not color:return
        tag=prefix+color.replace("#",""); self.text.tag_configure(tag,**{option:color}); self.color_tags[tag]=color; self.text.tag_add(tag,*sel)
    def clear_formatting(self):
        sel=self._selection()
        if not sel:return
        for tag in self.text.tag_names():
            if tag!="sel":self.text.tag_remove(tag,*sel)
    def get_value(self):return self.text.get("1.0","end-1c").strip()
    def serialize(self):
        result={"tags":[]}
        for tag in self.text.tag_names():
            if tag=="sel":continue
            ranges=self.text.tag_ranges(tag)
            if not ranges:continue
            item={"name":tag,"ranges":[]}
            if tag.startswith(("color_","highlight_")):item["color"]="#"+tag.split("_",1)[1]
            for i in range(0,len(ranges),2):item["ranges"].append([str(ranges[i]),str(ranges[i+1])])
            result["tags"].append(item)
        return result if result["tags"] else {}
    def apply_formatting(self,formatting):
        for item in formatting.get("tags",[]):
            tag=item.get("name",""); color=item.get("color")
            if tag.startswith("color_"):self.text.tag_configure(tag,foreground=color or "#"+tag.split("_",1)[1])
            elif tag.startswith("highlight_"):self.text.tag_configure(tag,background=color or "#"+tag.split("_",1)[1])
            elif tag not in self.text.tag_names():self._configure_builtin_tags()
            for start,end in item.get("ranges",[]):
                try:self.text.tag_add(tag,start,end)
                except tk.TclError:pass
