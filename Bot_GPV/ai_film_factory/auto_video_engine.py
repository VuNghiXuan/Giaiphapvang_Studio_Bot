import asyncio
import os
import time
import json
from playwright.async_api import async_playwright

# Import các module nội bộ của Vũ
from .audio_machine import AudioMachine
from .studio_machine import StudioMachine
from .post_production_machine import PostProductionMachine
from .effect_machine import EffectMachine
from .vision_machine import VisionMachine
from .auth_machine import AuthMachine 
from config import Config 

class AutoVideoEngine:
    def __init__(self, storage_path=None, logo_path="assets/logo.png", **kwargs):
        self.storage_path = storage_path or getattr(Config, 'BASE_STORAGE', "./storage")
        self.logo_path = logo_path
        self.target_domain = os.getenv("TARGET_DOMAIN", "https://giaiphapvang.net")
        
        # 1. Khởi tạo "Con mắt" AI (Bản Sync - KHÔNG dùng await)
        self.vision = VisionMachine()
        
        # 2. Khởi tạo bộ phận Đăng nhập
        self.auth_machine = AuthMachine(vision_machine=self.vision)
        
        # 3. Khởi tạo "Diễn viên"
        self.studio_machine = StudioMachine(self.target_domain, self.vision)
        
        # 4. Hỗ trợ âm thanh và hậu kỳ
        self.voice_config = kwargs.get('voice', 'vi-VN-HoaiMyNeural')
        self.audio_machine = AudioMachine(voice=self.voice_config)
        self.effect_machine = EffectMachine()
        self.post_machine = PostProductionMachine(self.logo_path)

    def check_ready_for_production(self, script_steps, logo_path=None):
        path_to_check = logo_path or self.logo_path
        checks = {
            "env_auth": bool(os.getenv("USER_EMAIL") and os.getenv("USER_PASSWORD")),
            "script_valid": isinstance(script_steps, list) and len(script_steps) > 0,
            "logo_exists": os.path.exists(path_to_check) if path_to_check else False,
        }
        missing = [k for k, v in checks.items() if not v]
        return len(missing) == 0, missing


    async def run_studio_bot(self, target_url, script_steps, project_name, form_name):
        """
        QUY TRÌNH: Kiểm tra -> Đăng nhập -> Diễn xuất -> Chốt Video -> Hậu kỳ
        """
        # 1. Kiểm tra sẵn sàng & Tinh lọc kịch bản
        script_steps = self._refine_script(script_steps)
        ready, missing = self.check_ready_for_production(script_steps)
        if not ready:
            print(f"🚨 Engine chưa sẵn sàng. Thiếu: {missing}")
            return None

        # 2. Khởi tạo đường dẫn lưu trữ
        video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
        os.makedirs(video_dir, exist_ok=True)
        
        audio_sync_data = []
        audio_paths = []
        raw_video_path = None

        async with async_playwright() as p:
            # 3. Khởi tạo trình duyệt
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
            
            # Record video cần context riêng để quản lý file
            context = await browser.new_context(
                no_viewport=True, 
                record_video_dir=video_dir, 
                record_video_size={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                # 4. Đăng nhập & Điều hướng (Phải có await)
                if not await self.auth_machine.login(page):
                    print("❌ Đăng nhập thất bại, dừng diễn xuất.")
                    return None
                
                print(f"🚀 Di chuyển tới: {target_url}")
                await page.goto(target_url or self.target_domain, wait_until="networkidle")
                await asyncio.sleep(2) # Chờ ổn định giao diện
                
                # 5. DIỄN XUẤT (Hàm này phải là async def và gọi bằng await)
                audio_sync_data, audio_paths = await self._perform_acting(
                    page, script_steps, video_dir
                )
                
                # CHỖ NÀY QUAN TRỌNG: Đợi 1 chút để frame cuối kịp ghi vào file
                await asyncio.sleep(2)
                
                # Lấy path TRƯỚC khi đóng context (Playwright bản async yêu cầu await ở path())
                # Lưu ý: Một số bản Playwright cũ dùng page.video.path() không cần await, 
                # nhưng bản async chuẩn là CÓ await.
                raw_video_path = await page.video.path()
                
                # Đóng context để Playwright "nhả" file video ra khỏi memory
                await context.close()
                
            except Exception as e:
                print(f"❌ Lỗi trong lúc quay: {e}")
                raw_video_path = None
            finally:
                # Luôn đóng trình duyệt để sạch RAM
                await browser.close()

        # 6. HẬU KỲ (Chạy sau khi đã thoát khỏi 'async with' của Playwright)
        if raw_video_path:
            print(f"🎞️ Bắt đầu hậu kỳ video: {raw_video_path}")
            return self._run_post_production(
                raw_video_path, 
                audio_sync_data, 
                script_steps, 
                video_dir, 
                form_name, 
                audio_paths,
                logger="print"
            )
        
        print("❌ Không có video thô, hủy bước hậu kỳ.")
        return None

    def _refine_script(self, script_steps):
        """Gỡ bỏ các lớp bọc JSON dư thừa từ AI (Qwen, Llama, Gemini)"""
        if not isinstance(script_steps, list):
            return []
        
        # Nếu AI bọc kịch bản trong 1 Object nằm trong List: [{ 'flow': [...] }]
        if len(script_steps) == 1 and isinstance(script_steps[0], dict):
            first_item = script_steps[0]
            possible_keys = ["flow", "kịch_bản_video", "steps", "script", "data"]
            for key in possible_keys:
                if key in first_item and isinstance(first_item[key], list):
                    print(f"⚠️ Đã gỡ lớp bọc '{key}' từ AI.")
                    return first_item[key]
        
        return script_steps

    async def _perform_acting(self, page, script_steps, video_dir):
        audio_sync_data = []
        audio_paths = []
        video_start_time = time.time()

        for i, step in enumerate(script_steps):
            current_offset = time.time() - video_start_time
            speech_text = step.get("speak") or step.get("text", "")
            
            # 1. Tạo âm thanh (Thêm try-except để nếu lỗi voice Bot vẫn diễn tiếp)
            a_path = os.path.join(video_dir, f"step_{i}.mp3")
            try:
                duration = await self.audio_machine.generate(speech_text, a_path)
            except Exception as e:
                print(f"⚠️ Lỗi Voice tại bước {i+1}: {e}")
                duration = 2.0 # Default để Bot không bị đứng hình

            audio_paths.append(a_path)
            audio_sync_data.append({
                "start_at": current_offset, 
                "file_path": a_path, 
                "text": speech_text
            })

            print(f"🎬 Diễn bước {i+1}/{len(script_steps)}: {speech_text[:50]}...")
            
            # 2. Xóa hiệu ứng cũ & Thực hiện bước diễn
            if hasattr(self.effect_machine, 'clear_effects'):
                await self.effect_machine.clear_effects(page)
            
            # Đưa text vào Subtitle trên Browser để quay clip
            if hasattr(self.effect_machine, 'show_subtitle'):
                await self.effect_machine.show_subtitle(page, speech_text)

            # 3. STUDIO THỰC THI (Click/Type/Hover)
            await self.studio_machine.execute_step(page, step, self.effect_machine)

            # 4. KIỂM TRA LỖI UI (Đã chuyển sang Async)
            is_ok, errors = await self.vision.check_health(page)
            if not is_ok:
                print(f"🚨 UI Error Step {i+1}: {errors}")

            # 5. Đợi Voice đọc xong
            await asyncio.sleep(max(0.5, duration - 0.2))

        # Cuối phim: Xóa sub
        if hasattr(self.effect_machine, 'clear_effects'):
            await self.effect_machine.clear_effects(page)

        return audio_sync_data, audio_paths

    def _run_post_production(self, raw_path, sync_data, steps, video_dir, form_name, audio_files):
        'Hậu kỳ: Xử lý FFmpeg/MoviePy và dọn dẹp file rác.'

        if not raw_path or not os.path.exists(raw_path):
            print("❌ Không tìm thấy video gốc để hậu kỳ.")
            return None

        # Đợi file video thô được Playwright giải phóng hoàn toàn
        time.sleep(3) 
        
        final_path = os.path.join(video_dir, f"{form_name}_FINAL.mp4")
        print(f"🎞️ Đang bắt đầu hậu kỳ video cho: {form_name}")
        
        success = self.post_machine.process(
            video_path=raw_path, 
            audio_sync_data=sync_data, 
            script_steps=steps, 
            output_path=final_path
        )
        
        if success:
            # Dọn dẹp audio tạm
            for p in audio_files:
                try: os.remove(p)
                except: pass
            print(f"✅ HOÀN TẤT: {final_path}")
            return final_path
            
        return None