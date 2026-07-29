# -*- coding: utf-8 -*-
from .common import *

class PhotoGallery(tk.Toplevel):
    def __init__(self, master, db, paths, disease_id, start_attachment_id=None):
        tk.Toplevel.__init__(self, master)
        self.db = db
        self.paths = paths
        self.disease_id = disease_id
        self.photos = list(db.image_attachments(disease_id))
        self.index = 0
        self.zoom = 1.0
        self.rotation = 0
        self.original_image = None
        self.tk_image = None

        self.title("Fotoğraf galerisi")
        self.geometry("1000x720")
        self.minsize(700, 500)
        self.transient(master)

        if start_attachment_id is not None:
            for idx, row in enumerate(self.photos):
                if int(row["id"]) == int(start_attachment_id):
                    self.index = idx
                    break

        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="◀ Önceki", command=self.previous).pack(side="left")
        ttk.Button(toolbar, text="Sonraki ▶", command=self.next).pack(side="left", padx=4)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Küçült", command=self.zoom_out).pack(side="left")
        ttk.Button(toolbar, text="Büyüt", command=self.zoom_in).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Sığdır", command=self.fit).pack(side="left")
        ttk.Button(toolbar, text="Döndür", command=self.rotate).pack(side="left", padx=4)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Ana fotoğraf yap", command=self.make_primary).pack(side="left")
        ttk.Button(toolbar, text="Açıklamayı düzenle", command=self.edit_description).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Dışarıda aç", command=self.open_external).pack(side="right")

        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.render())

        self.info_var = tk.StringVar()
        ttk.Label(self, textvariable=self.info_var, anchor="center", padding=8).pack(fill="x")

        self.bind("<Left>", lambda _e: self.previous())
        self.bind("<Right>", lambda _e: self.next())
        self.bind("<plus>", lambda _e: self.zoom_in())
        self.bind("<minus>", lambda _e: self.zoom_out())
        self.bind("<Escape>", lambda _e: self.destroy())

        if not self.photos:
            messagebox.showinfo(APP_NAME, "Bu kayıtta fotoğraf yok.", parent=master)
            self.destroy()
            return
        self.load_current()

    def current_row(self):
        return self.photos[self.index] if self.photos else None

    def current_path(self):
        row = self.current_row()
        return os.path.join(self.paths.base, row["relative_path"]) if row else ""

    def load_current(self):
        path = self.current_path()
        if not os.path.exists(path):
            self.original_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                max(10, self.canvas.winfo_width() // 2),
                max(10, self.canvas.winfo_height() // 2),
                text="Dosya bulunamadı:\n{}".format(path),
                fill="white",
                justify="center",
            )
            return
        if not PIL_AVAILABLE:
            messagebox.showerror(
                APP_NAME,
                "Galeri için Pillow bileşeni gerekli.\nDerleme dosyasına 'pip install pillow' eklenmelidir.",
                parent=self,
            )
            self.destroy()
            return
        try:
            self.original_image = Image.open(path).convert("RGB")
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)
            return
        self.zoom = 1.0
        self.rotation = 0
        self.fit()

    def render(self):
        if self.original_image is None or not PIL_AVAILABLE:
            return
        image = self.original_image.rotate(self.rotation, expand=True)
        width = max(1, int(image.width * self.zoom))
        height = max(1, int(image.height * self.zoom))
        image = image.resize((width, height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self.tk_image,
            anchor="center",
        )
        row = self.current_row()
        primary = " · ANA FOTOĞRAF" if row["is_primary"] else ""
        self.info_var.set(
            "{} / {} · {} · Yakınlaştırma: %{}{} · {}".format(
                self.index + 1,
                len(self.photos),
                os.path.basename(row["relative_path"]).split("_", 1)[-1],
                int(self.zoom * 100),
                primary,
                row["description"] or "Açıklama yok",
            )
        )

    def fit(self):
        if self.original_image is None:
            return
        canvas_w = max(300, self.canvas.winfo_width() - 30)
        canvas_h = max(250, self.canvas.winfo_height() - 30)
        image = self.original_image.rotate(self.rotation, expand=True)
        self.zoom = min(float(canvas_w) / image.width, float(canvas_h) / image.height, 1.0)
        self.render()

    def zoom_in(self):
        self.zoom = min(4.0, self.zoom * 1.25)
        self.render()

    def zoom_out(self):
        self.zoom = max(0.1, self.zoom / 1.25)
        self.render()

    def rotate(self):
        self.rotation = (self.rotation - 90) % 360
        self.fit()

    def previous(self):
        if self.photos:
            self.index = (self.index - 1) % len(self.photos)
            self.load_current()

    def next(self):
        if self.photos:
            self.index = (self.index + 1) % len(self.photos)
            self.load_current()

    def make_primary(self):
        row = self.current_row()
        if not row:
            return
        self.db.set_primary_attachment(self.disease_id, row["id"])
        self.photos = list(self.db.image_attachments(self.disease_id))
        for idx, item in enumerate(self.photos):
            if item["id"] == row["id"]:
                self.index = idx
                break
        self.master.refresh_attachments()
        self.render()

    def edit_description(self):
        row = self.current_row()
        if not row:
            return
        value = simpledialog.askstring(
            APP_NAME,
            "Fotoğraf açıklaması:",
            initialvalue=row["description"] or "",
            parent=self,
        )
        if value is None:
            return
        self.db.update_attachment_description(row["id"], value)
        self.photos = list(self.db.image_attachments(self.disease_id))
        for idx, item in enumerate(self.photos):
            if item["id"] == row["id"]:
                self.index = idx
                break
        self.master.refresh_attachments()
        self.render()

    def open_external(self):
        path = self.current_path()
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)


