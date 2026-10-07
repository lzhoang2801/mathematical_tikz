# Candidate dataset và evaluation: thử nghiệm 8 bài

Mục tiêu cuối là xây hàng nghìn row từ **đề bài + TikZ mẫu**. Tám bài ở đây là tập phát triển được Codex rà thủ công để hiểu và kiểm chứng các bước của harness. Không coi khả năng model tự làm đúng, lời chấm của model, hay trạng thái accepted của harness cũ là chuẩn chất lượng.

Nguồn được giữ riêng trong [candidate-flow-8.sources.jsonl](dataset-selection/candidate-flow-8.sources.jsonl). Kết quả là [8 candidate đã cố định instruction, target và rubric](dataset-selection/candidate-flow-8.jsonl). Tất cả vẫn là candidate; chưa có row nào được người dùng duyệt thành gold/SFT-ready.

## Flow đã thực hiện

1. Giữ nguyên đề bài và TikZ mẫu, lưu provenance và hash nguồn.
2. Xác định phạm vi cần vẽ từ nguồn; viết instruction tự chứa, ghi rõ các hình phụ được chọn.
3. Kiểm tra và sửa target theo instruction: toán học, cú pháp, nét vẽ và nhãn. Không mặc định TikZ nguồn đúng.
4. Viết rubric riêng cho từng instruction theo bốn dimension; nêu điều kiện đạt và các biểu diễn tương đương.
5. Kiểm tra target bằng compiler, đo tọa độ PGF thực, predicate toán học và đọc render. Thử hình đúng và hình cài lỗi để kiểm tra chính evaluator.
6. Cố định instruction + target + rubric cùng hash. Sinh baseline chỉ nhận instruction; chấm offline bằng tiêu chí đã cố định.

Thí nghiệm baseline là phép thử cho hợp đồng dữ liệu/evaluator. Nó không thay thế nhiệm vụ xây harness chuẩn bị dữ liệu.

## Candidate và tiêu chí cố định

| Case | Tiêu chí rubric | Kiểm tra quan hệ bằng code | Target |
| --- | ---: | ---: | --- |
| [bai-01](../runs/candidate-flow-20260928/bai-01/candidate-audited.json) | 9 | 11 | [Render](../runs/candidate-flow-20260928/bai-01/target-curated/target-1.png) |
| [bai-02](../runs/candidate-flow-20260928/bai-02/candidate-audited.json) | 8 | 14 | [Render](../runs/candidate-flow-20260928/bai-02/target-curated/target-1.png) |
| [bai-03](../runs/candidate-flow-20260928/bai-03/candidate-audited.json) | 8 | 10 | [Render](../runs/candidate-flow-20260928/bai-03/target-curated/target-1.png) |
| [bai-04](../runs/candidate-flow-20260928/bai-04/candidate-audited.json) | 6 | 8 | [Render](../runs/candidate-flow-20260928/bai-04/target-curated/target-1.png) |
| [bai-05](../runs/candidate-flow-20260928/bai-05/candidate-audited.json) | 7 | 15 | [Render](../runs/candidate-flow-20260928/bai-05/target-curated/target-1.png) |
| [bai-06](../runs/candidate-flow-20260928/bai-06/candidate-audited.json) | 9 | 22 | [Render](../runs/candidate-flow-20260928/bai-06/target-curated/target-1.png) |
| [user-tangents-01](../runs/candidate-flow-20260928/user-tangents-01/candidate-audited.json) | 14 | 14 | [Render](../runs/candidate-flow-20260928/user-tangents-01/target-curated/target-1.png) |
| [user-tangents-02](../runs/candidate-flow-20260928/user-tangents-02/candidate-audited.json) | 10 | 10 | [Render](../runs/candidate-flow-20260928/user-tangents-02/target-curated/target-1.png) |

Tổng: **8 candidate, 71 tiêu chí, 104 phép kiểm tra quan hệ**. Tám target compile thành công; các phép kiểm tra quan hệ đều đạt. Đây không phải bằng chứng tự động rằng mọi yêu cầu nội dung và thị giác đều đúng.

