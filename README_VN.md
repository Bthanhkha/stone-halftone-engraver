# Stone Halftone Engraver

**Hệ thống khắc ảnh trên đá sử dụng phương pháp halftone (điểm ảnh) với động cơ rung PWM**

## 📋 Giới thiệu

Dự án này cho phép bạn:
- 📷 Import ảnh (JPG, PNG, BMP, v.v.)
- 🎚️ Điều chỉnh độ sáng, tương phản trên giao diện đồ họa
- 🎨 Tự động chuyển ảnh thành lưới điểm halftone (dot matrix)
- ⚙️ Tùy chỉnh kích thước ô điểm, đường kính đầu gõ
- 💾 Sinh file G-code tương thích GRBL
- 🔌 Điều khiển độ rung động cơ DC qua tần số PWM (M3 Sxxx)

## 🏗️ Kiến trúc hệ thống

```
stone-halftone-engraver/
├── run_gui.bat                # Chạy giao diện đồ họa (Windows)
├── run_cli.bat                # Chạy từ dòng lệnh (Windows)
├── requirements.txt           # Thư viện Python cần thiết
├── README_VN.md              # Hướng dẫn tiếng Việt
├── README.md                 # Documentation (English)
├── src/
│   ├── stone_halftone.py     # Logic xử lý ảnh → G-code
│   ├── halftone_gui.py       # Giao diện Tkinter
│   ├── grbl_exporter.py      # Export G-code theo định dạng riêng
│   └── __init__.py
├── sample/
│   └── test.png              # Ảnh mẫu để test
└── output/
    ├── *.nc                  # File G-code sinh ra
    └── *.png                 # Ảnh preview halftone
```

## ⚙️ Cài đặt

### Yêu cầu hệ thống
- Windows 7 / 10 / 11
- Python 3.10 hoặc cao hơn
- ít nhất 500MB dung lượng ổ cứng
- Kết nối internet (để tải thư viện lần đầu)

### Bước 1: Cài đặt Python

1. Tải Python từ https://www.python.org/downloads/
2. Chọn bản Python 3.12 LTS hoặc cao hơn
3. **Quan trọng**: Tích chọn "Add Python to PATH" khi cài đặt
4. Chọn "Install Now"

### Bước 2: Clone hoặc tải dự án

**Cách 1: Dùng Git**
```bash
git clone https://github.com/Bthanhkha/stone-halftone-engraver.git
cd stone-halftone-engraver
```

**Cách 2: Tải ZIP**
1. Vào https://github.com/Bthanhkha/stone-halftone-engraver
2. Nhấn "Code" → "Download ZIP"
3. Giải nén vào thư mục mong muốn

### Bước 3: Chạy lần đầu

Đơn giản nhất: **Nhấp đôi `run_gui.bat`**

Lần chạy đầu tiên sẽ:
- Tạo môi trường ảo Python
- Tải thư viện cần thiết (Pillow)
- Khởi động giao diện

## 🎯 Hướng dẫn sử dụng

### 🖥️ Chế độ GUI (Đề xuất cho người dùng)

**Bước 1**: Nhấp đôi `run_gui.bat`

**Bước 2**: Giao diện sẽ hiển thị 4 tab:

#### Tab 1: ⚙️ Cài đặt

1. **Chọn ảnh**
   - Nhấn nút "Mở file ảnh"
   - Chọn file ảnh (JPG, PNG, BMP, TIFF)
   - Ảnh sẽ hiển thị tại Tab "🖼️ Ảnh gốc"

2. **Điều chỉnh ảnh**
   - **Độ sáng** (0.2 - 2.5): 
     - 0.2 = rất tối
     - 1.0 = bình thường
     - 2.5 = rất sáng
   - **Độ tương phản** (0.2 - 3.0):
     - 0.2 = mờ
     - 1.0 = bình thường
     - 3.0 = rất sắc nét

3. **Tham số khắc**
   - **Kích thước ô điểm (mm)**: 1.0 - 10.0
     - Nhỏ (1-2mm): chi tiết cao, khắc lâu
     - Vừa (3-4mm): cân bằng ⭐ (khuyến nghị)
     - Lớn (5-10mm): khắc nhanh, chi tiết thấp
   
   - **Đường kính đầu gõ (mm)**: 0.5 - 4.0
     - Nên chọn = 1/2 kích thước ô điểm
     - VD: ô 3mm → đầu 1.5mm
   
   - **Thời gian chạm (s)**: 0.02 - 0.5
     - Ngắn (0.02-0.05): khắc nhẹ
     - Trung bình (0.08): ⭐ khuyến nghị
     - Dài (0.2-0.5): khắc sâu

