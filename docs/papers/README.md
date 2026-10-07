# Paper register — TikZ research

Ngày kiểm tra: **2026-09-28**. Bộ chọn hiện tại: **26 công trình** = 10 PDF người dùng cung cấp + 16 nguồn bổ sung. Không phải số toàn bộ search hits hay số paper độc lập đã replication.

- [Related-work synthesis](../tikz-related-work.md): methods, evidence, giới hạn, transfer.
- [Research protocol](../tikz-research-protocol.md): hypotheses, controls, metrics, gates.
- [Working plan](../tikz-improvement-plan.md): tích hợp vào công việc đang có.

## 1. Phương pháp tìm kiếm và mức độ bằng chứng

Dùng workflow của nature-academic-search và researchwrite. Bắt đầu từ 10 PDF local, đọc method/dataset/evaluation/limitations và kiểm metadata ở nguồn gốc; mở rộng theo references và các cụm truy vấn:

| Chủ đề | Query families được sử dụng |
| --- | --- |
| Synthesis/reconstruction | TikZ generation, text-to-TikZ, image-to-TikZ, graphics program synthesis |
| Editing/data | TikZ editing, revision trajectories, instruction-guided diagram editing |
| Verification/harness | geometric diagram verification, visual verification TikZ, execution feedback, self-refinement |
| Training | rendering-aware reinforcement learning, TikZ fine-tuning, preference optimization, execution-centric data |
| Information selection | mathematical diagram descriptions, Penrose, diagram representations, DeFT |

**Nguồn:** arXiv, proceedings chính thức (ICLR/NeurIPS/ACL/ACM), publisher/institutional author pages và dataset cards được paper liên kết. Ưu tiên nghiên cứu có method/evaluation rõ; các paper nền tảng được giữ để đặt hypothesis, không dùng thay evidence TikZ.

Nature MCP đã truy vấn arXiv/Crossref. Nhánh arXiv trả HTTP 406; Crossref theo keyword có nhiều kết quả tutorial không phù hợp. Preflight local của skill thất bại kết nối (WinError 10061); không coi như đã tìm thành công trên mọi service. Tiếp tục bằng web search trên nguồn primary và DOI lookup qua MCP khi khả dụng. Không dùng citation counts hoặc kết quả từ blog/aggregator làm bằng chứng cho claims.

Deduplicate bằng arXiv ID/DOI/title; nhiều phiên bản của một paper là một công trình. Bản local là version anchor cho P01–P10. Với nguồn mới, version/phần đọc ghi bên dưới. “Method/results” nghĩa là đã đọc các phần đó qua full text, không tuyên bố đã audit mọi equation/appendix hoặc reproduce code. “Abstract” chỉ hỗ trợ framing/description, không đủ chọn implementation/hyperparameters.

Loại các kết quả không có contribution liên quan, tutorial LaTeX đơn thuần và claims chỉ từ secondary summaries. Chưa làm systematic screening với toàn bộ hit log; không dựng PRISMA counts hoặc kết luận search coverage đầy đủ. Paper datasets là related evidence/possible future auxiliary data, **không thay corpus curriculum local**.

## 2. Mười PDF local