Ví dụ bài tiếp tuyến thứ nhất: rubric kiểm riêng A ngoài đường tròn; B/C trên đường tròn; AB/AC vuông góc các bán kính tại tiếp điểm; K thuộc nghiêm ngặt cung nhỏ BC; PQ vuông góc OK; E/P/Q ở đúng các giao điểm. Coverage kiểm các nét và nhãn phải xuất hiện. Target giữ K=15° như ví dụ gốc, không biến thành cấu hình đối xứng để làm bài dễ hơn.

Các ngưỡng 0,5% cho sai số tương đối và 1° cho vuông góc/song song chỉ là cấu hình thử nghiệm này, không phải quy ước dataset đã được thống nhất. Thiếu binding tên điểm hoặc chưa kiểm chứng được là unknown, không phải pass.

## Harness có tác dụng gì

| Cơ chế | Kết quả thực nghiệm |
| --- | --- |
| Đo PGF + predicate toán học | Chấp nhận 8 bản dịch chuyển toàn hình; phát hiện cả 8 bản cố tình di chuyển một điểm làm sai quan hệ. Đây mới kiểm tính bất biến với dịch chuyển, chưa đại diện mọi biến thể code/layout. |
| Chuẩn hóa cú pháp theo diagnostic compiler | Hai đầu ra lỗi compile của bai-05 và user-tangents-02 biên dịch được sau các sửa cú pháp xác định, không thêm model call. Đây là hai phép sửa thử nghiệm có phạm vi hẹp, chưa phải bộ chuẩn hóa TikZ tổng quát. |
| Trả lỗi đo được cho lượt sửa có giới hạn | bai-06 có AC/BC≈1,732, trái AC<BC. Một lượt sửa nhận instruction + current TikZ + lỗi đo được, không nhận target hoặc toàn bộ rubric. Sau sửa, 22/22 kiểm tra quan hệ đạt. |
| Đọc PDF path, không dùng model judge | 57 subcheck về đoạn thẳng đạt trên 8 target. Cùng checker phát hiện BC bị thiếu trong user-tangents-02 sau sửa cú pháp. Một lần compile đo nhiều đoạn; contract từng row là dữ liệu, không phải luật viết riêng cho bài. |
| Không tự nâng trạng thái khi thiếu bằng chứng | Compile và quan hệ tọa độ đạt vẫn chưa chứng minh đủ nét, đúng nhãn hay dễ đọc. Các phần này được giữ riêng. |

Checker được giữ ở [verify_painted_segments.py](../tools/verify_painted_segments.py), nhận danh sách cặp điểm từ [stroke-checks.json](dataset-selection/candidate-flow-8.stroke-checks.json). [Kết quả 16 artifact](../runs/candidate-flow-20260928/visible-content-summary.json) gồm 8 target, 5 baseline compile được và 3 bản sửa.

Control cho checker gồm hình đúng, scale=1.2, xóa OC, chỉ vẽ hai mẩu đầu đoạn, nét opacity=0 và đổi tên binding C; lần lượt cho pass, pass, fail, fail, fail, unknown. [Evidence](../runs/candidate-flow-20260928/bai-06/content-control/painted-stroke-probe/evidence.json). Kiểm tra này mới chứng nhận các đoạn thẳng được xuất thành PDF stroke; không chứng nhận đường tròn, semantic label binding, clipping/occlusion hay readability.

Chi tiết và code/output trước-sau được giữ trong các thư mục `runs/candidate-flow-20260928/<id>/harness-repair/`. Các baseline gốc không bị ghi đè.

## Những chỗ không được giao quyền quyết định cho model

