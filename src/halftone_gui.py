from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# Ensure the module can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

try:
    from stone_halftone import process_image, adjust_image, build_halftone_points
except ImportError:
    messagebox.showerror("Lỗi import", "Không tìm thấy module stone_halftone.py\nChắc chắn halftone_gui.py và stone_halftone.py nằm cùng thư mục src/")
    sys.exit(1)


class HalftoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stone Halftone Engraver - PWM Vibration Motor")
        self.geometry("900x700")
        self.resizable(True, True)

        self.input_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="output/stone_toolpath.nc")
        self.preview_path = tk.StringVar(value="output/stone_preview.png")
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.cell_size_mm = tk.DoubleVar(value=3.0)
        self.tool_diameter_mm = tk.DoubleVar(value=1.2)
        self.dwell_time = tk.DoubleVar(value=0.08)

        # Store processed data for preview
        self.last_input_image = None
        self.last_preview_image = None
        self.last_gcode = None

        self.build_ui()

    def build_ui(self):
        """Build the GUI layout with tabs."""
        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Settings
        self.tab_settings = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_settings, text="⚙️ Cài đặt")
        self.build_settings_tab()

        # Tab 2: Input Image Preview
        self.tab_input = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_input, text="🖼️ Ảnh gốc")
        self.build_input_tab()

        # Tab 3: Halftone Preview
        self.tab_halftone = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_halftone, text="🎨 Ảnh điểm")
        self.build_halftone_tab()

        # Tab 4: G-code Viewer
        self.tab_gcode = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_gcode, text="📄 G-code")
        self.build_gcode_tab()

    def build_settings_tab(self):
        """Build settings tab with input, parameters, and controls."""
        main_frame = tk.Frame(self.tab_settings, padx=16, pady=16, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = tk.Label(main_frame, text="🎨 Stone Halftone Engraver", font=("Arial", 14, "bold"), bg="white")
        title.grid(row=0, column=0, columnspan=2, pady=(0, 16))

        # Input image selection
        tk.Label(main_frame, text="📁 Chọn ảnh:", font=("Arial", 10, "bold"), bg="white").grid(row=1, column=0, sticky="w", pady=(0, 4))
        btn_select = tk.Button(main_frame, text="Mở file ảnh", command=self.select_image, bg="#2196F3", fg="white", width=12)
        btn_select.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        self.entry_img = tk.Entry(main_frame, textvariable=self.input_path, width=50, state="readonly", relief=tk.SUNKEN)
        self.entry_img.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        # Adjustment section
        tk.Label(main_frame, text="🎚️ Điều chỉnh ảnh", font=("Arial", 10, "bold"), bg="white").grid(row=3, column=0, sticky="w", pady=(8, 8))

        tk.Label(main_frame, text="Độ sáng:", bg="white").grid(row=4, column=0, sticky="w", padx=(16, 0))
        scale_br = tk.Scale(main_frame, variable=self.brightness, from_=0.2, to=2.5, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale_br.grid(row=4, column=1, sticky="ew", pady=4)

        tk.Label(main_frame, text="Độ tương phản:", bg="white").grid(row=5, column=0, sticky="w", padx=(16, 0))
        scale_ct = tk.Scale(main_frame, variable=self.contrast, from_=0.2, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale_ct.grid(row=5, column=1, sticky="ew", pady=4)

        # Engraving parameters
        tk.Label(main_frame, text="⚙️ Tham số khắc", font=("Arial", 10, "bold"), bg="white").grid(row=6, column=0, sticky="w", pady=(12, 8))

        tk.Label(main_frame, text="Kích thước ô (mm):", bg="white").grid(row=7, column=0, sticky="w", padx=(16, 0))
        scale_cell = tk.Scale(main_frame, variable=self.cell_size_mm, from_=1.0, to=10.0, resolution=0.5, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale_cell.grid(row=7, column=1, sticky="ew", pady=4)

        tk.Label(main_frame, text="Đường kính đầu (mm):", bg="white").grid(row=8, column=0, sticky="w", padx=(16, 0))
        scale_tool = tk.Scale(main_frame, variable=self.tool_diameter_mm, from_=0.5, to=4.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale_tool.grid(row=8, column=1, sticky="ew", pady=4)

        tk.Label(main_frame, text="Thời gian chạm (s):", bg="white").grid(row=9, column=0, sticky="w", padx=(16, 0))
        scale_dwell = tk.Scale(main_frame, variable=self.dwell_time, from_=0.02, to=0.5, resolution=0.02, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
        scale_dwell.grid(row=9, column=1, sticky="ew", pady=4)

        # Output paths
        tk.Label(main_frame, text="💾 File đầu ra", font=("Arial", 10, "bold"), bg="white").grid(row=10, column=0, sticky="w", pady=(12, 8))

        tk.Label(main_frame, text="G-code:", bg="white", font=("Arial", 9)).grid(row=11, column=0, sticky="w", padx=(16, 0))
        tk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=11, column=1, sticky="ew")

        tk.Label(main_frame, text="Preview PNG:", bg="white", font=("Arial", 9)).grid(row=12, column=0, sticky="w", padx=(16, 0), pady=(6, 0))
        tk.Entry(main_frame, textvariable=self.preview_path, width=50).grid(row=12, column=1, sticky="ew")

        # Generate button
        btn_gen = tk.Button(
            main_frame,
            text="✓ TẠO G-CODE",
            command=self.generate,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            height=2
        )
        btn_gen.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(16, 0))

        main_frame.columnconfigure(1, weight=1)

    def build_input_tab(self):
        """Build tab to display input image."""
        frame = tk.Frame(self.tab_input, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(frame, text="📷 Ảnh gốc được import", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 8))

        self.canvas_input = tk.Canvas(frame, bg="lightgray", width=500, height=500)
        self.canvas_input.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="🔄 Làm mới", command=self.refresh_input_preview, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.label_input_info = tk.Label(btn_frame, text="Chưa tải ảnh", font=("Arial", 9), bg="white")
        self.label_input_info.pack(side=tk.LEFT)

    def build_halftone_tab(self):
        """Build tab to display halftone preview."""
        frame = tk.Frame(self.tab_halftone, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(frame, text="🎨 Ảnh sau khi tạo điểm halftone", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 8))

        self.canvas_halftone = tk.Canvas(frame, bg="lightgray", width=500, height=500)
        self.canvas_halftone.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="🔄 Làm mới", command=self.refresh_halftone_preview, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.label_halftone_info = tk.Label(btn_frame, text="Chưa xử lý ảnh", font=("Arial", 9), bg="white")
        self.label_halftone_info.pack(side=tk.LEFT)

    def build_gcode_tab(self):
        """Build tab to display G-code."""
        frame = tk.Frame(self.tab_gcode, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(frame, text="📄 Nội dung file G-code", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 8))

        # Text widget with scrollbar
        text_frame = tk.Frame(frame, bg="white")
        text_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_gcode = tk.Text(
            text_frame,
            font=("Courier New", 9),
            bg="white",
            fg="black",
            yscrollcommand=scrollbar.set,
            state="disabled"
        )
        self.text_gcode.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_gcode.yview)

        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="💾 Lưu G-code", command=self.save_gcode, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="📋 Copy", command=self.copy_gcode, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.label_gcode_info = tk.Label(btn_frame, text="Chưa tạo G-code", font=("Arial", 9), bg="white")
        self.label_gcode_info.pack(side=tk.LEFT)

    def select_image(self):
        """Open file dialog to select image."""
        filetypes = [
            ("Hình ảnh", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("BMP", "*.bmp"),
            ("Tất cả", "*.*")
        ]
        path = filedialog.askopenfilename(
            title="Chọn ảnh để khắc",
            filetypes=filetypes
        )
        if path:
            self.input_path.set(path)
            self.refresh_input_preview()

    def refresh_input_preview(self):
        """Refresh input image preview."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            self.canvas_input.delete("all")
            self.label_input_info.config(text="Lỗi: File không tồn tại")
            return

        try:
            img = Image.open(image_path)
            self.last_input_image = img
            
            # Display on canvas
            img.thumbnail((500, 500), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.canvas_input.delete("all")
            self.canvas_input.create_image(250, 250, image=photo)
            self.canvas_input.image = photo

            self.label_input_info.config(text=f"Kích thước: {img.width}x{img.height} | Định dạng: {img.format}")
            self.refresh_halftone_preview()

        except Exception as exc:
            self.canvas_input.delete("all")
            self.label_input_info.config(text=f"Lỗi: {exc}")

    def refresh_halftone_preview(self):
        """Refresh halftone preview based on current parameters."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            self.canvas_halftone.delete("all")
            self.label_halftone_info.config(text="Lỗi: Vui lòng chọn ảnh")
            return

        try:
            # Process image with current parameters
            adjusted = adjust_image(
                image_path,
                brightness=self.brightness.get(),
                contrast=self.contrast.get()
            )
            
            points = build_halftone_points(
                adjusted,
                cell_size_mm=self.cell_size_mm.get(),
                tool_diameter_mm=self.tool_diameter_mm.get()
            )

            # Generate preview image (create halftone dots)
            from stone_halftone import generate_preview_image
            preview = generate_preview_image(adjusted, self.cell_size_mm.get(), self.tool_diameter_mm.get())
            self.last_preview_image = preview

            # Display on canvas
            preview.thumbnail((500, 500), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(preview)
            self.canvas_halftone.delete("all")
            self.canvas_halftone.create_image(250, 250, image=photo)
            self.canvas_halftone.image = photo

            self.label_halftone_info.config(text=f"Tổng điểm: {len(points)} | Kích thước ô: {self.cell_size_mm.get():.1f}mm | Đầu: {self.tool_diameter_mm.get():.1f}mm")

        except Exception as exc:
            self.canvas_halftone.delete("all")
            self.label_halftone_info.config(text=f"Lỗi: {exc}")

    def generate(self):
        """Generate G-code from selected image and parameters."""
        image_path = self.input_path.get()
        if not image_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn ảnh đầu vào.")
            return

        if not Path(image_path).exists():
            messagebox.showerror("Lỗi", f"File không tồn tại:\n{image_path}")
            return

        out_path = self.output_path.get()
        preview_path = self.preview_path.get()

        if not out_path.strip():
            messagebox.showerror("Lỗi", "Vui lòng nhập đường dẫn file G-code.")
            return

        try:
            # Create output directories if needed
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(preview_path) or ".", exist_ok=True)

            # Process image
            result = process_image(
                input_path=image_path,
                output_gcode=out_path,
                preview_path=preview_path,
                brightness=self.brightness.get(),
                contrast=self.contrast.get(),
                cell_size_mm=self.cell_size_mm.get(),
                tool_diameter_mm=self.tool_diameter_mm.get(),
                dwell_s=self.dwell_time.get(),
            )

            # Read G-code content
            with open(out_path, 'r', encoding='utf-8') as f:
                self.last_gcode = f.read()

            # Update G-code display
            self.text_gcode.config(state="normal")
            self.text_gcode.delete(1.0, tk.END)
            self.text_gcode.insert(1.0, self.last_gcode)
            self.text_gcode.config(state="disabled")
            self.label_gcode_info.config(text=f"✓ G-code đã tạo | {result['points']} điểm | {out_path}")

            msg = (
                f"✓ Hoàn tất!\n\n"
                f"Tổng điểm khắc: {result['points']}\n\n"
                f"G-code: {result['gcode']}\n"
                f"Preview: {result['preview']}"
            )
            messagebox.showinfo("Thành công", msg)

        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể tạo G-code:\n\n{type(exc).__name__}: {exc}")

    def save_gcode(self):
        """Save G-code to file."""
        if not self.last_gcode:
            messagebox.showwarning("Cảnh báo", "Chưa tạo G-code. Vui lòng tạo G-code trước.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".nc",
            filetypes=[("NC files", "*.nc"), ("GCODE files", "*.gcode"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.last_gcode)
                messagebox.showinfo("Thành công", f"G-code đã lưu:\n{path}")
            except Exception as exc:
                messagebox.showerror("Lỗi", f"Không thể lưu file:\n{exc}")

    def copy_gcode(self):
        """Copy G-code to clipboard."""
        if not self.last_gcode:
            messagebox.showwarning("Cảnh báo", "Chưa tạo G-code.")
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(self.last_gcode)
            messagebox.showinfo("Thành công", "G-code đã copy vào clipboard")
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể copy:\n{exc}")


def main():
    """Entry point for the GUI application."""
    app = HalftoneApp()
    app.mainloop()


if __name__ == "__main__":
    main()
