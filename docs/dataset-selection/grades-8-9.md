# Lớp 8–9

## Kết quả

Manifest ảnh: [grades-8-9.images.jsonl](grades-8-9.images.jsonl) hiện có **1.419 crop** từ sáu sách: **632 selected**, **25 needs_review** và **762 excluded**. Nguồn được đối chiếu theo `book.final.md` và `layout.final.json`.

| Sách | Selected | Needs review | Excluded | Tổng |
| --- | ---: | ---: | ---: | ---: |
| `grade_8_sgk_1` | 129 | 1 | 92 | 222 |
| `grade_8_sgk_2` | 167 | 1 | 75 | 243 |
| `grade_8_sgv` | 47 | 2 | 187 | 236 |
| `grade_9_sgk_1` | 105 | 7 | 40 | 152 |
| `grade_9_sgk_2` | 129 | 7 | 157 | 293 |
| `grade_9_sgv` | 55 | 7 | 211 | 273 |
| **Tổng** | **632** | **25** | **762** | **1.419** |

Ba crop layout-only đủ gọn để selected: một hình hai tam giác vuông đồng dạng ở SGK 8 tập 2 tr.102 (`G05`), hình trụ SGK 9 tập 2 tr.101 (`G15`) và hình cầu tr.106 (`G15`). Tám crop layout-only khác có diagram core nhưng nằm trong bảng SGV dài trộn nhiều hàng hướng dẫn/lời giải; chúng được giữ `needs_review` để tách vùng diagram trước khi dùng cho Reconstruct. 586 crop bảng còn lại không có diagram core trong ảnh.

| Trang; sách | Crop nguồn (relative to corpus) | Quyết định; nhãn |
| --- | --- | --- |
| 8 SGK2, tr.102 | `8/grade_8_sgk_2/images/a233b7e70dc9f7e1ce96c042bb04b0faaeec567b21944d2a53b260be495eaec6.jpg` | selected; G05 |
| 9 SGK2, tr.101 | `9/grade_9_sgk_2/images/6150b9c8c62aabfdae7234ae95c41862dece0b02423ef45c232f5716de845bdc.jpg` | selected; G15 |
| 9 SGK2, tr.106 | `9/grade_9_sgk_2/images/aad6d8829cb5022f2527c798c2ebf24a9bf24c36637880aa335bbe032a2422ab.jpg` | selected; G15 |
| 8 SGV, tr.89 | `8/grade_8_sgv/images/4f53d8fbe6f3153c27249677265ad6174645ba547101c49c6ad604125d8ff6ca.jpg` | needs_review; G07 |
| 8 SGV, tr.90 | `8/grade_8_sgv/images/6a5a74e568a76bc966746c7c834ba10ec45fd2bb7e19c350102e2f666be3c5b6.jpg` | needs_review; G07 |
| 9 SGV, tr.87 | `9/grade_9_sgv/images/a705682fac66174c88b0b1be4a02a84dc472b7bc4ac66213059b8445e8508662.jpg` | needs_review; G15 |
| 9 SGV, tr.96 | `9/grade_9_sgv/images/442ae12e0e4f3c684ffddc8eac7fde0d8c749385f2e115722568e9a684b5a041.jpg` | needs_review; G06 |
| 9 SGV, tr.97 | `9/grade_9_sgv/images/af8e4e64b7b796b8670e3622dfa845a16a85a859bc43900e2d3b94a27047a17f.jpg` | needs_review; G06 |
| 9 SGV, tr.118 | `9/grade_9_sgv/images/f469d1b20464a1c855c4dbd1dc181c35d4534224edf94731702cbdc687f285d4.jpg` | needs_review; G09 |
| 9 SGV, tr.258 | `9/grade_9_sgv/images/0ad512a4e601a772388a01f545529e89b59463112f0986dfecca419c455c68ae.jpg` | needs_review; G15 |
| 9 SGV, tr.259 | `9/grade_9_sgv/images/a6c1f407482688e58adeeef3dae2fa911867306857dcbbfc9704c41651240031.jpg` | needs_review; G15 |

Các crop bảng hướng dẫn có nhắc vẽ đồ thị/hàm số nhưng không chứa đồ thị được vẽ; bảng giá trị cũng không được gán A01. Không thấy bảng biến thiên/xét dấu, trục số, miền nghiệm hay miền tích phân trong 597 crop layout-only đã kiểm. Bảng kết quả thống kê, bảng dữ liệu, bảng ký hiệu phép quay không có sơ đồ hình học và các crop chữ/công thức thuần đều excluded. Mô hình hình học thực tế được giữ nếu diagram thể hiện quan hệ hình học; crop ảnh chụp cảnh/vật thể vẫn phải xét nguyên crop.

Selected 632 crop có 632 nhãn đơn: A01 41; A04 1; G01 4; G02 3; G03 5; G04 3; G05 140; G06 71; G07 106; G08 16; G09 36; G10 41; G11 35; G13 7; G14 23; G15 100. Các nhãn phản ánh diagram thực có trong crop; không thêm nhãn chỉ vì một primitive xuất hiện. Ảnh selected đã được copy vào `assets` theo manifest.

## Nội dung cho Generate/Edit

Nguyên văn từng đơn vị đã tuyển nằm trong [grade-8.problems.jsonl](grade-8.problems.jsonl) và [grade-9.problems.jsonl](grade-9.problems.jsonl). Chỉ tính các hàng `prepared`:

| Lớp | Ví dụ | Luyện tập | Bài tập | Tổng |
| --- | ---: | ---: | ---: | ---: |
| 8 | 43 | 32 | 143 | 218 |
| 9 | 60 | 33 | 175 | 268 |
| **Tổng** | **103** | **65** | **318** | **486** |

Còn 17 đơn vị lớp 8 và 7 đơn vị lớp 9 ở trạng thái `needs_review`, không nằm trong tổng trên. Mỗi đơn vị giữ nguyên văn, khoảng dòng nguồn, nhãn loại, ảnh liên quan và liên kết ngữ cảnh khi cần. Một bài nhiều tiểu ý vẫn tính là một đơn vị. Ảnh bảng thống kê/ảnh chụp có thể được loại khỏi tập Reconstruct mà không loại một bài có đủ dữ kiện hình học để biên soạn Generate.