- Bản nháp chuẩn bị tự động chỉ có **3/8** case vượt qua schema và compile. Tất cả 8 candidate cuối đều có rà soát của Codex; không báo 8/8 như thành công tự động.
- Khi xóa đúng nét OC nhưng giữ mọi tọa độ, 22 kiểm tra quan hệ vẫn pass. Gemini 3.1 flash-lite chấm coverage pass cho cả hình đầy đủ và hình thiếu OC. Đây là false accept rõ ràng của cấu hình judge đã thử.
- Trên bai-01–04, judge này có 10 kết luận fail về toán mâu thuẫn với phép tính tọa độ và kiểm tra source/render. Nó cũng bỏ sót AC<BC sai ở bai-06; predicate xác định đã bắt được lỗi.
- DiagramIR chỉ là một nguồn quan sát bổ sung. Một trong năm lượt backtranslation của hình compile được không qua schema; bốn lượt qua schema vẫn chưa được chứng nhận trung thực về primitive, đơn vị và nhãn. Global IR checks không thay cho kiểm tra instruction.

Do đó các `dimension_scores` trong `evaluate-output/evaluation.json` chỉ là diagnostic của cấu hình judge, không dùng làm quyết định nhận row hay bảng xếp hạng chất lượng.

## Baseline và phân loại lỗi

| Case | Baseline compile | Kết luận sau rà soát độc lập |
| --- | --- | --- |
| bai-01 | Đạt | 9/9 tiêu chí đạt trong rà soát của Codex. |
| bai-02 | Đạt | 8/8 tiêu chí đạt trong rà soát của Codex. |
| bai-03 | Đạt | 8/8 tiêu chí đạt trong rà soát của Codex. |
| bai-04 | Đạt | Toán và render đạt; tiêu chí về nét OA phụ còn mơ hồ, giữ unknown. |
| bai-05 | Không đạt | Sửa cú pháp làm compile và 15 quan hệ đạt; các đoạn thẳng đạt. Rà source/render vẫn phát hiện chỉ vẽ nửa đường tròn thay vì cả đường tròn. |
| bai-06 | Đạt | AC<BC sai và nhãn dồn. Sau một lượt sửa theo số đo: 22 quan hệ, các đoạn bắt buộc và rà soát nội dung/readability đều đạt. |
| user-tangents-01 | Không đạt | Lỗi kết nối provider; giữ trong mẫu số, không có output để chấm. |
| user-tangents-02 | Không đạt | Sửa chấm phẩy làm compile và 10 quan hệ đạt; checker PDF phát hiện thiếu BC. Không được nhận row chỉ vì quan hệ tọa độ đúng. |

Baseline: 8 lượt sinh, 7 có TikZ và 5 compile thành công. Không có vòng LLM reviewer online. Tất cả tám trace đã được kiểm tra: instruction gửi đi khớp bản cố định và không chứa target/rubric. [Bằng chứng input](../runs/candidate-flow-20260928/generation-input-audit.json).

Một vấn đề của **rubric do mình viết** cũng được giữ lại: bai-04 cấm đường phụ “không có vai trò”, nhưng instruction không cấm OA và OA có thể giúp biểu diễn A ngoài đường tròn. Không được tùy tiện coi nét đó là lỗi model. [Adjudication](../runs/candidate-flow-20260928/bai-04/scope-adjudication.json) giữ unknown và giữ nguyên review đầu để không che lịch sử. Rubric này cần được làm rõ trước khi dùng làm gate tự động.

## Ý nghĩa cho batch vài nghìn row

Harness cần tạo và thực thi **hợp đồng dữ liệu cho từng row**, không chỉ thêm lời nhắc hoặc thêm một model reviewer:

