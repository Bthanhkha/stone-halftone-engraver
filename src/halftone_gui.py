from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from tkinter import *
from tkinter import messagebox, filedialog, ttk
from typing import Callable

from PIL import Image, ImageTk, ImageEnhance
import serial
import serial.tools.list_ports

from stone_halftone import process_image


class GRBLController:
    """Handle serial communication with GRBL machine."""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.connected = False
        self.status_callback: Callable[[str], None] | None = None
        
    def connect(self) -> bool:
        """Connect to GRBL machine."""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for connection stabilization
            self.connected = True
            self._log("Connected to GRBL")
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from GRBL machine."""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
                self.connected = False
                self._log("Disconnected")
                return True
        except Exception as e:
            self._log(f"Disconnect failed: {e}")
        return False
    
    def send_gcode(self, gcode: str, callback: Callable[[str], None] | None = None) -> bool:
        """Send G-code to GRBL machine."""
        if not self.connected or not self.serial:
            self._log("Not connected to GRBL")
            return False
        
        try:
            lines = [line.strip() for line in gcode.split('\n') if line.strip() and not line.startswith(';')]
            
            for i, line in enumerate(lines):
                self.serial.write((line + '\n').encode())
                
                # Wait for response
                response = self._read_response()
                self._log(f"[{i+1}/{len(lines)}] {line}")
                
                if callback:
                    callback(f"Sent {i+1}/{len(lines)}")
                
                if 'error' in response.lower():
                    self._log(f"GRBL Error: {response}")
                    return False
                
                time.sleep(0.01)  # Small delay between commands
            
            self._log("G-code sent successfully")
            return True
        except Exception as e:
            self._log(f"Send failed: {e}")
            return False
    
    def get_status(self) -> str:
        """Get GRBL machine status."""
        if not self.connected or not self.serial:
            return "Not connected"
        
        try:
            self.serial.write(b'?\n')
            response = self._read_response()
            return response
        except Exception as e:
            return f"Status error: {e}"
    
    def _read_response(self, timeout: float = 2.0) -> str:
        """Read response from GRBL."""
        start = time.time()
        response = ""
        
        while time.time() - start < timeout:
            if self.serial.in_waiting:
                byte = self.serial.read(1)
                if byte:
                    response += byte.decode('utf-8', errors='ignore')
                    if response.endswith('\n'):
                        break
            time.sleep(0.01)
        
        return response.strip()
    
    def _log(self, message: str):
        """Log message."""
        if self.status_callback:
            self.status_callback(message)


class SyncCanvasManager:
    """Manage synchronized zoom/pan between two canvases."""
    
    def __init__(self, canvas1: Canvas, canvas2: Canvas):
        self.canvas1 = canvas1
        self.canvas2 = canvas2
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.dragging = False
        self.drag_start = (0, 0)
        
        # Bind events
        for canvas in [self.canvas1, self.canvas2]:
            canvas.bind("<MouseWheel>", self._on_scroll)
            canvas.bind("<Button-4>", self._on_scroll)  # Linux scroll up
            canvas.bind("<Button-5>", self._on_scroll)  # Linux scroll down
            canvas.bind("<Button-1>", self._on_drag_start)
            canvas.bind("<B1-Motion>", self._on_drag)
            canvas.bind("<ButtonRelease-1>", self._on_drag_end)
    
    def _on_scroll(self, event):
        """Handle scroll wheel zoom."""
        delta = 1.1 if event.num == 4 or event.delta > 0 else 0.9
        self.zoom *= delta
        self.zoom = max(0.1, min(self.zoom, 10.0))  # Clamp zoom
    
    def _on_drag_start(self, event):
        """Start pan drag."""
        self.dragging = True
        self.drag_start = (event.x, event.y)
    
    def _on_drag(self, event):
        """Pan during drag."""
        if not self.dragging:
            return
        
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start = (event.x, event.y)
    
    def _on_drag_end(self, event):
        """End pan drag."""
        self.dragging = False
    
    def get_transform(self) -> tuple[float, float, float]:
        """Get current zoom and pan values."""
        return self.zoom, self.pan_x, self.pan_y
    
    def reset(self):
        """Reset zoom and pan to default."""
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0


class HalftoneEngraverGUI:
    """Main GUI application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Stone Halftone Engraver - GRBL Control")
        self.root.geometry("1600x1000")
        
        # State
        self.input_image_path = None
        self.processed = False
        self.original_image = None
        self.preview_image = None
        self.gcode_content = None
        
        # GRBL
        self.grbl = None
        
        # Image editing
        self.brightness = 1.0
        self.contrast = 1.0
        self.cell_size_mm = 3.0
        self.tool_diameter_mm = 1.2
        self.dwell_s = 0.08
        self.pwm_threshold = 20
        
        self._build_ui()
        self._setup_grbl_ports()
    
    def _build_ui(self):
        """Build GUI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Top: GRBL connection panel
        self._build_grbl_panel(main_frame)
        
        # Middle: Image display area
        image_frame = ttk.LabelFrame(main_frame, text="Image Preview & Zoom/Pan (Sync)", padding=5)
        image_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # Left: Original image
        left_frame = ttk.Frame(image_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        
        ttk.Label(left_frame, text="Original Image", font=("Arial", 10, "bold")).pack()
        self.canvas_original = Canvas(left_frame, bg="white", height=400)
        self.canvas_original.pack(fill=BOTH, expand=True)
        
        # Right: Preview (halftone) image
        right_frame = ttk.Frame(image_frame)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=5)
        
        ttk.Label(right_frame, text="Halftone Preview", font=("Arial", 10, "bold")).pack()
        self.canvas_preview = Canvas(right_frame, bg="white", height=400)
        self.canvas_preview.pack(fill=BOTH, expand=True)
        
        # Initialize sync canvas
        self.sync_canvas = SyncCanvasManager(self.canvas_original, self.canvas_preview)
        
        # Left panel: Controls
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=LEFT, fill=BOTH, padx=10)
        
        self._build_controls_panel(left_panel)
        
        # Right panel: Log
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=10)
        
        self._build_log_panel(right_panel)
    
    def _build_grbl_panel(self, parent):
        """Build GRBL connection panel."""
        grbl_frame = ttk.LabelFrame(parent, text="GRBL Machine Connection", padding=10)
        grbl_frame.pack(fill=X, pady=5)
        
        # Port selection
        port_frame = ttk.Frame(grbl_frame)
        port_frame.pack(fill=X, pady=5)
        
        ttk.Label(port_frame, text="COM Port:", width=12).pack(side=LEFT)
        self.port_combo = ttk.Combobox(port_frame, width=15, state="readonly")
        self.port_combo.pack(side=LEFT, padx=5)
        
        ttk.Button(port_frame, text="Refresh Ports", command=self._setup_grbl_ports).pack(side=LEFT)
        
        # Status
        status_frame = ttk.Frame(grbl_frame)
        status_frame.pack(fill=X, pady=5)
        
        ttk.Label(status_frame, text="Status:", width=12).pack(side=LEFT)
        self.status_label = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.status_label.pack(side=LEFT, padx=5)
        
        # Connect/Disconnect buttons
        button_frame = ttk.Frame(grbl_frame)
        button_frame.pack(fill=X, pady=5)
        
        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self._connect_grbl)
        self.connect_btn.pack(side=LEFT, padx=5)
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self._disconnect_grbl, state=DISABLED)
        self.disconnect_btn.pack(side=LEFT, padx=5)
        
        ttk.Button(button_frame, text="Get Status", command=self._get_grbl_status).pack(side=LEFT, padx=5)
    
    def _build_controls_panel(self, parent):
        """Build control panel."""
        # File selection
        file_frame = ttk.LabelFrame(parent, text="Image", padding=5)
        file_frame.pack(fill=X, pady=5)
        
        ttk.Button(file_frame, text="Load Image", command=self._load_image, width=20).pack(fill=X, pady=3)
        self.image_label = ttk.Label(file_frame, text="No image loaded", foreground="gray", wraplength=150)
        self.image_label.pack(fill=X, pady=3)
        
        # Image adjustments
        adj_frame = ttk.LabelFrame(parent, text="Adjustments", padding=5)
        adj_frame.pack(fill=X, pady=5)
        
        # Brightness
        ttk.Label(adj_frame, text="Brightness:", width=15).pack(anchor=W)
        self.brightness_scale = ttk.Scale(adj_frame, from_=0.2, to=2.5, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.brightness_scale.set(1.0)
        self.brightness_scale.pack(fill=X, pady=2)
        self.brightness_label = ttk.Label(adj_frame, text="1.00")
        self.brightness_label.pack(anchor=E)
        
        # Contrast
        ttk.Label(adj_frame, text="Contrast:", width=15).pack(anchor=W)
        self.contrast_scale = ttk.Scale(adj_frame, from_=0.2, to=3.0, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.contrast_scale.set(1.0)
        self.contrast_scale.pack(fill=X, pady=2)
        self.contrast_label = ttk.Label(adj_frame, text="1.00")
        self.contrast_label.pack(anchor=E)
        
        # Halftone parameters
        param_frame = ttk.LabelFrame(parent, text="Halftone", padding=5)
        param_frame.pack(fill=X, pady=5)
        
        # Cell size
        ttk.Label(param_frame, text="Cell Size (mm):", width=15).pack(anchor=W)
        self.cell_size_scale = ttk.Scale(param_frame, from_=1.0, to=10.0, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.cell_size_scale.set(3.0)
        self.cell_size_scale.pack(fill=X, pady=2)
        self.cell_size_label = ttk.Label(param_frame, text="3.00")
        self.cell_size_label.pack(anchor=E)
        
        # Tool diameter
        ttk.Label(param_frame, text="Tool Diameter (mm):", width=15).pack(anchor=W)
        self.tool_diameter_scale = ttk.Scale(param_frame, from_=0.5, to=5.0, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.tool_diameter_scale.set(1.2)
        self.tool_diameter_scale.pack(fill=X, pady=2)
        self.tool_diameter_label = ttk.Label(param_frame, text="1.20")
        self.tool_diameter_label.pack(anchor=E)
        
        # PWM threshold
        ttk.Label(param_frame, text="PWM Threshold:", width=15).pack(anchor=W)
        self.pwm_threshold_scale = ttk.Scale(param_frame, from_=0, to=100, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.pwm_threshold_scale.set(20)
        self.pwm_threshold_scale.pack(fill=X, pady=2)
        self.pwm_threshold_label = ttk.Label(param_frame, text="20")
        self.pwm_threshold_label.pack(anchor=E)
        
        # Dwell time
        ttk.Label(param_frame, text="Dwell Time (s):", width=15).pack(anchor=W)
        self.dwell_time_scale = ttk.Scale(param_frame, from_=0.01, to=1.0, orient=HORIZONTAL, command=self._on_adjustment_change)
        self.dwell_time_scale.set(0.08)
        self.dwell_time_scale.pack(fill=X, pady=2)
        self.dwell_time_label = ttk.Label(param_frame, text="0.08")
        self.dwell_time_label.pack(anchor=E)
        
        # Action buttons
        action_frame = ttk.LabelFrame(parent, text="Actions", padding=5)
        action_frame.pack(fill=X, pady=5)
        
        ttk.Button(action_frame, text="Generate G-code", command=self._generate_gcode, width=20).pack(fill=X, pady=3)
        ttk.Button(action_frame, text="Save G-code", command=self._save_gcode, width=20).pack(fill=X, pady=3)
        ttk.Button(action_frame, text="Send to GRBL", command=self._send_to_grbl, width=20).pack(fill=X, pady=3)
        
        # Reset zoom
        ttk.Button(action_frame, text="Reset Zoom/Pan", command=self._reset_zoom, width=20).pack(fill=X, pady=3)
    
    def _build_log_panel(self, parent):
        """Build log panel."""
        log_frame = ttk.LabelFrame(parent, text="Log", padding=5)
        log_frame.pack(fill=BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Text widget
        self.log_text = Text(log_frame, height=30, width=50, yscrollcommand=scrollbar.set)
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
    
    def _log(self, message: str):
        """Add message to log."""
        self.log_text.insert(END, f"{message}\n")
        self.log_text.see(END)
        self.root.update()
    
    def _setup_grbl_ports(self):
        """Setup available GRBL COM ports."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports if ports else ["No ports found"]
        if ports:
            self.port_combo.current(0)
    
    def _connect_grbl(self):
        """Connect to GRBL machine."""
        port = self.port_combo.get()
        if port == "No ports found":
            messagebox.showerror("Error", "No COM ports available")
            return
        
        self.grbl = GRBLController(port)
        self.grbl.status_callback = self._log
        
        if self.grbl.connect():
            self.status_label.config(text="Connected", foreground="green")
            self.connect_btn.config(state=DISABLED)
            self.disconnect_btn.config(state=NORMAL)
            self._log(f"Connected to {port}")
        else:
            messagebox.showerror("Error", "Failed to connect to GRBL")
    
    def _disconnect_grbl(self):
        """Disconnect from GRBL machine."""
        if self.grbl:
            self.grbl.disconnect()
            self.status_label.config(text="Disconnected", foreground="red")
            self.connect_btn.config(state=NORMAL)
            self.disconnect_btn.config(state=DISABLED)
            self._log("Disconnected from GRBL")
    
    def _get_grbl_status(self):
        """Get GRBL machine status."""
        if not self.grbl or not self.grbl.connected:
            messagebox.showwarning("Warning", "Not connected to GRBL")
            return
        
        status = self.grbl.get_status()
        self._log(f"GRBL Status: {status}")
    
    def _load_image(self):
        """Load image file."""
        filetypes = [("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        
        if not path:
            return
        
        try:
            self.input_image_path = path
            self.original_image = Image.open(path).convert("L")
            self.image_label.config(text=Path(path).name, foreground="black")
            self._log(f"Loaded: {Path(path).name}")
            self._display_original_image()
            self.processed = False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
            self._log(f"Error loading image: {e}")
    
    def _display_original_image(self):
        """Display original image on canvas."""
        if not self.original_image:
            return
        
        # Resize to fit canvas
        canvas_width = self.canvas_original.winfo_width()
        canvas_height = self.canvas_original.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 400
        
        img = self.original_image.copy()
        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(img)
        self.canvas_original.delete("all")
        self.canvas_original.create_image(canvas_width // 2, canvas_height // 2, image=photo)
        self.canvas_original.image = photo  # Keep reference
    
    def _display_preview_image(self):
        """Display preview image on canvas."""
        if not self.preview_image:
            return
        
        # Resize to fit canvas
        canvas_width = self.canvas_preview.winfo_width()
        canvas_height = self.canvas_preview.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 400
        
        img = self.preview_image.copy()
        img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(img)
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(canvas_width // 2, canvas_height // 2, image=photo)
        self.canvas_preview.image = photo  # Keep reference
    
    def _on_adjustment_change(self, value=None):
        """Handle adjustment slider changes."""
        self.brightness = float(self.brightness_scale.get())
        self.contrast = float(self.contrast_scale.get())
        self.cell_size_mm = float(self.cell_size_scale.get())
        self.tool_diameter_mm = float(self.tool_diameter_scale.get())
        self.dwell_s = float(self.dwell_time_scale.get())
        self.pwm_threshold = int(self.pwm_threshold_scale.get())
        
        # Update labels
        self.brightness_label.config(text=f"{self.brightness:.2f}")
        self.contrast_label.config(text=f"{self.contrast:.2f}")
        self.cell_size_label.config(text=f"{self.cell_size_mm:.2f}")
        self.tool_diameter_label.config(text=f"{self.tool_diameter_mm:.2f}")
        self.dwell_time_label.config(text=f"{self.dwell_s:.2f}")
        self.pwm_threshold_label.config(text=f"{self.pwm_threshold}")
        
        # Auto-regenerate preview if image is loaded
        if self.input_image_path and self.original_image:
            self._generate_gcode()
    
    def _generate_gcode(self):
        """Generate G-code from current image and settings."""
        if not self.input_image_path:
            messagebox.showwarning("Warning", "Please load an image first")
            return
        
        try:
            self._log("Generating G-code...")
            
            # Create temporary files
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            gcode_path = temp_dir / "preview.gcode"
            preview_path = temp_dir / "preview.png"
            
            # Process image
            result = process_image(
                input_path=self.input_image_path,
                output_gcode=str(gcode_path),
                preview_path=str(preview_path),
                brightness=self.brightness,
                contrast=self.contrast,
                cell_size_mm=self.cell_size_mm,
                tool_diameter_mm=self.tool_diameter_mm,
                dwell_s=self.dwell_s,
                pwm_threshold=self.pwm_threshold,
            )
            
            # Load preview image
            self.preview_image = Image.open(preview_path)
            self._display_preview_image()
            
            # Load G-code
            self.gcode_content = gcode_path.read_text()
            
            self._log(f"Generated {result['points']} engraving points")
            self.processed = True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate G-code: {e}")
            self._log(f"Error: {e}")
    
    def _save_gcode(self):
        """Save G-code to file."""
        if not self.gcode_content:
            messagebox.showwarning("Warning", "No G-code generated yet")
            return
        
        output_dir = filedialog.askdirectory(title="Select output directory")
        if not output_dir:
            return
        
        try:
            output_path = Path(output_dir) / "engraving.gcode"
            output_path.write_text(self.gcode_content, encoding="utf-8")
            messagebox.showinfo("Success", f"G-code saved to:\n{output_path}")
            self._log(f"G-code saved: {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save G-code: {e}")
            self._log(f"Error saving: {e}")
    
    def _send_to_grbl(self):
        """Send G-code to GRBL machine."""
        if not self.grbl or not self.grbl.connected:
            messagebox.showwarning("Warning", "Not connected to GRBL")
            return
        
        if not self.gcode_content:
            messagebox.showwarning("Warning", "No G-code generated yet")
            return
        
        if messagebox.askyesno("Confirm", "Send G-code to GRBL machine?"):
            # Send in background thread
            def send_thread():
                self._log("Sending G-code to GRBL...")
                success = self.grbl.send_gcode(
                    self.gcode_content,
                    callback=lambda msg: self._log(msg)
                )
                if success:
                    messagebox.showinfo("Success", "G-code sent successfully")
                else:
                    messagebox.showerror("Error", "Failed to send G-code")
            
            thread = threading.Thread(target=send_thread, daemon=True)
            thread.start()
    
    def _reset_zoom(self):
        """Reset zoom and pan."""
        self.sync_canvas.reset()
        self._display_original_image()
        self._display_preview_image()
        self._log("Zoom/Pan reset")


def main():
    root = Tk()
    app = HalftoneEngraverGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
