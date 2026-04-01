# import asyncio
# import os
# import json
# import edge_tts
# from pathlib import Path
# from dotenv import load_dotenv
# from playwright.async_api import async_playwright
# from moviepy.editor import (
#     VideoFileClip, AudioFileClip, concatenate_audioclips, 
#     CompositeVideoClip, ImageClip, CompositeAudioClip, concatenate_videoclips,
# )
# import time
# # Load biến môi trường từ file .env
# load_dotenv()

# class AutoVideoEngine:
#     def __init__(self, storage_path="./storage", logo_path="assets/logo.png", voice="vi-VN-HoaiMyNeural"):
#         self.storage_path = storage_path
#         self.logo_path = logo_path
#         self.voice = voice 
#         # Sử dụng domain từ môi trường hoặc mặc định
#         self.target_domain = os.getenv("TARGET_DOMAIN", "https://giaiphapvang.net")
        

#     def check_ready_for_production(self, script_steps, logo_path=None):
#         """Kiểm tra điều kiện trước khi chạy"""
#         checks = {
#             "env_auth": bool(os.getenv("USER_EMAIL") and os.getenv("USER_PASSWORD")),
#             "script_valid": isinstance(script_steps, list) and len(script_steps) > 0,
#             "logo_exists": os.path.exists(logo_path or self.logo_path),
#             "storage_writable": os.access(os.path.dirname(self.storage_path) or ".", os.W_OK)
#         }
#         missing = [k for k, v in checks.items() if not v]
#         if missing:
#             print(f"⚠️ Thiếu: {', '.join(missing)}")
#             return False, missing
#         return True, []

#     async def login(self, page):
#         """Hàm đăng nhập phiên bản: 'Bỏ qua mạng chậm' cho ông Vũ"""
#         print(f"🔑 Bắt đầu quy trình đăng nhập: {self.target_domain}")
#         try:
#             login_url = f"{self.target_domain.rstrip('/')}/auth/jwt/sign-in/"
            
#             print(f"🌐 Đang mở trang: {login_url}")
#             # FIX 1: Chỉ đợi DOM load xong, không đợi mạng rảnh (networkidle)
#             # Giảm timeout xuống 30s để nếu kẹt thì báo sớm còn biết đường xử lý
#             await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            
#             # Đợi thêm một chút cho chắc chắn các ô input xuất hiện
#             print("🔍 Đang tìm ô nhập liệu (Email/Password)...")
#             try:
#                 await page.wait_for_selector("input[name='email']", state="attached", timeout=10000)
#             except:
#                 print("⚠️ Cảnh báo: Đợi selector hơi lâu, có thể trang chưa hiện form.")

#             # FIX 2: Kiểm tra lại biến môi trường trước khi điền
#             user_email = os.getenv("USER_EMAIL")
#             user_pass = os.getenv("USER_PASSWORD")
            
#             if not user_email or not user_pass:
#                 print("❌ LỖI: Biến USER_EMAIL hoặc USER_PASSWORD trong file .env bị trống!")
#                 return False

#             print(f"✍️ Đang điền Email: {user_email}")
#             await page.fill("input[name='email']", user_email)
            
#             print("✍️ Đang điền Password...")
#             await page.fill("input[name='password']", user_pass)

#             print("🖱️ Nhấn nút Đăng nhập...")
#             # FIX 3: Dùng click bình thường, sau đó đợi URL thay đổi
#             await page.click("button[type='submit']")
            
#             print("⏳ Đang đợi hệ thống xác thực và chuyển hướng...")
            
#             # Đợi URL chứa chữ 'home' hoặc trang không còn là 'sign-in' nữa
#             try:
#                 # Code của Vũ: wait_for_url("**/home/**")
#                 await page.wait_for_url("**/home/**", timeout=20000)
#                 print("✨ Đăng nhập THÀNH CÔNG!")
#                 return True
#             except:
#                 if "/home" in page.url:
#                     print(f"✅ Đăng nhập thành công (Dựa trên URL hiện tại): {page.url}")
#                     return True
#                 else:
#                     print(f"❌ Kẹt tại URL: {page.url}")
#                     return False
                
#         except Exception as e:
#             print(f"🔥 LỖI PHÁT SINH: {str(e)}")
#             # Chụp ảnh debug khi bị Timeout
#             error_path = os.path.join(self.storage_path, "debug_timeout_error.png")
#             await page.screenshot(path=error_path)
#             print(f"📸 Đã chụp ảnh hiện trạng tại: {error_path}")
#             return False
   
        
#     async def generate_audio(self, text, output_path):
#         """Tạo giọng đọc AI"""
#         communicate = edge_tts.Communicate(text, self.voice, rate="-5%")
#         await communicate.save(output_path)
#         return output_path

#     async def move_mouse_humanlike(self, page, target_selector):
#         """Di chuyển chuột mượt mà"""
#         try:
#             locator = page.locator(target_selector).first
#             await locator.wait_for(state="visible", timeout=5000)
#             box = await locator.bounding_box()
#             if not box: return
#             await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=15) 
#         except: pass

