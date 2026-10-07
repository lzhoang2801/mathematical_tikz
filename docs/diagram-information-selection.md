# Chọn dữ kiện cần truyền đạt qua hình

Ghi nhận từ trao đổi ngày 2026-09-22. Đây là một bài toán nghiên cứu chính của TikZ improvement, xuất hiện khi harness biến định nghĩa hình vuông thành yêu cầu đánh dấu cả bốn góc vuông. Thêm ngoại lệ cho từng loại hình không giải quyết được việc lựa chọn thông tin.

**Câu hỏi chính:** từ đề bài, phạm vi vẽ hiện tại và hình đang có, xác định được bao nhiêu dữ kiện ứng viên; dữ kiện nào phải giữ để dựng đúng; dữ kiện nào cần được người đọc nhận ra trực tiếp; và phần thể hiện nào thực sự đóng góp vào việc hiểu bài?

## Ba tập cần phân biệt

| Tập | Vai trò | Ví dụ từ bài hình vuông cạnh 5 cm |
| --- | --- | --- |
| Dữ kiện ứng viên | Các mệnh đề có nguồn trong đề/yêu cầu hiện tại, cùng hệ quả định nghĩa cần xét | Loại hình là hình vuông; độ dài cạnh; các quan hệ do định nghĩa hình vuông quy định |
| Ràng buộc dựng hình | Những điều phải đúng trong hình học của output | Cạnh bằng nhau, góc vuông, độ dài phù hợp; không được bỏ chỉ vì không vẽ ký hiệu |
| Thông tin cần thể hiện | Nội dung cần truyền đạt bằng hình dạng, nét, nhãn, dấu hoặc số đo | Hình dạng và độ dài dựng; có cần thêm dấu góc, dấu bằng cạnh hoặc nhãn số đo hay không tùy yêu cầu và vai trò của chúng |

Một ràng buộc có thể được thể hiện qua chính cấu hình hình học, không cần một ký hiệu riêng. Ngược lại, nhìn có vẻ vuông góc hoặc bằng nhau không chứng minh rằng tọa độ đã thỏa điều kiện. Chọn nội dung và dựng đúng nội dung là hai trách nhiệm khác nhau.

## Chia nhỏ để giải quyết

1. **Định nghĩa đơn vị dữ kiện và giới hạn tập ứng viên.** Tách dữ kiện gốc, hệ quả định nghĩa và kết luận cần chứng minh. Không lấy toàn bộ bao đóng suy diễn vì có thể sinh vô hạn phát biểu tương đương. Quy định cách gộp mệnh đề trùng, cách xử lý điều kiện nhiều vế và mức khai triển một đối tượng có tên. Chưa chốt đơn vị này thì các con số candidate không so sánh được.
2. **Gắn dữ kiện với phạm vi hiện tại.** Generate xét bài hoàn chỉnh và yêu cầu vẽ; Edit xét thay đổi được yêu cầu cùng phần phải giữ của hình hiện tại; Reconstruct xét thông tin toán học nhìn thấy ở crop. Không tự ý bỏ chi tiết của crop chỉ vì nó ít hữu ích cho một lời giải giả định. Kết luận chưa chứng minh không tự động trở thành quan hệ được đánh dấu.
3. **Xác định vai trò.** Phân biệt đối tượng chính, quan hệ xác định cấu hình, đối tượng hỗ trợ, thông tin phân biệt nhánh/thứ tự, nhãn nhận diện, số đo và cách ký hiệu. Ghi lý do một dữ kiện có ích cho người đọc; không suy ra vai trò chỉ từ tên chương hoặc loại hình.
4. **Chọn cách truyền đạt.** Một dữ kiện có thể được truyền đạt qua hình dạng, đường hỗ trợ, vị trí/thứ tự điểm, nhãn hoặc ký hiệu. Quyết định cần thêm biểu hiện nào để tránh mơ hồ, đồng thời tránh lặp lại thông tin đã rõ. Không đồng nhất “được thể hiện” với “có thêm một dấu”.
5. **Đo đóng góp bằng can thiệp.** Giữ cấu hình và bố cục tương đương, bỏ một nhãn/dấu/đường hỗ trợ hoặc một nhóm thành phần rồi đánh giá điều gì trở nên thiếu hay mơ hồ. Tách thí nghiệm bỏ ký hiệu khỏi thí nghiệm bỏ ràng buộc hình học: thay đổi tọa độ có thể làm sai hình thay vì chỉ giảm thông tin.
6. **Hiệu chỉnh với người đọc.** Có thể có nhiều cách vẽ đủ thông tin. Thu thập lựa chọn chấp nhận được, lý do bất đồng và đánh giá cặp hình. Kiểm tra bỏ từng thành phần lẫn bỏ theo nhóm vì các biểu hiện có thể thay thế nhau hoặc chỉ hữu ích khi cùng xuất hiện.

