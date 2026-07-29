# -*- coding: utf-8 -*-
from .common import *

class RichTextEditor(ttk.Frame):
    """Tk Text üzerinde temel biçimlendirme ve JSON olarak saklama."""

    def __init__(self, master, value="", formatting=None, height=6):
        ttk.Frame.__init__(self, master)
        self.color_tags = {}
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 3))

        ttk.Button(toolbar, text="B", width=3, command=lambda: self.toggle_tag("bold")).pack(side="left")
        ttk.Button(toolbar, text="I", width=3, command=lambda: self.toggle_tag("italic")).pack(side="left", padx=2)
        ttk.Button(toolbar, text="U", width=3, command=lambda: self.toggle_tag("underline")).pack(side="left")
        ttk.Button(toolbar, text="Renk", command=self.choose_color).pack(side="left", padx=(6, 2))
        ttk.Button(toolbar, text="Biçimi temizle", command=self.clear_formatting).pack(side="left")
        ttk.Label(toolbar, text="  Seçili metne uygulanır").pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, height=height, wrap="word", undo=True)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        normal_font = ("Segoe UI", 9)
        self.text.configure(font=normal_font)
        self.text.tag_configure("bold", font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("italic", font=("Segoe UI", 9, "italic"))
        self.text.tag_configure("underline", underline=True)
        self.text.insert("1.0", value or "")
        self.apply_formatting(formatting or {})

    def _selection(self):
        try:
            return self.text.index("sel.first"), self.text.index("sel.last")
        except tk.TclError:
            return None

    def toggle_tag(self, tag):
        selection = self._selection()
        if not selection:
            return
        start, end = selection
        if tag in self.text.tag_names(start):
            self.text.tag_remove(tag, start, end)
        else:
            self.text.tag_add(tag, start, end)

    def choose_color(self):
        selection = self._selection()
        if not selection:
            return
        color = colorchooser.askcolor(parent=self.winfo_toplevel())[1]
        if not color:
            return
        tag = "color_" + color.replace("#", "")
        if tag not in self.color_tags:
            self.text.tag_configure(tag, foreground=color)
            self.color_tags[tag] = color
        self.text.tag_add(tag, selection[0], selection[1])

    def clear_formatting(self):
        selection = self._selection()
        if not selection:
            return
        for tag in self.text.tag_names():
            if tag in ("sel",):
                continue
            self.text.tag_remove(tag, selection[0], selection[1])

    def get_value(self):
        return self.text.get("1.0", "end-1c").strip()

    def serialize(self):
        result = {"tags": []}
        for tag in self.text.tag_names():
            if tag in ("sel",):
                continue
            ranges = self.text.tag_ranges(tag)
            if not ranges:
                continue
            item = {"name": tag, "ranges": []}
            if tag.startswith("color_"):
                item["color"] = "#" + tag.split("_", 1)[1]
            for index in range(0, len(ranges), 2):
                item["ranges"].append([str(ranges[index]), str(ranges[index + 1])])
            result["tags"].append(item)
        return result if result["tags"] else {}

    def apply_formatting(self, formatting):
        for item in formatting.get("tags", []):
            tag = item.get("name", "")
            if tag.startswith("color_"):
                color = item.get("color") or ("#" + tag.split("_", 1)[1])
                self.text.tag_configure(tag, foreground=color)
                self.color_tags[tag] = color
            for start, end in item.get("ranges", []):
                try:
                    self.text.tag_add(tag, start, end)
                except tk.TclError:
                    pass


