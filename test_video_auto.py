# main.py
import asyncio
from views.utils_dashboad.video_engine import VideoEngine #D:\ThanhVu\AI_code\Giaiphapvang_Studio_Bot\views\utils_dashboad\video_engine.py

async def main():
    # Giả sử đây là JSON mà Gemini vừa trả về cho Vũ
    script_json = [
        {"action": "speak", "text": "Chào mừng bạn đến với Giải Pháp Vàng. Hôm nay tôi sẽ hướng dẫn tạo khách hàng mới."},
        {"action": "highlight", "target": "#btn-add-customer", "text": "Đầu tiên, hãy nhấn vào nút Thêm mới ở góc màn hình."},
        {"action": "click", "target": "#btn-add-customer"},
        {"action": "type", "target": "#txt-name", "value": "Nguyễn Văn A", "text": "Sau đó bạn nhập tên khách hàng vào đây."},
        {"action": "speak", "text": "Giải Pháp Vàng - Công nghệ cho ngành kim hoàn."}
    ]
    
    engine = VideoEngine(logo_path="assets/logo.png")
    
    # URL là địa chỉ phần mềm ERP của Vũ (localhost hoặc web)
    target_url = "http://localhost:3000/customers" 
    
    print("🎬 Bắt đầu quay phim...")
    await engine.run_studio_bot(
        target_url=target_url,
        script_steps=script_json,
        project_name="Demo_Project",
        form_name="Them_Khach_Hang"
    )

if __name__ == "__main__":
    asyncio.run(main())