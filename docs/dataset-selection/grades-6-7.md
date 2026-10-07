# Lớp 6–7

## Kết quả

Manifest ảnh: [grades-6-7.images.jsonl](grades-6-7.images.jsonl) hiện có **1.777 crop** từ sáu sách: **608 selected**, **157 needs_review** và **1.012 excluded**.

| Sách | Selected | Needs review | Excluded |
| --- | ---: | ---: | ---: |
| grade_6_sgk_1 | 191 | 52 | 138 |
| grade_6_sgk_2 | 93 | 20 | 158 |
| grade_6_sgv | 23 | 9 | 198 |
| grade_7_sgk_1 | 179 | 46 | 162 |
| grade_7_sgk_2 | 96 | 28 | 90 |
| grade_7_sgv | 26 | 2 | 266 |
| **Tổng** | **608** | **157** | **1.012** |

Selected có **622 nhãn loại hình**: A04 30; G01 44; G02 115; G03 160; G04 20; G07 76; G08 12; G09 4; G14 106; G15 55. Nhãn được gán theo từng crop, không lấy toàn bộ loại hình của chương gán cho mọi ảnh.

Biểu đồ thống kê và bảng dữ liệu không được tính vào core. Đã đối chiếu các ca biểu đồ cột SGK 6 tập 2 tr. 78, cột kép tr. 83, quạt tròn SGK 7 tập 1 tr. 94 và biểu đồ đường tr. 102. Hai crop mang loại chart nhưng là sơ đồ hình học (miền chữ nhật có kích thước và hình khai triển khối) được giữ lần lượt với G07 và G15.

## Kết luận

Tập selected lớp 6–7 gồm các diagram có cấu trúc hình học, phép đối xứng, khối 3D và trục số phù hợp tái dựng bằng TikZ. Biểu đồ thống kê, bảng dữ liệu, ảnh trang trí/giao diện bị loại; các crop xác suất, mô hình cân và ảnh bối cảnh pha quan hệ toán học được giữ needs review khi chưa khớp taxonomy core. Ảnh selected đã được copy vào `assets` theo danh sách đã duyệt.

## Ghi chú

Lượt kiểm trước đã xem 42 contact sheet ảnh Markdown và 17 sheet layout-only. Đợt coverage bổ sung xem 25 contact sheet cho 1.172 crop layout và 3 sheet phóng to. Shortlist theo ngữ cảnh nội dung/tập trang: SGK 6 tập 1 tr. 60–111; SGK 6 tập 2 tr. 44–73; SGV 6 tr. 74–132 và 171–193; SGK 7 tập 1 tr. 6–15 và 28–88; SGK 7 tập 2 tr. 59–103; SGV 7 tr. 32–112, 127–131, 205–252 và 259–263.

## Nội dung cho Generate/Edit

[grades-6-7.problems.jsonl](grades-6-7.problems.jsonl) giữ nguyên văn từng đơn vị đã tuyển. Chỉ các hàng `prepared` được tính:

| Lớp | Ví dụ | Luyện tập | Bài tập | Tổng |
| --- | ---: | ---: | ---: | ---: |
| 6 | 13 | 18 | 102 | 133 |
| 7 | 49 | 33 | 150 | 232 |
| **Tổng** | **62** | **51** | **252** | **365** |

Còn 10 đơn vị cần rà soát, không tính trong tổng trên. Mỗi đơn vị có range và nguyên văn nguồn, mã loại diagram và ảnh liên quan; bài nhiều tiểu ý được tính một lần. Không lấy mục lục, tiêu đề bài học hoặc hoạt động làm một ví dụ/luyện tập/bài tập.
