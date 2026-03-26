import os
import asyncio

class StudioOrchestrator:
    def __init__(self, browser_agent, ai_manager):
        self.agent = browser_agent
        self.ai_studio = ai_manager

    async def create_auto_tutorial(self, scenario_name, steps, scenario_key):
        print(f"🎬 --- BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG: {scenario_name} ---")
        
        # BƯỚC 1: Bot thực hiện thao tác và quay phim
        video_raw, logs = await self.agent.run_scenario(scenario_name, steps)
        
        if not video_raw or not logs:
            print("❌ Lỗi: Bot không tạo được video hoặc log.")
            return

        # BƯỚC 2: AI soạn lời thoại từ Action Logs
        # Ta sẽ gửi 'logs' cho hàm rewrite_segments của mày
        print("🤖 AI đang soạn kịch bản từ các hành động thực tế...")
        
        # Format lại logs cho đúng cấu trúc của AIManager cũ
        raw_segments = []
        for log in logs:
            raw_segments.append({
                "start": log['start'],
                "end": log['start'] + 3.0, # Giả định mỗi câu nói dài 3s
                "text": log['text'],
                "freeze": False
            })

        # Gọi AI chuốt lời (sử dụng logic cũ của mày)
        refined_segments = self.ai_studio.rewrite_segments(raw_segments, scenario_key)
        
        if not refined_segments:
            print("⚠️ AI không chuốt được lời, dùng log gốc.")
            refined_segments = raw_segments

        # BƯỚC 3: Xuất video thành phẩm
        print("🎬 Đang render video lồng tiếng...")
        video_final = os.path.join("recordings", f"{scenario_name}_final.mp4")
        
        # Chỗ này gọi hàm lồng tiếng cũ của Vũ
        success = self.ai_studio.export_final_video(
            video_path=video_raw,
            script_segments=refined_segments,
            output_path=video_final,
            voice_id="vi-VN-HoaiMyNeural" # Giọng Hoài Mỹ cho mượt
        )

        if success:
            print(f"✅ THÀNH CÔNG! Video tại: {video_final}")
            # Mở luôn thư mục chứa video cho Vũ xem
            os.startfile(os.path.abspath("recordings"))
        else:
            print("❌ Render thất bại.")