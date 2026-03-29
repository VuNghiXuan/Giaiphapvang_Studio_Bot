import asyncio
import os
import edge_tts
import random
from playwright.async_api import async_playwright
# Cần cài đặt: pip install moviepy
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips, CompositeVideoClip, ImageClip, CompositeAudioClip

class VideoEngine:
    def __init__(self, storage_path="./storage", logo_path="assets/logo.png"):
        self.storage_path = storage_path
        self.logo_path = logo_path # Đường dẫn đến file logo PNG của Vũ
        self.voice = "vi-VN-HoaiMyNeural"

    async def generate_audio(self, text, output_path):
        """Sử dụng Edge-TTS để tạo giọng Hoài My cho từng bước"""
        # rate="+15%" để đọc nhanh hơn một chút cho súc tích
        communicate = edge_tts.Communicate(text, self.voice, rate="+15%")
        await communicate.save(output_path)
        return output_path

    async def move_mouse_humanlike(self, page, target_selector):
        """Di chuyển chuột theo đường cong Bezier để giống người thật (Simplifed)"""
        try:
            # Lấy tọa độ mục tiêu
            box = await page.locator(target_selector).bounding_box()
            if not box: return
            
            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2
            
            # Playwright hỗ trợ di chuyển mượt mà cơ bản bằng mouse.move
            # Để tạo độ cong thực sự thì cần thuật toán phức tạp hơn, 
            # ở đây ta dùng steps để tạo độ trễ nhẹ.
            await page.mouse.move(target_x, target_y, steps=20) 
            await asyncio.sleep(0.2) # Nghỉ nhẹ sau khi di chuyển
        except Exception as e:
            print(f"⚠️ Lỗi di chuyển chuột: {e}")

    def merge_audio_video_with_logo(self, video_raw_path, audio_paths, output_path, bg_music_path=None):
        try:
            print(f"🎬 Đang xử lý hậu kỳ...")
            video = VideoFileClip(video_raw_path)
            
            # 1. Ghép các đoạn thuyết minh
            voice_clips = [AudioFileClip(p) for p in audio_paths if os.path.exists(p)]
            if not voice_clips: return False
            final_voice = concatenate_audioclips(voice_clips)
            
            # 2. Xử lý Nhạc nền (Nếu có)
            if bg_music_path and os.path.exists(bg_music_path):
                bg_music = AudioFileClip(bg_music_path).volumex(0.1) # Giảm âm lượng nhạc nền xuống 10%
                # Lặp lại nhạc nền nếu video dài hơn nhạc
                bg_music = bg_music.loop(duration=final_voice.duration)
                final_audio = CompositeAudioClip([final_voice, bg_music])
            else:
                final_audio = final_voice

            # Khớp độ dài video với audio
            if final_audio.duration > video.duration:
                video = video.set_duration(final_audio.duration)
            
            video_with_audio = video.set_audio(final_audio)
            
            # 3. Chèn Logo
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path)
                        .set_duration(video_with_audio.duration)
                        .resize(height=60)
                        .set_opacity(0.8)
                        .set_position(("right", "top")))
                final_video = CompositeVideoClip([video_with_audio, logo])
            else:
                final_video = video_with_audio

            # 4. Xuất video
            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
            
            # 5. DỌN DẸP FILE TẠM (Cleanup)
            video.close()
            final_video.close()
            for p in audio_paths:
                try: os.remove(p) # Xóa các file mp3 tạm
                except: pass
            
            return True
        except Exception as e:
            print(f"❌ Lỗi hậu kỳ: {e}")
            return False

    async def run_studio_bot(self, target_url, script_steps, project_name, form_name):
        """
        Con Bot 'Tự biên tự diễn': 
        Mở trình duyệt -> Diễn theo kịch bản -> Quay phim -> Lồng tiếng -> Chèn Logo
        """
        async with async_playwright() as p:
            # 1. Khởi tạo trình duyệt (Headless=False để Vũ xem nó diễn)
            # Khuyên dùng: Dùng channel="chrome" để giống trình duyệt thật nhất
            browser = await p.chromium.launch(headless=False) 
            
            # 2. Thiết lập quay phim màn hình
            # Cấu trúc: storage/Project_Name/videos/Form_Name/
            video_dir = os.path.join(self.storage_path, project_name, "videos", form_name)
            os.makedirs(video_dir, exist_ok=True)
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}, # Chuẩn HD 720p
                record_video_dir=video_dir # Tự động quay WebM
            )
            
            page = await context.new_page()
            print(f"🚀 Bot 'Giải Pháp Vàng' đang tiến vào: {target_url}")
            await page.goto(target_url)
            
            audio_files = []

            # 3. Duyệt qua từng bước trong kịch bản JSON
            for i, step in enumerate(script_steps):
                action = step.get("action")
                target = step.get("target")
                speech = step.get("text", "")
                val = step.get("value", "")
                
                # --- PHẦN LỒNG TIẾNG ---
                if speech:
                    a_path = os.path.join(video_dir, f"step_{i}.mp3")
                    await self.generate_audio(speech, a_path)
                    audio_files.append(a_path)
                    print(f"🎙️ Hoài My lồng tiếng step {i}...")
                    
                    # Lấy độ dài audio để Bot 'chờ' cho nói hết
                    # (Cần import AudioFileClip để lấy duration chính xác nhất ở đây)
                    try:
                        temp_audio = AudioFileClip(a_path)
                        audio_duration = temp_audio.duration
                        temp_audio.close()
                    except:
                        audio_duration = 1.0 # Fail-safe
                else:
                    audio_duration = 0.5 # Khoảng lặng mặc định

                # --- PHẦN DIỄN XUẤT (PLAYWRIGHT) ---
                try:
                    # Di chuyển chuột mượt mà đến mục tiêu nếu có
                    if target:
                        await page.locator(target).scroll_into_view_if_needed()
                        await self.move_mouse_humanlike(page, target) 

                    if action == "highlight":
                        # Dùng evaluate để vẽ viền vàng nổi bật (Highlight)
                        await page.locator(target).evaluate("el => el.style.outline = '5px solid yellow'")
                        
                    elif action == "click":
                        await page.click(target)
                        
                    elif action == "type":
                        # Gõ chậm (delay) cho thật
                        await page.type(target, str(val), delay=100)

                    # Quan trọng: Bot đứng chờ Hoài My nói xong mới làm bước tiếp theo
                    # Ta cộng thêm 0.3s để ngắt nghỉ tự nhiên
                    await asyncio.sleep(audio_duration + 0.3)
                    
                except Exception as e:
                    print(f"⚠️ Lỗi step {i} ({action} trên {target}): {e}")

            # 4. Đóng máy
            await context.close()
            raw_video_path = await page.video.path()
            await browser.close()
            
            # 5. Hợp nhất âm thanh, video và chèn LOGO
            print("🎬 Bot diễn xong, bắt đầu nấy video...")
            final_output = os.path.join(video_dir, f"{form_name}_final.mp4")
            success = self.merge_audio_video_with_logo(raw_video_path, audio_files, final_output)
            
            if success:
                print(f"✅ THÀNH CÔNG! Video tại: {final_output}")
                return final_output
            else:
                print("❌ Xuất video thất bại, trả về video thô.")
                return raw_video_path