# Related works: TikZ harness, verification và dữ liệu fine-tuning

Chốt tìm kiếm **2026-09-28**. Tổng hợp **10 paper PDF local và 16 công trình bổ sung**, với mức độ đọc khác nhau được ghi tại [sổ nguồn](papers/README.md). Đây là focused scoping review; không tuyên bố exhaustive coverage hoặc novelty “đầu tiên”. ID P01–P10/R01–R16 chỉ để nối evidence với experiments trong [research protocol](tikz-research-protocol.md).

## 1. Luận điểm nghiên cứu rút ra

Hướng phù hợp cho repo là **đo đúng → kiểm định feedback → cải thiện harness → curate dữ liệu → thử SFT**. Đây là đề xuất tổng hợp, không phải kết quả thực nghiệm tại repo. Literature không đưa ra một metric duy nhất đủ chứng minh hình vừa đúng toán, đúng nội dung cần vẽ và dễ đọc.

Có ba khoảng cách cần nghiên cứu:

1. **Hình hợp lệ và hình đúng yêu cầu khác nhau.** DiagramIR kiểm cấu trúc đã quan sát; MagicGeo/GeoLoom bổ sung constraints; benchmark theo ảnh lại đo giống hình. Repo cần tách instruction-derived requirements, observed geometry và hidden reference. Mỗi tầng có thể sai độc lập.
2. **Feedback tốt và thêm compute khác nhau.** DeTikZify dùng search; Self-Refine dùng revision; Imperfect Visual Verification cho thấy verifier có thể khiến dừng sai. Cần đối chứng one-shot, review/repair và best-of-two cùng trần compute, đồng thời báo chi phí thực tế.
3. **Nhiều trajectories và nhiều supervision đáng tin khác nhau.** EdiTikZ có revisions tự nhiên nhưng instruction tự sinh còn lỗi; Edit2TikZ cho thấy chất lượng input ảnh hưởng edit. Dataset local cần lineage, approval và preservation trước khi biến trace thành SFT pairs.

Đóng góp khả thi trước tiên là một nghiên cứu có kiểm soát trên nguồn SGK Việt Nam lớp 6–12: **information selection × feedback reliability**, kèm dữ liệu final/repair có provenance. Chưa cần thay direct TikZ bằng DSL, thêm MCTS hoặc train RL để thực hiện nghiên cứu đó.

## 2. Các dòng phương pháp và khả năng chuyển giao

| Dòng phương pháp | Paper tiêu biểu | Chuyển giao cho repo | Giới hạn cần giữ |
| --- | --- | --- | --- |
| Direct code SFT, image/text alignment | P01, P02, P04, P07 | SFT cú pháp/cấu trúc; reconstruction làm nguồn supervision; kiểm soát task mix | Mô hình chuyên scientific figures không tự đạt instruction fidelity SGK |
| Geometry formalization/solver | P03, P06, R06 | Requirement annotations, numeric constraints, sai số độ dài/góc | Chỉ lấy verification ideas; không thay generation path đã thống nhất |
| Executable/render verification | P05, R10, R14 | Typed errors, unknown, false accept, repair utility | Compile hoặc cấu trúc nội tại không đủ chấm toán/coverage |
| Editing và revision data | P08, P09, P10, R02 | Current-code contract, change/preserve sets, real repair pairs | Image editing, auxiliary-line generation và current-TikZ Edit khác input |
| Execution/render-reward learning | P07, R03, R11, R16 | SFT baseline trước; reward audit; ablation từng thành phần | Similarity/cycle/reward tăng chưa chứng minh toán đúng |
| Representation/information selection | R01, R05, R07, R08, R09 | Scope instruction, multiple valid layouts, controlled omissions | Không suy từ ít nét hoặc VQA score sang hiệu quả học tập |
| Self-refinement/preference | R12, R13, R15 | Compute-matched repair control, preservation, approved preferences | Kết quả ở task/model khác chỉ tạo hypothesis |

