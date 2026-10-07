# Sáu bài f9062486: instruction và target theo bước dựng

22 cặp `instruction`–`target_tikz` được biên soạn từ **bai-01–bai-06**. Mỗi hàng là một Generate độc lập: instruction tự đủ, bắt đầu từ dữ kiện chính rồi tích lũy những phép dựng cần xuất hiện. Không tạo thêm bước khi câu hỏi mới không thay đổi hình.

Dữ liệu đầy đủ, gồm TikZ trực tiếp và rubric riêng: [JSONL](C:/Users/Onn/Documents/Git/problem_tikz/docs/dataset-selection/problem-tikz-f9062486-stages.jsonl). Đề gốc và mẫu nguồn vẫn ở [fixtures.json](C:/Users/Onn/Documents/Git/problem_tikz/problem-tikz-f9062486/fixtures.json); chúng là provenance, không phải input của drawing worker.

Worker chỉ nhận `instruction`. `target_tikz`, `evaluation_rubric`, `scope_decisions` và provenance nằm ở phần chuẩn bị/evaluator. `predecessor_id` mô tả thứ tự tích lũy; không cần đưa hàng trước vào worker.

| Bài | Cặp | Phạm vi tích lũy |
| --- | ---: | --- |
| bai-01 | 4 | Tam giác và đường cao → Đối xứng và đường song song → Đoạn HE cho tiểu ý (a) → Đường tròn CDE cho tiểu ý (b) |
| bai-02 | 3 | Hình vuông và E theo số đo → Đường tròn đường kính BE → Hình chiếu O lên CD |
| bai-03 | 3 | Đường tròn và tia tiếp tuyến Ax → OB cho tiểu ý (a) → C và BC cho tiểu ý (b) |
| bai-04 | 2 | Cát tuyến với thứ tự A-B-C → Tiếp tuyến AM |
| bai-05 | 4 | Đường kính và hình chiếu C → Trung điểm và đường vuông góc OC → Giao điểm D,E trên cùng nửa đường tròn → Đường tròn tâm C qua D |
| bai-06 | 6 | Đường kính, C và trung điểm H → Tiếp tuyến tại B và giao D → CD,OC cho tiểu ý (b) → Giao thứ hai E và trung điểm M → Đường tròn DBC cho tiểu ý (c) → I và giao F cho tiểu ý (d) |

Các đoạn/tia/circle xuất hiện trong câu hỏi được đưa vào instruction bằng yêu cầu dựng cụ thể. Các kết luận cần chứng minh không được dùng làm giả thiết hoặc ký hiệu kết quả: HA=HE, HE tiếp tuyến, BC/CD tiếp tuyến, M đồng viên hay F thuộc (O). OF ở bài 02 được ghi nhận là hình phụ được chọn cho lời giải; M≠I ở bài 05 là lựa chọn cấu hình minh họa để nhãn phân biệt.

## Kiểm tra

Đây là **biên soạn thủ công bởi assistant**, không phải thành công tự động từ model. 22/22 target compile/render; 144 kiểm tra quan hệ từ tọa độ PGF đều pass. Mỗi target cũng có một biến thể quay–tịnh tiến hợp lệ và một đối chứng tọa độ bị làm sai được phát hiện. Hai nhãn “3 cm” của bài 02 đã được dịch và kiểm tra lại; bản đầu được giữ trong `initial/`.

Ảnh cuối của cả 22 cặp đã được subagent rà hình học, phạm vi và nhãn. Các kiểm tra tọa độ không chứng nhận mọi nét vẽ, bán kính hiển thị, nhãn hay ký hiệu: các phần đó đã được rà nguồn/ảnh riêng. Bài 05 còn kiểm tra D,E nằm cùng phía AB với C bằng tọa độ đo được.

Evidence: [summary.json](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/summary.json) và [protocol.json](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/protocol.json); từng thư mục target có `verification.json`. Tolerance hiện tại là tolerance phát triển cục bộ, chưa phải chính sách chung của dataset.

Mọi hàng vẫn có `status: candidate`, `human_review_status: pending`, `experiment_role: development_only`; **chưa có hàng selected/prepared và chưa chạy evaluation model**. Khi so sánh model/harness, giữ cố định instruction, target và rubric của cùng hàng. Các bước của một bài phải ở cùng split.

## bai-01

### bai-01-s01 — Tam giác và đường cao

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ tam giác ABC vuông tại A với AB < AC. H là chân đường cao từ A trên đoạn BC. Vẽ ba cạnh và AH; đánh dấu góc vuông tại A và H, ghi nhãn A,B,C,H.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s01/verification.json)

