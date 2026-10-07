# Phạm vi và tuyển dữ liệu TikZ

Tài liệu này ghi quy tắc tuyển mẫu và vị trí dữ liệu để chuẩn bị dataset. [Đề cương nghiên cứu](<K-12 Mathematical Diagrams with TikZ.md>) chỉ trình bày phạm vi, thiết kế và kết quả tổng hợp.

## Phạm vi tuyển

Đợt chuẩn bị dữ liệu này chỉ xử lý **lớp 6–12**. Taxonomy hình học giữ nguyên [geometry-k12-vn.md](geometry-k12-vn.md). Mã `G01–G17` tương ứng với 17 loại Hình học; `A01–A06` là 6 loại Đại số. Tổng cộng có **23 loại hình**, không gộp Đại số vào 17 loại Hình học.

| Mã | Loại hình |
| --- | --- |
| G01 | Điểm, đường thẳng, đoạn thẳng, đường cong |
| G02 | Tia, góc và đo góc |
| G03 | Tam giác và các đường đặc biệt |
| G04 | Tam giác bằng nhau |
| G05 | Tam giác đồng dạng và Thalès |
| G06 | Hệ thức lượng trong tam giác vuông và mô hình đo đạc |
| G07 | Tứ giác đặc biệt |
| G08 | Đa giác đều |
| G09 | Đường tròn và dựng hình |
| G10 | Góc trong đường tròn và tứ giác nội tiếp |
| G11 | Tiếp tuyến và vị trí tương đối đường thẳng–đường tròn |
| G12 | Vectơ và các phép toán |
| G13 | Hình học tọa độ Oxy, đường thẳng, đường tròn, conic |
| G14 | Phép biến hình phẳng |
| G15 | Khối đa diện và khối tròn xoay |
| G16 | Quan hệ, thiết diện, góc và khoảng cách trong không gian |
| G17 | Hệ tọa độ và đối tượng Oxyz |
| A01 | Đồ thị hàm số |
| A02 | Bảng biến thiên và bảng xét dấu |
| A03 | Đường tròn lượng giác |
| A04 | Khoảng, điểm và dấu trên trục số |
| A05 | Miền nghiệm bất phương trình |
| A06 | Miền tô tích phân |

Một ảnh có thể mang nhiều mã. Đồ thị hàm số theo công thức và biểu đồ thống kê theo số liệu được phân biệt bằng nội dung bài.

**Ngoài tập chính:** biểu đồ thống kê chuẩn, bảng dữ liệu, công thức rời, biểu tượng dàn trang và tranh minh họa thuần bối cảnh. Venn, cây xác suất/tổ hợp, đồ thị rời rạc và bản vẽ kỹ thuật đầy đủ giữ ở nhóm mở rộng khảo sát, chưa đưa vào danh sách ảnh tuyển.

Mô hình thực tế thuộc core khi các đối tượng và quan hệ hình học là nội dung cần tái dựng. Ảnh chụp chiếm phần chính, dù có thêm mũi tên/số đo, được để chờ rà soát cho Reconstruct nguyên crop. Ảnh pha cảnh vật hoặc giao diện phần mềm cần xét chính crop đó; không coi phần hình toán tưởng tượng sau khi cắt bỏ các thành phần khác là một ảnh nguồn đã sẵn sàng.

## Danh sách để chuẩn bị dataset

Danh sách tập trung: [dataset-selection.json](dataset-selection.json). Mỗi ảnh đã tuyển có mã loại, các nguồn sách/dòng/trang, SHA-256 và đường dẫn `asset_path` trong repo. Các ảnh có nội dung byte trùng nhau được gộp, vẫn giữ mọi nguồn.

**Trạng thái: đã copy đủ 2.204 ảnh selected vào `assets`; SHA-256 khớp manifest.**

Các hồ sơ rà soát theo khối:

- [Lớp 6–7](dataset-selection/grades-6-7.md): danh sách ảnh và nguyên văn ví dụ/luyện tập/bài tập.
- [Lớp 8–9](dataset-selection/grades-8-9.md): danh sách ảnh và nguyên văn ví dụ/luyện tập/bài tập.
- [Lớp 10–11](dataset-selection/grades-10-11.md): danh sách ảnh.
- [Lớp 12](dataset-selection/grade-12.md): danh sách ảnh.

Đơn vị nội dung là **một ví dụ, một luyện tập hoặc một bài tập hoàn chỉnh**, có thể gồm nhiều tiểu ý. Không dùng số block ToC hay số tiêu đề làm số bài. `source_text` giữ nguyên đoạn nguồn, kể cả lời giải nếu có; đây là hồ sơ để biên soạn input và target, chưa phải cặp huấn luyện đã gán TikZ.

Các bài phụ thuộc “hình bên” giữ đường dẫn hình liên quan. Bài không có ảnh sẵn vẫn có thể phục vụ Generate nếu có đủ nội dung để xác lập diagram.

## Kết quả tuyển

Danh sách tổng hợp có **2.204 ảnh** và **851 đơn vị nội dung**: 165 ví dụ, 116 luyện tập, 570 bài tập. Có ảnh cho đủ 17 loại Hình học và 6 loại Đại số nêu trên.

285 crop và 34 đơn vị nội dung đang chờ rà soát nằm ngoài các tổng đã tuyển.

