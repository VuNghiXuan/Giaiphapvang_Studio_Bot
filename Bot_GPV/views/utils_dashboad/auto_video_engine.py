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
        # Sử dụng domain từ môi trường hoặc mặc định
        self.target_domain = os.getenv("TARGET_DOMAIN", "https://giaiphapvang.net")

    def check_ready_for_production(self, script_steps, logo_path=None):
        """Kiểm tra điều kiện trước khi chạy"""
        checks = {
            "env_auth": bool(os.getenv("USER_EMAIL") and os.getenv("USER_PASSWORD")),
            "script_valid": isinstance(script_steps, list) and len(script_steps) > 0,
            "logo_exists": os.path.exists(logo_path or self.logo_path),
            "storage_writable": os.access(os.path.dirname(self.storage_path) or ".", os.W_OK)
        }
        missing = [k for k, v in checks.items() if not v]
        if missing:
            print(f"⚠️ Thiếu: {', '.join(missing)}")
            return False, missing
        return True, []

    async def login(self, page):
        """Hàm đăng nhập phiên bản: 'Bỏ qua mạng chậm' cho ông Vũ"""
        print(f"🔑 Bắt đầu quy trình đăng nhập: {self.target_domain}")
        try:
            login_url = f"{self.target_domain.rstrip('/')}/auth/jwt/sign-in/"
            
            print(f"🌐 Đang mở trang: {login_url}")
            # FIX 1: Chỉ đợi DOM load xong, không đợi mạng rảnh (networkidle)
            # Giảm timeout xuống 30s để nếu kẹt thì báo sớm còn biết đường xử lý
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            
            # Đợi thêm một chút cho chắc chắn các ô input xuất hiện
            print("🔍 Đang tìm ô nhập liệu (Email/Password)...")
            try:
                await page.wait_for_selector("input[name='email']", state="attached", timeout=10000)
            except:
                print("⚠️ Cảnh báo: Đợi selector hơi lâu, có thể trang chưa hiện form.")

            # FIX 2: Kiểm tra lại biến môi trường trước khi điền
            user_email = os.getenv("USER_EMAIL")
            user_pass = os.getenv("USER_PASSWORD")
            
            if not user_email or not user_pass:
                print("❌ LỖI: Biến USER_EMAIL hoặc USER_PASSWORD trong file .env bị trống!")
                return False

            print(f"✍️ Đang điền Email: {user_email}")
            await page.fill("input[name='email']", user_email)
            
            print("✍️ Đang điền Password...")
            await page.fill("input[name='password']", user_pass)

            print("🖱️ Nhấn nút Đăng nhập...")
            # FIX 3: Dùng click bình thường, sau đó đợi URL thay đổi
            await page.click("button[type='submit']")
            
            print("⏳ Đang đợi hệ thống xác thực và chuyển hướng...")
            
            # Đợi URL chứa chữ 'home' hoặc trang không còn là 'sign-in' nữa
            try:
                # Code của Vũ: wait_for_url("**/home/**")
                await page.wait_for_url("**/home/**", timeout=20000)
                print("✨ Đăng nhập THÀNH CÔNG!")
                return True
            except:
                if "/home" in page.url:
                    print(f"✅ Đăng nhập thành công (Dựa trên URL hiện tại): {page.url}")
                    return True
                else:
                    print(f"❌ Kẹt tại URL: {page.url}")
                    return False
                
        except Exception as e:
            print(f"🔥 LỖI PHÁT SINH: {str(e)}")
            # Chụp ảnh debug khi bị Timeout
            error_path = os.path.join(self.storage_path, "debug_timeout_error.png")
            await page.screenshot(path=error_path)
            print(f"📸 Đã chụp ảnh hiện trạng tại: {error_path}")
            return False
    
    # 1. Thay vì dùng locator cứng, hãy dùng hàm tìm nút thông minh giống Scraper
    async def smart_click(page, text_pattern):
        # Tìm tất cả button/link có chứa text (không phân biệt hoa thường)
        selector = f"text=/{text_pattern}/i" 
        locator = page.locator(selector).first
        
        # Đợi nó xuất hiện và ổn định
        await locator.wait_for(state="visible", timeout=10000)
        
        # CHIÊU CỦA SCRAPER: Đợi thêm một chút cho chắc cú
        await asyncio.sleep(0.5) 
        
        await locator.click(force=True)
        print(f"✅ Đã click thành công nút chứa: {text_pattern}")

        # 2. Áp dụng vào vòng lặp Step của ông:
        if action == "click":
            if "Thêm mới" in target or "button" in target:
                # Nếu là nút bấm, dùng chiêu Regex của Scraper
                await smart_click(page, "Thêm mới|Tạo mới|Thêm")
            else:
                # Các link bình thường
                await t_locator.click(force=True)
            
            # SAU KHI CLICK NÚT "THÊM MỚI": Bắt buộc phải đợi Dialog/Form của MUI hiện ra
            if "Thêm" in target:
                print("⏳ Đang đợi Form/Dialog hiện ra...")
                await page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", state="visible", timeout=10000)
                await asyncio.sleep(1) # Cho animation chạy xong hẳn
            
        
    async def generate_audio(self, text, output_path):
        """Tạo giọng đọc AI"""
        communicate = edge_tts.Communicate(text, self.voice, rate="+15%")
        await communicate.save(output_path)
        return output_path

    async def move_mouse_humanlike(self, page, target_selector):
        """Di chuyển chuột mượt mà"""
        try:
            locator = page.locator(target_selector).first
            await locator.wait_for(state="visible", timeout=5000)
            box = await locator.bounding_box()
            if not box: return
            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15) 
        except: pass

    def merge_audio_video_with_logo(self, video_raw_path, audio_paths, output_path):
        """Hậu kỳ video"""
        if not video_raw_path or not os.path.exists(video_raw_path):
            print(f"❌ Không tìm thấy video thô: {video_raw_path}")
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
        """Quy trình chạy Bot chính"""
        ready, _ = self.check_ready_for_production(script_steps)
        if not ready: return None

        async with async_playwright() as p:
            # 1. Mở Browser và ÉP MAXIMIZED
            browser = await p.chromium.launch(
                headless=False, 
                args=["--start-maximized"] # Mở to cửa sổ ngay từ đầu
            ) 
            
            video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
            os.makedirs(video_dir, exist_ok=True)
            
            # 2. FIX QUAN TRỌNG: Dùng no_viewport=True để trang web hiện đầy đủ như màn hình thật
            context = await browser.new_context(
                no_viewport=True, 
                record_video_dir=video_dir
            )
            page = await context.new_page()
            
            # 3. Đăng nhập theo logic Vũ yêu cầu
            if not await self.login(page):
                # Chụp ảnh nếu login fail để debug
                await page.screenshot(path=os.path.join(video_dir, "login_error.png"))
                await browser.close()
                return None

            # 4. Vào trang nghiệp vụ sau khi đã login
            print(f"🚀 Tiến vào trang: {target_url}")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            
            # ĐỢI THÊM: Cho phép các script xử lý dữ liệu chạy xong (quan trọng với trang Chi nhánh)
            await page.wait_for_load_state("networkidle") 
            await asyncio.sleep(2) # Nghỉ thêm 2s cho chắc cú

            audio_files = []
            raw_video_path = None

            try:
                for i, step in enumerate(script_steps):
                    action = step.get("action")
                    target = step.get("target")
                    speech = step.get("text", "")
                    val = step.get("value", "")
                    
                    # --- FIX LỖI TẠI ĐÂY: Khởi tạo giá trị mặc định ---
                    audio_duration = 0.5 
                    
                    # Xử lý âm thanh (nếu có lời thoại)
                    if speech:
                        a_path = os.path.join(video_dir, f"step_{i}.mp3")
                        await self.generate_audio(speech, a_path)
                        audio_files.append(a_path)
                        try:
                            clip = AudioFileClip(a_path)
                            audio_duration = clip.duration
                            clip.close()
                        except Exception as e:
                            print(f"⚠️ Lỗi lấy độ dài audio step {i}: {e}")

                    # Thực hiện hành động trên trang
                    try:
                        if target:
                            # --- CHIÊU QUAN TRỌNG: KIỂM TRA ĐỊA CHỈ TRƯỚC ---
                            # Nếu target là một URL và Bot đã đứng ở URL đó rồi thì BỎ QUA step này.
                            current_url = page.url.rstrip('/')
                            clean_target = target.split("'")[1].rstrip('/') if "href" in target else target.rstrip('/')
                            
                            if action == "click" and clean_target in current_url:
                                print(f"✅ Step {i}: Đạo diễn Vũ ơi, mình đang ở đúng trang rồi, bỏ qua bước Click Menu này nhé!")
                            else:
                                t_locator = page.locator(target).first
                                
                                print(f"🔍 Step {i}: Đang xử lý {target}...")
                                # Đợi Attached (có trong code) thay vì Visible để tránh lỗi UI bị che
                                await t_locator.wait_for(state="attached", timeout=5000)
                                await t_locator.scroll_into_view_if_needed()
                                
                                # Di chuyển chuột cho chuyên nghiệp
                                await self.move_mouse_humanlike(page, target) 

                                if action == "highlight":
                                    await t_locator.evaluate("el => el.style.outline = '5px solid yellow'")
                                elif action == "click":
                                    # Dùng force=True để click bất chấp nếu có cái gì che nhẹ
                                    await t_locator.click(force=True)
                                elif action == "type":
                                    await t_locator.fill("") 
                                    await t_locator.type(str(val), delay=100)

                        # Luôn đợi đọc xong lời thoại mới qua cảnh mới
                        await asyncio.sleep(audio_duration + 0.5)

                    except Exception as e:
                        print(f"⚠️ Step {i} có vấn đề nhẹ: {e}")
                        # Chụp ảnh để ông Vũ soi lỗi
                        await page.screenshot(path=os.path.join(video_dir, f"debug_step_{i}.png"))

                # Chờ 2s để Playwright chốt file video thô
                await asyncio.sleep(2)
                raw_video_path = await page.video.path()
            
            finally:
                await context.close()
                await browser.close()
            
            # 5. Xuất video hoàn thiện
            if raw_video_path:
                print("🎬 Bắt đầu hậu kỳ cuối cùng...")
                final_output = os.path.join(video_dir, f"{form_name}_final_vũ.mp4")
                success = self.merge_audio_video_with_logo(raw_video_path, audio_files, final_output)
                return final_output if success else raw_video_path
            
            return None