4. **Đường dẫn file đầu ra**
   - Mặc định: `output/stone_toolpath.nc` (G-code)
   - Mặc định: `output/stone_preview.png` (hình xem trước)

5. **Nhấn "✓ TẠO G-CODE"** để xử lý

#### Tab 2: 🖼️ Ảnh gốc

- Hiển thị ảnh đã import
- Kích thước gốc: X × Y pixels
- Nhấn "🔄 Làm mới" để cập nhật nếu chọn ảnh mới

#### Tab 3: 🎨 Ảnh điểm

- Hiển thị ảnh sau khi chuyển thành halftone dot
- Các điểm tối = những vị trí rung mạnh (PWM cao)
- Các điểm sáng = những vị trí rung nhẹ (PWM thấp)
- Tự động cập nhật khi bạn thay đổi độ sáng, tương phản, kích thước ô

#### Tab 4: 📄 G-code

- Hiển thị nội dung file G-code sinh ra
- Nút "💾 Lưu G-code": lưu vào file mới
- Nút "📋 Copy": sao chép vào clipboard để dán vào trình gửi GRBL khác
- Thông tin: số điểm, đường dẫn file

### 💻 Chế độ CLI (Dòng lệnh)

**Chạy nhanh với ảnh mẫu**:
```bash
run_cli.bat
```

**Chạy với ảnh của bạn**:
```bash
python src\stone_halftone.py ^
    --input path\to\your\image.jpg ^
    --output output\my_toolpath.nc ^
    --preview output\my_preview.png ^
    --brightness 1.1 ^
    --contrast 1.5 ^
    --cell-size-mm 3.0 ^
    --tool-diameter-mm 1.2 ^
    --dwell-s 0.08
```

**Tham số dòng lệnh**:
- `--input`: đường dẫn ảnh đầu vào (bắt buộc)
- `--output`: đường dẫn G-code đầu ra (bắt buộc)
- `--preview`: đường dẫn ảnh halftone preview (bắt buộc)
- `--brightness`: độ sáng (0.2 - 2.5, mặc định 1.0)
- `--contrast`: độ tương phản (0.2 - 3.0, mặc định 1.0)
- `--cell-size-mm`: kích thước ô (1.0 - 10.0, mặc định 3.0)
- `--tool-diameter-mm`: đường kính đầu (0.5 - 4.0, mặc định 1.2)
- `--dwell-s`: thời gian chạm (0.02 - 0.5, mặc định 0.08)

## 📊 Định dạng G-code

### Format chuẩn GRBL

```gcode
G21 ; millimeters
G90 ; absolute positioning
G92 X0 Y0
G0 X10.000 Y20.000  ; move to position
M3 S200             ; vibrate at PWM 200 (intensity)
G4 P0.080           ; dwell 80ms
M5                  ; stop vibration
G0 X15.000 Y25.000  ; next position
M3 S80              ; vibrate at PWM 80
G4 P0.080
M5
G0 X0 Y0            ; return to origin
M5
M2                  ; end program
```

### Giải thích lệnh

| Lệnh | Ý nghĩa |
|------|----------|
| `G21` | Đơn vị mm |
| `G90` | Định vị tuyệt đối |
| `G92 X0 Y0` | Đặt gốc tọa độ |
| `G0 X Y` | Di chuyển nhanh đến (X, Y) |
| `M3 Sxxx` | Bật motor PWM với giá trị xxx (0-255) |
| `G4 Ps` | Dừng s giây (cho vibration tác động) |
| `M5` | Tắt motor |
| `M2` | Kết thúc chương trình |

### Format PWM tùy chỉnh cho Driver riêng

Nếu driver của bạn dùng format riêng (không phải GRBL), bạn có thể sử dụng module `grbl_exporter.py`:

```python
from src.grbl_exporter import export_pwm_driver

export_pwm_driver(
    points=[(x, y, r, pwm), ...],
    output_path="output/driver_format.txt",
    driver_type="modbus",  # hoặc "serial", "usb", v.v.
)
```

## 🔧 Kết nối với GRBL Controller

### Phần cứng cần
- Arduino Uno / Nano (chạy Firmware GRBL)
- CNC Shield v3 (tùy chọn, giúp kết nối dễ dàng)
- Stepper motor cho X, Y axis
- Động cơ DC + Module PWM điều khiển cho đầu gõ
- Nguồn 12V/24V tùy yêu cầu