1. Model đề xuất scope/instruction/target/rubric; harness kiểm schema, provenance, mâu thuẫn phạm vi và tính đủ của các điều kiện đã khai báo.
2. Tách điều kiện toán học khỏi đối tượng phải thực sự được vẽ. Thư viện phép kiểm dùng chung; mỗi row cung cấp đối tượng, toán hạng và điều kiện cụ thể. Không viết một bộ luật riêng cho từng đề.
3. Compile và quan sát kết quả thực thi để thu bằng chứng. Phép kiểm trả pass/fail/unknown kèm số đo hoặc nét thiếu; unknown không bị đổi thành pass.
4. Chỉ sửa lỗi được xác định: sửa cú pháp cơ học khi biết phép đổi tương đương; lỗi dựng hình nhận diagnostic cụ thể cho lượt sửa có giới hạn. Kiểm tra lại bằng cùng hợp đồng.
5. Hàng chờ rà soát nhận lỗi nguồn, scope/rubric mơ hồ, binding không xác định, primitive chưa hỗ trợ và lỗi sau ngân sách sửa. Không gom các trường hợp đó vào “model kém”.
6. Giữ hash/version và artifact từng lượt, resume theo row, cache có kiểm danh tính, concurrency có giới hạn. Xuất SFT từ các cặp đã qua quality gate; giữ các biến thể cùng nguồn trong cùng split.

Bước nhân rộng phải đo **tỉ lệ candidate đúng không cần sửa tay, tỉ lệ sửa thành công, false accept/false reject của checker, unknown/review rate, và chi phí trên mỗi row được nhận**. Token/latency của model đơn lẻ không thay thế các chỉ số này. Chưa chạy batch hàng nghìn row và chưa có ước lượng chi phí đáng tin cậy cho toàn bộ taxonomy.

## Artifact và tái hiện

- [Chuẩn bị candidate](../tools/prepare_tikz_candidates.py): thử nghiệm có giới hạn và giữ raw responses/lỗi.
- [Kiểm tra và evaluation độc lập](../tools/evaluate_tikz_candidates.py): predicate hình học, calibration, controls, baseline và evidence offline.
- [Tổng hợp từng case](../runs/candidate-flow-20260928/review-summary.json).
- [Trace và usage](../runs/candidate-flow-20260928/usage-summary.json); [toàn bộ trace](../runs/candidate-flow-20260928/traces.json).

Dùng Python environment hiện có của MathPaper với `-B`. Không sửa MathPaper và không cài dependency. Script là prototype cố định cho 8 case này, chưa phải runner sản xuất cho vài nghìn row. Bản protocol lúc freeze được giữ tại `runs/candidate-flow-20260928/protocol/frozen-evaluator.py`; các kết quả evaluation ghi hash evaluator thực dùng. Candidate/rubric không bị thay đổi sau freeze; sửa kiểm tra cache/reporting của evaluator được lưu riêng bằng code hash.

Các kiểm tra đã chạy: operator self-check gồm ca đúng/sai/suy biến/thiếu binding; compile/render tám target; positive/negative geometry controls; `ruff --select F`; `git diff --check`. Không chạy formatter. Model gemini-3.5-flash-lite dùng sampling mặc định cố định của provider; SDK bỏ qua temperature=0, nên không tuyên bố generation deterministic.

## Số liệu các lượt gọi model đã thực hiện

**36/36 trace LangSmith đã xác nhận hoàn tất**, trong project MathPaper theo cấu hình môi trường hiện có. Token chỉ cộng các call có usage metadata; không suy diễn phí của các call thiếu metadata. Các kiểm tra PGF/PDF path không gọi model.

| Stage | Calls | Lỗi call/parse | Median giây/call | Token có ghi nhận |
| --- | ---: | ---: | ---: | ---: |
| audit-candidate | 3 | 2 | 39.67 | 46,818 |
| direct-tikz-baseline | 8 | 1 | 25.89 | 48,770 |
| extract-observed-diagramir | 5 | 1 | 34.34 | 31,394 |
| offline-rubric-review | 5 | 0 | 4.46 | 26,221 |
| prepare-candidate | 12 | 2 | 25.13 | 71,397 |
| calibrate-content-coverage | 2 | 0 | 6.67 | 12,002 |
| repair-from-measured-failure | 1 | 0 | 20.70 | 7,950 |

Không dùng median này để ước lượng thời gian trên mỗi row được nhận: chưa đo đủ thời gian rà soát/sửa tay, tỷ lệ unknown và chi phí cho các nhóm diagram khác. Những lượt judge/backtranslation trong bảng là thí nghiệm so sánh, không phải các bước bắt buộc đề xuất cho từng row trong batch.
