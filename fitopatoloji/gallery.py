# -*- coding: utf-8 -*-
from .common import *


class PhotoGallery(tk.Toplevel):
    """Fotoğraf galerisi ve gelişmiş, kalıcı anotasyon editörü."""

    TOOLS = (
        ("select", "Seç / Taşı"),
        ("arrow", "Ok"),
        ("rect", "Dikdörtgen"),
        ("oval", "Daire"),
        ("pen", "Kalem"),
        ("text", "Metin"),
        ("number", "Numara"),
        ("eraser", "Silgi"),
    )

    def __init__(self, master, db, paths, disease_id, start_attachment_id=None):
        tk.Toplevel.__init__(self, master); center_toplevel(self)
        self.db = db
        self.paths = paths
        self.disease_id = disease_id
        self.photos = list(db.image_attachments(disease_id))
        self.index = 0
        self.zoom = 1.0
        self.rotation = 0
        self.original_image = None
        self.tk_image = None
        self.image_left = 0.0
        self.image_top = 0.0
        self.display_width = 1
        self.display_height = 1

        self.tool = "select"
        self.tool_var = tk.StringVar(value=self.tool)
        self.draw_color = "#ff2d2d"
        self.line_width = 4
        self.width_var = tk.StringVar(value=str(self.line_width))
        self.annotations = []
        self.undo_stack = []
        self.redo_stack = []
        self.current_annotation = None
        self.drag_start = None
        self.selected_index = None
        self.move_origin = None
        self.move_snapshot = None
        self.annotations_visible = tk.BooleanVar(value=True)
        self.dirty = False
        self._render_job = None

        self.title("Fotoğraf galerisi ve gelişmiş anotasyon")
        self.geometry("1180x780")
        self.minsize(850, 600)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)

        if start_attachment_id is not None:
            for idx, row in enumerate(self.photos):
                if int(row["id"]) == int(start_attachment_id):
                    self.index = idx
                    break

        self._build_toolbar()

        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0, cursor="arrow")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._schedule_render)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.info_var = tk.StringVar()
        ttk.Label(self, textvariable=self.info_var, anchor="center", padding=8).pack(fill="x")

        self.bind("<Left>", lambda _e: self.previous())
        self.bind("<Right>", lambda _e: self.next())
        self.bind("<plus>", lambda _e: self.zoom_in())
        self.bind("<KP_Add>", lambda _e: self.zoom_in())
        self.bind("<minus>", lambda _e: self.zoom_out())
        self.bind("<KP_Subtract>", lambda _e: self.zoom_out())
        self.bind("<Control-s>", lambda _e: self.save_annotations())
        self.bind("<Control-z>", lambda _e: self.undo())
        self.bind("<Control-y>", lambda _e: self.redo())
        self.bind("<Delete>", lambda _e: self.delete_selected())
        self.bind("<Escape>", self._escape_action)

        if not self.photos:
            messagebox.showinfo(APP_NAME, "Bu kayıtta fotoğraf yok.", parent=master)
            self.destroy()
            return
        self.load_current()

    def _build_toolbar(self):
        top = ttk.Frame(self, padding=(8, 7, 8, 3))
        top.pack(fill="x")

        left = ttk.Frame(top)
        left.pack(side="left")
        ttk.Button(left, text="◀ Önceki", command=self.previous).pack(side="left")
        ttk.Button(left, text="Sonraki ▶", command=self.next).pack(side="left", padx=4)
        ttk.Separator(left, orient="vertical").pack(side="left", fill="y", padx=7)
        ttk.Button(left, text="Küçült", command=self.zoom_out).pack(side="left")
        ttk.Button(left, text="Büyüt", command=self.zoom_in).pack(side="left", padx=4)
        ttk.Button(left, text="Sığdır", command=self.fit).pack(side="left")
        ttk.Button(left, text="Döndür", command=self.rotate).pack(side="left", padx=4)

        right = ttk.Frame(top)
        right.pack(side="right")
        ttk.Button(right, text="Ana fotoğraf yap", command=self.make_primary).pack(side="left")
        ttk.Button(right, text="Açıklama", command=self.edit_description).pack(side="left", padx=4)
        ttk.Button(right, text="Dışarıda aç", command=self.open_external).pack(side="left")

        tools_row = ttk.Frame(self, padding=(8, 3, 8, 7))
        tools_row.pack(fill="x")
        tools = ttk.Frame(tools_row)
        tools.pack(anchor="center")

        for value, label in self.TOOLS:
            ttk.Radiobutton(
                tools,
                text=label,
                value=value,
                variable=self.tool_var,
                command=self.change_tool,
            ).pack(side="left", padx=2)

        ttk.Separator(tools, orient="vertical").pack(side="left", fill="y", padx=7)
        self.color_button = ttk.Button(tools, text="Renk ■", command=self.choose_color)
        self.color_button.pack(side="left", padx=2)
        ttk.Label(tools, text="Kalınlık:").pack(side="left", padx=(7, 2))
        width_box = ttk.Combobox(
            tools,
            textvariable=self.width_var,
            values=("1", "2", "3", "4", "6", "8", "10", "14"),
            width=3,
            state="readonly",
        )
        width_box.pack(side="left", padx=(0, 5))
        width_box.bind("<<ComboboxSelected>>", self.change_width)
        ttk.Button(tools, text="Geri al", command=self.undo).pack(side="left", padx=2)
        ttk.Button(tools, text="Yinele", command=self.redo).pack(side="left", padx=2)
        ttk.Button(tools, text="Seçileni sil", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Button(tools, text="Tümünü sil", command=self.clear_annotations).pack(side="left", padx=2)
        ttk.Checkbutton(
            tools,
            text="İşaretleri göster",
            variable=self.annotations_visible,
            command=self.render,
        ).pack(side="left", padx=(7, 2))
        ttk.Button(tools, text="PNG dışa aktar", command=self.export_annotated_image).pack(side="left", padx=2)
        ttk.Button(tools, text="Kaydet", command=self.save_annotations).pack(side="left", padx=(7, 2))

    def current_row(self):
        return self.photos[self.index] if self.photos else None

    def current_path(self):
        row = self.current_row()
        return os.path.join(self.paths.base, row["relative_path"]) if row else ""

    def current_attachment_id(self):
        row = self.current_row()
        return int(row["id"]) if row else None

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
            with Image.open(path) as source:
                self.original_image = source.convert("RGB")
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)
            return

        self.zoom = 1.0
        self.rotation = 0
        self.annotations = self.db.attachment_annotations(self.current_attachment_id())
        self.undo_stack = []
        self.redo_stack = []
        self.current_annotation = None
        self.drag_start = None
        self.selected_index = None
        self.move_origin = None
        self.move_snapshot = None
        self.dirty = False
        self.fit()

    def _schedule_render(self, _event=None):
        if self._render_job is not None:
            try:
                self.after_cancel(self._render_job)
            except Exception:
                pass
        self._render_job = self.after(40, self.render)

    def render(self):
        self._render_job = None
        if self.original_image is None or not PIL_AVAILABLE:
            return

        image = self.original_image.rotate(self.rotation, expand=True)
        width = max(1, int(image.width * self.zoom))
        height = max(1, int(image.height * self.zoom))
        resampling = getattr(Image, "Resampling", Image)
        image = image.resize((width, height), resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(image)

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        self.image_left = (canvas_w - width) / 2.0
        self.image_top = (canvas_h - height) / 2.0
        self.display_width = width
        self.display_height = height

        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_w // 2,
            canvas_h // 2,
            image=self.tk_image,
            anchor="center",
            tags=("photo",),
        )
        if self.annotations_visible.get():
            self._draw_all_annotations()

        row = self.current_row()
        primary = " · ANA FOTOĞRAF" if row["is_primary"] else ""
        changed = " · KAYDEDİLMEDİ" if self.dirty else ""
        selected = " · SEÇİLİ: {}".format(self.selected_index + 1) if self.selected_index is not None else ""
        self.info_var.set(
            "{} / {} · {} · Yakınlaştırma: %{}{}{}{} · {}".format(
                self.index + 1,
                len(self.photos),
                os.path.basename(row["relative_path"]).split("_", 1)[-1],
                int(self.zoom * 100),
                primary,
                changed,
                selected,
                row["description"] or "Açıklama yok",
            )
        )

    def _draw_all_annotations(self):
        for index, annotation in enumerate(self.annotations):
            self._draw_annotation(annotation, selected=(index == self.selected_index))
        if self.current_annotation:
            self._draw_annotation(self.current_annotation, preview=True)

    def _draw_annotation(self, annotation, preview=False, selected=False):
        kind = annotation.get("type")
        points = annotation.get("points") or []
        if not points:
            return
        coords = []
        for point in points:
            x, y = self.image_to_canvas(point[0], point[1])
            coords.extend((x, y))
        color = annotation.get("color") or self.draw_color
        width = max(1, int((annotation.get("width") or self.line_width) * max(0.6, self.zoom)))
        tags = ("annotation", "preview" if preview else "saved")
        if kind == "rect" and len(coords) >= 4:
            self.canvas.create_rectangle(*coords[:4], outline=color, width=width, tags=tags)
        elif kind == "oval" and len(coords) >= 4:
            self.canvas.create_oval(*coords[:4], outline=color, width=width, tags=tags)
        elif kind == "arrow" and len(coords) >= 4:
            self.canvas.create_line(
                *coords[:4], fill=color, width=width, arrow=tk.LAST,
                arrowshape=(12, 14, 5), tags=tags
            )
        elif kind == "pen" and len(coords) >= 4:
            self.canvas.create_line(
                *coords, fill=color, width=width, smooth=True,
                splinesteps=16, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tags
            )
        elif kind == "text" and len(coords) >= 2:
            self.canvas.create_text(
                coords[0], coords[1], text=annotation.get("text", ""), fill=color,
                anchor="nw", font=("Arial", max(10, int(14 * max(0.7, self.zoom))), "bold"), tags=tags
            )
        elif kind == "number" and len(coords) >= 2:
            radius = max(10, int(14 * max(0.7, self.zoom)))
            x, y = coords[0], coords[1]
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, outline=color, width=width, tags=tags)
            self.canvas.create_text(
                x, y, text=str(annotation.get("number", 1)), fill=color,
                font=("Arial", max(9, int(12 * max(0.7, self.zoom))), "bold"), tags=tags
            )

        if selected and not preview:
            bbox = self._annotation_bbox_canvas(annotation)
            if bbox:
                pad = 5
                self.canvas.create_rectangle(
                    bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad,
                    outline="#00bfff", width=1, dash=(4, 3), tags=("selection",)
                )

    def _annotation_bbox_canvas(self, annotation):
        points = annotation.get("points") or []
        if not points:
            return None
        canvas_points = [self.image_to_canvas(p[0], p[1]) for p in points]
        xs = [p[0] for p in canvas_points]
        ys = [p[1] for p in canvas_points]
        if annotation.get("type") in ("text", "number"):
            x, y = canvas_points[0]
            if annotation.get("type") == "number":
                return x-18, y-18, x+18, y+18
            text = annotation.get("text", "")
            return x, y, x + max(35, len(text) * 9), y + 24
        return min(xs), min(ys), max(xs), max(ys)

    def change_tool(self):
        self.tool = self.tool_var.get()
        self.current_annotation = None
        self.drag_start = None
        if self.tool != "select":
            self.selected_index = None
        if self.tool in ("arrow", "rect", "oval", "pen", "text", "number", "eraser") and self.rotation != 0:
            self.rotation = 0
            self.fit()
        cursors = {
            "select": "hand2", "arrow": "crosshair", "rect": "crosshair",
            "oval": "crosshair", "pen": "pencil", "text": "xterm",
            "number": "crosshair", "eraser": "dotbox",
        }
        try:
            self.canvas.configure(cursor=cursors.get(self.tool, "arrow"))
        except tk.TclError:
            self.canvas.configure(cursor="crosshair" if self.tool != "select" else "arrow")
        self.render()

    def change_width(self, _event=None):
        try:
            self.line_width = max(1, int(self.width_var.get()))
        except (TypeError, ValueError):
            self.line_width = 4
            self.width_var.set("4")

    def choose_color(self):
        _rgb, value = colorchooser.askcolor(color=self.draw_color, parent=self, title="Anotasyon rengi")
        if value:
            self.draw_color = value
            self.color_button.configure(text="Renk {}".format(value.upper()))

    def canvas_inside_image(self, x, y):
        return (
            self.image_left <= x <= self.image_left + self.display_width
            and self.image_top <= y <= self.image_top + self.display_height
        )

    def canvas_to_image(self, x, y):
        if self.zoom <= 0:
            return 0.0, 0.0
        px = (x - self.image_left) / self.zoom
        py = (y - self.image_top) / self.zoom
        if self.original_image is not None:
            px = min(max(px, 0.0), float(self.original_image.width))
            py = min(max(py, 0.0), float(self.original_image.height))
        return px, py

    def image_to_canvas(self, x, y):
        return self.image_left + x * self.zoom, self.image_top + y * self.zoom

    def on_press(self, event):
        if self.original_image is None or not self.canvas_inside_image(event.x, event.y):
            return
        point = self.canvas_to_image(event.x, event.y)

        if self.tool == "select":
            self.selected_index = self._find_annotation_at(point, tolerance=16.0 / max(self.zoom, 0.1))
            if self.selected_index is not None:
                self.move_origin = point
                self.move_snapshot = json.loads(json.dumps(self.annotations[self.selected_index], ensure_ascii=False))
            else:
                self.move_origin = None
                self.move_snapshot = None
            self.render()
            return

        if self.tool == "eraser":
            self.erase_at(point)
            return

        if self.tool == "text":
            value = simpledialog.askstring(APP_NAME, "Fotoğraf üzerine eklenecek metin:", parent=self)
            if value:
                self._push_undo()
                self.annotations.append({
                    "type": "text", "color": self.draw_color, "width": self.line_width,
                    "points": [list(point)], "text": value,
                })
                self.selected_index = len(self.annotations) - 1
                self.dirty = True
                self.render()
            return

        if self.tool == "number":
            used = [int(a.get("number", 0)) for a in self.annotations if a.get("type") == "number"]
            next_number = max(used or [0]) + 1
            self._push_undo()
            self.annotations.append({
                "type": "number", "color": self.draw_color, "width": self.line_width,
                "points": [list(point)], "number": next_number,
            })
            self.selected_index = len(self.annotations) - 1
            self.dirty = True
            self.render()
            return

        self.drag_start = point
        self.current_annotation = {
            "type": self.tool,
            "color": self.draw_color,
            "width": self.line_width,
            "points": [list(point), list(point)],
        }
        self.render()

    def on_drag(self, event):
        if self.tool == "select" and self.selected_index is not None and self.move_origin and self.move_snapshot:
            x = min(max(event.x, self.image_left), self.image_left + self.display_width)
            y = min(max(event.y, self.image_top), self.image_top + self.display_height)
            point = self.canvas_to_image(x, y)
            dx = point[0] - self.move_origin[0]
            dy = point[1] - self.move_origin[1]
            moved = json.loads(json.dumps(self.move_snapshot, ensure_ascii=False))
            moved["points"] = [[p[0] + dx, p[1] + dy] for p in moved.get("points", [])]
            self.annotations[self.selected_index] = moved
            self.render()
            return

        if not self.current_annotation or self.drag_start is None:
            return
        x = min(max(event.x, self.image_left), self.image_left + self.display_width)
        y = min(max(event.y, self.image_top), self.image_top + self.display_height)
        point = self.canvas_to_image(x, y)
        if self.current_annotation["type"] == "pen":
            previous = self.current_annotation["points"][-1]
            if abs(previous[0] - point[0]) + abs(previous[1] - point[1]) >= max(1.0, 2.0 / max(self.zoom, 0.1)):
                self.current_annotation["points"].append(list(point))
        else:
            self.current_annotation["points"] = [list(self.drag_start), list(point)]
        self.render()

    def on_release(self, _event):
        if self.tool == "select" and self.selected_index is not None and self.move_origin and self.move_snapshot:
            before = self.move_snapshot
            after = self.annotations[self.selected_index]
            if before.get("points") != after.get("points"):
                previous_state = json.loads(json.dumps(self.annotations, ensure_ascii=False))
                previous_state[self.selected_index] = before
                self.undo_stack.append(previous_state)
                if len(self.undo_stack) > 50:
                    self.undo_stack.pop(0)
                self.redo_stack = []
                self.dirty = True
            self.move_origin = None
            self.move_snapshot = None
            self.render()
            return

        if not self.current_annotation:
            return
        points = self.current_annotation.get("points") or []
        valid = len(points) >= 2
        if valid and self.current_annotation["type"] != "pen":
            valid = abs(points[0][0] - points[-1][0]) + abs(points[0][1] - points[-1][1]) >= 3
        if valid and self.current_annotation["type"] == "pen":
            valid = len(points) >= 2
        if valid:
            self._push_undo()
            self.annotations.append(self.current_annotation)
            self.selected_index = len(self.annotations) - 1
            self.dirty = True
        self.current_annotation = None
        self.drag_start = None
        self.render()

    def _snapshot(self):
        return json.loads(json.dumps(self.annotations, ensure_ascii=False))

    def _push_undo(self):
        self.undo_stack.append(self._snapshot())
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack = []

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self._snapshot())
        self.annotations = self.undo_stack.pop()
        self.current_annotation = None
        self.drag_start = None
        self.selected_index = None
        self.dirty = True
        self.render()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self._snapshot())
        self.annotations = self.redo_stack.pop()
        self.current_annotation = None
        self.drag_start = None
        self.selected_index = None
        self.dirty = True
        self.render()

    def _find_annotation_at(self, image_point, tolerance):
        best_index = None
        best_distance = None
        for index in range(len(self.annotations) - 1, -1, -1):
            distance = self._annotation_distance(self.annotations[index], image_point)
            if distance <= tolerance and (best_distance is None or distance < best_distance):
                best_index = index
                best_distance = distance
        return best_index

    def erase_at(self, image_point):
        index = self._find_annotation_at(image_point, 16.0 / max(self.zoom, 0.1))
        if index is not None:
            self._push_undo()
            del self.annotations[index]
            self.selected_index = None
            self.dirty = True
            self.render()

    def delete_selected(self):
        if self.selected_index is None or not (0 <= self.selected_index < len(self.annotations)):
            return
        self._push_undo()
        del self.annotations[self.selected_index]
        self.selected_index = None
        self.dirty = True
        self.render()

    def _annotation_distance(self, annotation, point):
        points = annotation.get("points") or []
        if not points:
            return 1e12
        kind = annotation.get("type")
        px, py = point
        if kind in ("text", "number"):
            x, y = points[0]
            return ((px - x) ** 2 + (py - y) ** 2) ** 0.5
        if kind in ("rect", "oval") and len(points) >= 2:
            x1, y1 = points[0]
            x2, y2 = points[-1]
            left, right = sorted((x1, x2))
            top, bottom = sorted((y1, y2))
            if left <= px <= right and top <= py <= bottom:
                return min(px - left, right - px, py - top, bottom - py)
            dx = max(left - px, 0, px - right)
            dy = max(top - py, 0, py - bottom)
            return (dx * dx + dy * dy) ** 0.5
        best = 1e12
        for p1, p2 in zip(points, points[1:]):
            best = min(best, self._point_segment_distance(point, p1, p2))
        return best

    @staticmethod
    def _point_segment_distance(point, p1, p2):
        px, py = point
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)
        t = min(1.0, max(0.0, t))
        cx = x1 + t * dx
        cy = y1 + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def clear_annotations(self):
        if not self.annotations:
            return
        if not messagebox.askyesno(APP_NAME, "Bu fotoğraftaki tüm işaretlemeler silinsin mi?", parent=self):
            return
        self._push_undo()
        self.annotations = []
        self.selected_index = None
        self.dirty = True
        self.render()

    def save_annotations(self, silent=False):
        attachment_id = self.current_attachment_id()
        if attachment_id is None:
            return False
        try:
            self.db.save_attachment_annotations(attachment_id, self.annotations)
            self.dirty = False
            self.render()
            if not silent:
                messagebox.showinfo(APP_NAME, "Fotoğraf işaretlemeleri kaydedildi.", parent=self)
            return True
        except Exception as exc:
            messagebox.showerror(APP_NAME, "İşaretlemeler kaydedilemedi:\n{}".format(exc), parent=self)
            return False

    def export_annotated_image(self):
        if self.original_image is None:
            return
        default_name = os.path.splitext(os.path.basename(self.current_path()))[0] + "_anotasyonlu.png"
        target = filedialog.asksaveasfilename(
            parent=self,
            title="Anotasyonlu görseli kaydet",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG görsel", "*.png"), ("JPEG görsel", "*.jpg;*.jpeg")],
        )
        if not target:
            return
        try:
            from PIL import ImageDraw, ImageFont
            image = self.original_image.copy().convert("RGB")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("arial.ttf", 18)
                font_bold = ImageFont.truetype("arialbd.ttf", 18)
            except Exception:
                font = ImageFont.load_default()
                font_bold = font
            for annotation in self.annotations:
                self._draw_annotation_on_image(draw, annotation, font, font_bold)
            image.save(target)
            messagebox.showinfo(APP_NAME, "Anotasyonlu görsel kaydedildi:\n{}".format(target), parent=self)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Görsel dışa aktarılamadı:\n{}".format(exc), parent=self)

    def _draw_annotation_on_image(self, draw, annotation, font, font_bold):
        kind = annotation.get("type")
        points = annotation.get("points") or []
        if not points:
            return
        color = annotation.get("color") or self.draw_color
        width = max(1, int(annotation.get("width") or self.line_width))
        xy = [tuple(p) for p in points]
        if kind == "rect" and len(xy) >= 2:
            draw.rectangle([xy[0], xy[-1]], outline=color, width=width)
        elif kind == "oval" and len(xy) >= 2:
            draw.ellipse([xy[0], xy[-1]], outline=color, width=width)
        elif kind == "pen" and len(xy) >= 2:
            draw.line(xy, fill=color, width=width, joint="curve")
        elif kind == "arrow" and len(xy) >= 2:
            import math
            start, end = xy[0], xy[-1]
            draw.line([start, end], fill=color, width=width)
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            size = max(12, width * 4)
            p1 = (end[0] - size * math.cos(angle - 0.5), end[1] - size * math.sin(angle - 0.5))
            p2 = (end[0] - size * math.cos(angle + 0.5), end[1] - size * math.sin(angle + 0.5))
            draw.polygon([end, p1, p2], fill=color)
        elif kind == "text":
            draw.text(xy[0], annotation.get("text", ""), fill=color, font=font_bold)
        elif kind == "number":
            x, y = xy[0]
            radius = 16
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], outline=color, width=width)
            value = str(annotation.get("number", 1))
            try:
                box = draw.textbbox((0, 0), value, font=font_bold)
                tw, th = box[2] - box[0], box[3] - box[1]
            except Exception:
                tw, th = draw.textsize(value, font=font_bold)
            draw.text((x - tw/2.0, y - th/2.0), value, fill=color, font=font_bold)

    def _confirm_save_changes(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            APP_NAME,
            "Bu fotoğraftaki işaretlemeler kaydedilmedi.\n\nKaydetmek ister misiniz?",
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            return self.save_annotations(silent=True)
        return True

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
        if self.annotations:
            messagebox.showinfo(
                APP_NAME,
                "İşaretlemelerin konumu korunması için anotasyonlu fotoğraflarda döndürme görünümü kullanılmaz.",
                parent=self,
            )
            return
        self.rotation = (self.rotation - 90) % 360
        self.fit()

    def previous(self):
        if self.photos and self._confirm_save_changes():
            self.index = (self.index - 1) % len(self.photos)
            self.load_current()

    def next(self):
        if self.photos and self._confirm_save_changes():
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
        if hasattr(self.master, "refresh_attachments"):
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
        if hasattr(self.master, "refresh_attachments"):
            self.master.refresh_attachments()
        self.render()

    def open_external(self):
        path = self.current_path()
        try:
            os.startfile(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, "Fotoğraf açılamadı:\n{}".format(exc), parent=self)

    def _escape_action(self, _event=None):
        if self.current_annotation or self.selected_index is not None:
            self.current_annotation = None
            self.drag_start = None
            self.selected_index = None
            self.render()
        else:
            self.close()

    def close(self):
        if self._confirm_save_changes():
            self.destroy()
