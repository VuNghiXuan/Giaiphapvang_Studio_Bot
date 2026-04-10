import asyncio
import os
import time
import json
from playwright.async_api import async_playwright
import traceback

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
        
        # 1. Khởi tạo "Con mắt" AI
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


    # async def run_studio_bot(self, target_url, script_steps, project_name, module_name, form_name):
    #     """
    #     THỰC THI DIỄN XUẤT TỰ ĐỘNG
    #     """
    #     # 1. Tinh lọc kịch bản (Trị lỗi NoneType từ AI)
    #     script_steps = self._refine_script(script_steps)
    #     ready, missing = self.check_ready_for_production(script_steps)
    #     if not ready:
    #         print(f"🚨 Engine chưa sẵn sàng. Thiếu: {missing}")
    #         return None

    #     # 2. Thiết lập đường dẫn làm việc
    #     video_dir = Config.get_asset_path(project_name, module_name, form_name, asset_type="videos")
    #     os.makedirs(video_dir, exist_ok=True)
    #     print(f"📂 [PATH]: Thư mục làm việc: {video_dir}")
        
    #     raw_video_path = None
    #     audio_sync_data = []
    #     audio_paths = []

    #     async with async_playwright() as p:
    #         browser = await p.chromium.launch(headless=False, args=["--start-maximized"])

    #         # --- GIAI ĐOẠN 1: LOGIN ---
    #         print("🔍 [Thám thính]: Đang chuẩn bị phiên đăng nhập...")
    #         probe_context = await browser.new_context(no_viewport=True)
    #         probe_page = await probe_context.new_page()
            
    #         if not await self.auth_machine.login(probe_page):
    #             print("❌ Dọn sân thất bại: Không thể đăng nhập.")
    #             await browser.close()
    #             return None
            
    #         await probe_page.goto(target_url or self.target_domain, wait_until="networkidle")
    #         state = await probe_context.storage_state()
    #         await probe_context.close() 

    #         # --- GIAI ĐOẠN 2: RECORDING ---
    #         print(f"🎬 [Bấm máy]: Bắt đầu ghi hình tại: {video_dir}")
    #         video_context = await browser.new_context(
    #             storage_state=state, 
    #             no_viewport=True, 
    #             record_video_dir=video_dir, 
    #             record_video_size={'width': 1920, 'height': 1080}
    #         )
    #         page = await video_context.new_page()
    #         await page.goto(target_url, wait_until="networkidle")
    #         await asyncio.sleep(2) 

    #         try:
    #             # Thực thi diễn xuất chính
    #             acting_result = await self._perform_acting(page, script_steps, video_dir)
                
    #             if acting_result and isinstance(acting_result, tuple):
    #                 audio_sync_data, audio_paths = acting_result
    #             else:
    #                 audio_sync_data, audio_paths = [], []

    #             await asyncio.sleep(2) # End-card
                
    #             # Quan trọng: Lấy path video thô trước khi đóng context
    #             raw_video_path = await page.video.path()
    #             await video_context.close()
    #             print(f"📹 [VIDEO RAW]: {raw_video_path}")
                
    #         except Exception as e:
    #             print(f"❌ Lỗi nghiêm trọng trong lúc quay: {e}")
    #             traceback.print_exc()
    #         finally:
    #             await browser.close()

    #     # --- GIAI ĐOẠN 3: HẬU KỲ ---
    #     if raw_video_path and os.path.exists(raw_video_path) and audio_sync_data:
    #         print(f"🎞️ [Hậu kỳ]: Bắt đầu Render video cuối cùng...")
    #         return self._run_post_production(
    #             raw_path=raw_video_path, 
    #             sync_data=audio_sync_data, 
    #             steps=script_steps, 
    #             video_dir=video_dir, 
    #             form_name=form_name, 
    #             audio_files=audio_paths
    #         )
        
    #     print("⚠️ Không đủ điều kiện để hậu kỳ (Thiếu video hoặc audio sync).")
    #     return None
    
    async def run_studio_bot(self, target_url=None, script_steps=None, project_name=None, module_name=None, form_name=None, **kwargs):
        """
        THỰC THI DIỄN XUẤT TỰ ĐỘNG - GPV STUDIO BOT
        Bản cập nhật: Chống lỗi thiếu tham số và tự động định cấu hình đường dẫn.
        """
        # 0. Xử lý tham số linh hoạt (Fallback)
        target_url = target_url or self.target_domain
        # Nếu bên Orchestrator truyền project_folder thay vì project_name thì vẫn nhận được
        project_name = project_name or kwargs.get('project_folder') or "GPV_Production"
        module_name = module_name or "Chung"
        form_name = form_name or "Trang_Chu"

        # 1. Tinh lọc kịch bản (Trị lỗi NoneType từ AI)
        script_steps = self._refine_script(script_steps)
        ready, missing = self.check_ready_for_production(script_steps)
        if not ready:
            print(f"🚨 Engine chưa sẵn sàng. Thiếu: {missing}")
            return None

        # 2. Thiết lập đường dẫn làm việc (Sử dụng Config của Vũ)
        video_dir = Config.get_asset_path(project_name, module_name, form_name, asset_type="videos")
        os.makedirs(video_dir, exist_ok=True)
        print(f"📂 [PATH]: Thư mục làm việc: {video_dir}")
        
        raw_video_path = None
        audio_sync_data = []
        audio_paths = []

        async with async_playwright() as p:
            # Khởi chạy trình duyệt (Headless=False để xem Bot diễn)
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"])

            # --- GIAI ĐOẠN 1: LOGIN (Lấy Session/State) ---
            print("🔍 [Thám thính]: Đang chuẩn bị phiên đăng nhập...")
            probe_context = await browser.new_context(no_viewport=True)
            probe_page = await probe_context.new_page()
            
            if not await self.auth_machine.login(probe_page):
                print("❌ Dọn sân thất bại: Không thể đăng nhập.")
                await browser.close()
                return None
            
            # Sau khi login xong, lấy trạng thái storage để tái sử dụng
            await probe_page.goto(target_url, wait_until="networkidle")
            state = await probe_context.storage_state()
            await probe_context.close() 

            # --- GIAI ĐOẠN 2: RECORDING (Ghi hình diễn xuất) ---
            print(f"🎬 [Bấm máy]: Bắt đầu ghi hình tại: {video_dir}")
            video_context = await browser.new_context(
                storage_state=state, 
                no_viewport=True, 
                record_video_dir=video_dir, 
                record_video_size={'width': 1920, 'height': 1080}
            )
            page = await video_context.new_page()
            
            # Đi tới trang đích để bắt đầu diễn
            await page.goto(target_url, wait_until="networkidle")
            await asyncio.sleep(2) # Đợi page ổn định

            try:
                # Thực thi diễn xuất chính từ StudioMachine
                acting_result = await self._perform_acting(page, script_steps, video_dir)
                
                if acting_result and isinstance(acting_result, tuple):
                    audio_sync_data, audio_paths = acting_result
                else:
                    audio_sync_data, audio_paths = [], []

                await asyncio.sleep(2) # Đợi End-card/Cảnh cuối
                
                # QUAN TRỌNG: Phải lấy path video trước khi đóng context
                raw_video_path = await page.video.path()
                
                # Đóng context để Playwright "nhả" file video ra ổ đĩa
                await video_context.close()
                print(f"📹 [VIDEO RAW]: {raw_video_path}")
                
            except Exception as e:
                print(f"❌ Lỗi nghiêm trọng trong lúc quay: {e}")
                traceback.print_exc()
            finally:
                await browser.close()

        # --- GIAI ĐOẠN 3: HẬU KỲ (Render sản phẩm cuối) ---
        if raw_video_path and os.path.exists(raw_video_path) and audio_sync_data:
            print(f"🎞️ [Hậu kỳ]: Bắt đầu Render video cuối cùng...")
            # Gọi PostProductionMachine để ghép Audio, Subtitle và Logo
            return self._run_post_production(
                raw_path=raw_video_path, 
                sync_data=audio_sync_data, 
                steps=script_steps, 
                video_dir=video_dir, 
                form_name=form_name, 
                audio_files=audio_paths
            )
        
        print("⚠️ Không đủ điều kiện để hậu kỳ (Thiếu video hoặc audio sync).")
        return None
    
    async def _perform_acting(self, page, script_steps, video_dir):
        """
        [PHÂN CẢNH DIỄN XUẤT] - Bảo vệ đa tầng chống 'NoneType'.
        """
        audio_sync_data = []
        audio_paths = []
        video_start_time = time.time()

        print(f"🎭 [Bot Diễn Viên]: Đang diễn {len(script_steps)} phân cảnh...")

        try:
            for i, step in enumerate(script_steps):
                # Chốt chặn NoneType tại vòng lặp
                if step is None or not isinstance(step, dict):
                    print(f"⚠️ Bỏ qua bước {i} do dữ liệu không hợp lệ.")
                    continue 

                # Trích xuất nội dung Voice-over
                speech_text = (
                    step.get("vo") or 
                    step.get("speak") or 
                    step.get("text") or 
                    f"Thực hiện {step.get('action', 'thao tác')}"
                )
                speech_text = str(speech_text).strip()
                
                print(f"🎬 Cảnh {i+1}/{len(script_steps)}: {speech_text[:60]}...")

                # 1. Tạo Audio
                a_filename = f"step_{i}_{int(time.time())}.mp3"
                a_path = os.path.join(video_dir, a_filename)
                duration = 2.0 
                try:
                    duration = await self.audio_machine.generate(speech_text, a_path)
                except Exception as audio_err:
                    print(f"⚠️ Lỗi Audio bước {i}: {audio_err}")

                # 2. Tính toán Sync & Hiển thị Subtitle
                current_offset = time.time() - video_start_time
                if hasattr(self.effect_machine, 'show_subtitle'):
                    await self.effect_machine.show_subtitle(page, speech_text)

                # 3. Thực thi UI
                success = await self.studio_machine.execute_step(page, step)
                
                # 4. Ghi nhận dữ liệu nếu thành công
                if success:
                    if os.path.exists(a_path):
                        audio_paths.append(a_path)
                        audio_sync_data.append({
                            "start_at": current_offset,
                            "file_path": a_path, 
                            "text": speech_text,
                            "duration": duration 
                        })
                    
                    # Chờ voice đọc xong + nghỉ ngắn
                    await asyncio.sleep(max(1.0, duration + 0.5))
                else:
                    print(f"❌ Diễn hỏng tại bước {i}")
                
                # 5. Dọn dẹp Subtitle
                if hasattr(self.effect_machine, 'clear_effects'):
                    await self.effect_machine.clear_effects(page)

        except Exception as e:
            print(f"🚨 Lỗi diễn xuất: {e}")
            traceback.print_exc()

        return audio_sync_data, audio_paths

    def _refine_script(self, script_steps):
        """
        Chuẩn hóa kịch bản, gỡ bỏ các lớp JSON bọc ngoài.
        """
        # Nếu AI trả về Dict có chứa list steps
        if isinstance(script_steps, dict):
            for key in ["steps", "flow", "script", "data", "kịch_bản_video"]:
                if key in script_steps and isinstance(script_steps[key], list):
                    script_steps = script_steps[key]
                    break
            if isinstance(script_steps, dict):
                script_steps = [script_steps]

        if not isinstance(script_steps, list):
            return []

        final_steps = []
        for step in script_steps:
            if not step or not isinstance(step, dict):
                continue
            
            # Đồng bộ key action
            if "action" not in step and "step" in step:
                step["action"] = step["step"]

            # Đảm bảo luôn có voice-over
            if "vo" not in step:
                step["vo"] = step.get("expected_result") or step.get("action") or "Đang thực hiện"
                
            final_steps.append(step)

        return final_steps

    
    def _run_post_production(self, raw_path, sync_data, steps, video_dir, form_name, audio_files, **kwargs):
        """
        Hậu kỳ: Ghép nối và dọn dẹp.
        """
        time.sleep(3) # Đợi Playwright nhả file video
        
        # Format tên file cuối cùng
        slug_name = Config.slugify_vietnamese(form_name) if hasattr(Config, 'slugify_vietnamese') else form_name
        final_path = os.path.join(video_dir, f"{slug_name}_FINAL.mp4")
        
        print(f"🎞️ Bắt đầu render: {final_path}")
        
        success = self.post_machine.process(
            video_path=raw_path, 
            audio_sync_data=sync_data, 
            script_steps=steps, 
            output_path=final_path
        )
        
        if success:
            for p in audio_files:
                try: os.remove(p)
                except: pass
            print(f"✅ HOÀN TẤT: {final_path}")
            return final_path
            
        return None