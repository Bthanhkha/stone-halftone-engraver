from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageEnhance


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def adjust_image(input_path: str, brightness: float = 1.0, contrast: float = 1.0) -> Image.Image:
    """Load and adjust image (brightness, contrast)."""
    img = Image.open(input_path).convert("L")
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    return img


def build_halftone_points(
    image: Image.Image,
    cell_size_mm: float,
    tool_diameter_mm: float,
    origin_x_mm: float = 0.0,
    origin_y_mm: float = 0.0,
    pwm_threshold: int = 20,
) -> List[Tuple[float, float, float, int]]:
    """
    Generate halftone points from image.
    
    Each grid cell produces ONE dot with:
    - Position: center of cell
    - Size: based on darkness level (dot_ratio)
    - PWM: controls vibration intensity (0-255)
    
    Returns list of (x_mm, y_mm, radius_mm, pwm_value).
    """
    width_px, height_px = image.size
    cell_px = max(1, int(round(cell_size_mm)))
    points: List[Tuple[float, float, float, int]] = []

    for y in range(0, height_px, cell_px):
        for x in range(0, width_px, cell_px):
            # Get cell
            cell = image.crop((x, y, min(x + cell_px, width_px), min(y + cell_px, height_px)))
            values = list(cell.getdata())
            if not values:
                continue

            # Calculate mean brightness in cell
            mean_value = sum(values) / len(values)
            
            # Convert brightness to darkness (0=bright, 1=dark)
            darkness = 1.0 - (mean_value / 255.0)
            dot_ratio = clamp(darkness, 0.0, 1.0)

            # Calculate PWM value (0-255)
            pwm_value = int(round(255.0 * dot_ratio))
            
            # Skip if PWM too low (no engraving)
            if pwm_value < pwm_threshold:
                continue

            # Calculate dot radius based on darkness
            cell_half = cell_size_mm / 2.0
            safe_tool_radius = max(0.1, tool_diameter_mm / 2.0)
            max_radius = max(0.0, cell_half - safe_tool_radius)
            radius_mm = max_radius * dot_ratio

            # Calculate dot center position
            center_x = origin_x_mm + (x + cell_px / 2.0)
            center_y = origin_y_mm + (y + cell_px / 2.0)
            
            points.append((center_x, center_y, radius_mm, pwm_value))

    return points


def generate_preview_image(
    image: Image.Image,
    cell_size_mm: float,
    tool_diameter_mm: float,
    output_path: str | None = None,
    pwm_threshold: int = 20,
) -> Image.Image:
    """Generate preview image showing halftone dots."""
    width_px, height_px = image.size
    preview = Image.new("L", (width_px, height_px), 255)
    draw = ImageDraw.Draw(preview)

    cell_px = max(1, int(round(cell_size_mm)))
    points = build_halftone_points(
        image, 
        cell_size_mm, 
        tool_diameter_mm,
        pwm_threshold=pwm_threshold
    )
    
    for x_mm, y_mm, radius_mm, pwm_value in points:
        if radius_mm <= 0.05:
            continue
        
        # Convert mm to pixels
        x_px = int(x_mm)
        y_px = int(y_mm)
        r_px = max(1, int(round(radius_mm * (cell_px / max(1.0, cell_size_mm)))))
        
        # Draw dot with darkness based on PWM
        box = [x_px - r_px, y_px - r_px, x_px + r_px, y_px + r_px]
        fill = int(clamp(255.0 - (pwm_value / 255.0) * 255.0, 0, 255))
        draw.ellipse(box, fill=fill)

    if output_path:
        preview.save(output_path)
    return preview


