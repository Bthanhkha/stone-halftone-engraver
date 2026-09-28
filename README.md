# Stone Halftone Engraver

Một hệ thống khắc ảnh trên đá theo phương pháp halftone/điểm ảnh, sử dụng GRBL làm controller trung tâm.

Mục tiêu của phiên bản đầu tiên:
- Đọc một ảnh đầu vào và điều chỉnh độ sáng/độ tương phản.
- Chuyển ảnh thành lưới điểm (dot matrix) phù hợp với đầu gõ và kích thước đá.
- Sinh ra file G-code cho máy khắc CNC/GRBL.
- Cho phép người dùng cài đặt kích thước đầu gõ, kích thước ô điểm, chiều sâu khắc tối đa.

## Tính năng chính
- Điều chỉnh brightness / contrast theo thời gian thực.
- Tạo mảng điểm halftone theo mức xám.
- Tự động tính toán bán kính và độ sâu điểm dựa trên độ đậm của ảnh.
- Xuất preview dạng ảnh và file G-code.
- Dễ tích hợp với GRBL `/dev/ttyUSB0`, COM port, hoặc chạy trên máy tính riêng.

## Kiến trúc đề xuất
- `src/stone_halftone.py`: logic xử lý ảnh, tính toán halftone và sinh G-code.
- `src/halftone_gui.py`: giao diện người dùng đơn giản bằng Tkinter để điều chỉnh các tham số.
- `requirements.txt`: phụ thuộc Python.

## Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy giao diện

```bash
python src/halftone_gui.py
```

## Chạy ở dạng dòng lệnh

```bash
python src/stone_halftone.py \
  --input assets/sample.jpg \
  --output output/stone_toolpath.nc \
  --preview output/stone_preview.png \
  --cell-size-mm 3.0 \
  --tool-diameter-mm 1.2 \
  --max-depth-mm 2.5 \
  --brightness 1.1 \
  --contrast 1.5
```

## Nguyên tắc khắc bằng điểm ảnh

- Ảnh sáng => các điểm nhỏ, mỏng, nông.
- Ảnh tối => các điểm lớn, dày, sâu.
- Độ dày/thưa của điểm được kiểm soát bằng `cell_size_mm` và `tool_diameter_mm`.
- Độ sâu điểm được quy đổi theo mức xám của ảnh.

## Lưu ý cho vật liệu đá
- Nên thử với mẫu thô trước khi khắc bản chính.
- Chọn đầu gõ nhỏ hơn hoặc bằng 1/2 kích thước ô điểm để tránh chồng lấn.
- Dùng tốc độ lên xuống Z phù hợp với độ cứng của đá.
- Nên thực hiện test độ sâu trên mảnh đá nhỏ trước.

## Ứng dụng tiếp theo
- Tự động tạo offset theo hướng cắt để tránh lệch dao.
- Mô phỏng preview 3D.
- Tích hợp giữa Raspberry Pi / CNC controller / GRBL.
- Tạo mode khắc “điểm” với nhiều độ sâu khác nhau theo vùng ảnh.

## Ghi chú kỹ thuật

Dự án này đang ở giai đoạn MVP, tập trung vào:
- điều chỉnh ảnh,
- chuyển đổi sang halftone,
- sinh G-code hoàn chỉnh cho GRBL.