## 3. Đọc sâu 10 paper hiện có

### P01 — AutomaTikZ: Text-Guided Synthesis of Scientific Vector Graphics with TikZ

**Nguồn:** [PDF local](papers/2310.00367v2.pdf), [arXiv](https://arxiv.org/abs/2310.00367), ICLR 2024. Trọng tâm đọc: PDF tr. 4–9, §§3–6.

Paper fine-tune trực tiếp mô hình code từ caption–TikZ; DaTikZ có khoảng 119.789 cặp. Nhánh multimodal CLiMA dùng alignment hình để hỗ trợ generation. Đây là bằng chứng rằng TikZ code có thể học qua supervised pairs mà không cần một symbolic-generation framework.

Điểm quan trọng hơn leaderboard là **construct validity của metric**: typography attacks/chèn nội dung caption vào hình có thể làm visual score tăng mà không tạo một sơ đồ tốt hơn. CSR của paper là compiler sampling ratio; không được đọc như tỷ lệ compile thành công theo định nghĩa của repo.

**Áp dụng:** E5 giữ direct TikZ SFT; E0/E8 dùng compile, toán, coverage và readability riêng. Visual score chỉ làm diagnostic. Caption scientific figure và instruction từ bài hoàn chỉnh không phải cùng input distribution; cần local task supervision thay vì chỉ đổi prompt của model đã train trên caption.

### P02 — DeTikZify: Synthesizing Graphics Programs for Scientific Figures and Sketches with TikZ

**Nguồn:** [PDF local](papers/2405.15306v3.pdf), [arXiv](https://arxiv.org/abs/2405.15306), NeurIPS 2024. PDF tr. 4–10, §5 và Tables 2–5.

DeTikZify nối reconstruction bằng VLM với inference-time search: candidate programs được compile/render, rồi đánh giá so với ảnh đầu vào để hướng MCTS. Dữ liệu DaTikZ v2 có 360.583 programs; MetaFig/SketchFig bổ sung hình và sketch. Paper xét cả giới hạn output và thời gian, nên hữu ích cho cách báo cost–quality.

Similarity với **source image hợp lệ** trong Reconstruct khác với được nhìn hidden target trong Generate/Edit. Search có lợi ở một số metric/budget nhưng không chứng minh MCTS cần thiết cho mọi case. Điểm AVG chuẩn hóa trong bảng cũng không có cùng thang với AVG của paper khác.

**Áp dụng:** E3 so bounded repair với best-of-two trước. Chỉ cân nhắc search phức tạp nếu phân tích cho thấy simple sampling/feedback chạm trần và có compute phù hợp. Đánh giá cả pipeline trên all-cases, không chỉ chọn candidate compile.

### P03 — MagicGeo: Training-Free Text-Guided Geometric Diagram Generation

**Nguồn:** [PDF local](papers/2502.13855v1.pdf), [arXiv](https://arxiv.org/abs/2502.13855), preprint 2025. Method và ablation: PDF tr. 3–7; limitations tr. 9.

MagicGeo formalize points/relations, giải constraints rồi render TikZ. Benchmark có 220 plane-geometry requests; một số câu không tự đủ nghĩa được bổ sung bằng facts lấy từ diagram. Table 3 báo tỷ lệ point/constraint formalization được kiểm thủ công tăng từ 94,7% lên 98,7% sau solver feedback trong cấu hình paper; đây là kết quả formalization, không phải acceptance của diagram cuối theo bốn tiêu chí local.

Paper cung cấp lý do để dùng executable geometric constraints và giải thích lỗi formalization. Tuy nhiên solver có thể rất chậm ở bài phức tạp; input đã được làm rõ cũng thuận lợi hơn statement mơ hồ ngoài thực tế.

**Áp dụng:** E1 kiểm yêu cầu độ dài/góc/quan hệ trên output, E2 tách giá trị làm rõ input khỏi năng lực dựng hình. Facts bổ sung từ ảnh phải có provenance và điều kiện input rõ; nếu lấy từ hidden reference thì đó là oracle, không phải production input-equivalent baseline. Không chuyển repo sang formalization→solver→TikZ; đó là kiến trúc khác với direct generation đã chọn.

### P04 — TikZero: Zero-Shot Text-Guided Graphics Program Synthesis

**Nguồn:** [PDF local](papers/2503.11509v3.pdf), [ICCV 2025 official paper page](https://openaccess.thecvf.com/content/ICCV2025/html/Belouadi_TikZero_Zero-Shot_Text-Guided_Graphics_Program_Synthesis_ICCV_2025_paper.html), [arXiv v3](https://arxiv.org/abs/2503.11509v3). PDF tr. 3–8, §§3–6.

TikZero khai thác image→code foundation và text→visual representation alignment khi caption–code pairs hạn chế. DaTikZ v3 có 456.469 programs; phần có caption nhỏ hơn nhiều. TikZero+ tiếp tục dùng aligned supervision, nên “zero-shot” không có nghĩa toàn bộ hệ chưa từng học dữ liệu liên quan.

Kết quả và ablations cho thấy chất lượng/cách phối hợp supervision quan trọng; không thể lấy AVG đã chuẩn hóa ở các bảng khác nhau rồi coi như cùng một accuracy. Paper cũng thảo luận ảnh hưởng typography tới metric.

**Áp dụng:** E5 tách câu hỏi “public reconstruction warm-up có giúp?” khỏi “local task-aligned SFT có giúp?”. So cùng token budget, tránh gán lợi ích của thêm dữ liệu cho curriculum order. Chưa có lý do xây alignment adapter riêng khi harness và approved local targets vẫn là nút thắt.

### P05 — DiagramIR: An Automatic Pipeline for Educational Math Diagram Evaluation

**Nguồn:** [PDF local](papers/2511.08283v1.pdf), [arXiv](https://arxiv.org/abs/2511.08283), 2025. PDF tr. 1–5, §2 và Tables 1–3.

Pipeline dùng LLM chuyển TikZ thành IR rồi chạy deterministic checks. Nghiên cứu gồm 398 teacher requests, chia 12 dev/386 test; trong judge và rubric đã thử, κ của hai cấu hình DiagramIR là 0,483/0,555 so với 0,388/0,498 cho các code/image judges so sánh. Đây là agreement vừa phải trong thí nghiệm cụ thể; không chứng minh verifier tổng quát, source fidelity hay độ bao phủ mọi instruction.

Bằng chứng này ủng hộ representation giúp kiểm tra có cấu trúc; **không** chứng minh extractor luôn đúng hoặc bộ rule bao phủ instruction fidelity. Primitive coverage hữu hạn; tính đúng nội tại của observation khác với đúng hình mà bài yêu cầu. Một IR bỏ sót nét có thể làm downstream checks dễ pass hơn.

**Áp dụng:** E1 tách hand-verified observed IR → checks khỏi TikZ/render → extractor → checks. Hiệu chuẩn trên valid alternatives và faults đã biết. Các controlled probes local là regression evidence cho một số failure modes, không là ước lượng tổng quát về paper. Upstream score tiếp tục là evidence, chưa là acceptance gate.

### P06 — GeoLoom: High-quality Geometric Diagram Generation from Textual Input

**Nguồn:** [PDF local](papers/2512.08180v2.pdf), [arXiv](https://arxiv.org/abs/2512.08180), ICML 2026 theo bản v2. PDF tr. 3–9, dataset/method, Table 1 và Table 4.

GeoLoom dùng GeoLingua và coordinate solver, render bằng Matplotlib. GeoNF có 4.730 cặp natural-language ↔ GeoLingua (4.300/430), không phải TikZ targets. Appendix A.2 (PDF tr. 12) mô tả đội 10 annotators chuyên toán, 3 teacher inspectors và 2 domain experts; mỗi instance được hai người annotate độc lập/blind, inspector kiểm tra và experts xử lý tranh chấp/audit acceptance. Paper phân biệt length/angle consistency với đánh giá khác, hữu ích hơn việc gộp mọi thứ thành pixel similarity.

Phạm vi chính là 2D Euclidean geometry; input ambiguity, solver convergence và representation coverage vẫn là giới hạn. Tỷ lệ manual accuracy của một model không thể so trực tiếp với compile rate, CLIP hay DiagramIR κ.

**Áp dụng:** mượn quy trình adjudication và numeric relation checks cho E0/E1; GeoNF không trực tiếp cung cấp supervision TikZ. Paper còn có overlap failures dù numeric metrics tốt, củng cố việc chấm readability riêng. Với G/A taxonomy rộng hơn, unsupported phải explicit. Không dùng tên chapter để gán diagram type, không áp dụng Euclidean checks cho mọi algebra plot hoặc spatial diagram.

### P07 — TikZilla: Scaling Text-to-TikZ with High-Quality Data and Reinforcement Learning

**Nguồn:** [PDF local](papers/2603.03072v3.pdf), [arXiv](https://arxiv.org/abs/2603.03072), ICLR 2026 theo bản local. PDF tr. 4–10, §§4–6, Tables 3–5.

TikZilla mở rộng DaTikZ v4 lên 2.000.880 programs, có compile repair/caption generation, rồi SFT và GRPO với render-oriented reward. Test 1.047 samples và human subset nhỏ hơn rất nhiều; phải giữ riêng các cấp evidence đó.

Description noise có thể truyền vào training. Ablation caption mixing cần đọc theo đúng số trong bảng: Table 4 báo AVG 0,289 cho desc., 0,313 cho desc. ∨ cap. và 0,319 cho desc. + cap., trong khi phần diễn giải nói trộn/oversample caption làm giảm hiệu năng; không dùng câu “mixing luôn làm giảm chất lượng” làm nguyên lý curriculum. Reward từ figure encoder không tự kiểm nội dung toán học.

**Áp dụng:** E5 trước E8. Public scale có thể hỗ trợ syntax/layout; local reviewed instruction/target phục vụ fidelity. Audit reward hacking, compare replay bằng token budget và không giả định render reward thay evaluator bốn tiêu chí.

### P08 — GeoTikzBridge: Advancing Multimodal Code Generation for Geometric Perception and Reasoning

**Nguồn:** [PDF local](papers/2603.22687v2.pdf), [CVPR 2026 official paper page](https://openaccess.thecvf.com/content/CVPR2026/html/Sun_GeoTikzBridge_Advancing_Multimodal_Code_Generation_for_Geometric_Perception_and_Reasoning_CVPR_2026_paper.html), [arXiv v2](https://arxiv.org/abs/2603.22687v2). PDF tr. 3–7, §3 và Tables 1–4.

Paper dùng image-to-code pairs và iterative pseudo-labeling có similarity filtering; dataset Base khoảng 2,5M. Nhánh Instruct khoảng 419k theo PDF phục vụ generation of auxiliary lines, gắn với reasoning. Đây không phải mặc định một bộ current-TikZ + arbitrary edit instruction.

Pseudo-label quality và lọc là chủ đề có thể tái sử dụng, nhưng CLIP threshold không xác nhận quan hệ hình học. Line-deletion augmentation có thể phù hợp mục tiêu gốc mà không bảo toàn nghĩa của một bài SGK. Số hàng public release có thể khác paper snapshot.

**Áp dụng:** E4/E6 dùng real repair/edit lineage; E7 chỉ áp augmentation có preconditions. Chất lượng downstream reasoning là một endpoint khác, không thay measurement của hình.

### P09 — Edit2TikZ: A Comprehensive and Challenging Benchmark for Scientific Figure Editing with TikZ

**Nguồn:** [PDF local](papers/2608.13441v1.pdf), [arXiv](https://arxiv.org/abs/2608.13441), preprint/work in progress 2026. PDF tr. 3–8, metrics và Tables 4–6.

Benchmark có 1.548 samples, 4.711 edit units; phân biệt change success và preservation. Input chủ yếu gồm image + instruction, vì vậy reconstruction error đi vào editing score. Thử nghiệm với gold source cho thấy compile thay đổi đáng kể trong các model/config được thử; không thể quy toàn bộ hiệu ứng cho khả năng edit.

Paper có validation judge với người trên một subset và curriculum reconstruction→editing. Các kết quả đó tạo hypothesis có ích nhưng không biến VLM judge thành executable verifier, cũng không bảo đảm curriculum thắng trên current-code input của repo.

**Áp dụng:** E4 so reviewed current_tikz với generated current_tikz; báo teacher-forced và rollout riêng. E5 kiểm order với cùng examples/tokens. E6 giữ preservation evidence; không chỉ chấm requested delta.

### P10 — EdiTikZ: Scientific Figure Editing from Revision Trajectories

**Nguồn:** [PDF local](papers/2609.01409v2.pdf), [arXiv](https://arxiv.org/abs/2609.01409), preprint 2026. PDF tr. 4–10, §§3–5 và Tables 3–5.

EdiTikZ khai thác revisions từ arXiv/GitHub/TeX StackExchange, sinh instructions hai chiều, rồi SFT/GDPO. Pipeline trong PDF: 430.442 candidates thuộc 87.051 groups → 390.516 accepted pairs → 781.032 directional trajectories. Benchmark 345 pairs/690 directions là một đơn vị đếm khác.

Audit 125 pairs cho thấy plausibility cao vẫn đi cùng instruction errors đáng kể: khoảng một nửa có ít nhất một lỗi. Vì thế natural revisions không miễn bước semantic review. [DaEdiTikZ public viewer](https://huggingface.co/datasets/nllg/DaEdiTikZ) hiện hiển thị khoảng 106k rows; cần pin release/split/unit trước khi dùng, không sửa paper count theo viewer hoặc ngược lại.

**Áp dụng:** E6 lưu before/after, đúng instruction delta và group lineage. Approved revisions local phù hợp contract current_tikz hơn edit-from-image. Raw model trajectories chưa là training targets; group split phải giữ hai chiều và các revisions họ hàng cùng nguồn.

## 4. Công trình bổ sung: evidence và giả thuyết chuyển giao

### R01 — MathemaTikZ (Learning@Scale 2025)

[Malik, Hao, Kacholia và Demszky](https://doi.org/10.1145/3698205.3729558), [author PDF](https://www.dorademszky.com/publications/49731.pdf), §4/Table 2: thay đổi chất lượng description và TikZ primer trên các model; human-enhanced descriptions hữu ích nhưng primer không đồng đều. Description được viết từ ảnh gốc là điều kiện oracle, không chứng minh pipeline production tự chọn đúng thông tin. **E2:** tách raw instruction, input-only scope và human oracle; cố định model/budget. Nguồn này sát câu hỏi information selection hơn chỉ học cú pháp TikZ.

### R02 — Diagram-MMU (2026)

[Bo et al.](https://arxiv.org/abs/2608.12262), [full text §3.4/§4/Appendix H](https://arxiv.org/html/2608.12262v1): parsing, editing, DQA; dùng semantic objects từ rendered SVG để đối chiếu type/text/color/box. Retrieval/planning không luôn giúp; paper không đánh giá execution-feedback loop trong phạm vi đó. **E1/E4:** object coverage và preservation là diagnostics hữu ích, nhưng box/object F1 không chứng minh góc, độ dài hoặc lời giải đúng. Không xem một kết quả “agentic” như bằng chứng cho loop local.

### R03 — SciTikZ và Dual Self-Consistency RL (2026)

[Lin et al.](https://arxiv.org/abs/2604.06079), [v2, §4.3/§5](https://arxiv.org/html/2604.06079v2): curate execution-centric data, SFT rồi visual/cycle learning; round-trip code→render→code được ràng buộc fidelity để giảm nghiệm suy biến. **E5/E8:** chất lượng curation và reward audit có thể quan trọng trước RL. Self-consistency vẫn có thể nhất quán với một hình sai instruction. Human comparison trên subset cùng compile không thay kết quả all-cases. Đã đọc v1 và kiểm lại round-trip/reward cùng evaluation ở v2; chưa replication hoặc audit code.

### R04 — Math-Vision Diagrams (ICANN 2026 theo arXiv)

[Kashyap et al.](https://arxiv.org/abs/2608.08964), [§3.5/§7.3](https://arxiv.org/html/2608.08964v1): 2.920 images, prompts từ descriptions của các VLM và SME audit trên subset. Paper tự phân biệt caption-conditioned reconstruction với authentic problem-driven generation, và image metrics với mathematical validity. **E0/E2:** ghi provenance của input; không dùng caption từ target như statement nguyên bản. Báo failures toàn bộ và diagnostic common-compile intersection riêng; chọn phần cùng compile vẫn có selection bias.

### R05 — Penrose (SIGGRAPH/TOG 2020)

[Ye et al., author project/paper](https://penrose.cs.cmu.edu/siggraph20/): tách mathematical content khỏi visual style và tối ưu layout dưới constraints. Bài học là có thể có nhiều bố cục hợp lệ cho cùng nội dung. **E0/E2:** đánh giá semantic equivalence theo instruction trước pixel/code equality; omission study giữ nguyên geometry để không lẫn tác động bố cục. Đây là nguồn thiết kế biểu diễn, không là bằng chứng cần chuyển harness sang một DSL mới.

### R06 — Inter-GPS (ACL 2021)

[Lu et al.](https://aclanthology.org/2021.acl-long.528/): formalize text/diagram rồi symbolic reasoning trên Geometry3K. Các phần method/error analysis giúp phân biệt lỗi perception/formalization với lỗi downstream reasoning. **E1:** cùng logic đó, đo extractor và checker riêng. Đây là geometry solving, không phải nghiên cứu generation/editing; solver accuracy không dùng làm drawing-quality score. Mức đọc: metadata/abstract và các phần method/results liên quan, không toàn paper.

### R07 — Why a Diagram is (Sometimes) Worth Ten Thousand Words (1987)

[Larkin và Simon](https://onlinelibrary.wiley.com/doi/10.1111/j.1551-6708.1987.tb00863.x): nền tảng phân biệt thông tin một representation chứa và công sức suy luận để sử dụng nó. **E2:** reader task có thể đo khả năng lấy đúng facts, thời gian và ambiguity. Chỉ xác minh abstract/metadata trong lượt này; không dùng nguồn này để khẳng định hiệu quả một annotation cụ thể hoặc thành tích học sinh.

### R08 — DeFT: A Conceptual Framework for Considering Learning with Multiple Representations (2006)

[Ainsworth, institutional record](https://nottingham-repository.worktribe.com/output/23577631): xem design, functions và tasks cùng nhau khi dùng representations. **E2:** chọn information theo nhiệm vụ người đọc, không tối ưu số annotation thấp nhất. Mức đọc abstract/metadata; đây là conceptual framing, chưa là bằng chứng thực nghiệm cho việc bỏ dấu vuông hoặc dấu bằng trong SGK local.

### R09 — From Text to Visuals (2025)

[Lee et al.](https://arxiv.org/abs/2503.07429), [§§2–4](https://arxiv.org/html/2503.07429v1): SVG diagrams cho math hints, có prompting ablations và VQA evaluation. **E2/E4:** scope của hình cần theo hint/instruction đang yêu cầu; phải biết cái gì thay đổi và cái gì giữ. Cùng một model tham gia generate/evaluate và chưa có student-outcome evidence hạn chế kết luận. Chỉ chuyển giao thiết kế task/evaluation; không nhập dữ liệu ngoài scope lớp 6–12 hoặc đổi output sang SVG.

### R10 — Imperfect Visual Verification for Code Edition: A Case Study on TikZ (2026)

[Reux et al.](https://arxiv.org/abs/2606.15693), [§§3–7](https://arxiv.org/html/2606.15693v1): khảo sát generator/verifier combinations và iterative edits; verifier không hoàn hảo có thể accept sớm hình sai. Feedback phải vừa đúng vừa giúp sửa, hai điều không đồng nhất. **E1/E3:** đo classification, false accept, repair gain và damage riêng. Không diễn giải lời bàn về verifier tổng quát thành kết luận “không thể có deterministic checks”; repo vẫn kiểm được những predicates có contract rõ.

### R11 — Rendering-Aware Reinforcement Learning for Vector Graphics Generation (NeurIPS 2025)

[Rodriguez et al.](https://arxiv.org/abs/2505.20793), [conference PDF, §§3–5](https://papers.nips.cc/paper_files/paper/2025/file/57126328c3b40cf618a34f1c5df24d8a-Paper-Conference.pdf): SFT SVG trước rendering-aware RL; reward kết hợp visual/edge/length signals, và SVG-domain SFT warm-start ảnh hưởng hiệu quả trong setting Im2SVG. **E5/E8:** kiểm syntax/execution và reward component trước đầu tư rollout lớn. SVG similarity không chuyển thẳng thành fidelity toán của TikZ; length penalty cũng có thể làm mất nội dung.

### R12 — Self-Refine: Iterative Refinement with Self-Feedback (NeurIPS 2023)

[Madaan et al., official proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html), §3/Algorithm 1 và Appendix G: một model sinh, nhận xét và sửa; hiệu quả tùy task/model/iteration. **E3:** fixed-budget repair phải so với independent sampling và xét diminishing returns. Kết quả trên bảy tác vụ gốc không phải chứng cứ rằng self-review TikZ local đáng tin.

### R13 — Large Language Models Cannot Self-Correct Reasoning Yet (ICLR 2024)

[Huang et al., official proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html), §§3–4: trong các điều kiện intrinsic correction được thử, model có thể sửa một đáp án đúng thành sai. **E3/E4:** thêm damage/no-op/preservation measurements và external executable feedback. Không hiểu tiêu đề như định lý cho mọi model hiện tại hay mọi dạng feedback; đối tượng paper là reasoning và cấu hình cụ thể.

### R14 — CodeRL: Mastering Code Generation through Pretrained Models and Deep Reinforcement Learning (NeurIPS 2022)

[Le et al., official proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/8636419dea1aa9fbd25fc4248e702da4-Abstract-Conference.html), §3.3.1/§4.4: execution outcomes và critic-guided learning trên code tasks. **E1/E6:** giả thuyết của repo là lưu loại lỗi và repair transitions tạo supervision có ích; CodeRL không thử curated TikZ repair pairs. Unit tests theo task kiểm nhiều semantics hơn compiler TikZ; không chuyển “compile pass” thành “đúng bài”, không cần nhập nguyên RL architecture.

### R15 — Direct Preference Optimization (NeurIPS 2023)

[Rafailov et al., official proceedings](https://papers.nips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html), §3/§7: tối ưu từ preferred/rejected pairs mà không cần PPO hoặc một reward model riêng theo pipeline đó. **E8:** đây là nhánh thử khi đã có local preferences đáng tin, sau SFT. Chất lượng preference và distribution shift vẫn quyết định; paper không chứng minh DPO là lựa chọn tốt nhất cho TikZ.

### R16 — DaVinci: Reinforcing Visual-Structural Syntax in MLLMs for Generalized Scientific Diagram Parsing (ICLR 2026)

[Zeng et al., official proceedings](https://proceedings.iclr.cc/paper_files/paper/2026/hash/8ef4d68682f79c6c9ff0e065232cf141-Abstract-Conference.html): mô tả hai giai đoạn học primitive/syntax và structural-aware RL cho diagram parsing. **E5:** tạo hypothesis về curriculum primitive→composed diagrams. Chỉ xác minh abstract/metadata; chưa dùng làm căn cứ chọn reward chi tiết, hyperparameters hoặc tuyên bố ưu thế. Nếu mở nhánh này, đọc method/code và audit data trước.

## 5. Những cách so sánh dễ dẫn đến kết luận sai

| So sánh dễ nhầm | Cách làm trong protocol |
| --- | --- |
| MCTS/repair nhiều calls vs one-shot rồi quy hết lợi ích cho verifier | Cap toàn bộ author/reviewer/extractor/selector, báo actual spend và best-of-two control |
| Prompt có target-derived description vs statement gốc | Gắn oracle label; main comparison dùng input information tương đương |
| Similarity tốt trên các ca compile | Báo compile và all-case joint accept; subset chỉ diagnostic |
| IR đúng nội tại vs đáp ứng instruction | Required facts và observed facts độc lập; hidden-reference grade không quay lại worker |
| Current-code Edit vs edit-from-image | Hai input regimes tách biệt; decomposition reconstruction/editing |
| Joint vs staged training dùng data/tokens khác nhau | Cùng multiset/tokens/updates; thứ tự là biến can thiệp |
| Repair data thắng vì nhìn thêm source groups | Control cùng source pool và replay bằng token budget |
| Public training corpus lớn vs local dataset | Audit overlap, license, task coverage và source shift trước pooling |
| Một judge đồng ý với chính teacher | Blind human adjudication trên subset và phân tích disagreement; consensus chưa chứng minh truth |

## 6. Approach đề xuất và giá trị kỳ vọng

**Approach A — harness được kiểm định theo yêu cầu đầu vào (E0–E4).** Direct TikZ → shared compiler/render → observed structure → calibrated checks đối chiếu input-side requirements → bounded repair. Contribution cần chứng minh là giảm false acceptance hoặc chi phí đạt joint accept; không phải “có IR” hoặc “có agent”.

**Approach B — dữ liệu repair có lineage và preservation (E5–E6).** Từ approved source groups, lưu final targets và các lần sửa có input/feedback/delta hợp lệ. So final-only, final+repair và final replay bằng tokens. Contribution cần chứng minh là tổng quát hóa ngoài họ hình và ngoài synthetic fault types đã thấy.

**Approach C — information selection theo task (E2, sau đó E5).** Phân biệt candidate facts, construction constraints và visible information; controlled omissions giữ geometry cố định. Đo recoverability/ambiguity, không đặt một checklist dấu hình học cho mọi shape. Nếu input-side annotation giúp, mới thử học selector tại caller boundary; chưa thêm một agent chọn facts trước khi có labels và baseline.

**Approach D — model và harness bổ sung nhau hay thay thế nhau (E9).** Factorial base/SFT × old/selected harness cho biết cải thiện đến từ đâu. Có thể một model tốt hơn cần ít feedback hơn; có thể harness giúp base model gần bằng SFT với chi phí thấp hơn. Đây là câu hỏi thực nghiệm, chưa có kết luận trước chạy.

Augmentation, DPO và online RL là nhánh **có điều kiện**. Mỗi nhánh phải vượt baseline đơn giản tương ứng trên holdout với cost rõ ràng. Không lấy số lượng phương pháp đã triển khai làm thước đo độ hoàn thiện research.
