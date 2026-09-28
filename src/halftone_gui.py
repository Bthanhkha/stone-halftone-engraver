from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

# Ensure the module can import from the same directory
sys.path.insert(0, str(Path(__file__).parent))

try:
    from stone_halftone import process_image
except ImportError:
    messagebox.showerror("Lỗi import", "Không tìm thấy module stone_halftone.py\nChắc chắn halftone_gui.py và stone_halftone.py nằm cùng thư mục src/")
    sys.exit(1)


class HalftoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stone Halftone Engraver - PWM Vibration Motor")
        self.geometry("600x480")
        self.resizable(False, False)

        self.input_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="output/stone_toolpath.nc")
        self.preview_path = tk.StringVar(value="output/stone_preview.png")
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast = tk.DoubleVar(value=1.0)
        self.cell_size_mm = tk.DoubleVar(value=3.0)
        self.tool_diameter_mm = tk.DoubleVar(value=1.2)
        self.dwell_time = tk.DoubleVar(value=0.08)

        self.build_ui()

    def build_ui(self):
        """Build the GUI layout without argparse."""
        main_frame = tk.Frame(self, padx=16, pady=16, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = tk.Label(main_frame, text="🎨 Stone Halftone Engraver", font=("Arial", 14, "bold"), bg="white")
        title.grid(row=0, column=0, columnspan=2, pady=(0, 16))

        # Input image selection
        tk.Label(main_frame, text="📁 Chọn ảnh:", font=("Arial", 10, "bold"), bg="white").grid(row=1, column=0, sticky="w", pady=(0, 4))
        btn_select = tk.Button(main_frame, text="Mở file ảnh", command=self.select_image, bg="#2196F3", fg="white", width=12)
        btn_select.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        entry_img = tk.Entry(main_frame, textvariable=self.input_path, width=50, state="readonly", relief=tk.SUNKEN)
        entry_img.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        # Adjustment section
        tk.Label(main_frame, text="🎚️ Điều chỉnh ảnh", font=("Arial", 10, "bold"), bg="white").grid(row=3, column=0, sticky="w", pady=(8, 8))

        tk.Label(main_frame, text="Độ sáng:", bg="white").grid(row=4, column=0, sticky="w", padx=(16, 0))
        scale_br = tk.Scale(main_frame, variable=self.brightness, from_=0.2, to=2.5, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
        scale_br.grid(row=4, column=1, sticky="ew", pady=4)

        tk.Label(main_frame, text="Độ tương phản:", bg="white").grid(row=5, column=0, sticky="w", padx=(16, 0))
        scale_ct = tk.Scale(main_frame, variable=self.contrast, from_=0.2, to=3.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
        scale_ct.grid(row=5, column=1, sticky="ew", pady=4)

        # Engraving parameters
        tk.Label(main_frame, text="⚙️ Tham số khắc", font=("Arial", 10, "bold"), bg="white").grid(row=6, column=0, sticky="w", pady=(12, 8))

        tk.Label(main_frame, text="Kích thước ô (mm):", bg="white").grid(row=7, column=0, sticky="w", padx=(16, 0))
        scale_cell = tk.Scale(main_frame, variable=self.cell_size_mm, from_=1.0, to=10.0, resolution=0.5, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
        scale_cell.grid(row=7, column=1, sticky="ew", pady=4)

        tk.Label(main_frame, text="Đường kính đầu (mm):", bg="white").grid(row=8, column=0, sticky="w", padx=(16, 0))
        scale_tool = tk.Scale(main_frame, variable=self.tool_diameter_mm, from_=0.5, to=4.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#E8E8E8", length=200)
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

            msg = (
                f"✓ Hoàn tất!\n\n"
                f"Tổng điểm khắc: {result['points']}\n\n"
                f"G-code: {result['gcode']}\n"
                f"Preview: {result['preview']}"
            )
            messagebox.showinfo("Thành công", msg)

        except Exception as exc:
            messagebox.showerror("Lỗi", f"Không thể tạo G-code:\n\n{type(exc).__name__}: {exc}")


def main():
    """Entry point for the GUI application."""
    app = HalftoneApp()
    app.mainloop()


if __name__ == "__main__":
    main()
