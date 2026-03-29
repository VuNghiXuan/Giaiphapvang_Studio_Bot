"""
Bước 1: Nâng cấp "Bộ não" AI (Kịch bản Đạo diễn)
Vũ đừng để AI soạn văn bản thô nữa. Hãy bắt Gemini trả về một Mảng JSON các hành động. Mỗi hành động phải gắn liền với một selector (ID/Class của nút) và câu thoại tương ứng.

Input: Metadata từ DB (danh sách field, button).

Output (JSON):

JSON
[
  {"act": "move", "target": "#menu_chinhanh", "speech": "Đầu tiên, Hoài My sẽ mở mục Chi nhánh nhé."},
  {"act": "click", "target": "#btn_add", "speech": "Tiếp theo, mình bấm vào nút Tạo mới ở góc màn hình."},
  {"act": "type", "target": "input[name='branch_name']", "val": "Quận 1", "speech": "Tại đây, Vũ chỉ cần nhập tên chi nhánh là Quận 1."}
]
Bước 2: Lồng tiếng trước (Voice Pre-gen)
Trước khi Bot mở trình duyệt, hãy chạy edge-tts để chuyển toàn bộ các câu speech trong JSON thành file âm thanh.

Cách làm: Duyệt mảng JSON, gọi edge-tts tạo ra 1.mp3, 2.mp3,... lưu vào folder temp_voice.

Tại sao: Để khi Bot chạy, mình biết chính xác mỗi câu thoại dài bao nhiêu giây để điều khiển tốc độ chuột cho khớp.

Bước 3: Cấu hình "Máy quay" (Playwright Recorder)
Vũ dùng tính năng quay phim màn hình tích hợp sẵn của Playwright. Nó rất nhẹ và nét.

Python
browser = await p.chromium.launch()
context = await browser.new_context(
    record_video_dir="recordings/", # Tự động quay phim
    record_video_size={"width": 1280, "height": 720}
)
page = await context.new_page()
Bước 4: Bot "Tự diễn" (The Orchestrator)
Đây là trái tim của hệ thống. Vũ chạy một vòng lặp đi qua từng bước trong kịch bản JSON:

Phát âm thanh: Dùng một thư viện Python (như pygame hoặc playsound) để phát file n.mp3.

Lấy độ dài: Kiểm tra file MP3 đó dài bao nhiêu giây (VD: 5 giây).

Diễn xuất: Điều khiển Playwright di chuyển chuột từ từ (Smooth move) đến mục tiêu và thực hiện hành động (Click/Type).

Đợi: Phải có lệnh await page.wait_for_timeout(duration_of_mp3) để đảm bảo Hoài My nói xong câu đó thì mới sang hành động tiếp theo.

Bước 5: Đóng gói thành phẩm (Final Render)
Sau khi Playwright đóng trình duyệt, Vũ sẽ có một file video .webm (không có tiếng).

Xử lý: Dùng FFmpeg để trộn tất cả các file MP3 lẻ vào file video đó theo đúng mốc thời gian.

Kết quả: Một file .mp4 hoàn chỉnh, có tiếng Hoài My lồng khít vào từng cú click chuột của Bot.

Tại sao cách này lại "Đỉnh"?
Chuột di chuyển như người: Vũ có thể code hàm smooth_mouse_move để chuột không "biến hình" mà di chuyển lướt trên màn hình.

Không lệch pha: Vì mình biết độ dài file MP3, mình bắt Bot phải chờ tiếng nói xong mới làm tiếp.

Tự động 100%: Vũ chỉ cần đưa URL và Metadata, hệ thống tự "đẻ" ra video marketing.

Vũ muốn tôi viết code mẫu cho cái hàm "Smooth Mouse Move" (Di chuyển chuột mượt mà) để video trông thật hơn không? Dân kỹ thuật nhìn chuột di chuyển mượt mới thấy sướng mắt!
"""