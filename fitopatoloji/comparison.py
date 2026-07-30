# -*- coding: utf-8 -*-
from .common import *


COMPARE_FIELDS = [
    ("group_name", "Etmen grubu"),
    ("synonyms", "Sinonimler / eski adlar"),
    ("hosts", "Konukçular"),
    ("affected_organs", "Etkilenen organlar"),
    ("symptoms", "Belirtiler"),
    ("pathogen_features", "Etmenin özellikleri"),
    ("disease_cycle", "Hastalık döngüsü"),
    ("epidemiology", "Epidemiyoloji / çevre koşulları"),
    ("differential_diagnosis", "Ayırıcı teşhis"),
    ("cultural_control", "Kültürel mücadele"),
    ("biological_control", "Biyolojik mücadele"),
    ("chemical_control", "Kimyasal mücadele / prensipler"),
]


def _terms(value):
    result = set()
    for part in re.split(r"[,;\n/|]+", value or ""):
        term = " ".join(part.strip().lower().split())
        if len(term) >= 2:
            result.add(term)
    return result


def similarity_score(left, right):
    """Return a transparent, deterministic similarity score from archive data."""
    weights = (("hosts", 35), ("affected_organs", 25), ("symptoms", 40))
    score = 0.0
    details = []
    for field, weight in weights:
        a = _terms(left[field])
        b = _terms(right[field])
        if not a or not b:
            continue
        overlap = a & b
        union = a | b
        ratio = float(len(overlap)) / float(len(union)) if union else 0.0
        score += ratio * weight
        if overlap:
            details.append("{}: {}".format(dict(COMPARE_FIELDS).get(field, field), ", ".join(sorted(overlap))))
    if (left["group_name"] or "").strip().lower() == (right["group_name"] or "").strip().lower() and left["group_name"]:
        score += 5.0
        details.append("aynı etmen grubu")
    return min(100, int(round(score))), details


