import asyncio
import os
import json
import edge_tts
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_audioclips, 
    CompositeVideoClip, ImageClip, CompositeAudioClip
)

# Load biến môi trường từ file .env
load_dotenv()

class AutoVideoEngine:
    def __init__(self, storage_path="./storage", logo_path="assets/logo.png", voice="vi-VN-HoaiMyNeural"):
        self.storage_path = storage_path
        self.logo_path = logo_path
        self.voice = voice 
        self.target_domain = os.getenv("TARGET_DOMAIN", "https://giaiphapvang.net")

    def check_ready_for_production(self, script_steps, logo_path=None):
        checks = {
            "env_auth": bool(os.getenv("USER_EMAIL") and os.getenv("USER_PASSWORD")),
            "script_valid": isinstance(script_steps, list) and len(script_steps) > 0,
            "logo_exists": os.path.exists(logo_path or self.logo_path),
            "storage_writable": os.access(os.path.dirname(self.storage_path) or ".", os.W_OK)
        }
        missing = [k for k, v in checks.items() if not v]
        if missing:
            print(f"⚠️ Thiếu điều kiện: {', '.join(missing)}")
            return False, missing
        return True, []

    async def login(self, page):
        """Hàm đăng nhập gia cố - Đợi selector thay vì đợi URL"""
        print(f"🔑 Đang đăng nhập: {self.target_domain}")
        try:
            login_url = f"{self.target_domain.rstrip('/')}/auth/jwt/sign-in/"
            await page.goto(login_url, wait_until="networkidle")
            
            await page.fill("input[name='email']", os.getenv("USER_EMAIL"))
            await page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
            await page.click("button[type='submit']")
            
            # ĐỢI SELECTOR ĐẶC TRƯNG (Ví dụ cái Menu hoặc nút Logout) thay vì URL
            # Tôi để timeout 20s cho chắc
            try:
                await page.wait_for_selector(".main-sidebar, .nav-link, a[href*='logout']", timeout=20000)
                print("🏠 Đăng nhập thành công!")
                return True
            except:
                # Backup: Nếu không thấy selector nhưng URL thay đổi thì vẫn cho qua
                if "sign-in" not in page.url:
                    print("🏠 Đăng nhập thành công (Dựa trên URL)!")
                    return True
            return False
        except Exception as e:
            print(f"❌ Lỗi đăng nhập: {e}")
            return False

    async def generate_audio(self, text, output_path):
        communicate = edge_tts.Communicate(text, self.voice, rate="+15%")
        await communicate.save(output_path)
        return output_path

    async def move_mouse_humanlike(self, page, target_selector):
        try:
            # Đợi selector xuất hiện rồi mới di chuyển chuột
            locator = page.locator(target_selector).first
            await locator.wait_for(state="visible", timeout=5000)
            box = await locator.bounding_box()
            if not box: return
            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15) 
        except: pass

    def merge_audio_video_with_logo(self, video_raw_path, audio_paths, output_path):
        if not video_raw_path or not os.path.exists(video_raw_path):
            print(f"❌ Không tìm thấy file video thô: {video_raw_path}")
            return False
        try:
            video = VideoFileClip(video_raw_path)
            voice_clips = [AudioFileClip(p) for p in audio_paths if os.path.exists(p)]
            if not voice_clips: return False
            
            final_voice = concatenate_audioclips(voice_clips)
            if final_voice.duration > video.duration:
                video = video.set_duration(final_voice.duration)
            
            video_with_audio = video.set_audio(final_voice)
            
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path).set_duration(video_with_audio.duration)
                        .resize(height=60).set_opacity(0.8).set_position(("right", "top")))
                final_video = CompositeVideoClip([video_with_audio, logo])
            else:
                final_video = video_with_audio

            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, logger=None)
            video.close()
            final_video.close()
            for p in audio_paths:
                try: os.remove(p)
                except: pass
            return True
        except Exception as e:
            print(f"❌ Lỗi hậu kỳ: {e}")
            return False

    async def run_studio_bot(self, target_url, script_steps, project_name, form_name):
        ready, _ = self.check_ready_for_production(script_steps)
        if not ready: return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--start-maximized"]) 
            video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
            os.makedirs(video_dir, exist_ok=True)
            
            context = await browser.new_context(viewport={'width': 1280, 'height': 720}, record_video_dir=video_dir)
            page = await context.new_page()
            
            # 1. Login
            if not await self.login(page):
                await browser.close()
                return None

            # 2. Vào trang nghiệp vụ
            print(f"🚀 Tiến vào trang: {target_url}")
            await page.goto(target_url, wait_until="networkidle", timeout=60000)
            
            audio_files = []
            raw_video_path = None

            try:
                # 3. Chạy kịch bản
                for i, step in enumerate(script_steps):
                    action = step.get("action")
                    target = step.get("target")
                    speech = step.get("text", "")
                    val = step.get("value", "")
                    
                    # Tạo Voice
                    audio_duration = 0.5
                    if speech:
                        a_path = os.path.join(video_dir, f"step_{i}.mp3")
                        await self.generate_audio(speech, a_path)
                        audio_files.append(a_path)
                        try:
                            clip = AudioFileClip(a_path)
                            audio_duration = clip.duration
                            clip.close()
                        except: pass

                    # THỰC THI HÀNH ĐỘNG - GIA CỐ PHẦN ĐỢI NÚT
                    try:
                        if target:
                            # Đợi nút xuất hiện và sẵn sàng để click (tối đa 15s)
                            t_locator = page.locator(target).first
                            await t_locator.wait_for(state="visible", timeout=15000)
                            await t_locator.scroll_into_view_if_needed()
                            await self.move_mouse_humanlike(page, target) 

                            if action == "highlight":
                                await t_locator.evaluate("el => el.style.outline = '5px solid yellow'")
                            elif action == "click":
                                # Ép click (force=True) nếu nút bị che khuất nhẹ
                                await t_locator.click(force=True)
                            elif action == "type":
                                await t_locator.fill("") # Xóa sạch trước khi gõ
                                await t_locator.type(str(val), delay=100)

                        await asyncio.sleep(audio_duration + 0.5)
                    except Exception as e:
                        print(f"⚠️ Lỗi step {i} ({action}): {e}")
                        # Chụp ảnh lỗi để Vũ kiểm tra xem tại sao không nhấn được
                        await page.screenshot(path=os.path.join(video_dir, f"error_step_{i}.png"))

                # Đợi một chút cho video kịp finalize
                await asyncio.sleep(2)
                raw_video_path = await page.video.path()
            
            finally:
                await context.close()
                await browser.close()
            
            # 4. Xuất video
            if raw_video_path:
                print("🎬 Xử lý hậu kỳ...")
                final_output = os.path.join(video_dir, f"{form_name}_final_vũ.mp4")
                success = self.merge_audio_video_with_logo(raw_video_path, audio_files, final_output)
                return final_output if success else raw_video_path
            
            return None