#     def merge_audio_video_with_logo(self, video_raw_path, audio_sync_data, output_path):
#         """Hậu kỳ dùng cơ chế TIMELINE để khớp tuyệt đối"""
#         try:
#             video = VideoFileClip(video_raw_path)
            
#             # Tạo danh sách audio clips đặt đúng vị trí trên timeline
#             clips_with_timing = []
#             for item in audio_sync_data:
#                 if os.path.exists(item['file_path']):
#                     a_clip = AudioFileClip(item['file_path']).set_start(item['start_at'])
#                     clips_with_timing.append(a_clip)

#             if not clips_with_timing: return False
            
#             # Trộn các đoạn audio vào đúng mốc giây của video
#             final_audio = CompositeAudioClip(clips_with_timing)
            
#             # Nếu tổng tiếng dài hơn video, mở rộng video (đóng băng frame cuối)
#             if final_audio.duration > video.duration:
#                 last_frame = video.get_frame(video.duration - 0.1)
#                 freeze_clip = ImageClip(last_frame).set_duration(final_audio.duration - video.duration).set_fps(video.fps)
#                 video = concatenate_videoclips([video, freeze_clip])

#             video_with_audio = video.set_audio(final_audio)

#             # Chèn Logo và Xuất file (giữ bitrate cao cho nét)
#             if self.logo_path and os.path.exists(self.logo_path):
#                 logo = (ImageClip(self.logo_path).set_duration(video_with_audio.duration)
#                         .resize(height=70).set_opacity(0.8).set_position(("right", "top")))
#                 final_video = CompositeVideoClip([video_with_audio, logo])
#             else:
#                 final_video = video_with_audio

#             final_video.write_videofile(output_path, codec="libx264", bitrate="5000k", fps=24, logger=None)
            
#             # Dọn dẹp
#             video.close()
#             final_video.close()
#             return True
#         except Exception as e:
#             print(f"❌ Lỗi Sync: {e}")
#             return False

#     async def apply_spotlight(self, page, target_selector):
#         """UPGRADE: Hiệu ứng Spotlight làm nổi bật vùng đang nói đến"""
#         try:
#             await page.evaluate("""(selector) => {
#                 const el = document.querySelector(selector);
#                 if (!el) return;
#                 // Tạo một lớp phủ mờ toàn trang
#                 let overlay = document.getElementById('bot-spotlight-overlay');
#                 if (!overlay) {
#                     overlay = document.createElement('div');
#                     overlay.id = 'bot-spotlight-overlay';
#                     Object.assign(overlay.style, {
#                         position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
#                         backgroundColor: 'rgba(0,0,0,0.5)', zIndex: '9999', pointerEvents: 'none',
#                         transition: 'all 0.5s'
#                     });
#                     document.body.appendChild(overlay);
#                 }
#                 const rect = el.getBoundingClientRect();
#                 overlay.style.clipPath = `polygon(
#                     0% 0%, 0% 100%, 
#                     ${rect.left}px 100%, ${rect.left}px ${rect.top}px, 
#                     ${rect.right}px ${rect.top}px, ${rect.right}px ${rect.bottom}px, 
#                     ${rect.left}px ${rect.bottom}px, ${rect.left}px 100%, 
#                     100% 100%, 100% 0%
#                 )`;
#             }""", target_selector)
#         except: pass

#     async def clear_effects(self, page):
#         """Xóa các hiệu ứng highlight sau mỗi step"""
#         try:
#             await page.evaluate("const el = document.getElementById('bot-spotlight-overlay'); if(el) el.remove();")
#         except: pass
        
#     async def _handle_audio_step(self, i, speech, video_dir, audio_files):
#         """Tạo âm thanh và trả về thời lượng để đồng bộ video"""
#         if not speech:
#             return 0.5
        
#         a_path = os.path.join(video_dir, f"step_{i}.mp3")
#         await self.generate_audio(speech, a_path)
#         audio_files.append(a_path)
        
#         try:
#             from moviepy.editor import AudioFileClip
#             with AudioFileClip(a_path) as clip:
#                 return clip.duration
#         except Exception as e:
#             print(f"⚠️ Không lấy được độ dài audio: {e}")
#             return 1.5

#     async def _execute_ui_action(self, page, step, i, video_dir):
#         """Thực hiện hành động UI với cơ chế chống gãy (Anti-Timeout)"""
#         action = step.get("action")
#         target = step.get("target")
#         val = step.get("value", "")

#         if not target: return

#         # 1. Bỏ qua nếu đã ở đúng URL
#         current_url = page.url.rstrip('/')
#         clean_target = target.split("'")[1].rstrip('/') if "href" in target else target.rstrip('/')
#         if action == "click" and clean_target in current_url:
#             print(f"✅ Step {i}: Đã ở đúng trang, bỏ qua.")
#             return

#         try:
#             # 2. Cơ chế Smart Locator cho MUI Buttons
#             t_locator = None
#             if "Thêm mới" in str(target) or "Lưu" in str(target):
#                 # Thử nhiều phương án selector khác nhau
#                 for s in [target, "button:has-text('Thêm mới')", "//button[contains(.,'Thêm mới')]", "button.MuiButton-root"]:
#                     loc = page.locator(s).first
#                     if await loc.is_visible():
#                         t_locator = loc
#                         break
            