class DiseaseComparison(tk.Toplevel):
    def __init__(self, master, db, initial_id=None):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.db = db
        self.records = []
        self.selected_records = []
        self.search_var = tk.StringVar()
        self.group_var = tk.StringVar(value="TÜMÜ")
        self.status_var = tk.StringVar(value="Karşılaştırmak için 2–4 kayıt seçin.")

        self.title("Ayırıcı tanı ve hastalık karşılaştırması")
        self.geometry("1180x760")
        self.minsize(900, 600)
        self.transient(master)

        self._build_ui()
        self._load_groups()
        self._refresh_candidates()
        if initial_id:
            self._select_initial(initial_id)

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Ara:").pack(side="left")
        search = ttk.Entry(top, textvariable=self.search_var, width=28)
        search.pack(side="left", padx=(4, 10))
        ttk.Label(top, text="Grup:").pack(side="left")
        self.group_combo = ttk.Combobox(top, textvariable=self.group_var, state="readonly", width=24)
        self.group_combo.pack(side="left", padx=(4, 10))
        ttk.Button(top, text="Karşılaştır", command=self.compare_selected).pack(side="left")
        ttk.Button(top, text="Benzerleri bul", command=self.find_similar).pack(side="left", padx=4)
        ttk.Button(top, text="PDF karşılaştırma", command=self.export_comparison_pdf).pack(side="left")
        ttk.Button(top, text="Kapat", command=self.destroy).pack(side="right")
        search.bind("<KeyRelease>", lambda _e: self.after_idle(self._refresh_candidates))
        self.group_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_candidates())

        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        chooser = ttk.LabelFrame(pane, text="Hastalık kayıtları", padding=6)
        result = ttk.LabelFrame(pane, text="Karşılaştırma", padding=6)
        pane.add(chooser, weight=2)
        pane.add(result, weight=5)

        ttk.Label(chooser, text="Ctrl tuşuyla 2–4 kayıt seçebilirsiniz.", wraplength=280).pack(anchor="w", pady=(0, 5))
        list_frame = ttk.Frame(chooser)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, selectmode="extended", exportselection=False, font=("Segoe UI", 9))
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<Double-1>", lambda _e: self.compare_selected())

        self.result_canvas = tk.Canvas(result, highlightthickness=0, background="#ffffff")
        yscroll = ttk.Scrollbar(result, orient="vertical", command=self.result_canvas.yview)
        xscroll = ttk.Scrollbar(result, orient="horizontal", command=self.result_canvas.xview)
        self.result_canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.result_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        result.rowconfigure(0, weight=1)
        result.columnconfigure(0, weight=1)

        self.result_inner = ttk.Frame(self.result_canvas, padding=6)
        self.result_window = self.result_canvas.create_window((0, 0), window=self.result_inner, anchor="nw")
        self.result_inner.bind("<Configure>", self._update_scrollregion)
        self.result_canvas.bind("<Configure>", self._resize_result_window)

        ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken", padding=(6, 3)).pack(fill="x", side="bottom")

    def _update_scrollregion(self, _event=None):
        self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all"))

    def _resize_result_window(self, event):
        required = max(event.width, 660)
        self.result_canvas.itemconfigure(self.result_window, width=required)

    def _load_groups(self):
        self.group_combo["values"] = ["TÜMÜ"] + self.db.list_groups()

    def _refresh_candidates(self):
        selected_ids = set()
        for idx in self.listbox.curselection():
            if idx < len(self.records):
                selected_ids.add(int(self.records[idx]["id"]))
        self.records = list(self.db.search(
            query=self.search_var.get(),
            group_name=self.group_var.get(),
        ))
        self.listbox.delete(0, "end")
        for idx, row in enumerate(self.records):
            marker = "★ " if row["favorite"] else ""
            self.listbox.insert("end", "{}{} — {}".format(marker, row["scientific_name"], row["disease_name"]))
            if int(row["id"]) in selected_ids:
                self.listbox.selection_set(idx)
        self.status_var.set("{} kayıt listelendi. Karşılaştırmak için 2–4 kayıt seçin.".format(len(self.records)))

    def _select_initial(self, disease_id):
        for idx, row in enumerate(self.records):
            if int(row["id"]) == int(disease_id):
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                break

    def _selected_full_records(self):
        indices = list(self.listbox.curselection())
        if len(indices) < 2:
            messagebox.showinfo(APP_NAME, "Karşılaştırmak için en az iki kayıt seçin.", parent=self)
            return []
        if len(indices) > 4:
            messagebox.showinfo(APP_NAME, "Okunabilirlik için en fazla dört kayıt seçebilirsiniz.", parent=self)
            return []
        return [self.db.get(self.records[idx]["id"]) for idx in indices]

    def _clear_result(self):
        for child in self.result_inner.winfo_children():
            child.destroy()

    def compare_selected(self):
        records = self._selected_full_records()
        if not records:
            return
        self.selected_records = records
        self._render_comparison(records)

    def _render_comparison(self, records):
        self._clear_result()
        column_count = len(records) + 1
        for col in range(column_count):
            self.result_inner.columnconfigure(col, weight=1 if col else 0, minsize=180 if col == 0 else 250)

        ttk.Label(self.result_inner, text="Özellik", font=("Segoe UI", 10, "bold"), relief="solid", padding=7).grid(row=0, column=0, sticky="nsew")
        for col, record in enumerate(records, 1):
            title = "{}\n{}".format(record["scientific_name"], record["disease_name"])
            ttk.Label(self.result_inner, text=title, font=("Segoe UI", 10, "bold"), justify="center", relief="solid", padding=7).grid(row=0, column=col, sticky="nsew")

        row_no = 1
        for field, label in COMPARE_FIELDS:
            ttk.Label(self.result_inner, text=label, font=("Segoe UI", 9, "bold"), wraplength=170, justify="left", relief="solid", padding=6).grid(row=row_no, column=0, sticky="nsew")
            for col, record in enumerate(records, 1):
                value = (record[field] or "").strip() or "—"
                text = tk.Text(self.result_inner, width=30, height=self._text_height(value), wrap="word", relief="solid", borderwidth=1, background="#ffffff")
                text.insert("1.0", value)
                text.configure(state="disabled")
                text.grid(row=row_no, column=col, sticky="nsew")
            row_no += 1

        if len(records) == 2:
            score, details = similarity_score(records[0], records[1])
            explanation = "; ".join(details) if details else "Ortak yapılandırılmış terim bulunamadı."
            ttk.Label(self.result_inner, text="Arşiv verisine göre benzerlik", font=("Segoe UI", 9, "bold"), relief="solid", padding=6).grid(row=row_no, column=0, sticky="nsew")
            ttk.Label(self.result_inner, text="%{}\n{}".format(score, explanation), wraplength=520, justify="left", relief="solid", padding=7).grid(row=row_no, column=1, columnspan=2, sticky="nsew")

        self.status_var.set("{} hastalık karşılaştırılıyor. Sonuç yalnızca arşivde girilmiş bilgilere dayanır.".format(len(records)))
        self.result_canvas.yview_moveto(0)
        self.result_canvas.xview_moveto(0)

    @staticmethod
    def _text_height(value):
        lines = max(2, min(9, (len(value) // 42) + value.count("\n") + 1))
        return lines

    def find_similar(self):
        indices = list(self.listbox.curselection())
        if len(indices) != 1:
            messagebox.showinfo(APP_NAME, "Benzer hastalıkları bulmak için tek bir kayıt seçin.", parent=self)
            return
        base = self.db.get(self.records[indices[0]]["id"])
        candidates = []
        for compact in self.db.search():
            if int(compact["id"]) == int(base["id"]):
                continue
            row = self.db.get(compact["id"])
            score, details = similarity_score(base, row)
            if score > 0:
                candidates.append((score, row, details))
        candidates.sort(key=lambda item: (-item[0], (item[1]["scientific_name"] or "").lower()))
        self._render_similar(base, candidates[:30])

    def _render_similar(self, base, candidates):
        self._clear_result()
        ttk.Label(self.result_inner, text="{} — {} için benzer kayıtlar".format(base["scientific_name"], base["disease_name"]), font=("Segoe UI", 11, "bold"), padding=6).grid(row=0, column=0, columnspan=4, sticky="w")
        headers = ("Benzerlik", "Etmen", "Hastalık", "Ortak noktalar")
        widths = (10, 28, 28, 60)
        for col, header in enumerate(headers):
            ttk.Label(self.result_inner, text=header, font=("Segoe UI", 9, "bold"), relief="solid", padding=5).grid(row=1, column=col, sticky="nsew")
            self.result_inner.columnconfigure(col, minsize=widths[col] * 7, weight=1 if col == 3 else 0)
        if not candidates:
            ttk.Label(self.result_inner, text="Arşivde girilmiş konukçu, organ ve belirti bilgilerine göre benzer kayıt bulunamadı.", padding=8).grid(row=2, column=0, columnspan=4, sticky="w")
        for row_no, (score, record, details) in enumerate(candidates, 2):
            values = ("%{}".format(score), record["scientific_name"], record["disease_name"], "; ".join(details) or "—")
            for col, value in enumerate(values):
                ttk.Label(self.result_inner, text=value, wraplength=420 if col == 3 else 220, justify="left", relief="solid", padding=5).grid(row=row_no, column=col, sticky="nsew")
        self.status_var.set("Benzerlik puanı yalnızca girilmiş konukçu, organ ve belirti terimlerinden hesaplandı.")
        self.result_canvas.yview_moveto(0)

    def export_comparison_pdf(self):
        if not self.selected_records:
            records = self._selected_full_records()
            if not records:
                return
            self.selected_records = records
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror(APP_NAME, "PDF için ReportLab bileşeni bulunamadı.", parent=self)
            return
        output = filedialog.asksaveasfilename(
            title="Karşılaştırma raporunu kaydet",
            defaultextension=".pdf",
            initialfile="Hastalik_Karsilastirma.pdf",
            filetypes=[("PDF dosyası", "*.pdf")],
            parent=self,
        )
        if not output:
            return
        try:
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("CmpTitle", parent=styles["Title"], fontSize=16, leading=20, alignment=TA_CENTER)
            body_style = ParagraphStyle("CmpBody", parent=styles["BodyText"], fontSize=7.5, leading=10)
            heading_style = ParagraphStyle("CmpHead", parent=body_style, fontSize=8, leading=10)
            doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=1.1 * cm, rightMargin=1.1 * cm, topMargin=1.1 * cm, bottomMargin=1.1 * cm, title="Hastalık karşılaştırması", author=APP_NAME)
            story = [Paragraph("Hastalık Karşılaştırma Raporu", title_style), Spacer(1, 0.3 * cm)]
            header = [Paragraph("Özellik", heading_style)]
            for record in self.selected_records:
                header.append(Paragraph(xml_escape(record["scientific_name"] or "") + "<br/>" + xml_escape(record["disease_name"] or ""), heading_style))
            data = [header]
            for field, label in COMPARE_FIELDS:
                row = [Paragraph(xml_escape(label), heading_style)]
                for record in self.selected_records:
                    value = xml_escape((record[field] or "").strip() or "—").replace("\n", "<br/>")
                    row.append(Paragraph(value, body_style))
                data.append(row)
            available = 18.8 * cm
            first_width = 3.4 * cm
            other_width = (available - first_width) / len(self.selected_records)
            table = Table(data, colWidths=[first_width] + [other_width] * len(self.selected_records), repeatRows=1)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.25 * cm))
            story.append(Paragraph("Not: Bu karşılaştırma yalnızca arşive girilmiş verilere dayanır; tanı yerine geçmez.", body_style))
            doc.build(story)
            messagebox.showinfo(APP_NAME, "PDF karşılaştırma raporu oluşturuldu:\n{}".format(output), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "PDF oluşturulamadı:\n{}".format(exc), parent=self)