### bai-01-s02 — Đối xứng và đường song song

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ tam giác ABC vuông tại A với AB < AC. H là chân đường cao từ A trên đoạn BC. Vẽ ba cạnh và AH; đánh dấu góc vuông tại A và H, ghi nhãn A,B,C,H. D đối xứng với B qua H; qua D kẻ đường song song AB cắt đoạn AC tại E. Vẽ DE và ghi nhãn D,E.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s02/verification.json)

### bai-01-s03 — Đoạn HE cho tiểu ý (a)

Phần nguồn: `(a)`; loại bước: `solution_carrier`.

```prompt
Vẽ tam giác ABC vuông tại A với AB < AC. H là chân đường cao từ A trên đoạn BC. Vẽ ba cạnh và AH; đánh dấu góc vuông tại A và H, ghi nhãn A,B,C,H. D đối xứng với B qua H; qua D kẻ đường song song AB cắt đoạn AC tại E. Vẽ DE và ghi nhãn D,E. Thêm đoạn HE bằng nét đứt.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s03/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s03/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s03/verification.json)

### bai-01-s04 — Đường tròn CDE cho tiểu ý (b)

Phần nguồn: `(b)`; loại bước: `solution_carrier`.

```prompt
Vẽ tam giác ABC vuông tại A với AB < AC. H là chân đường cao từ A trên đoạn BC. Vẽ ba cạnh và AH; đánh dấu góc vuông tại A và H, ghi nhãn A,B,C,H. D đối xứng với B qua H; qua D kẻ đường song song AB cắt đoạn AC tại E. Vẽ DE và ghi nhãn D,E. Thêm đoạn HE bằng nét đứt. Thêm đường tròn qua C,D,E bằng nét đứt; không đặt nhãn cho tâm phụ.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s04/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s04/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s04/verification.json)

Ảnh bước cuối (bai-01-s04):

![bai-01 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-01-s04/page-1.png)

## bai-02

### bai-02-s01 — Hình vuông và E theo số đo

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ hình vuông ABCD theo thứ tự các đỉnh quanh biên, AB = 4 cm. Lấy E trong đoạn AD sao cho AE = 3 cm. Vẽ bốn cạnh, ghi nhãn A,B,C,D,E và hai số đo 4 cm trên AB, 3 cm trên AE.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s01/verification.json)

### bai-02-s02 — Đường tròn đường kính BE

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ hình vuông ABCD theo thứ tự các đỉnh quanh biên, AB = 4 cm. Lấy E trong đoạn AD sao cho AE = 3 cm. Vẽ bốn cạnh, ghi nhãn A,B,C,D,E và hai số đo 4 cm trên AB, 3 cm trên AE. Vẽ BE và đường tròn đường kính BE, tâm O là trung điểm BE; ghi nhãn O.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s02/verification.json)

### bai-02-s03 — Hình chiếu O lên CD

Phần nguồn: `single proof`; loại bước: `solution_auxiliary`.

```prompt
Vẽ hình vuông ABCD theo thứ tự các đỉnh quanh biên, AB = 4 cm. Lấy E trong đoạn AD sao cho AE = 3 cm. Vẽ bốn cạnh, ghi nhãn A,B,C,D,E và hai số đo 4 cm trên AB, 3 cm trên AE. Vẽ BE và đường tròn đường kính BE, tâm O là trung điểm BE; ghi nhãn O. Dựng F là hình chiếu vuông góc của O lên CD; vẽ OF nét đứt, đánh dấu góc vuông tại F và ghi nhãn F.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s03/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s03/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s03/verification.json)

Ảnh bước cuối (bai-02-s03):

![bai-02 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-02-s03/page-1.png)

## bai-03

### bai-03-s01 — Đường tròn và tia tiếp tuyến Ax

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O bán kính 6 cm, A thuộc đường tròn. Tia Ax là tiếp tuyến tại A; lấy B trên tia với AB = 8 cm. Vẽ OA và tia Ax có mũi tên vượt B, ghi x ở đầu tia; ghi nhãn O,A,B, số đo 6 cm trên OA, 8 cm trên AB và dấu góc vuông OAB.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s01/verification.json)

### bai-03-s02 — OB cho tiểu ý (a)

Phần nguồn: `(a)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O bán kính 6 cm, A thuộc đường tròn. Tia Ax là tiếp tuyến tại A; lấy B trên tia với AB = 8 cm. Vẽ OA và tia Ax có mũi tên vượt B, ghi x ở đầu tia; ghi nhãn O,A,B, số đo 6 cm trên OA, 8 cm trên AB và dấu góc vuông OAB. Thêm OB bằng nét đứt.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s02/verification.json)