#             if not t_locator:
#                 t_locator = page.locator(target).first
#                 # Tăng timeout lên 15s cho các bước quan trọng
#                 await t_locator.wait_for(state="visible", timeout=15000)

#             # 3. Diễn xuất: Cuộn và di chuyển chuột
#             await t_locator.scroll_into_view_if_needed()
#             if hasattr(self, 'apply_spotlight'):
#                 await self.apply_spotlight(page, t_locator)
#             await self.move_mouse_humanlike(page, t_locator)

#             # 4. Thực hiện Action
#             if action == "highlight":
#                 await t_locator.evaluate("el => el.style.outline = '5px solid #FFD700'")
            
#             elif action == "click":
#                 # Chiêu cuối: Click vào tọa độ vật lý để xuyên qua các lớp mờ của MUI
#                 box = await t_locator.bounding_box()
#                 if box:
#                     await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
#                 else:
#                     await t_locator.click(force=True)
                
#                 # Đợi Form mở ra (Quan trọng để tránh lỗi Step 4, 5...)
#                 if "Thêm mới" in (await t_locator.inner_text()):
#                     print("🕒 Đang đợi Form hiện hình...")
#                     await page.wait_for_timeout(2000)
#                     await page.wait_for_load_state("networkidle")

#             elif action == "type":
#                 # Click và xóa sạch trước khi gõ (MUI Input đôi khi kẹt giá trị cũ)
#                 await t_locator.click()
#                 await page.keyboard.press("Control+A")
#                 await page.keyboard.press("Backspace")
#                 await t_locator.type(str(val), delay=60)

#         except Exception as e:
#             # Chụp ảnh hiện trường để Vũ soi lỗi
#             shot_path = os.path.join(video_dir, f"CRITICAL_step_{i}.png")
#             await page.screenshot(path=shot_path)
#             print(f"❌ Step {i} gãy nặng: {e}. Check ảnh: {shot_path}")
#             raise e # Dừng kịch bản ngay để không tốn thời gian chạy lỗi domino
    
#     async def run_studio_bot(self, target_url, script_steps, project_name, form_name):
#         ready, _ = self.check_ready_for_production(script_steps)
#         if not ready: return None

#         video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
#         os.makedirs(video_dir, exist_ok=True)
        
#         audio_files = []
#         audio_sync_data = [] # FIX: Lưu mốc thời gian [giây bắt đầu, đường dẫn file]

#         async with async_playwright() as p:
#             browser = await p.chromium.launch(headless=False, args=["--start-maximized", "--no-sandbox"])
#             context = await browser.new_context(
#                 no_viewport=True, 
#                 record_video_size={'width': 1920, 'height': 1080},
#                 record_video_dir=video_dir
#             )
#             page = await context.new_page()

#             try:
#                 if not await self.login(page): return None
                
#                 print(f"🚀 Tiến vào trang: {target_url}")
#                 await page.goto(target_url, wait_until="networkidle")
                
#                 # Mốc 0 của video (bắt đầu tính giây từ đây)
#                 video_start_time = time.time() 

#                 for i, step in enumerate(script_steps):
#                     # 1. Tạo audio
#                     duration = await self._handle_audio_step(i, step.get("text"), video_dir, audio_files)
                    
#                     # GHI LẠI: Giây thứ mấy trong video thì step này bắt đầu
#                     current_video_second = time.time() - video_start_time
#                     audio_sync_data.append({
#                         "start_at": current_video_second,
#                         "file_path": audio_files[-1],
#                         "duration": duration
#                     })

#                     if hasattr(self, 'clear_effects'): await self.clear_effects(page)

#                     # 2. DIỄN UI (Bắt đầu diễn là tiếng bắt đầu khớp)
#                     print(f"🎙️ Step {i} - Bắt đầu lúc {current_video_second:.2f}s")
                    
#                     # Tăng delay gõ phím để hình không chạy quá nhanh
#                     await self._execute_ui_action(page, step, i, video_dir)
                    
#                     # Đợi thêm cho khớp với tiếng đọc của Hoài Mỹ
#                     await asyncio.sleep(max(0.5, duration - 1.0)) 

#                 await asyncio.sleep(2)
#                 raw_video_path = await page.video.path()

#             except Exception as e:
#                 print(f"🔥 Lỗi: {e}")
#                 raw_video_path = None
#             finally:
#                 await context.close()
#                 await browser.close()

#         if raw_video_path:
#             # Truyền thêm audio_sync_data vào hậu kỳ
#             return self._finalize_production(raw_video_path, audio_sync_data, video_dir, form_name)
#         return None
    
#     def _finalize_production(self, raw_path, audio_sync_data, video_dir, form_name):
#         final_output = os.path.join(video_dir, f"{form_name}_final_sync.mp4")
#         # Truyền audio_sync_data thay vì chỉ audio_paths
#         success = self.merge_audio_video_with_logo(raw_path, audio_sync_data, final_output)
#         return final_output if success else raw_path