### Phần mềm gửi G-code

**Cách 1**: Dùng giao diện GUI (đơn giản nhất)
1. Tạo G-code từ tab "📄 G-code"
2. Nhấn "📋 Copy" để copy nội dung
3. Mở Visualizer hoặc Sender GRBL (UGS, Candle, bCNC)
4. Dán G-code vào
5. Nhấn "Send" để gửi đến Arduino

**Cách 2**: Lưu file `.nc` rồi mở bằng:
- **UGS (Universal Gcode Sender)**: https://winder.github.io/ugs_website/
- **Candle**: https://github.com/Denvi/Candle
- **bCNC**: https://github.com/vlachoudis/bCNC

**Cách 3**: Upload trực tiếp từ Python
```python
import serial

# Kết nối Arduino
ser = serial.Serial('COM3', 115200, timeout=1)

# Đọc G-code
with open('output/stone_toolpath.nc', 'r') as f:
    gcode = f.read()

# Gửi từng dòng
for line in gcode.split('\n'):
    if line.strip() and not line.startswith(';'):
        ser.write((line + '\n').encode())
        response = ser.readline().decode()
        print(f"> {line}")
        print(f"< {response}")

ser.close()
```

## 🎨 Lựa chọn tham số tối ưu

### Cho chi tiết cao (ảnh có nhiều gradient)
```
Độ sáng: 1.0
Độ tương phản: 1.5 - 2.0
Kích thước ô: 2.0 - 3.0 mm
Đầu gõ: 1.0 - 1.5 mm
Thời gian chạm: 0.06 - 0.10 s
```

### Cho tốc độ khắc nhanh
```
Độ sáng: 1.1
Độ tương phản: 1.2 - 1.4
Kích thước ô: 4.0 - 5.0 mm
Đầu gõ: 2.0 - 2.5 mm
Thời gian chạm: 0.04 - 0.06 s
```

### Cho độ sâu lớn (khắc sâu)
```
Độ sáng: 0.9 - 1.0
Độ tương phản: 1.8 - 2.5
Kích thước ô: 2.5 - 3.5 mm
Đầu gõ: 1.0 - 1.5 mm
Thời gian chạm: 0.12 - 0.25 s
```

## 📝 Lưu ý quan trọng

### Trước khi khắc bản chính
1. **Luôn test trên mẫu nhỏ** trước
2. Chuẩn bị dụng cụ
   - Đá hoặc vật liệu khắc
   - Kính bảo vệ mắt
   - Khẩu trang (bụi đá)
3. Kiểm tra:
   - Cơ chế XY chạy mượt
   - Động cơ rung không bị cắt điện
   - Đầu gõ không bị rơi

### Xử sự cố

| Vấn đề | Nguyên nhân | Giải pháp |
|-------|------------|----------|
| Ảnh quá tối/sáng | Độ sáng sai | Điều chỉnh slider "Độ sáng" |
| Điểm không đều | Độ tương phản thấp | Tăng "Độ tương phản" |
| Khắc quá nhanh/chậm | Thời gian chạm | Điều chỉnh "Thời gian chạm" |
| G-code không chạy | COM port sai | Kiểm tra Device Manager |
| Động cơ rung quá yếu | PWM quá thấp | Tăng tối đa độ tương phản |

## 📚 Tham khảo thêm

- GRBL Documentation: https://github.com/gnea/grbl/wiki
- G-code Reference: https://en.wikibooks.org/wiki/CNC_Programming
- Halftone Dithering: https://en.wikipedia.org/wiki/Halftone

## 📄 License

MIT License - Tự do sử dụng, sửa đổi, phân phối

## 🤝 Đóng góp

Nếu bạn có ý kiến, lỗi cần báo, hoặc muốn cải thiện:
1. Fork dự án
2. Tạo branch mới: `git checkout -b feature/your-feature`
3. Commit thay đổi: `git commit -m 'Add some feature'`
4. Push: `git push origin feature/your-feature`
5. Tạo Pull Request

## 👨‍💻 Tác giả

**Bthanhkha** - Tạo dự án Stone Halftone Engraver

## 📞 Liên hệ

Nếu có câu hỏi, vui lòng mở Issue trên GitHub hoặc liên hệ qua email.

---

**Chúc bạn khắc thành công!** 🎉
