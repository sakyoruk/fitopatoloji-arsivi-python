# -*- coding: utf-8 -*-
"""Fotoğraf galerisi ve temel anotasyon araçları.

Anotasyonlar, her fotoğrafın yanında ``<dosya>.annotations.json`` adıyla
saklanır. Böylece veritabanı şemasında değişiklik yapmadan kullanılabilir.
"""

import json
import os

from .common import *


class PhotoGallery(tk.Toplevel):
    ANNOTATION_VERSION = 1
    DEFAULT_COLOR = "#ff2d2d"

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

        # Anotasyon durumu
        self.tool = "none"
        self.annotation_color = self.DEFAULT_COLOR
        self.pen_width = 3
        self.annotations = []
        self.undo_stack = []
        self.dirty = False
        self.drag_start = None
        self.drag_points = []
        self.preview_item = None
        self.image_item = None
        self.image_box = None  # (left, top, right, bottom)
        self.rendered_image_size = (1, 1)

        self.title("Fotoğraf galerisi")
        self.geometry("1180x780")
        self.minsize(800, 560)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)

        if start_attachment_id is not None:
            for idx, row in enumerate(self.photos):
                if int(row["id"]) == int(start_attachment_id):
                    self.index = idx
                    break

        self._build_toolbar()

        self.canvas = tk.Canvas(
            self,
            background="#202020",
            highlightthickness=0,
            cursor="arrow",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.render())
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

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
        self.bind("<Delete>", lambda _e: self.erase_selected_or_nearest())
        self.bind("<Escape>", self.on_escape)

        if not self.photos:
            messagebox.showinfo(APP_NAME, "Bu kayıtta fotoğraf yok.", parent=master)
            self.destroy()
            return
        self.load_current()

    # ------------------------------------------------------------------ UI
    def _build_toolbar(self):
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

        self.tool_var = tk.StringVar(value="none")
        tools = [
            ("Gezin", "none"),
            ("Ok", "arrow"),
            ("Dikdörtgen", "rect"),
            ("Daire", "oval"),
            ("Kalem", "pen"),
            ("Silgi", "eraser"),
        ]
        for text, value in tools:
            ttk.Radiobutton(
                toolbar,
                text=text,
                value=value,
                variable=self.tool_var,
                command=lambda v=value: self.set_tool(v),
            ).pack(side="left", padx=1)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Geri al", command=self.undo).pack(side="left")
        ttk.Button(toolbar, text="Tümünü sil", command=self.clear_annotations).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Kaydet", command=self.save_annotations).pack(side="left")

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(toolbar, text="Ana fotoğraf yap", command=self.make_primary).pack(side="left")
        ttk.Button(toolbar, text="Açıklama", command=self.edit_description).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Dışarıda aç", command=self.open_external).pack(side="right")

    # ------------------------------------------------------------- Fotoğraf
    def current_row(self):
        return self.photos[self.index] if self.photos else None

    def current_path(self):
        row = self.current_row()
        return os.path.join(self.paths.base, row["relative_path"]) if row else ""

    def annotation_path(self):
        path = self.current_path()
        return path + ".annotations.json" if path else ""

    def load_current(self):
        path = self.current_path()
        if not os.path.exists(path):
            self.original_image = None
            self.annotations = []
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
        self.annotations = []
        self.undo_stack = []
        self.dirty = False
        self.load_annotations()
        self.fit()

    def render(self):
        if self.original_image is None or not PIL_AVAILABLE:
            return

        image = self.original_image.rotate(self.rotation, expand=True)
        width = max(1, int(image.width * self.zoom))
        height = max(1, int(image.height * self.zoom))
        image = image.resize((width, height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(image)

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        center_x = canvas_w // 2
        center_y = canvas_h // 2
        left = center_x - width / 2.0
        top = center_y - height / 2.0
        self.image_box = (left, top, left + width, top + height)
        self.rendered_image_size = (width, height)

        self.canvas.delete("all")
        self.image_item = self.canvas.create_image(
            center_x,
            center_y,
            image=self.tk_image,
            anchor="center",
            tags=("photo",),
        )
        self.draw_annotations()
        self.update_info()

    def update_info(self):
        row = self.current_row()
        if not row:
            self.info_var.set("")
            return
        primary = " · ANA FOTOĞRAF" if row["is_primary"] else ""
        changed = " · KAYDEDİLMEDİ" if self.dirty else ""
        count = len([a for a in self.annotations if int(a.get("rotation", 0)) == self.rotation])
        self.info_var.set(
            "{} / {} · {} · Yakınlaştırma: %{} · İşaret: {}{}{} · {}".format(
                self.index + 1,
                len(self.photos),
                os.path.basename(row["relative_path"]).split("_", 1)[-1],
                int(self.zoom * 100),
                count,
                primary,
                changed,
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
        if self.original_image is None:
            return
        self.zoom = min(4.0, self.zoom * 1.25)
        self.render()

    def zoom_out(self):
        if self.original_image is None:
            return
        self.zoom = max(0.1, self.zoom / 1.25)
        self.render()

    def rotate(self):
        if self.original_image is None:
            return
        self.cancel_preview()
        self.rotation = (self.rotation - 90) % 360
        self.fit()

    def previous(self):
        if not self.photos:
            return
        if not self.confirm_save_if_dirty():
            return
        self.index = (self.index - 1) % len(self.photos)
        self.load_current()

    def next(self):
        if not self.photos:
            return
        if not self.confirm_save_if_dirty():
            return
        self.index = (self.index + 1) % len(self.photos)
        self.load_current()

    # ------------------------------------------------------------- Araçlar
    def set_tool(self, tool):
        self.tool = tool
        cursors = {
            "none": "arrow",
            "arrow": "crosshair",
            "rect": "crosshair",
            "oval": "crosshair",
            "pen": "pencil",
            "eraser": "dotbox",
        }
        try:
            self.canvas.configure(cursor=cursors.get(tool, "arrow"))
        except tk.TclError:
            self.canvas.configure(cursor="crosshair" if tool != "none" else "arrow")
        self.cancel_preview()

    def on_canvas_press(self, event):
        if self.original_image is None:
            return
        if self.tool == "none":
            return
        if self.tool == "eraser":
            self.erase_at(event.x, event.y)
            return

        point = self.canvas_to_normalized(event.x, event.y, clamp=False)
        if point is None:
            return
        self.drag_start = point
        self.drag_points = [point]
        self.cancel_preview()

    def on_canvas_drag(self, event):
        if self.drag_start is None or self.tool in ("none", "eraser"):
            return
        point = self.canvas_to_normalized(event.x, event.y, clamp=True)
        if point is None:
            return

        if self.tool == "pen":
            previous = self.drag_points[-1]
            if abs(point[0] - previous[0]) + abs(point[1] - previous[1]) > 0.001:
                self.drag_points.append(point)
        else:
            self.drag_points = [self.drag_start, point]
        self.draw_preview()

    def on_canvas_release(self, event):
        if self.drag_start is None or self.tool in ("none", "eraser"):
            return
        point = self.canvas_to_normalized(event.x, event.y, clamp=True)
        if point is None:
            self.cancel_preview()
            return

        if self.tool == "pen":
            if not self.drag_points or self.drag_points[-1] != point:
                self.drag_points.append(point)
            points = self._simplify_pen_points(self.drag_points)
        else:
            points = [self.drag_start, point]

        self.cancel_preview()
        if not self._valid_annotation(self.tool, points):
            return

        annotation = {
            "type": self.tool,
            "points": [[round(x, 6), round(y, 6)] for x, y in points],
            "color": self.annotation_color,
            "width": self.pen_width,
            "rotation": self.rotation,
        }
        self.annotations.append(annotation)
        self.undo_stack.append(("add", annotation))
        self.dirty = True
        self.render()

    def on_canvas_right_click(self, event):
        if self.tool == "eraser":
            self.erase_at(event.x, event.y)
        else:
            self.cancel_preview()

    def on_escape(self, _event=None):
        if self.preview_item is not None or self.drag_start is not None:
            self.cancel_preview()
        else:
            self.close()

    def draw_preview(self):
        self.cancel_preview_item_only()
        if not self.drag_points:
            return
        coords = self.points_to_canvas(self.drag_points)
        if not coords:
            return

        common = {
            "fill": self.annotation_color,
            "width": self.pen_width,
            "dash": (4, 2),
            "tags": ("preview",),
        }
        if self.tool == "arrow" and len(coords) >= 4:
            self.preview_item = self.canvas.create_line(*coords[:4], arrow=tk.LAST, **common)
        elif self.tool == "rect" and len(coords) >= 4:
            self.preview_item = self.canvas.create_rectangle(
                coords[0], coords[1], coords[2], coords[3],
                outline=self.annotation_color,
                width=self.pen_width,
                dash=(4, 2),
                tags=("preview",),
            )
        elif self.tool == "oval" and len(coords) >= 4:
            self.preview_item = self.canvas.create_oval(
                coords[0], coords[1], coords[2], coords[3],
                outline=self.annotation_color,
                width=self.pen_width,
                dash=(4, 2),
                tags=("preview",),
            )
        elif self.tool == "pen" and len(coords) >= 4:
            self.preview_item = self.canvas.create_line(
                *coords,
                fill=self.annotation_color,
                width=self.pen_width,
                smooth=True,
                splinesteps=12,
                tags=("preview",),
            )

    def cancel_preview_item_only(self):
        if self.preview_item is not None:
            try:
                self.canvas.delete(self.preview_item)
            except Exception:
                pass
            self.preview_item = None

    def cancel_preview(self):
        self.cancel_preview_item_only()
        self.drag_start = None
        self.drag_points = []

    # ---------------------------------------------------------- Anotasyon
    def draw_annotations(self):
        for index, annotation in enumerate(self.annotations):
            if int(annotation.get("rotation", 0)) != self.rotation:
                continue
            self.draw_annotation(annotation, index)

    def draw_annotation(self, annotation, index):
        points = annotation.get("points") or []
        coords = self.points_to_canvas(points)
        if len(coords) < 4:
            return

        kind = annotation.get("type")
        color = annotation.get("color") or self.DEFAULT_COLOR
        width = max(1, int(annotation.get("width", 3)))
        tags = ("annotation", "ann-{}".format(index))

        if kind == "arrow":
            self.canvas.create_line(
                *coords[:4], fill=color, width=width, arrow=tk.LAST,
                arrowshape=(12 + width * 2, 14 + width * 2, 5 + width),
                tags=tags,
            )
        elif kind == "rect":
            self.canvas.create_rectangle(
                coords[0], coords[1], coords[2], coords[3],
                outline=color, width=width, tags=tags,
            )
        elif kind == "oval":
            self.canvas.create_oval(
                coords[0], coords[1], coords[2], coords[3],
                outline=color, width=width, tags=tags,
            )
        elif kind == "pen":
            self.canvas.create_line(
                *coords, fill=color, width=width, smooth=True,
                splinesteps=12, capstyle=tk.ROUND, joinstyle=tk.ROUND,
                tags=tags,
            )

    def erase_at(self, canvas_x, canvas_y):
        candidates = self.canvas.find_overlapping(
            canvas_x - 8, canvas_y - 8, canvas_x + 8, canvas_y + 8
        )
        selected_index = None
        for item in reversed(candidates):
            for tag in self.canvas.gettags(item):
                if tag.startswith("ann-"):
                    try:
                        selected_index = int(tag.split("-", 1)[1])
                    except ValueError:
                        selected_index = None
                    break
            if selected_index is not None:
                break

        if selected_index is None:
            closest = self.canvas.find_closest(canvas_x, canvas_y)
            if closest:
                for tag in self.canvas.gettags(closest[0]):
                    if tag.startswith("ann-"):
                        try:
                            selected_index = int(tag.split("-", 1)[1])
                        except ValueError:
                            selected_index = None
                        break

        if selected_index is None or not (0 <= selected_index < len(self.annotations)):
            return
        annotation = self.annotations.pop(selected_index)
        self.undo_stack.append(("delete", selected_index, annotation))
        self.dirty = True
        self.render()

    def erase_selected_or_nearest(self):
        # Klavye Delete için güvenli davranış: son anotasyonu sil.
        visible = [
            i for i, item in enumerate(self.annotations)
            if int(item.get("rotation", 0)) == self.rotation
        ]
        if not visible:
            return
        index = visible[-1]
        annotation = self.annotations.pop(index)
        self.undo_stack.append(("delete", index, annotation))
        self.dirty = True
        self.render()

    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        if action[0] == "add":
            target = action[1]
            for idx in range(len(self.annotations) - 1, -1, -1):
                if self.annotations[idx] is target or self.annotations[idx] == target:
                    self.annotations.pop(idx)
                    break
        elif action[0] == "delete":
            index, annotation = action[1], action[2]
            self.annotations.insert(min(index, len(self.annotations)), annotation)
        elif action[0] == "clear":
            self.annotations = action[1]
        self.dirty = True
        self.render()

    def clear_annotations(self):
        current_rotation_items = [
            item for item in self.annotations
            if int(item.get("rotation", 0)) == self.rotation
        ]
        if not current_rotation_items:
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Bu görünümdeki tüm işaretler silinsin mi?",
            parent=self,
        ):
            return
        old_annotations = list(self.annotations)
        self.annotations = [
            item for item in self.annotations
            if int(item.get("rotation", 0)) != self.rotation
        ]
        self.undo_stack.append(("clear", old_annotations))
        self.dirty = True
        self.render()

    # -------------------------------------------------------------- Kayıt
    def load_annotations(self):
        path = self.annotation_path()
        if not path or not os.path.exists(path):
            self.annotations = []
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                items = data.get("annotations", [])
            elif isinstance(data, list):
                items = data
            else:
                items = []
            self.annotations = [item for item in items if self._annotation_is_readable(item)]
        except Exception as exc:
            self.annotations = []
            messagebox.showwarning(
                APP_NAME,
                "Fotoğraf işaretleri yüklenemedi:\n{}".format(exc),
                parent=self,
            )

    def save_annotations(self, silent=False):
        path = self.annotation_path()
        if not path:
            return False
        data = {
            "version": self.ANNOTATION_VERSION,
            "image": os.path.basename(self.current_path()),
            "annotations": self.annotations,
        }
        try:
            if self.annotations:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=2)
            elif os.path.exists(path):
                os.remove(path)
            self.dirty = False
            self.update_info()
            if not silent:
                messagebox.showinfo(APP_NAME, "Fotoğraf işaretleri kaydedildi.", parent=self)
            return True
        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                "Fotoğraf işaretleri kaydedilemedi:\n{}".format(exc),
                parent=self,
            )
            return False

    def confirm_save_if_dirty(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel(
            APP_NAME,
            "Fotoğraf işaretleri değişti. Kaydedilsin mi?",
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            return self.save_annotations(silent=True)
        return True

    # --------------------------------------------------------- Koordinatlar
    def canvas_to_normalized(self, canvas_x, canvas_y, clamp=False):
        if not self.image_box:
            return None
        left, top, right, bottom = self.image_box
        if clamp:
            canvas_x = min(max(canvas_x, left), right)
            canvas_y = min(max(canvas_y, top), bottom)
        elif not (left <= canvas_x <= right and top <= canvas_y <= bottom):
            return None
        width = max(1.0, right - left)
        height = max(1.0, bottom - top)
        return ((canvas_x - left) / width, (canvas_y - top) / height)

    def normalized_to_canvas(self, point):
        if not self.image_box:
            return None
        left, top, right, bottom = self.image_box
        x, y = point
        return (left + float(x) * (right - left), top + float(y) * (bottom - top))

    def points_to_canvas(self, points):
        coords = []
        for point in points:
            converted = self.normalized_to_canvas(point)
            if converted is None:
                continue
            coords.extend(converted)
        return coords

    @staticmethod
    def _simplify_pen_points(points):
        if len(points) <= 2:
            return points
        simplified = [points[0]]
        for point in points[1:-1]:
            previous = simplified[-1]
            if abs(point[0] - previous[0]) + abs(point[1] - previous[1]) >= 0.0025:
                simplified.append(point)
        simplified.append(points[-1])
        return simplified

    @staticmethod
    def _valid_annotation(kind, points):
        if kind == "pen":
            return len(points) >= 2
        if len(points) < 2:
            return False
        x1, y1 = points[0]
        x2, y2 = points[1]
        return abs(x2 - x1) >= 0.003 or abs(y2 - y1) >= 0.003

    @staticmethod
    def _annotation_is_readable(item):
        if not isinstance(item, dict):
            return False
        if item.get("type") not in ("arrow", "rect", "oval", "pen"):
            return False
        points = item.get("points")
        return isinstance(points, list) and len(points) >= 2

    # ----------------------------------------------------------- Eski işler
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

    def close(self):
        if not self.confirm_save_if_dirty():
            return
        self.destroy()