def generate_gcode(
    points: Iterable[Tuple[float, float, float, int]],
    output_path: str | None = None,
    dwell_s: float = 0.08,
) -> str:
    """
    Generate G-code without Z-axis.
    
    The dot depth is encoded by PWM vibration intensity:
    - M3 Sxxx: xxx = PWM value (0-255)
    - G4 Ps: dwell time s (seconds)
    - Higher PWM = stronger vibration = deeper engraving
    
    Line format:
      G0 X Y       ; move to position
      M3 Sxxx      ; set vibration intensity (PWM)
      G4 Ps        ; vibrate for s seconds
      M5           ; stop vibration
    """
    lines: List[str] = [
        "; Stone Halftone Engraver - PWM Vibration Motor",
        "; No Z-axis: depth encoded by PWM intensity",
        ";",
        "G21 ; millimeters",
        "G90 ; absolute positioning",
        "G92 X0 Y0 ; set origin",
    ]

    point_count = 0
    for x_mm, y_mm, radius_mm, pwm_value in points:
        if radius_mm <= 0.05:
            continue
        
        point_count += 1
        lines.append(f"; Point {point_count} - PWM {pwm_value}")
        lines.append(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
        lines.append(f"M3 S{pwm_value}")
        lines.append(f"G4 P{dwell_s:.3f}")
        lines.append("M5")

    lines.extend([
        "; End sequence",
        "G0 X0 Y0",
        "M5",
        "M2 ; end program",
    ])

    gcode = "\n".join(lines) + "\n"
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(gcode, encoding="utf-8")
    return gcode


def process_image(
    input_path: str,
    output_gcode: str,
    preview_path: str,
    brightness: float = 1.0,
    contrast: float = 1.0,
    cell_size_mm: float = 3.0,
    tool_diameter_mm: float = 1.2,
    dwell_s: float = 0.08,
    pwm_threshold: int = 20,
) -> dict:
    """
    Process image: adjust -> generate halftone points -> create G-code & preview.
    
    Args:
        input_path: Input image file path
        output_gcode: Output G-code file path
        preview_path: Output preview image path
        brightness: Brightness adjustment (0.2-2.5)
        contrast: Contrast adjustment (0.2-3.0)
        cell_size_mm: Halftone cell size in mm
        tool_diameter_mm: Tool diameter in mm
        dwell_s: Vibration dwell time in seconds
        pwm_threshold: Minimum PWM to create a dot (0-255)
    
    Returns:
        Dictionary with processing results
    """
    # Adjust image
    adjusted = adjust_image(input_path, brightness=brightness, contrast=contrast)
    
    # Generate halftone points
    points = build_halftone_points(
        adjusted,
        cell_size_mm=cell_size_mm,
        tool_diameter_mm=tool_diameter_mm,
        pwm_threshold=pwm_threshold,
    )
    
    # Generate G-code
    generate_gcode(points, output_path=output_gcode, dwell_s=dwell_s)
    
    # Generate preview
    generate_preview_image(
        adjusted,
        cell_size_mm,
        tool_diameter_mm,
        output_path=preview_path,
        pwm_threshold=pwm_threshold,
    )
    
    return {
        "points": len(points),
        "preview": preview_path,
        "gcode": output_gcode,
        "brightness": brightness,
        "contrast": contrast,
        "cell_size_mm": cell_size_mm,
        "tool_diameter_mm": tool_diameter_mm,
        "dwell_s": dwell_s,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate halftone dot-toolpath for PWM vibration engraving.")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output G-code path (.nc or .gcode)")
    parser.add_argument("--preview", required=True, help="Output preview image path")
    parser.add_argument("--brightness", type=float, default=1.0, help="Brightness adjustment factor")
    parser.add_argument("--contrast", type=float, default=1.0, help="Contrast adjustment factor")
    parser.add_argument("--cell-size-mm", type=float, default=3.0, help="Halftone cell size in mm")
    parser.add_argument("--tool-diameter-mm", type=float, default=1.2, help="Tool diameter in mm")
    parser.add_argument("--dwell-s", type=float, default=0.08, help="Vibration dwell time in seconds")
    parser.add_argument("--pwm-threshold", type=int, default=20, help="Minimum PWM value to create dot")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = process_image(
        input_path=args.input,
        output_gcode=args.output,
        preview_path=args.preview,
        brightness=args.brightness,
        contrast=args.contrast,
        cell_size_mm=args.cell_size_mm,
        tool_diameter_mm=args.tool_diameter_mm,
        dwell_s=args.dwell_s,
        pwm_threshold=args.pwm_threshold,
    )
    print(f"Generated {result['points']} engraving points")
    print(f"G-code: {result['gcode']}")
    print(f"Preview: {result['preview']}")
