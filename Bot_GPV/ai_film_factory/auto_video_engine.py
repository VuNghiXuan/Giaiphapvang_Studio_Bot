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


    async def run_studio_bot(self, target_url=None, script_steps=None, project_name=None, full_path_str=None, **kwargs):
        """
        [MAIN CONTROL] THỰC THI DIỄN XUẤT TỰ ĐỘNG - GPV STUDIO BOT (Đồng bộ chuẩn Config.get_path)
        """
        # 1. SETUP: Chuẩn bị kịch bản và đường dẫn
        target_url = target_url or self.target_domain
        project_name = project_name or kwargs.get('project_folder') or "GPV_Production"
        
        # --- 🔥 ĐỔI MỚI LOGIC ĐƯỜNG DẪN TẠI ĐÂY ---
        # Nếu không có full_path_str, ta dùng các tham số cũ để fallback
        if not full_path_str:
            m = kwargs.get('module_name', 'Chung')
            f = kwargs.get('form_name', 'Trang_Chu')
            full_path_str = f"{m} | {f}"

        script_steps = self._refine_script(script_steps)
        ready, missing = self.check_ready_for_production(script_steps)
        if not ready:
            print(f"🚨 Engine chưa sẵn sàng. Thiếu: {missing}")
            return None

        # SỬ DỤNG CONFIG.GET_PATH ĐỂ ĐỒNG BỘ VỚI DATA ARCHIVER
        # Nó sẽ tạo: storage/ung_dung_vang/he_thong/settings/chi_nhanh/videos
        video_dir = Config.get_path(full_path_str,
                                    asset_type="videos",
                                    project_slug=project_name)
        
        # Tên file video final (lấy slug của thằng cuối cùng trong chuỗi)
        last_part = full_path_str.split('|')[-1].strip()
        final_file_name = Config.slugify(last_part)
        
        print(f"📂 [PATH]: {video_dir}")
        # ------------------------------------------

        # 2. RECORDING: Chạy Playwright để quay phim
        # (Giữ nguyên logic của ông)
        raw_video_path, audio_sync_data, audio_paths = await self._execute_recording_phase(
            target_url, script_steps, video_dir
        )

        # 3. POST-PRODUCTION: Hậu kỳ render video final
        if raw_video_path and os.path.exists(raw_video_path) and audio_sync_data:
            # Truyền final_file_name vào để hậu kỳ đặt tên file cho chuẩn
            return self._execute_post_production_phase(
                raw_video_path, audio_sync_data, script_steps, video_dir, final_file_name, audio_paths
            )
        
        print("⚠️ Không đủ điều kiện để hậu kỳ (Thiếu video hoặc audio sync).")
        return None

    # def _prepare_storage_path(self, project, module, form):
    #     """Hàm nhỏ 1: Xử lý logic tạo thư mục"""
    #     try:
    #         if hasattr(Config, 'get_asset_path'):
    #             video_dir = Config.get_asset_path(project, module, form, asset_type="videos")
    #         else:
    #             from pathlib import Path
    #             video_dir = str(Path(self.storage_path) / project / module / form / "videos")
    #     except Exception:
    #         video_dir = os.path.join(self.storage_path, "temp_rendering")
        
    #     os.makedirs(video_dir, exist_ok=True)
    #     print(f"📂 [PATH]: {video_dir}")
    #     return video_dir

    async def _execute_recording_phase(self, target_url, script_steps, video_dir):
        """Hàm nhỏ 2: Chạy Playwright để ghi hình"""
        raw_video_path = None
        audio_sync_data = []
        audio_paths = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
            
            # --- GĐ 1: LẤY SESSION (Sửa lỗi Timeout tại đây) ---
            probe_context = await browser.new_context(no_viewport=True)
            probe_page = await probe_context.new_page()
            
            if not await self.auth_machine.login(probe_page):
                print("❌ Login thất bại.")
                await browser.close()
                return None, [], []
            
            # Thay đổi wait_until để tránh treo 30s
            await probe_page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            state = await probe_context.storage_state()
            await probe_context.close() 

            # --- GĐ 2: QUAY PHIM ---
            video_context = await browser.new_context(
                storage_state=state, 
                no_viewport=True, 
                record_video_dir=video_dir, 
                record_video_size={'width': 1920, 'height': 1080}
            )
            page = await video_context.new_page()
            
            try:
                # Ép load trang, nếu timeout vẫn cố chạy tiếp
                try:
                    await page.goto(target_url, wait_until="load", timeout=45000)
                except Exception:
                    print("⚠️ Page load hơi lâu, Bot bắt đầu diễn luôn...")
                
                await asyncio.sleep(3) 

                # Thực thi diễn xuất
                acting_result = await self._perform_acting(page, script_steps, video_dir)
                if acting_result:
                    audio_sync_data, audio_paths = acting_result

                await asyncio.sleep(2) 
                raw_video_path = await page.video.path()
                await video_context.close()
            except Exception as e:
                print(f"❌ Lỗi Recording: {e}")
                traceback.print_exc()
            finally:
                await browser.close()
                
        return raw_video_path, audio_sync_data, audio_paths

    def _execute_post_production_phase(self, raw_path, sync_data, steps, video_dir, form_name, audio_files):
        """Hàm nhỏ 3: Xử lý hậu kỳ sau khi có video thô"""
        print(f"🎞️ [Hậu kỳ]: Render video final cho {form_name}...")
        
        final_video = self._run_post_production(
            raw_path=raw_path, 
            sync_data=sync_data, 
            steps=steps, 
            video_dir=video_dir, 
            form_name=form_name, 
            audio_files=audio_files
        )
        
        # Dọn dẹp video thô để đỡ nặng máy
        if final_video and os.path.exists(raw_path):
            try:
                # Đợi 2s để file không bị chiếm dụng bởi process khác
                time.sleep(2)
                os.remove(raw_path)
            except: 
                pass
                
        return final_video
    
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
        [POST-PRODUCTION] Hậu kỳ: Ghép nối, chèn sub, logo và dọn dẹp file tạm.
        """
        # Đợi 3 giây để Playwright đóng file stream hoàn toàn, tránh lỗi 'File in use'
        time.sleep(3) 
        
        # 1. Định dạng tên file bằng slugify của Config (Đảm bảo đồng bộ với folder)
        # Nếu form_name là "Thông tin công ty" -> slug_name sẽ là "thong_tin_cong_ty"
        slug_name = Config.slugify(form_name) if hasattr(Config, 'slugify') else form_name
        final_file_name = f"{slug_name}_FINAL.mp4"
        
        # Đảm bảo video_dir là đối tượng Path để nối chuỗi cho chuẩn
        from pathlib import Path
        final_path = str(Path(video_dir) / final_file_name)
        
        print(f"🎞️ [Render]: Bắt đầu xử lý hậu kỳ cho -> {final_path}")
        
        # 2. Gọi Post Machine thực hiện render (FFmpeg / MoviePy)
        success = self.post_machine.process(
            video_path=raw_path, 
            audio_sync_data=sync_data, 
            script_steps=steps, 
            output_path=final_path
        )
        
        # 3. DỌN DẸP CHIẾN TRƯỜNG
        if success:
            print("🧹 [Cleanup]: Đang dọn dẹp các file audio và video thô...")
            
            # Xóa các file MP3 tạm
            for p in audio_files:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as e:
                    print(f"⚠️ Không thể xóa file tạm {p}: {e}")

            # Xóa file video thô (raw) ghi bởi Playwright
            if raw_path and os.path.exists(raw_path):
                try:
                    os.remove(raw_path)
                except:
                    pass
            
            # Bonus: Nếu ông có dùng folder 'temp_voice' trong videos/, hãy xóa nó nếu trống
            temp_dir = Path(video_dir) / "temp_voice"
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                try: temp_dir.rmdir()
                except: pass

            print(f"✅ HOÀN TẤT XUẤT BẢN: {final_path}")
            return final_path
            
        print("❌ Lỗi trong quá trình render video final.")
        return None