### bai-03-s03 — C và BC cho tiểu ý (b)

Phần nguồn: `(b)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O bán kính 6 cm, A thuộc đường tròn. Tia Ax là tiếp tuyến tại A; lấy B trên tia với AB = 8 cm. Vẽ OA và tia Ax có mũi tên vượt B, ghi x ở đầu tia; ghi nhãn O,A,B, số đo 6 cm trên OA, 8 cm trên AB và dấu góc vuông OAB. Thêm OB bằng nét đứt. Qua A kẻ đường vuông góc OB, lấy C là giao điểm thứ hai của đường này với đường tròn, C khác A. Vẽ AC, BC và OC; đánh dấu góc vuông ở giao AC với OB, ghi nhãn C, không đặt tên cho giao điểm phụ đó.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s03/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s03/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s03/verification.json)

Ảnh bước cuối (bai-03-s03):

![bai-03 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-03-s03/page-1.png)

## bai-04

### bai-04-s01 — Cát tuyến với thứ tự A-B-C

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O bán kính R và A ở ngoài. Đường thẳng d qua A cắt đường tròn tại hai điểm phân biệt B,C theo thứ tự A-B-C, AB < AC. Vẽ d kéo dài hai phía qua A,C, ghi d và các nhãn O,A,B,C.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s01/verification.json)

### bai-04-s02 — Tiếp tuyến AM

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O bán kính R và A ở ngoài. Đường thẳng d qua A cắt đường tròn tại hai điểm phân biệt B,C theo thứ tự A-B-C, AB < AC. Vẽ d kéo dài hai phía qua A,C, ghi d và các nhãn O,A,B,C. Vẽ tiếp tuyến đoạn AM tại M và bán kính OM, đánh dấu góc vuông OMA và ghi nhãn M.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s02/verification.json)

Ảnh bước cuối (bai-04-s02):

![bai-04 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-04-s02/page-1.png)

## bai-05

### bai-05-s01 — Đường kính và hình chiếu C

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O đường kính AB; chọn C khác A,B trên một nửa đường tròn. H là hình chiếu vuông góc của C lên AB. Vẽ AB, OC, CH, đánh dấu góc vuông tại H và ghi nhãn O,A,B,C,H.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s01/verification.json)

### bai-05-s02 — Trung điểm và đường vuông góc OC

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O đường kính AB; chọn C khác A,B trên một nửa đường tròn. H là hình chiếu vuông góc của C lên AB. Vẽ AB, OC, CH, đánh dấu góc vuông tại H và ghi nhãn O,A,B,C,H. M là trung điểm CH. Qua M kẻ đường thẳng vuông góc OC, cắt OC tại I; chọn cấu hình minh họa với M khác I. Vẽ đường đó, đánh dấu góc vuông tại I, gạch bằng nhau trên CM,MH và ghi nhãn M,I.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s02/verification.json)

### bai-05-s03 — Giao điểm D,E trên cùng nửa đường tròn

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O đường kính AB; chọn C khác A,B trên một nửa đường tròn. H là hình chiếu vuông góc của C lên AB. Vẽ AB, OC, CH, đánh dấu góc vuông tại H và ghi nhãn O,A,B,C,H. M là trung điểm CH. Qua M kẻ đường thẳng vuông góc OC, cắt OC tại I; chọn cấu hình minh họa với M khác I. Vẽ đường đó, đánh dấu góc vuông tại I, gạch bằng nhau trên CM,MH và ghi nhãn M,I. Gọi D,E là hai giao điểm phân biệt của đường qua M với nửa đường tròn chứa C; ghi nhãn cả hai. Có thể hoán đổi tên D,E nếu giữ đúng các phép dựng tiếp theo.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s03/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s03/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s03/verification.json)

### bai-05-s04 — Đường tròn tâm C qua D

Phần nguồn: `single proof`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O đường kính AB; chọn C khác A,B trên một nửa đường tròn. H là hình chiếu vuông góc của C lên AB. Vẽ AB, OC, CH, đánh dấu góc vuông tại H và ghi nhãn O,A,B,C,H. M là trung điểm CH. Qua M kẻ đường thẳng vuông góc OC, cắt OC tại I; chọn cấu hình minh họa với M khác I. Vẽ đường đó, đánh dấu góc vuông tại I, gạch bằng nhau trên CM,MH và ghi nhãn M,I. Gọi D,E là hai giao điểm phân biệt của đường qua M với nửa đường tròn chứa C; ghi nhãn cả hai. Có thể hoán đổi tên D,E nếu giữ đúng các phép dựng tiếp theo. Thêm đường tròn tâm C đi qua D và bán kính CD bằng nét đứt.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s04/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s04/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s04/verification.json)

Ảnh bước cuối (bai-05-s04):

![bai-05 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-05-s04/page-1.png)

## bai-06

### bai-06-s01 — Đường kính, C và trung điểm H

Phần nguồn: `givens`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s01/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s01/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s01/verification.json)

### bai-06-s02 — Tiếp tuyến tại B và giao D

Phần nguồn: `givens / (a)`; loại bước: `main_givens`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H. Tiếp tuyến tại B cắt tia OH tại D. Vẽ đường tiếp tuyến kéo dài qua B,D và tia OH có mũi tên vượt D; đánh dấu góc vuông OBD, ghi nhãn D.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s02/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s02/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s02/verification.json)

### bai-06-s03 — CD,OC cho tiểu ý (b)

Phần nguồn: `(b)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H. Tiếp tuyến tại B cắt tia OH tại D. Vẽ đường tiếp tuyến kéo dài qua B,D và tia OH có mũi tên vượt D; đánh dấu góc vuông OBD, ghi nhãn D. Thêm CD và OC bằng nét đứt.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s03/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s03/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s03/verification.json)

