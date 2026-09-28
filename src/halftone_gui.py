from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import math

# Ensure the module can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

try:
    from stone_halftone import process_image, adjust_image, build_halftone_points, generate_preview_image
    from grbl_exporter import export_gcode
except ImportError:
    messagebox.showerror("Lỗi import", "Không tìm thấy module stone_halftone.py")
    sys.exit(1)


class SyncCanvas:
    """Synchronized canvas for image display with zoom and pan."""
    
    def __init__(self, parent, sync_group=None):
        self.parent = parent
        self.canvas = tk.Canvas(parent, bg="lightgray", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.scrollbar_h = tk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_v = tk.Scrollbar(parent, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.config(xscrollcommand=self.on_scroll_x, yscrollcommand=self.on_scroll_y)
        
        # Image data
        self.original_image = None
        self.displayed_image = None
        self.photo_image = None
        self.canvas_image_id = None
        
        # Zoom and pan state
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # Sync group
        self.sync_group = sync_group or []
        self.sync_group.append(self)
        self.is_syncing = False
        
        # Event bindings
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-4>", self.on_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_wheel)  # Linux scroll down
        self.canvas.bind("<Button-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
    
    def on_scroll_x(self, *args):
        """Handle horizontal scroll."""
        if not self.is_syncing:
            self.sync_scroll()
        self.scrollbar_h.set(*args)
    
    def on_scroll_y(self, *args):
        """Handle vertical scroll."""
        if not self.is_syncing:
            self.sync_scroll()
        self.scrollbar_v.set(*args)
    
    def sync_scroll(self):
        """Sync scroll position with other canvases."""
        for canvas in self.sync_group:
            if canvas != self:
                canvas.is_syncing = True
                canvas.canvas.xview_moveto(self.canvas.xview()[0])
                canvas.canvas.yview_moveto(self.canvas.yview()[0])
                canvas.is_syncing = False
    
    def display_image(self, image: Image.Image):
        """Display image."""
        self.original_image = image.convert("RGB")
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update_canvas()
    
    def update_canvas(self):
        """Update canvas with current zoom/pan."""
        if not self.original_image:
            return
        
        # Calculate new size
        w = max(1, int(self.original_image.width * self.zoom))
        h = max(1, int(self.original_image.height * self.zoom))
        
        # Resize image
        self.displayed_image = self.original_image.resize((w, h), Image.Resampling.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(self.displayed_image)
        
        # Update canvas
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)
        
        self.canvas_image_id = self.canvas.create_image(
            self.pan_x, self.pan_y, image=self.photo_image, anchor="nw"
        )
        
        # Update scroll region
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # Sync with other canvases
        self.sync_zoom_pan()
    
    def on_wheel(self, event):
        """Handle mouse wheel zoom."""
        if not self.original_image:
            return
        
        # Get mouse position
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Zoom factor
        if event.num in (4, 5) or event.delta < 0:
            factor = 0.8  # Zoom out
        else:
            factor = 1.25  # Zoom in
        
        # Calculate new zoom
        old_zoom = self.zoom
        self.zoom = max(0.1, min(5.0, self.zoom * factor))
        
        # Adjust pan to keep mouse position stable
        self.pan_x = x - (x - self.pan_x) * (self.zoom / old_zoom)
        self.pan_y = y - (y - self.pan_y) * (self.zoom / old_zoom)
        
        self.update_canvas()
    
    def on_pan_start(self, event):
        """Start panning."""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def on_pan_move(self, event):
        """Handle panning."""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        self.pan_x += dx
        self.pan_y += dy
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        
        self.update_canvas()
    
    def on_pan_end(self, event):
        """End panning."""
        pass
    
    def sync_zoom_pan(self):
        """Sync zoom and pan with other canvases."""
        for canvas in self.sync_group:
            if canvas != self:
                canvas.zoom = self.zoom
                canvas.pan_x = self.pan_x
                canvas.pan_y = self.pan_y
                canvas.update_canvas()
    
    def fit_to_window(self):
        """Fit image to window."""
        if not self.original_image:
            return
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 400
            canvas_h = 400
        
        zoom_w = canvas_w / self.original_image.width
        zoom_h = canvas_h / self.original_image.height
        
        self.zoom = min(zoom_w, zoom_h) * 0.95
        self.pan_x = 0
        self.pan_y = 0
        
        self.update_canvas()


class HalftoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stone Halftone Engraver - PWM Vibration Motor")
        self.geometry("1600x900")
        self.resizable(True, True)

        # Variables
        self.input_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="")
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.cell_size_mm = tk.DoubleVar(value=3.0)
        self.tool_diameter_mm = tk.DoubleVar(value=1.2)
        self.dwell_time = tk.DoubleVar(value=0.08)
        self.export_format = tk.StringVar(value="grbl")

        # Data
        self.last_input_image = None
        self.last_preview_image = None
        self.last_gcode = None
        self.last_points = None
        self.sync_group = []

        self.build_ui()
        self.update_output_path()

    def build_ui(self):
        """Build 3-column layout: controls | input image | halftone image."""
        # Main container
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True)

        # ===== LEFT PANEL: CONTROLS =====
        left_panel = tk.Frame(main_container, bg="white", width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=8, pady=8)
        left_panel.pack_propagate(False)

        # Scrollable controls
        canvas_controls = tk.Canvas(left_panel, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(left_panel, orient=tk.VERTICAL, command=canvas_controls.yview)
        scrollable_frame = tk.Frame(canvas_controls, bg="white")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas_controls.configure(scrollregion=canvas_controls.bbox("all"))
        )

        canvas_controls.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas_controls.configure(yscrollcommand=scrollbar.set)

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas_controls.yview_scroll(int(-1*(event.delta/120)), "units")
        scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)

        canvas_controls.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.build_controls(scrollable_frame)

        # ===== CENTER PANEL: INPUT IMAGE =====
        center_panel = tk.Frame(main_container, bg="gray20")
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        tk.Label(center_panel, text="📷 Ảnh gốc", font=("Arial", 10, "bold"), bg="gray20", fg="white").pack()

        self.input_canvas = SyncCanvas(center_panel, sync_group=self.sync_group)
        self.canvas_input = self.input_canvas.canvas

        # ===== RIGHT PANEL: HALFTONE IMAGE =====
        right_panel = tk.Frame(main_container, bg="gray20")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right_panel, text="🎨 Ảnh điểm đập", font=("Arial", 10, "bold"), bg="gray20", fg="white").pack()

        self.halftone_canvas = SyncCanvas(right_panel, sync_group=self.sync_group)
        self.canvas_halftone = self.halftone_canvas.canvas

    def build_controls(self, parent):
        """Build control panel."""
        # Title
        tk.Label(parent, text="⚙️ Điều chỉnh", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(8, 12))

        # === INPUT IMAGE ===
        tk.Label(parent, text="📁 Ảnh đầu vào", font=("Arial", 10, "bold"), bg="white").pack(anchor="w", pady=(8, 4))
        
        btn_frame = tk.Frame(parent, bg="white")
        btn_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Button(btn_frame, text="Chọn ảnh", command=self.select_image, bg="#2196F3", fg="white", width=15).pack(fill=tk.X, padx=4)

        self.label_img_path = tk.Label(parent, text="Chưa chọn ảnh", font=("Arial", 8), bg="white", wraplength=250, justify=tk.LEFT, fg="gray")
        self.label_img_path.pack(anchor="w", padx=4, pady=(0, 12))

        # === IMAGE ADJUSTMENT ===
        self.build_section(parent, "🎚️ Điều chỉnh ảnh")

        tk.Label(parent, text="Độ sáng:", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        scale = tk.Scale(parent, variable=self.brightness, from_=0.2, to=2.5, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale.pack(fill=tk.X, padx=8, pady=(2, 8))

        tk.Label(parent, text="Độ tương phản:", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        scale = tk.Scale(parent, variable=self.contrast, from_=0.2, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale.pack(fill=tk.X, padx=8, pady=(2, 8))

        # === ENGRAVING PARAMETERS ===
        self.build_section(parent, "⚙️ Tham số khắc")

        tk.Label(parent, text="Kích thước ô (mm):", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        scale = tk.Scale(parent, variable=self.cell_size_mm, from_=1.0, to=10.0, resolution=0.5, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale.pack(fill=tk.X, padx=8, pady=(2, 8))

        tk.Label(parent, text="Đường kính đầu (mm):", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        scale = tk.Scale(parent, variable=self.tool_diameter_mm, from_=0.5, to=4.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200, command=lambda v: self.refresh_preview())
        scale.pack(fill=tk.X, padx=8, pady=(2, 8))

        tk.Label(parent, text="Thời gian chạm (s):", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        scale = tk.Scale(parent, variable=self.dwell_time, from_=0.02, to=0.5, resolution=0.02, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
        scale.pack(fill=tk.X, padx=8, pady=(2, 8))

        # === OUTPUT FILES ===
        self.build_section(parent, "💾 File đầu ra")

        tk.Label(parent, text="G-code:", font=("Arial", 9), bg="white").pack(anchor="w", padx=8)
        
        output_frame = tk.Frame(parent, bg="white")
        output_frame.pack(fill=tk.X, padx=8, pady=(2, 4))
        
        tk.Entry(output_frame, textvariable=self.output_path, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(output_frame, text="📂", command=self.choose_output_dir, width=3).pack(side=tk.LEFT, padx=(4, 0))

        # === EXPORT FORMAT ===
        self.build_section(parent, "📤 Định dạng xuất")

        formats = [
            ("GRBL", "grbl"),
            ("CSV", "csv"),
            ("JSON", "json"),
            ("MATLAB", "matlab"),
        ]

        for label, value in formats:
            tk.Radiobutton(
                parent,
                text=label,
                variable=self.export_format,
                value=value,
                font=("Arial", 9),
                bg="white"
            ).pack(anchor="w", padx=12)

        # === ACTION BUTTONS ===
        tk.Frame(parent, bg="white", height=8).pack()

        btn_gen = tk.Button(
            parent,
            text="✓ TẠO G-CODE",
            command=self.generate,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            height=2
        )
        btn_gen.pack(fill=tk.X, padx=8, pady=(8, 4))

        btn_export = tk.Button(
            parent,
            text="📤 XUẤT",
            command=self.export_gcode,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            height=2
        )
        btn_export.pack(fill=tk.X, padx=8, pady=(0, 4))

        btn_copy = tk.Button(
            parent,
            text="📋 COPY G-CODE",
            command=self.copy_gcode,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            height=2
        )
        btn_copy.pack(fill=tk.X, padx=8, pady=(0, 4))

        btn_zoom = tk.Button(
            parent,
            text="🔍 Fit Images",
            command=self.fit_images,
            bg="#9C27B0",
            fg="white",
            font=("Arial", 9),
            height=1
        )
        btn_zoom.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Status
        tk.Frame(parent, bg="white", height=8).pack()
        self.status_label = tk.Label(parent, text="Sẵn sàng", font=("Arial", 8), bg="white", fg="gray")
        self.status_label.pack(anchor="w", padx=8)

    def build_section(self, parent, title):
        """Build a titled section."""
        tk.Label(parent, text=title, font=("Arial", 10, "bold"), bg="white").pack(anchor="w", padx=8, pady=(12, 6))
        tk.Frame(parent, bg="#E8E8E8", height=1).pack(fill=tk.X, padx=8, pady=(0, 6))

    def update_output_path(self):
        """Update output path with timestamp."""
        from datetime import datetime
        home = Path.home()
        output_dir = home / "Downloads" / "stone_engrave"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path.set(str(output_dir / f"toolpath_{timestamp}.nc"))

    def select_image(self):
        """Select input image."""
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
            self.label_img_path.config(text=f"✓ {Path(path).name}")
            self.refresh_images()

    def choose_output_dir(self):
        """Choose output directory."""
        directory = filedialog.askdirectory(title="Chọn thư mục lưu G-code")
        if directory:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(directory) / f"toolpath_{timestamp}.nc"
            self.output_path.set(str(output_file))
            self.status_label.config(text=f"Thư mục: {directory}", fg="green")

    def refresh_images(self):
        """Refresh both input and halftone images."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            self.status_label.config(text="❌ File không tồn tại", fg="red")
            return

        try:
            img = Image.open(image_path)
            self.last_input_image = img.convert("L")
            self.input_canvas.display_image(img.convert("RGB"))
            
            self.refresh_preview()
            self.status_label.config(text="✓ Ảnh tải thành công", fg="green")
        except Exception as exc:
            self.status_label.config(text=f"❌ Lỗi: {exc}", fg="red")

    def refresh_preview(self):
        """Refresh halftone preview."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            return

        try:
            adjusted = adjust_image(
                image_path,
                brightness=self.brightness.get(),
                contrast=self.contrast.get()
            )

            self.last_points = build_halftone_points(
                adjusted,
                cell_size_mm=self.cell_size_mm.get(),
                tool_diameter_mm=self.tool_diameter_mm.get()
            )

            preview = generate_preview_image(
                adjusted,
                self.cell_size_mm.get(),
                self.tool_diameter_mm.get()
            )
            self.last_preview_image = preview
            self.halftone_canvas.display_image(preview.convert("RGB"))

            self.status_label.config(
                text=f"✓ {len(self.last_points)} điểm | ô {self.cell_size_mm.get():.1f}mm | đầu {self.tool_diameter_mm.get():.1f}mm",
                fg="green"
            )
        except Exception as exc:
            self.status_label.config(text=f"❌ Lỗi: {exc}", fg="red")

    def generate(self):
        """Generate G-code."""
        image_path = self.input_path.get()
        if not image_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn ảnh.")
            return

        output_path = self.output_path.get()
        if not output_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục đầu ra.")
            return

        try:
            # Create directories
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Verify write permission
            if not os.access(output_dir, os.W_OK):
                raise PermissionError(f"Không có quyền ghi: {output_dir}")

            # Generate preview path
            preview_path = str(output_dir / f"{Path(output_path).stem}_preview.png")

            # Process image
            result = process_image(
                input_path=image_path,
                output_gcode=output_path,
                preview_path=preview_path,
                brightness=self.brightness.get(),
                contrast=self.contrast.get(),
                cell_size_mm=self.cell_size_mm.get(),
                tool_diameter_mm=self.tool_diameter_mm.get(),
                dwell_s=self.dwell_time.get(),
            )

            # Read G-code
            with open(output_path, 'r', encoding='utf-8') as f:
                self.last_gcode = f.read()

            self.status_label.config(text=f"✓ G-code tạo thành công: {output_path}", fg="green")
            messagebox.showinfo("Thành công", f"G-code đã tạo:\n{output_path}\n\nTổng điểm: {result['points']}")

        except Exception as exc:
            self.status_label.config(text=f"❌ Lỗi: {exc}", fg="red")
            messagebox.showerror("Lỗi", f"Không thể tạo G-code:\n{exc}")

    def export_gcode(self):
        """Export with selected format."""
        if not self.last_points:
            messagebox.showwarning("Cảnh báo", "Tạo G-code trước khi xuất.")
            return

        fmt = self.export_format.get()
        output_path = self.output_path.get()
        output_path = str(Path(output_path).with_suffix(".nc"))

        # Change extension based on format
        if fmt == "csv":
            output_path = output_path.replace(".nc", ".csv")
        elif fmt == "json":
            output_path = output_path.replace(".nc", ".json")
        elif fmt == "matlab":
            output_path = output_path.replace(".nc", ".m")

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            export_gcode(self.last_points, output_path, format_type=fmt, dwell_s=self.dwell_time.get())
            self.status_label.config(text=f"✓ Xuất {fmt.upper()}: {output_path}", fg="green")
            messagebox.showinfo("Thành công", f"Đã xuất {fmt.upper()}:\n{output_path}")
        except Exception as exc:
            self.status_label.config(text=f"❌ Lỗi xuất: {exc}", fg="red")
            messagebox.showerror("Lỗi", f"Không thể xuất:\n{exc}")

    def copy_gcode(self):
        """Copy G-code to clipboard."""
        if not self.last_gcode:
            messagebox.showwarning("Cảnh báo", "Tạo G-code trước.")
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(self.last_gcode)
            self.status_label.config(text="✓ G-code copied to clipboard", fg="green")
            messagebox.showinfo("Thành công", "G-code đã copy vào clipboard")
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể copy:\n{exc}")

    def fit_images(self):
        """Fit both images to window."""
        self.input_canvas.fit_to_window()
        self.halftone_canvas.fit_to_window()
        self.status_label.config(text="✓ Fit to window", fg="green")


def main():
    app = HalftoneApp()
    app.mainloop()


if __name__ == "__main__":
    main()
