#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stone Halftone Engraver - Windows Test Script
Tests the complete pipeline on Windows with sample image
"""

from pathlib import Path
import subprocess
import sys
import os


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_success(msg: str):
    """Print success message."""
    print(f"\n✓ {msg}")


def print_error(msg: str):
    """Print error message."""
    print(f"\n✗ {msg}")
    sys.exit(1)


def create_sample_image(output_path: Path):
    """Create a sample test image if it doesn't exist."""
    if output_path.exists():
        print_success(f"Sample image already exists: {output_path}")
        return

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print_error(
            "Pillow not installed. Install with: pip install Pillow"
        )

    print("Creating sample image...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a test image with patterns
    img = Image.new("L", (400, 400), 255)
    draw = ImageDraw.Draw(img)

    # Draw grid pattern
    for i in range(0, 400, 20):
        draw.line((i, 0, i, 400), fill=150, width=2)
        draw.line((0, i, 400, i), fill=150, width=2)

    # Draw circles (dark)
    for y in range(80, 320, 40):
        for x in range(80, 320, 40):
            draw.ellipse((x, y, x + 20, y + 20), fill=40)

    # Draw rectangle
    draw.rectangle((50, 50, 150, 150), outline=100, width=3)

    # Draw text
    try:
        draw.text((160, 360), "Test", fill=0)
    except Exception:
        pass  # Font might not be available

    img.save(output_path)
    print_success(f"Sample image created: {output_path}")


def check_python():
    """Check Python version."""
    print_header("Python Environment")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")

    if sys.version_info < (3, 10):
        print_error("Python 3.10+ required")

    print_success("Python version OK")


def check_dependencies():
    """Check and install dependencies."""
    print_header("Dependencies")

    try:
        import PIL
        print_success(f"Pillow {PIL.__version__} installed")
    except ImportError:
        print("Installing Pillow...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        print_success("Pillow installed")


def test_image_processing(root: Path):
    """Test image processing pipeline."""
    print_header("Image Processing Test")

    sys.path.insert(0, str(root / "src"))

    try:
        from stone_halftone import (
            adjust_image,
            build_halftone_points,
            generate_gcode,
            generate_preview_image,
        )
    except ImportError as e:
        print_error(f"Failed to import stone_halftone: {e}")

    img_path = root / "sample" / "test.png"
    output_dir = root / "output"
    output_dir.mkdir(exist_ok=True)

    # Test 1: Image adjustment
    print("\n1. Adjusting image (brightness=1.1, contrast=1.4)...")
    adjusted = adjust_image(str(img_path), brightness=1.1, contrast=1.4)
    print_success(f"Image size: {adjusted.size}")

    # Test 2: Build halftone points
    print("\n2. Building halftone points (cell=3mm, tool=1.2mm)...")
    points = build_halftone_points(adjusted, cell_size_mm=3.0, tool_diameter_mm=1.2)
    print_success(f"Generated {len(points)} engraving points")

    # Test 3: Generate preview
    print("\n3. Generating preview image...")
    preview = generate_preview_image(adjusted, cell_size_mm=3.0, tool_diameter_mm=1.2)
    preview_path = output_dir / "test_preview.png"
    preview.save(preview_path)
    print_success(f"Preview saved: {preview_path}")

    # Test 4: Generate G-code
    print("\n4. Generating G-code (dwell=0.08s)...")
    gcode = generate_gcode(points, output_path=None, dwell_s=0.08)
    gcode_path = output_dir / "test.nc"
    gcode_path.write_text(gcode, encoding="utf-8")
    print_success(f"G-code saved: {gcode_path}")

    # Show G-code snippet
    lines = gcode.split("\n")
    print(f"\n  G-code preview (first 10 lines):")
    for line in lines[:10]:
        if line.strip():
            print(f"  > {line}")

    return True


def test_exporters(root: Path):
    """Test multiple export formats."""
    print_header("Export Formats Test")

    sys.path.insert(0, str(root / "src"))

    try:
        from stone_halftone import adjust_image, build_halftone_points
        from grbl_exporter import export_gcode
    except ImportError as e:
        print_error(f"Failed to import modules: {e}")

    img_path = root / "sample" / "test.png"
    output_dir = root / "output"

    adjusted = adjust_image(str(img_path), brightness=1.1, contrast=1.4)
    points = build_halftone_points(adjusted, cell_size_mm=3.0, tool_diameter_mm=1.2)

    formats = ["grbl", "csv", "json", "matlab"]
    extensions = {
        "grbl": ".nc",
        "csv": ".csv",
        "json": ".json",
        "matlab": ".m",
    }

    for fmt in formats:
        out_path = output_dir / f"test_{fmt}{extensions[fmt]}"
        print(f"\nExporting to {fmt.upper()}: {out_path.name}")
        try:
            export_gcode(points, str(out_path), format_type=fmt)
            file_size = out_path.stat().st_size
            print_success(f"Exported {file_size} bytes")
        except Exception as e:
            print_error(f"Failed to export {fmt}: {e}")


def show_results(root: Path):
    """Display results summary."""
    print_header("Results Summary")

    output_dir = root / "output"
    if not output_dir.exists():
        print("No output files generated")
        return

    files = sorted(output_dir.glob("*"))
    if not files:
        print("No output files found")
        return

    print(f"\nGenerated {len(files)} file(s):\n")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  • {f.name:<30} ({size_kb:>6.1f} KB)")

    print(f"\nOutput directory: {output_dir.resolve()}")


def main():
    """Main test sequence."""
    root = Path(__file__).resolve().parent

    print("\n" + "#" * 60)
    print("#  Stone Halftone Engraver - Windows Test Suite")
    print("#" * 60)

    try:
        check_python()
        check_dependencies()
        create_sample_image(root / "sample" / "test.png")
        test_image_processing(root)
        test_exporters(root)
        show_results(root)

        print_header("All Tests Passed!")
        print("\n✓ Pipeline working correctly on Windows")
        print("✓ You can now use run_gui.bat to launch the GUI")
        print("\nPress Enter to close this window...")
        input()

    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