| ID | Citation / version đọc | Local PDF | Điểm đọc phục vụ synthesis |
| --- | --- | --- | --- |
| P01 | Belouadi, Lauscher & Eger. **AutomaTikZ: Text-Guided Synthesis of Scientific Vector Graphics with TikZ.** ICLR 2024. arXiv 2310.00367v2 | [27 trang](2310.00367v2.pdf) · [primary](https://arxiv.org/abs/2310.00367v2) | §§3–6, tr. 4–9; data/SFT, metric attacks |
| P02 | Belouadi, Ponzetto & Eger. **DeTikZify: Synthesizing Graphics Programs for Scientific Figures and Sketches with TikZ.** NeurIPS 2024. arXiv 2405.15306v3 | [29 trang](2405.15306v3.pdf) · [primary](https://arxiv.org/abs/2405.15306v3) | §5, Tables 2–5, tr. 4–10; MCTS và cost |
| P03 | Wang et al. **MagicGeo: Training-Free Text-Guided Geometric Diagram Generation.** Preprint 2025. arXiv 2502.13855v1 | [12 trang](2502.13855v1.pdf) · [primary](https://arxiv.org/abs/2502.13855v1) | Method/ablations, tr. 3–7; limits tr. 9 |
| P04 | Belouadi et al. **TikZero: Zero-Shot Text-Guided Graphics Program Synthesis.** ICCV 2025. arXiv 2503.11509v3 | [20 trang](2503.11509v3.pdf) · [ICCV official](https://openaccess.thecvf.com/content/ICCV2025/html/Belouadi_TikZero_Zero-Shot_Text-Guided_Graphics_Program_Synthesis_ICCV_2025_paper.html) · [arXiv](https://arxiv.org/abs/2503.11509v3) | §§3–6, tr. 3–8; alignment/data/metrics |
| P05 | Kumar et al. **DiagramIR: An Automatic Pipeline for Educational Math Diagram Evaluation.** 2025. arXiv 2511.08283v1 | [18 trang](2511.08283v1.pdf) · [primary](https://arxiv.org/abs/2511.08283v1) | §2/Tables 1–3, tr. 1–5; IR/evaluation |
| P06 | Wei et al. **GeoLoom: High-quality Geometric Diagram Generation from Textual Input.** ICML 2026 theo v2. arXiv 2512.08180v2 | [22 trang](2512.08180v2.pdf) · [primary](https://arxiv.org/abs/2512.08180v2) | Method/data/Tables 1, 4, tr. 3–9 |
| P07 | Greisinger & Eger. **TikZilla: Scaling Text-to-TikZ with High-Quality Data and Reinforcement Learning.** ICLR 2026. arXiv 2603.03072v3 | [33 trang](2603.03072v3.pdf) · [primary](https://arxiv.org/abs/2603.03072v3) | §§4–6/Tables 3–5, tr. 4–10 |
| P08 | Sun et al. **GeoTikzBridge: Advancing Multimodal Code Generation for Geometric Perception and Reasoning.** CVPR 2026. arXiv 2603.22687v2 | [25 trang](2603.22687v2.pdf) · [CVPR official](https://openaccess.thecvf.com/content/CVPR2026/html/Sun_GeoTikzBridge_Advancing_Multimodal_Code_Generation_for_Geometric_Perception_and_Reasoning_CVPR_2026_paper.html) · [arXiv](https://arxiv.org/abs/2603.22687v2) | §3/Tables 1–4, tr. 3–7 |
| P09 | Zhang et al. **Edit2TikZ: A Comprehensive and Challenging Benchmark for Scientific Figure Editing with TikZ.** Preprint/work in progress 2026. arXiv 2608.13441v1 | [9 trang](2608.13441v1.pdf) · [primary](https://arxiv.org/abs/2608.13441v1) | Metrics/Tables 4–6, tr. 3–8 |
| P10 | Greisinger, Zhao & Eger. **EdiTikZ: Scientific Figure Editing from Revision Trajectories.** Preprint 2026. arXiv 2609.01409v2 | [35 trang](2609.01409v2.pdf) · [primary](https://arxiv.org/abs/2609.01409v2) | §§3–5/Tables 3–5, tr. 4–10 |

Trang ở đây là PDF page 1-based, không nhất thiết số trang in trên paper. Venue chỉ nêu theo nguồn đã kiểm; arXiv version date không dùng thay publication year.

## 3. Mười sáu nguồn bổ sung

Giữ primary links để truy cập lawful full text; chưa tải thêm bản PDF vào repo.

| ID | Citation | Primary source / mức đọc |
| --- | --- | --- |
| R01 | Malik, Hao, Kacholia & Demszky. **MathemaTikZ: A Dataset and Benchmark for Mathematical Diagram Generation.** Learning@Scale 2025, 95–104. DOI **10.1145/3698205.3729558** | [DOI](https://doi.org/10.1145/3698205.3729558) · [author PDF](https://www.dorademszky.com/publications/49731.pdf). Method §4/Table 2, PDF tr. 5–6; metadata Crossref |
| R02 | Bo et al. **Diagram-MMU: A Multi-Modal Benchmark for Scientific Diagrams.** 2026, arXiv 2608.12262v1 | [primary](https://arxiv.org/abs/2608.12262v1) · [HTML](https://arxiv.org/html/2608.12262v1). Method/results §3.4/§4, Appendix H |
| R03 | Lin et al. **Scientific Graphics Program Synthesis via Dual Self-Consistency Reinforcement Learning.** 2026, arXiv 2604.06079 | [primary](https://arxiv.org/abs/2604.06079) · [HTML v1](https://arxiv.org/html/2604.06079v1) · [HTML v2](https://arxiv.org/html/2604.06079v2). Đọc §§3–5/limitations ở v1; kiểm lại §4.3/§5 ở v2 |
| R04 | Kashyap et al. **Math-Vision Diagrams: A Comprehensive Benchmark for Evaluating LLM Mathematical Diagram Generation Capabilities.** ICANN 2026 theo arXiv, 2608.08964v1 | [primary](https://arxiv.org/abs/2608.08964v1) · [HTML](https://arxiv.org/html/2608.08964v1). Method/limitations §3.5/§7.3; [dataset card](https://huggingface.co/datasets/mathdiagrams/MathVisionBenchmark) |
| R05 | Ye et al. **Penrose: From Mathematical Notation to Beautiful Diagrams.** ACM TOG 39(4), Article 144, 2020. DOI 10.1145/3386569.3392375 | [author project](https://penrose.cs.cmu.edu/siggraph20/) · [author PDF](https://www.cs.cmu.edu/~jssunshi/assets/pdf/penrose.pdf). Representation/method sections liên quan |
| R06 | Lu et al. **Inter-GPS: Interpretable Geometry Problem Solving with Formal Language and Symbolic Reasoning.** ACL-IJCNLP 2021. DOI 10.18653/v1/2021.acl-long.528 | [ACL record/PDF](https://aclanthology.org/2021.acl-long.528/). Metadata/abstract + selected method/results, Tables 5/7 |
| R07 | Larkin & Simon. **Why a Diagram is (Sometimes) Worth Ten Thousand Words.** Cognitive Science 11, 65–100, 1987. DOI 10.1111/j.1551-6708.1987.tb00863.x | [publisher](https://onlinelibrary.wiley.com/doi/10.1111/j.1551-6708.1987.tb00863.x). Abstract/metadata; conceptual framing only |
| R08 | Ainsworth. **DeFT: A Conceptual Framework for Considering Learning with Multiple Representations.** Learning and Instruction 16(3), 183–198, 2006. DOI 10.1016/j.learninstruc.2006.03.001 | [institutional record](https://nottingham-repository.worktribe.com/output/23577631). Abstract/metadata; conceptual framing only |
| R09 | Lee, Lee, Feng & Lan. **From Text to Visuals: Using LLMs to Generate Math Diagrams with Vector Graphics.** 2025, arXiv 2503.07429v1 | [primary](https://arxiv.org/abs/2503.07429v1) · [HTML](https://arxiv.org/html/2503.07429v1). §§2–4, task/prompt/evaluation |
| R10 | Reux, Acher, Khelladi, Quinton & Barais. **Imperfect Visual Verification for Code Edition: A Case Study on TikZ.** 2026, arXiv 2606.15693v1 | [primary](https://arxiv.org/abs/2606.15693v1) · [HTML](https://arxiv.org/html/2606.15693v1). §§3–7, verification/feedback experiments |
| R11 | Rodriguez et al. **Rendering-Aware Reinforcement Learning for Vector Graphics Generation.** NeurIPS 2025, arXiv 2505.20793 | [arXiv](https://arxiv.org/abs/2505.20793) · [conference PDF](https://papers.nips.cc/paper_files/paper/2025/file/57126328c3b40cf618a34f1c5df24d8a-Paper-Conference.pdf). §§3–5/Tables 1–2 |
| R12 | Madaan et al. **Self-Refine: Iterative Refinement with Self-Feedback.** NeurIPS 2023, arXiv 2303.17651 | [official proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html). §3/Algorithm 1, Appendix G |
| R13 | Huang et al. **Large Language Models Cannot Self-Correct Reasoning Yet.** ICLR 2024, arXiv 2310.01798 | [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html). §§3–4/Tables 4–6, scoped to intrinsic correction |
| R14 | Le et al. **CodeRL: Mastering Code Generation through Pretrained Models and Deep Reinforcement Learning.** NeurIPS 2022, arXiv 2207.01780 | [official proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/8636419dea1aa9fbd25fc4248e702da4-Abstract-Conference.html). §3.3.1/§4.4 |
| R15 | Rafailov et al. **Direct Preference Optimization: Your Language Model is Secretly a Reward Model.** NeurIPS 2023, arXiv 2305.18290 | [official proceedings](https://papers.nips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html). §3/§7 |
| R16 | Zeng et al. **DaVinci: Reinforcing Visual-Structural Syntax in MLLMs for Generalized Scientific Diagram Parsing.** ICLR 2026 | [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2026/hash/8ef4d68682f79c6c9ff0e065232cf141-Abstract-Conference.html) · [OpenReview PDF](https://openreview.net/pdf?id=OAXECnLxuk). Abstract/metadata only |

## 4. Xung đột metadata và cautions

- **MathemaTikZ DOI:** author page gắn DOI 10.1145/3657604.3664698, nhưng Crossref trả về paper khác (*Scaling High-Leverage Curriculum Scaffolding in Middle-School Mathematics*, 2024). DOI đúng theo Crossref cho MathemaTikZ là **10.1145/3698205.3729558**. Author PDF dùng title *A Benchmark for K-12 Mathematical Diagram Generation*; catalog dùng published title. Không copy DOI từ author page một cách máy móc.
- **DaEdiTikZ units/release:** PDF v2 báo 390.516 edit pairs/781.032 directional trajectories; [HF viewer](https://huggingface.co/datasets/nllg/DaEdiTikZ) hiển thị khoảng 106k rows ở snapshot đã xem. Mỗi row có i/j code/images, instructions hai chiều và group_id. Cần pin revision/config/split và count bằng loader trước dùng; không xem các số này là cùng một snapshot hay đơn vị.
- **GeoTikzBridge release:** PDF Instruct khoảng 419k, public viewer có thể hiện khoảng 421k. Count sau load đúng release mới là count training; không hand-enter paper count vào local manifest.
- **DaTikZ v3 count:** TikZero Table 1 báo 456.469 programs; TikZilla Table 2 báo 456.407. Giữ count gắn với paper snapshot; chưa xác định khác biệt release/đơn vị nên không gộp thành một số chuẩn.
- **TikZilla ablation:** không trích diễn giải caption-mixing như kết luận chắc chắn khi hướng biến thiên không khớp Table 4. Dùng local ablation để kiểm hypothesis curriculum.
- **SciTikZ version:** bản hiện tại v2 (2026-08-28); sau đọc v1 đã kiểm lại fidelity-gated round-trip reward và evaluation §4.3/§5 ở v2. Chưa audit code/appendix diff; cần làm trước khi tái hiện training.
- Không so AVG chuẩn hóa giữa các paper; không đồng nhất compile success, κ agreement, visual similarity, reasoning accuracy, preference và joint accept. Mỗi source có task/input/denominator khác nhau.

## 5. Dấu vân tay PDF local

SHA-256 và số trang được đọc từ chính các file trong thư mục này, giúp phát hiện khi version thay đổi. Không phải chữ ký xác nhận mọi claim của paper.


| File | Pages | SHA-256 |
| --- | ---: | --- |
| 2310.00367v2.pdf | 27 | 63e0f81a525dff822d6134d8b69e8c255ef7c4301c89caef5bddb8ced778dab5 |
| 2405.15306v3.pdf | 29 | a342217524b16e7392c1d35fb87f7f27779980caa07b46d74f97fd44aa035209 |
| 2502.13855v1.pdf | 12 | 18c827ba09288e52107e4388e3da40f2eef8e86544153eaf2d644480330f2038 |
| 2503.11509v3.pdf | 20 | bf1370a49a72857eeae3f6fdd4895db53163a66be91245fa8bf8c35502c57b17 |
| 2511.08283v1.pdf | 18 | ba2c13864ea624f4b9d4c7851a468ba97627522a36031785cd15db7876959943 |
| 2512.08180v2.pdf | 22 | f75fae833d0e3171377c3cc1423ddf99634c8392aff16329ad4968429577d8c9 |
| 2603.03072v3.pdf | 33 | 3e4d4dc2e30be538434330223b7c8e91f94e154463a77c7c8ee2b527093dfafe |
| 2603.22687v2.pdf | 25 | f351c449c7df3d76890866d590dbbbd2bc397333e61285d426ded93f354f1ac0 |
| 2608.13441v1.pdf | 9 | 42822f96852b1e9be3bd2d65b8bf76583c6199170f1602b15f27e9a11d01b205 |
| 2609.01409v2.pdf | 35 | 9760537de116b9dd00bcc0113bbefc99b4f24c1014bc96148e86f40c7e028e52 |