### bai-06-s04 — Giao thứ hai E và trung điểm M

Phần nguồn: `(c)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H. Tiếp tuyến tại B cắt tia OH tại D. Vẽ đường tiếp tuyến kéo dài qua B,D và tia OH có mũi tên vượt D; đánh dấu góc vuông OBD, ghi nhãn D. Thêm CD và OC bằng nét đứt. Đường thẳng AD cắt đường tròn lần thứ hai tại E, E khác A; M là trung điểm AE. Vẽ AD kéo dài qua A,D, đánh dấu AM = ME bằng hai gạch và ghi nhãn E,M.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s04/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s04/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s04/verification.json)

### bai-06-s05 — Đường tròn DBC cho tiểu ý (c)

Phần nguồn: `(c)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H. Tiếp tuyến tại B cắt tia OH tại D. Vẽ đường tiếp tuyến kéo dài qua B,D và tia OH có mũi tên vượt D; đánh dấu góc vuông OBD, ghi nhãn D. Thêm CD và OC bằng nét đứt. Đường thẳng AD cắt đường tròn lần thứ hai tại E, E khác A; M là trung điểm AE. Vẽ AD kéo dài qua A,D, đánh dấu AM = ME bằng hai gạch và ghi nhãn E,M. Thêm đường tròn xác định bởi ba điểm D,B,C bằng nét đứt, không ghi nhãn tâm phụ; giữ M tại trung điểm AE đã dựng.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s05/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s05/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s05/verification.json)

### bai-06-s06 — I và giao F cho tiểu ý (d)

Phần nguồn: `(d)`; loại bước: `solution_carrier`.

```prompt
Vẽ đường tròn tâm O đường kính AB. Chọn C khác A,B trên đường tròn sao cho AC < BC; H là trung điểm BC. Vẽ AB, AC, BC; đánh dấu BH = HC bằng một gạch và ghi nhãn O,A,B,C,H. Tiếp tuyến tại B cắt tia OH tại D. Vẽ đường tiếp tuyến kéo dài qua B,D và tia OH có mũi tên vượt D; đánh dấu góc vuông OBD, ghi nhãn D. Thêm CD và OC bằng nét đứt. Đường thẳng AD cắt đường tròn lần thứ hai tại E, E khác A; M là trung điểm AE. Vẽ AD kéo dài qua A,D, đánh dấu AM = ME bằng hai gạch và ghi nhãn E,M. Thêm đường tròn xác định bởi ba điểm D,B,C bằng nét đứt, không ghi nhãn tâm phụ; giữ M tại trung điểm AE đã dựng. I là trung điểm DH; đường thẳng BI cắt đường thẳng AH tại F. Vẽ hai đường đó đủ dài để thấy giao F, đánh dấu DI = IH bằng ba gạch và ghi nhãn I,F.
```

[TikZ](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s06/target.tikz) · [PNG](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s06/page-1.png) · [Kiểm tra](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s06/verification.json)

Ảnh bước cuối (bai-06-s06):

![bai-06 bước cuối](C:/Users/Onn/Documents/Git/problem_tikz/runs/prepare-f9062486-stages-20261002/bai-06-s06/page-1.png)
