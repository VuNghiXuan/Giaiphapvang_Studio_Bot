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
        ready, missing = self.check_ready_for_production(script_steps)
        if not ready:
            print(f"🚨 Engine chưa sẵn sàng. Thiếu: {missing}")
            return None

        video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
        os.makedirs(video_dir, exist_ok=True)
        
        audio_sync_data = []
        audio_paths = []
        raw_video_path = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
            context = await browser.new_context(
                no_viewport=True, 
                record_video_dir=video_dir, 
                record_video_size={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            try:
                # --- BƯỚC 1: ĐĂNG NHẬP ---
                if not await self.auth_machine.login(page):
                    print("❌ Dừng quy trình: Không thể đăng nhập vào Giai Pháp Vàng.")
                    return None
                
                # --- BƯỚC 2: ĐIỀU HƯỚNG ---
                target_url = target_url or self.target_domain
                print(f"🌐 Điều hướng đến: {target_url}")
                await page.goto(target_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(2) 
                video_start_time = time.time()

                # --- BƯỚC 3: DIỄN XUẤT (STEP-BY-STEP) ---
                for i, step in enumerate(script_steps):
                    current_video_offset = time.time() - video_start_time
                    speech_text = step.get("speak") or step.get("text", "")
                    
                    # 3.1. Tạo Voice
                    a_path = os.path.join(video_dir, f"step_{i}.mp3")
                    duration = await self.audio_machine.generate(speech_text, a_path)
                    
                    audio_paths.append(a_path)
                    audio_sync_data.append({
                        "start_at": current_video_offset, 
                        "file_path": a_path, 
                        "text": speech_text
                    })

                    print(f"🎬 Diễn bước {i+1}: {speech_text[:60]}...")
                    
                    # Spotlight hiệu ứng
                    if hasattr(self.effect_machine, 'clear_effects'):
                        await self.effect_machine.clear_effects(page)

                    # 3.2. Thực hiện hành động (Dùng await nếu StudioMachine vẫn là async)
                    await self.studio_machine.execute_step(page, step, self.effect_machine)

                    # Đợi voice đọc xong
                    wait_time = max(0.5, duration - 0.5)
                    await asyncio.sleep(wait_time)

                    # --- CHỖ SỬA QUAN TRỌNG: 3.3. Check lỗi UI (BỎ await) ---
                    # Vì VisionMachine.check_health trả về Tuple (bool, list), KHÔNG ĐƯỢC await nó.
                    is_ok, errors = self.vision.check_health(page) 
                    if not is_ok:
                        print(f"🚨 Phát hiện lỗi trên trang: {errors}")

                await asyncio.sleep(2)
                raw_video_path = await page.video.path()
                
            except Exception as e:
                print(f"❌ Lỗi Engine trong lúc quay: {e}")
            finally:
                await context.close()
                await browser.close()

        # --- BƯỚC 4: HẬU KỲ ---
        if raw_video_path and os.path.exists(raw_video_path):
            # Đợi 2s để Playwright chốt file video thô
            time.sleep(2)
            final_path = os.path.join(video_dir, f"{form_name}_FINAL_PRODUCTION.mp4")
            print(f"🎞️ Đang bắt đầu hậu kỳ...")
            
            success = self.post_machine.process(
                video_path=raw_video_path, 
                audio_sync_data=audio_sync_data, 
                script_steps=script_steps, 
                output_path=final_path
            )
            
            if success:
                # Dọn dẹp file tạm trong D:\ThanhVu
                for p_audio in audio_paths:
                    try: os.remove(p_audio)
                    except: pass
                print(f"✅ Xuất video thành công: {final_path}")
                return final_path
                
        return None