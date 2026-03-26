import asyncio
import os
import sys
from dotenv import load_dotenv

# Import các module cốt lõi từ thư mục core
from core.browser_agent import BrowserAgent
from core.ai_manager import AIManager
from core.auto_knowledge_base import KnowledgeBase

# Load biến môi trường từ file .env
load_dotenv()

async def main():
    # 1. Khởi tạo các thành phần hệ thống
    kb = KnowledgeBase()
    agent = BrowserAgent()
    ai_studio = AIManager() 

    # 2. Kiểm tra thông tin đăng nhập từ .env
    email_login = os.getenv("USER_EMAIL")
    pass_login = os.getenv("USER_PASSWORD")

    if not email_login or not pass_login:
        print("❌ LỖI: Vũ chưa cấu hình USER_EMAIL hoặc USER_PASSWORD trong file .env kìa!")
        return

    # 3. Lấy kịch bản từ KnowledgeBase
    scenario_key = "login_system" 
    scene = kb.scenarios.get(scenario_key)
    
    if not scene:
        print(f"❌ LỖI: Không tìm thấy kịch bản '{scenario_key}' trong KnowledgeBase.")
        return
        
    steps_config = scene['selectors']

    # 4. Định nghĩa quy trình thao tác chi tiết (Sử dụng Selector thông minh)
    script_steps = [
        {
            "action": "goto", 
            "selector": steps_config['url'], 
            "description": "Truy cập vào trang đăng nhập hệ thống Giải Pháp Vàng."
        },
        {
            "action": "fill", 
            "selector": steps_config['email'], 
            "value": email_login, 
            "description": "Nhập tài khoản email quản trị."
        },
        {
            "action": "fill", 
            "selector": steps_config['password'], 
            "value": pass_login, 
            "description": "Nhập mật khẩu bảo mật."
        },
        {
            "action": "click", 
            "selector": steps_config['submit'], 
            "description": "Nhấn nút Đăng nhập để bắt đầu phiên làm việc."
        },
        {
            "action": "wait", 
            "value": steps_config['btn_he_thong'], 
            "description": "Đợi màn hình điều hướng (App Launcher) xuất hiện."
        },
        {
            "action": "click", 
            "selector": steps_config['btn_he_thong'], 
            "description": "Truy cập vào phân hệ Hệ thống."
        },
        {
            "action": "wait", 
            "value": steps_config['dashboard_verify'], 
            "description": "Đã đăng nhập và vào màn hình Dashboard thành công."
        }
    ]

    print(f"🎬 --- BẮT ĐẦU QUY TRÌNH: {scene['title']} ---")

    # --- BƯỚC 1: CHẠY BOT VÀ QUAY VIDEO ---
    # Lúc này BrowserAgent sẽ vừa click vừa 'cào' page_context ở mỗi bước
    video_raw, action_logs = await agent.run_scenario(scenario_key, script_steps)
    
    if not video_raw or not action_logs:
        print("❌ Quy trình thất bại ở bước quay phim. Vũ kiểm tra lại file ảnh timeout nhé!")
        return

    print(f"✅ Đã có video thô và {len(action_logs)} mốc dữ liệu trang web.")

    # --- BƯỚC 2: AI BIÊN SOẠN KỊCH BẢN (Dựa trên context đã cào) ---
    print("🤖 AI đang phân tích dữ liệu màn hình và viết lời thoại...")
    refined_segments = ai_studio.rewrite_segments(action_logs, scenario_key)

    if not refined_segments:
        print("❌ AI không thể tạo lời thoại từ dữ liệu logs.")
        return

    # --- BƯỚC 3: LỒNG TIẾNG VÀ RENDER VIDEO CUỐI CÙNG ---
    output_final = os.path.join("recordings", f"{scenario_key}_FINAL_STUDIO.mp4")
    
    print("🎙️ Đang lồng tiếng và trộn video...")
    success = ai_studio.export_final_video(
        video_path=video_raw,
        script_segments=refined_segments,
        output_path=output_final
    )

    # --- KẾT THÚC ---
    if success:
        print("\n" + "="*50)
        print(f"🚀 THÀNH CÔNG RỰC RỠ VŨ ƠI!")
        print(f"📍 Video thành phẩm: {os.path.abspath(output_final)}")
        print("="*50)
        
        # Tự động mở video để Vũ 'nghiệm thu'
        if sys.platform == "win32":
            os.startfile(os.path.abspath(output_final))
    else:
        print("❌ Lỗi trong quá trình render video cuối cùng.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng chương trình theo yêu cầu.")