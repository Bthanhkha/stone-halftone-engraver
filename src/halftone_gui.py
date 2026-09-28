from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import io

# Ensure the module can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

try:
    from stone_halftone import process_image, adjust_image, build_halftone_points, generate_preview_image
    from grbl_exporter import export_gcode
except ImportError:
    messagebox.showerror("Lỗi import", "Không tìm thấy module stone_halftone.py\nChắc chắn halftone_gui.py và stone_halftone.py nằm cùng thư mục src/")
    sys.exit(1)


class ImageCanvas(tk.Frame):
    """Custom canvas for image display with zoom and pan support."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.canvas = tk.Canvas(self, bg="lightgray", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.scrollbar_h = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.scrollbar_v = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.config(xscrollcommand=self.scrollbar_h.set, yscrollcommand=self.scrollbar_v.set)
        
        self.image_obj = None
        self.photo_image = None
        self.canvas_image_id = None
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux scroll down
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.on_pan)
    
    def display_image(self, image: Image.Image) -> None:
        """Display image on canvas."""
        self.image_obj = image
        self.zoom_level = 1.0
        self.update_display()
    
    def update_display(self) -> None:
        """Update canvas display with current zoom/pan."""
        if not self.image_obj:
            return
        
        # Resize image based on zoom
        zoom_size = (int(self.image_obj.width * self.zoom_level), 
                     int(self.image_obj.height * self.zoom_level))
        
        if zoom_size[0] > 0 and zoom_size[1] > 0:
            display_img = self.image_obj.resize(zoom_size, Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(display_img)
            
            # Remove old image if exists
            if self.canvas_image_id:
                self.canvas.delete(self.canvas_image_id)
            
            self.canvas_image_id = self.canvas.create_image(0, 0, image=self.photo_image, anchor="nw")
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def on_mousewheel(self, event) -> None:
        """Handle zoom with mouse wheel."""
        if not self.image_obj:
            return
        
        # Get mouse position relative to canvas
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Zoom factor
        if event.num == 5 or event.delta < 0:
            factor = 0.8  # Zoom out
        else:
            factor = 1.2  # Zoom in
        
        self.zoom_level = max(0.1, min(5.0, self.zoom_level * factor))
        self.update_display()
    
    def start_pan(self, event) -> None:
        """Start panning."""
        self.pan_x = event.x
        self.pan_y = event.y
    
    def on_pan(self, event) -> None:
        """Handle panning."""
        dx = event.x - self.pan_x
        dy = event.y - self.pan_y
        
        self.canvas.xview_scroll(-dx, "units")
        self.canvas.yview_scroll(-dy, "units")
        
        self.pan_x = event.x
        self.pan_y = event.y
    
    def sync_view(self, other_canvas: 'ImageCanvas') -> None:
        """Sync zoom and pan with another canvas."""
        self.zoom_level = other_canvas.zoom_level
        self.update_display()
        
        # Sync scroll position
        self.canvas.xview_moveto(other_canvas.canvas.xview()[0])
        self.canvas.yview_moveto(other_canvas.canvas.yview()[0])


class HalftoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stone Halftone Engraver - PWM Vibration Motor")
        self.geometry("1200x800")
        self.resizable(True, True)

        self.input_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="output/stone_toolpath.nc")
        self.preview_path = tk.StringVar(value="output/stone_preview.png")
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.cell_size_mm = tk.DoubleVar(value=3.0)
        self.tool_diameter_mm = tk.DoubleVar(value=1.2)
        self.dwell_time = tk.DoubleVar(value=0.08)
        self.export_format = tk.StringVar(value="grbl")
        self.region_mode = tk.BooleanVar(value=False)
        self.region_x1 = tk.IntVar(value=0)
        self.region_y1 = tk.IntVar(value=0)
        self.region_x2 = tk.IntVar(value=100)
        self.region_y2 = tk.IntVar(value=100)

        # Store processed data for preview
        self.last_input_image = None
        self.last_preview_image = None
        self.last_gcode = None
        self.last_points = None

        self.build_ui()

    def build_ui(self):
        """Build the GUI layout with tabs."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Settings
        self.tab_settings = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_settings, text="⚙️ Cài đặt")
        self.build_settings_tab()

        # Tab 2: Side-by-side comparison
        self.tab_comparison = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_comparison, text="🔍 So sánh")
        self.build_comparison_tab()

        # Tab 3: Export format selector
        self.tab_export = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_export, text="📤 Export")
        self.build_export_tab()

        # Tab 4: Region editor
        self.tab_region = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_region, text="🎯 Chỉnh vùng")
        self.build_region_tab()

        # Tab 5: G-code Viewer
        self.tab_gcode = tk.Frame(notebook, bg="white")
        notebook.add(self.tab_gcode, text="📄 G-code")
        self.build_gcode_tab()

    def build_settings_tab(self):
        """Build settings tab with input, parameters, and controls."""
        main_frame = tk.Frame(self.tab_settings, padx=16, pady=16, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="🎨 Stone Halftone Engraver", font=("Arial", 14, "bold"), bg="white").grid(row=0, column=0, columnspan=2, pady=(0, 16))

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
        tk.Entry(main_frame, textvariable=self.output_path).grid(row=11, column=1, sticky="ew")

        tk.Label(main_frame, text="Preview PNG:", bg="white", font=("Arial", 9)).grid(row=12, column=0, sticky="w", padx=(16, 0), pady=(6, 0))
        tk.Entry(main_frame, textvariable=self.preview_path).grid(row=12, column=1, sticky="ew")

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

    def build_comparison_tab(self):
        """Build side-by-side comparison tab with synchronized zoom/pan."""
        frame = tk.Frame(self.tab_comparison, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Header
        tk.Label(frame, text="So sánh ảnh gốc và ảnh điểm (Zoom/Pan đồng bộ)", font=("Arial", 11, "bold"), bg="white").pack(anchor="w", pady=(0, 8))

        # Canvas frame for side-by-side
        canvas_frame = tk.Frame(frame, bg="white")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Left canvas (input image)
        left_frame = tk.Frame(canvas_frame, bg="white")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        tk.Label(left_frame, text="📷 Ảnh gốc", font=("Arial", 10, "bold"), bg="white").pack(anchor="w")
        self.canvas_input = ImageCanvas(left_frame, height=400)
        self.canvas_input.pack(fill=tk.BOTH, expand=True)

        # Right canvas (halftone image)
        right_frame = tk.Frame(canvas_frame, bg="white")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(right_frame, text="🎨 Ảnh điểm", font=("Arial", 10, "bold"), bg="white").pack(anchor="w")
        self.canvas_halftone = ImageCanvas(right_frame, height=400)
        self.canvas_halftone.pack(fill=tk.BOTH, expand=True)

        # Sync zoom/pan between canvases
        self.canvas_input.canvas.bind("<MouseWheel>", lambda e: self.sync_canvases())
        self.canvas_input.canvas.bind("<Button-4>", lambda e: self.sync_canvases())
        self.canvas_input.canvas.bind("<Button-5>", lambda e: self.sync_canvases())
        self.canvas_halftone.canvas.bind("<MouseWheel>", lambda e: self.sync_canvases())
        self.canvas_halftone.canvas.bind("<Button-4>", lambda e: self.sync_canvases())
        self.canvas_halftone.canvas.bind("<Button-5>", lambda e: self.sync_canvases())

        # Bottom controls
        btn_frame = tk.Frame(frame, bg="white")
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_frame, text="🔄 Làm mới", command=self.refresh_comparison, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="🔍 Fit to window", command=self.fit_to_window, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=(0, 8))
        self.label_comparison_info = tk.Label(btn_frame, text="Chưa tải ảnh", font=("Arial", 9), bg="white")
        self.label_comparison_info.pack(side=tk.LEFT)

    def sync_canvases(self):
        """Synchronize zoom level and scroll position between canvases."""
        self.canvas_halftone.sync_view(self.canvas_input)

    def fit_to_window(self):
        """Fit images to window."""
        if self.canvas_input.image_obj:
            self.canvas_input.zoom_level = 1.0
            self.canvas_input.update_display()
        if self.canvas_halftone.image_obj:
            self.canvas_halftone.zoom_level = 1.0
            self.canvas_halftone.update_display()

    def build_export_tab(self):
        """Build export format selector tab."""
        frame = tk.Frame(self.tab_export, padx=16, pady=16, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="📤 Chọn định dạng xuất", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 16))

        # Format selection
        fmt_frame = tk.Frame(frame, bg="white")
        fmt_frame.pack(fill=tk.X, pady=(0, 16))

        formats = [
            ("GRBL (chuẩn CNC)", "grbl"),
            ("CSV (bảng tính)", "csv"),
            ("JSON (API/Web)", "json"),
            ("MATLAB (phân tích)", "matlab"),
            ("ModBus RTU (PLC)", "modbus"),
        ]

        for label, value in formats:
            tk.Radiobutton(
                fmt_frame,
                text=label,
                variable=self.export_format,
                value=value,
                font=("Arial", 10),
                bg="white"
            ).pack(anchor="w", pady=4)

        # Format description
        desc_frame = tk.LabelFrame(frame, text="📋 Mô tả định dạng", font=("Arial", 10, "bold"), bg="white", padx=8, pady=8)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        descriptions = {
            "grbl": "G-code chuẩn cho GRBL Controller (Arduino + CNC Shield)\nCó lệnh M3 Sxxx điều khiển PWM",
            "csv": "Bảng dữ liệu CSV: X, Y, Radius, PWM, Intensity\nThích hợp cho Excel, Gnuplot, hoặc phần mềm custom",
            "json": "JSON format cho API, Web viewer, hoặc mobile app\nCó đầy đủ metadata và thông tin điểm",
            "matlab": "MATLAB script để vẽ biểu đồ và phân tích\nVẽ trajectory 2D và phân tích phân bố PWM",
            "modbus": "ModBus RTU format cho industrial PLC\nMỗi điểm gửi via register: X, Y, PWM",
        }

        self.desc_label = tk.Label(desc_frame, text=descriptions.get("grbl", ""), font=("Arial", 9), bg="white", justify=tk.LEFT, wraplength=500)
        self.desc_label.pack(anchor="w")

        # Update description when format changes
        for label, value in formats:
            tk.Radiobutton(
                fmt_frame,
                text=label,
                variable=self.export_format,
                value=value,
                command=lambda v=value: self.update_format_description(v),
                font=("Arial", 10),
                bg="white"
            )

        # Export button
        tk.Button(
            frame,
            text="💾 Xuất theo định dạng được chọn",
            command=self.export_with_format,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            height=2
        ).pack(fill=tk.X, pady=(0, 8))

        self.export_status = tk.Label(frame, text="Chưa xuất", font=("Arial", 9), bg="white", fg="gray")
        self.export_status.pack(anchor="w")

    def update_format_description(self, fmt):
        """Update format description."""
        descriptions = {
            "grbl": "G-code chuẩn cho GRBL Controller (Arduino + CNC Shield)\nCó lệnh M3 Sxxx điều khiển PWM",
            "csv": "Bảng dữ liệu CSV: X, Y, Radius, PWM, Intensity\nThích hợp cho Excel, Gnuplot, hoặc phần mềm custom",
            "json": "JSON format cho API, Web viewer, hoặc mobile app\nCó đầy đủ metadata và thông tin điểm",
            "matlab": "MATLAB script để vẽ biểu đồ và phân tích\nVẽ trajectory 2D và phân tích phân bố PWM",
            "modbus": "ModBus RTU format cho industrial PLC\nMỗi điểm gửi via register: X, Y, PWM",
        }
        self.desc_label.config(text=descriptions.get(fmt, ""))

    def build_region_tab(self):
        """Build region editor tab for selective processing."""
        frame = tk.Frame(self.tab_region, padx=16, pady=16, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="🎯 Chỉnh sửa vùng xử lý", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 16))

        # Enable/disable region mode
        region_check = tk.Checkbutton(
            frame,
            text="Chỉ xử lý vùng được chọn (không toàn bộ ảnh)",
            variable=self.region_mode,
            font=("Arial", 10),
            bg="white",
            command=self.toggle_region_mode
        )
        region_check.pack(anchor="w", pady=(0, 12))

        # Region coordinates
        coord_frame = tk.LabelFrame(frame, text="📍 Tọa độ vùng (pixel)", font=("Arial", 10, "bold"), bg="white", padx=8, pady=8)
        coord_frame.pack(fill=tk.X, pady=(0, 16))

        tk.Label(coord_frame, text="X1 (trái):", bg="white").grid(row=0, column=0, sticky="w", padx=(16, 0))
        tk.Spinbox(coord_frame, from_=0, to=10000, textvariable=self.region_x1, width=10).grid(row=0, column=1, sticky="w", padx=(8, 0))

        tk.Label(coord_frame, text="Y1 (trên):", bg="white").grid(row=0, column=2, sticky="w", padx=(16, 0))
        tk.Spinbox(coord_frame, from_=0, to=10000, textvariable=self.region_y1, width=10).grid(row=0, column=3, sticky="w", padx=(8, 0))

        tk.Label(coord_frame, text="X2 (phải):", bg="white").grid(row=1, column=0, sticky="w", padx=(16, 0))
        tk.Spinbox(coord_frame, from_=0, to=10000, textvariable=self.region_x2, width=10).grid(row=1, column=1, sticky="w", padx=(8, 0))

        tk.Label(coord_frame, text="Y2 (dưới):", bg="white").grid(row=1, column=2, sticky="w", padx=(16, 0))
        tk.Spinbox(coord_frame, from_=0, to=10000, textvariable=self.region_y2, width=10).grid(row=1, column=3, sticky="w", padx=(8, 0))

        # Depth estimation
        depth_frame = tk.LabelFrame(frame, text="📊 Ước tính độ sâu theo mật độ", font=("Arial", 10, "bold"), bg="white", padx=8, pady=8)
        depth_frame.pack(fill=tk.X)

        tk.Label(depth_frame, text="Loại vật liệu:", bg="white").pack(anchor="w", pady=(8, 4))

        material_var = tk.StringVar(value="granite")
        materials = [
            ("Granite (đá hoa cương)", "granite"),
            ("Marble (đá hoa cương trắng)", "marble"),
            ("Limestone (đá vôi)", "limestone"),
            ("Sandstone (đá cát)", "sandstone"),
            ("Slate (đá phiến)", "slate"),
        ]

        for label, value in materials:
            tk.Radiobutton(depth_frame, text=label, variable=material_var, value=value, font=("Arial", 9), bg="white").pack(anchor="w")

        # Info
        info_text = ("Ước tính độ sâu:\n"
                     "• Granite: mềm → 0.5-1.0mm, trung bình → 1.0-2.0mm, cứng → 2.0-4.0mm\n"
                     "• Marble: nhạy → 0.3-0.8mm, trung bình → 0.8-1.5mm, sâu → 1.5-3.0mm\n"
                     "• Limestone: nhanh → 0.2-0.6mm, trung bình → 0.6-1.2mm, sâu → 1.2-2.5mm")
        tk.Label(depth_frame, text=info_text, font=("Arial", 8), bg="white", justify=tk.LEFT).pack(anchor="w", pady=(8, 0))

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
            self.refresh_comparison()

    def refresh_comparison(self):
        """Refresh both input and halftone preview."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            self.canvas_input.canvas.delete("all")
            self.canvas_halftone.canvas.delete("all")
            self.label_comparison_info.config(text="Lỗi: File không tồn tại")
            return

        try:
            img = Image.open(image_path)
            self.last_input_image = img
            
            # Display input image
            self.canvas_input.display_image(img.copy())

            # Generate and display halftone
            self.refresh_preview()

        except Exception as exc:
            self.canvas_input.canvas.delete("all")
            self.canvas_halftone.canvas.delete("all")
            self.label_comparison_info.config(text=f"Lỗi: {exc}")

    def refresh_preview(self):
        """Refresh halftone preview based on current parameters."""
        image_path = self.input_path.get()
        if not image_path or not Path(image_path).exists():
            return

        try:
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
            self.last_points = points

            preview = generate_preview_image(adjusted, self.cell_size_mm.get(), self.tool_diameter_mm.get())
            self.last_preview_image = preview

            # Display halftone image
            self.canvas_halftone.display_image(preview.copy())

            self.label_comparison_info.config(
                text=f"Tổng điểm: {len(points)} | Kích thước ô: {self.cell_size_mm.get():.1f}mm | Đầu: {self.tool_diameter_mm.get():.1f}mm"
            )

        except Exception as exc:
            self.canvas_halftone.canvas.delete("all")
            self.label_comparison_info.config(text=f"Lỗi: {exc}")

    def toggle_region_mode(self):
        """Toggle region mode."""
        if self.region_mode.get():
            messagebox.showinfo("Chế độ vùng", "Chỉ vùng được chọn sẽ được xử lý")
        else:
            messagebox.showinfo("Chế độ toàn bộ", "Toàn bộ ảnh sẽ được xử lý")

    def export_with_format(self):
        """Export with selected format."""
        if not self.last_points:
            messagebox.showwarning("Cảnh báo", "Chưa tạo G-code. Vui lòng tạo G-code trước.")
            return

        fmt = self.export_format.get()
        output_path = self.output_path.get()

        if fmt == "grbl":
            output_path = output_path.replace(".nc", f"_{fmt}.nc")
        elif fmt == "csv":
            output_path = output_path.replace(".nc", ".csv")
        elif fmt == "json":
            output_path = output_path.replace(".nc", ".json")
        elif fmt == "matlab":
            output_path = output_path.replace(".nc", ".m")
        elif fmt == "modbus":
            output_path = output_path.replace(".nc", ".modbus")

        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            export_gcode(self.last_points, output_path, format_type=fmt, dwell_s=self.dwell_time.get())
            self.export_status.config(text=f"✓ Xuất {fmt.upper()}: {output_path}", fg="green")
            messagebox.showinfo("Thành công", f"Đã xuất {fmt.upper()} thành công:\n{output_path}")
        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể xuất:\n{exc}")

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
            # Create output directories
            out_dir = os.path.dirname(out_path) or "."
            preview_dir = os.path.dirname(preview_path) or "."
            
            os.makedirs(out_dir, exist_ok=True)
            os.makedirs(preview_dir, exist_ok=True)

            # Verify directories are writable
            if not os.access(out_dir, os.W_OK):
                raise PermissionError(f"Không có quyền ghi vào thư mục: {out_dir}")
            if not os.access(preview_dir, os.W_OK):
                raise PermissionError(f"Không có quyền ghi vào thư mục: {preview_dir}")

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

        except PermissionError as e:
            messagebox.showerror("Lỗi Quyền", f"Lỗi quyền truy cập:\n{e}\n\nVui lòng chọn thư mục khác hoặc chạy với quyền quản trị viên.")
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
