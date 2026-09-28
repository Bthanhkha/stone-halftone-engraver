from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from stone_halftone import process_image


class HalftoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stone Halftone Engraver")
        self.geometry("500x420")

        self.input_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="output/stone_toolpath.nc")
        self.preview_path = tk.StringVar(value="output/stone_preview.png")
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.cell_size_mm = tk.DoubleVar(value=3.0)
        self.tool_diameter_mm = tk.DoubleVar(value=1.2)
        self.max_depth_mm = tk.DoubleVar(value=2.5)

        self.build_ui()

    def build_ui(self):
        frame = tk.Frame(self, padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Button(frame, text="Chọn ảnh", command=self.select_image).grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        tk.Entry(frame, textvariable=self.input_path, width=40).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        self.add_slider(frame, "Độ sáng", self.brightness, 0.2, 2.5, 0.1, 1, 1)
        self.add_slider(frame, "Độ tương phản", self.contrast, 0.2, 3.0, 0.1, 2, 2)
        self.add_slider(frame, "Kích thước ô điểm (mm)", self.cell_size_mm, 1.0, 10.0, 0.5, 3, 3)
        self.add_slider(frame, "Đường kính đầu gõ (mm)", self.tool_diameter_mm, 0.5, 4.0, 0.1, 4, 4)
        self.add_slider(frame, "Độ sâu tối đa (mm)", self.max_depth_mm, 0.5, 6.0, 0.1, 5, 5)

        tk.Label(frame, text="File G-code").grid(row=6, column=0, sticky="w", pady=(6, 0))
        tk.Entry(frame, textvariable=self.output_path).grid(row=6, column=1, sticky="ew")

        tk.Label(frame, text="Preview").grid(row=7, column=0, sticky="w", pady=(6, 0))
        tk.Entry(frame, textvariable=self.preview_path).grid(row=7, column=1, sticky="ew")

        tk.Button(frame, text="Tạo G-code", command=self.generate, bg="#4CAF50", fg="white", height=2).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        frame.columnconfigure(1, weight=1)

    def add_slider(self, parent, label, variable, from_, to, resolution, row, col):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        tk.Scale(
            parent,
            variable=variable,
            from_=from_,
            to=to,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            length=220,
        ).grid(row=row, column=1, sticky="ew")

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")])
        if path:
            self.input_path.set(path)

    def generate(self):
        image_path = self.input_path.get()
        if not image_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn ảnh đầu vào.")
            return

        out_path = self.output_path.get()
        preview_path = self.preview_path.get()
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(preview_path) or ".", exist_ok=True)

        try:
            process_image(
                input_path=image_path,
                output_gcode=out_path,
                preview_path=preview_path,
                brightness=self.brightness.get(),
                contrast=self.contrast.get(),
                cell_size_mm=self.cell_size_mm.get(),
                tool_diameter_mm=self.tool_diameter_mm.get(),
                max_depth_mm=self.max_depth_mm.get(),
            )
            messagebox.showinfo("Hoàn tất", f"G-code đã được tạo:\n{out_path}\n\nPreview:\n{preview_path}")
        except Exception as exc:  # pragma: no cover - GUI safety path
            messagebox.showerror("Lỗi", f"Không thể tạo G-code:\n{exc}")


if __name__ == "__main__":
    app = HalftoneApp()
    app.mainloop()