## Annotation thử nghiệm

Các hướng đóng góp để khảo sát là: bộ annotation có nguồn cho candidate và vai trò thông tin; phương pháp chọn phần cần thể hiện theo yêu cầu vẽ; và thí nghiệm tách lỗi lựa chọn thông tin khỏi lỗi sinh TikZ. Đây mới là giả thuyết nghiên cứu, chưa phải tuyên bố tính mới hoặc kết quả đã chứng minh.

Làm annotation ngoại tuyến trước khi thêm hành vi vào harness. Với mỗi mẫu, lưu phạm vi/yêu cầu vẽ, mệnh đề ứng viên, nguồn đối chiếu, loại gốc/định nghĩa/kết luận, ràng buộc dựng hình tương ứng, cách thể hiện được đề xuất, lý do giữ/bỏ và trạng thái người duyệt. Không yêu cầu model worker tạo một sổ nghĩa vụ hoặc representation trung gian.

Chỉ tính các số sau từ annotation đã có, không điền số minh họa:

- Số candidate theo cùng một quy tắc tách mệnh đề và phiên bản annotation.
- Số candidate cần cho dựng hình đúng.
- Số candidate cần được người đọc nhận ra trong phạm vi hiện tại.
- Số thành phần thể hiện thực tế; một dấu hoặc nét có thể phục vụ nhiều dữ kiện.
- Dữ kiện quan trọng bị bỏ sót, phần thể hiện dư và trường hợp người duyệt chưa thống nhất.

Những số này phục vụ phân tích lỗi và nghiên cứu lựa chọn thông tin. Chúng không thay bốn tiêu chí đánh giá chung: compile, đúng toán/cấu trúc, đầy đủ và dễ đọc; không được dùng để thưởng việc vẽ càng ít càng tốt.

## Thử nghiệm đầu tiên

Lấy hai bài nguồn đã có trong [pilot](dataset-selection/tikz-pilot.jsonl) làm ví dụ mở đầu, rồi bổ sung trường hợp mà hình dạng đơn thuần không đủ: chân đường cao nằm ngoài cạnh, hai giao điểm có thứ tự khác nhau, tiếp tuyến, hình không gian và biểu diễn đại số có miền/nhánh/dấu. Chỉ đưa các trường hợp vào tập khi tìm được nguồn thật phù hợp.

So sánh: chỉ đề bài; đề bài kèm phạm vi vẽ rõ; và đề bài kèm mô tả thông tin cần truyền đạt do người duyệt biên soạn. Trường hợp cuối là điều kiện oracle để chẩn đoán, không phải baseline production và không được làm rò reference vào worker trong benchmark chuẩn. Đánh giá xem lỗi nằm ở hiểu đề, lựa chọn nội dung, cách mã hóa hình học, bố cục hay reviewer.

Trong pilot hiện tại, lỗi nét góc vuông thừa ở A là một triệu chứng quan sát được. Nó chưa chứng minh mọi ký hiệu góc đều thừa, hoặc mọi hình ít dấu hơn đều tốt hơn. Các target đề xuất vẫn chờ người duyệt.

## Ranh giới triển khai

- `problem_tikz` chỉ nhận `instruction` bắt buộc và `current_tikz` tùy chọn. Mỗi lần gọi độc lập, không tự lấy bài toán, lời giải hoặc lịch sử từ caller. Author và reviewer cùng nhận instruction và TikZ đầu vào của lần gọi đó.
- Author của solve harness chịu trách nhiệm chọn dữ kiện, mô tả đủ các đối tượng/điều kiện và phạm vi dựng hình theo bước lập luận. Drawing harness chịu trách nhiệm hiện thực hóa và trình bày phạm vi đó; nó không tự quyết định cần dựng thêm gì cho lời giải. Caller có thể giữ hình đã chấp nhận và truyền lại rõ ràng cho yêu cầu sửa tiếp theo.
- Dataset Generate phải biên soạn instruction từ bài nguồn đầy đủ; Edit phải nêu đủ điều kiện của phần thay đổi. Việc chọn dữ kiện để đưa vào instruction là một phần của bài toán nghiên cứu, không phải lý do để tự động nhét toàn bộ đề bài vào drawing harness.
- Annotation lựa chọn dữ kiện là dữ liệu phân tích bên ngoài workflow, không phải Diagram IR hoặc một graph mới.
- Không biến các ví dụ hình vuông/tam giác thành danh sách ngoại lệ. Trước hết kiểm tra sự nhất quán giữa prompt, reviewer và evaluator; sau đó dùng tập annotation để đo tác động của thay đổi.