Ảnh selected được tổng hợp từ các file nguồn còn tồn tại và có tham chiếu trong Markdown hoặc layout. Hồ sơ ví dụ/luyện tập/bài tập giữ nguyên trong các manifest riêng.

## Double-check nhãn

Ba trường hợp đã đối chiếu với crop và nội dung bài: ảnh sản phẩm mây tre minh họa vị trí các đường tròn được gán G09; hình đo gang tay bị loại khỏi tập diagram; đồ thị (y=C(x)/x) ở lớp 12 được gán A01.

## Nguồn và kiểm tra

Corpus local: `C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums`.

- **Lớp 6–9:** dùng `book.final.md`, `layout.final.json`, `toc.final.json` theo [README](C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums/README.md) và [delivery.json](C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums/delivery.json).
- **Lớp 10–12:** dùng `full.md`, `layout.json` và thư mục `images` đi cùng.
- Không đọc hoặc tuyển dữ liệu lớp 1–5 trong đợt này.

Danh sách ảnh được chọn theo nội dung và kiểm tra crop thực tế. Các quyết định `selected / excluded / needs_review` nằm trong manifest từng khối. Hồ sơ bài dùng `prepared / needs_review`; chỉ `prepared` được cộng vào số nội dung đã chuẩn bị.

Chạy lại phép kiểm chứng và đối chiếu danh sách tổng hợp:

```powershell
.\.venv\Scripts\python.exe tools/prepare_dataset_selection.py --corpus C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums
```

Công cụ kiểm tra đường dẫn, đúng artifact theo lớp, dòng chứa ảnh hoặc image_path trên trang layout được trích dẫn, nguyên văn/range nội dung bài, nhãn loại, trạng thái đã xem ảnh, hash và số lượng. Chạy với `--write` để tổng hợp lại JSON sau khi cập nhật các manifest. Công cụ không copy ảnh và không sửa corpus.

## Copy ảnh và xuất hai figure

Code: [tools/dataset_assets.py](../tools/dataset_assets.py). Chạy từ thư mục repo:

```powershell
.\.venv\Scripts\python.exe tools/dataset_assets.py copy
.\.venv\Scripts\python.exe tools/dataset_assets.py figures
```

Sau khi xuất lại ToC/Markdown từ layout trong corpus, chạy `python tools/refresh_dataset_selection.py --corpus PATH --write` để cập nhật neo ảnh, neo bài toán và dựng lại `dataset-selection.json`.

Lệnh `copy` lấy đúng các ảnh `selected` trong `dataset-selection.json`, dùng tên và đường dẫn `asset_path`, kiểm SHA-256 trước/sau copy và bỏ qua file đã có đúng nội dung. File trùng tên nhưng khác nội dung sẽ báo lỗi. Có thể chỉ định `--corpus PATH` khi corpus nằm ở máy khác.

Lệnh `figures` đọc ảnh trong `assets` và xuất đúng hai PNG:

- [dataset-coverage-overview.png](dataset-coverage-overview.png): phạm vi loại hình trong bộ dữ liệu Toán lớp 6–12.
- [dataset-type-counts.png](dataset-type-counts.png): phân bố số ảnh theo từng loại hình.

Độ phân giải mặc định 200 DPI; thêm `--dpi 300` nếu cần. [dataset-coverage-sources.json](dataset-coverage-sources.json) ghi nguồn của 23 ảnh minh họa. Lệnh `python tools/dataset_assets.py check` chạy kiểm tra copy, chạy lại, hash, xung đột file và giới hạn đường dẫn/lớp.

## Cấu trúc mẫu sau gán nhãn

| Task | Input | Target |
| --- | --- | --- |
| Generate | `instruction`: đề bài/yêu cầu vẽ đã biên soạn từ ví dụ, luyện tập hoặc bài tập | `target_tikz` |
| Edit | `current_tikz` + `instruction` | `target_tikz` sau sửa |
| Reconstruct | `image` + `instruction` | `target_tikz` |

Thuộc tính phân loại gồm `task`, `grade`, `diagram_types`, `source_kind` (ví dụ/luyện tập/bài tập khi có), `book_role` (SGK/SGV/chuyên đề). Mã diagram tra về category/subcategory trong taxonomy. Nguồn và liên kết giữa các biến thể được giữ ở metadata, không thêm vào input Edit.

Target TikZ cần được biên dịch và đối chiếu trước khi đưa vào tập đánh giá. Các bản cùng bài/hình, kể cả bản trong SGV và mẫu dẫn xuất, được nhóm trước khi chia train/validation/test.

## Tài liệu khảo sát cũ

[dataset-source-audit.json](dataset-source-audit.json) lưu kiểm kê nguồn và 33 minh chứng của lượt khảo sát trước, không phải thống kê dataset đã tuyển. Board `dataset-coverage-overview.png` và danh sách nguồn đi kèm đã được thay bằng 23 mẫu từ tập selected hiện tại.

Đồng bộ manifest với ảnh còn trong corpus và dựng lại neo nguồn bằng code:

```powershell
.\.venv\Scripts\python.exe tools/refresh_dataset_selection.py --corpus C:/Users/Onn/Documents/Git/curriculum_grounding/curriculums --write
```

Lệnh này bỏ dòng ảnh không còn file hoặc không còn tham chiếu, rồi cập nhật thống kê ảnh trong manifest tổng hợp.
