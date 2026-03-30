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

# Load biến môi trường từ file .env (USER_EMAIL, USER_PASSWORD)
load_dotenv()

class AutoVideoEngine:
    def __init__(self, storage_path="./storage", logo_path="assets/logo.png", voice="vi-VN-HoaiMyNeural"):
        self.storage_path = storage_path
        self.logo_path = logo_path
        self.voice = voice # Lấy từ giao diện người dùng truyền vào
        self.target_domain = os.getenv("TARGET_DOMAIN", "https://giaiphapvang.net")

    def check_ready_for_production(self, script_steps, logo_path=None):
        """
        Kiểm tra toàn bộ quy trình có đủ điều kiện sản xuất video chưa.
        """
        checks = {
            "env_auth": bool(os.getenv("USER_EMAIL") and os.getenv("USER_PASSWORD")),
            "script_valid": isinstance(script_steps, list) and len(script_steps) > 0,
            "logo_exists": os.path.exists(logo_path or self.logo_path),
            "storage_writable": os.access(os.path.dirname(self.storage_path) or ".", os.W_OK)
        }
        
        missing = [k for k, v in checks.items() if not v]
        if missing:
            print(f"⚠️ Chưa đủ điều kiện sản xuất. Thiếu: {', '.join(missing)}")
            return False, missing
        
        print("🚀 Mọi thứ đã sẵn sàng để xuất bản video!")
        return True, []

    async def login(self, page):
        """Hàm đăng nhập sử dụng thông tin từ .env"""
        print(f"🔑 Đang đăng nhập hệ thống: {self.target_domain}")
        try:
            # Xây dựng URL login chuẩn
            login_url = f"{self.target_domain.rstrip('/')}/auth/jwt/sign-in/"
            await page.goto(login_url)
            
            # Điền thông tin từ .env
            await page.fill("input[name='email']", os.getenv("USER_EMAIL"))
            await page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
            await page.click("button[type='submit']")
            
            # Chờ chuyển hướng thành công (timeout 30s)
            await page.wait_for_url("**/home/**", timeout=30000)
            print("🏠 Đăng nhập thành công!")
            await asyncio.sleep(1) # Nghỉ 1s cho ổn định
            return True
        except Exception as e:
            print(f"❌ Đăng nhập thất bại: {e}")
            return False

    async def generate_audio(self, text, output_path):
        """Sử dụng Edge-TTS tạo giọng đọc"""
        communicate = edge_tts.Communicate(text, self.voice, rate="+15%")
        await communicate.save(output_path)
        return output_path

    async def move_mouse_humanlike(self, page, target_selector):
        """Di chuyển chuột mượt mà"""
        try:
            box = await page.locator(target_selector).bounding_box()
            if not box: return
            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2
            await page.mouse.move(target_x, target_y, steps=20) 
            await asyncio.sleep(0.2)
        except: pass

    def merge_audio_video_with_logo(self, video_raw_path, audio_paths, output_path):
        """Hậu kỳ: Ghép tiếng, lồng logo, xuất video final"""
        try:
            video = VideoFileClip(video_raw_path)
            voice_clips = [AudioFileClip(p) for p in audio_paths if os.path.exists(p)]
            if not voice_clips: return False
            
            final_voice = concatenate_audioclips(voice_clips)
            
            # Khớp độ dài video với audio nếu audio dài hơn
            if final_voice.duration > video.duration:
                video = video.set_duration(final_voice.duration)
            
            video_with_audio = video.set_audio(final_voice)
            
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path)
                        .set_duration(video_with_audio.duration)
                        .resize(height=60)
                        .set_opacity(0.8)
                        .set_position(("right", "top")))
                final_video = CompositeVideoClip([video_with_audio, logo])
            else:
                final_video = video_with_audio

            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
            
            # Dọn dẹp
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
        """Quy trình sản xuất tự động hoàn chỉnh"""
        
        # 1. Kiểm tra sẵn sàng
        ready, _ = self.check_ready_for_production(script_steps)
        if not ready: return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False) 
            
            video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
            os.makedirs(video_dir, exist_ok=True)
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir=video_dir
            )
            
            page = await context.new_page()
            
            # 2. ĐĂNG NHẬP TRƯỚC KHI QUAY
            logged_in = await self.login(page)
            if not logged_in:
                await browser.close()
                return None

            # 3. TIẾN VÀO TRANG CẦN QUAY
            print(f"🚀 Bot đang tiến vào trang nghiệp vụ: {target_url}")
            await page.goto(target_url)
            await page.wait_for_load_state("networkidle")
            
            audio_files = []

            # 4. DIỄN THEO KỊCH BẢN
            for i, step in enumerate(script_steps):
                action = step.get("action")
                target = step.get("target")
                speech = step.get("text", "")
                val = step.get("value", "")
                
                # Tạo âm thanh trước
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

                # Thực hiện hành động trên trang
                try:
                    if target:
                        await page.locator(target).scroll_into_view_if_needed()
                        await self.move_mouse_humanlike(page, target) 

                    if action == "highlight":
                        await page.locator(target).evaluate("el => el.style.outline = '5px solid yellow'")
                    elif action == "click":
                        await page.click(target)
                    elif action == "type":
                        await page.type(target, str(val), delay=100)

                    # Chờ nói hết câu
                    await asyncio.sleep(audio_duration + 0.4)
                except Exception as e:
                    print(f"⚠️ Lỗi step {i}: {e}")

            # 5. ĐÓNG MÁY VÀ XUẤT VIDEO
            await context.close()
            raw_video_path = await page.video.path()
            await browser.close()
            
            print("🎬 Đang xử lý hậu kỳ cuối cùng...")
            final_output = os.path.join(video_dir, f"{form_name}_final_vũ.mp4")
            success = self.merge_audio_video_with_logo(raw_video_path, audio_files, final_output)
            
            return final_output if success else raw_video_path