import os
import time
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, 
    ImageClip, CompositeAudioClip, concatenate_videoclips
)

class PostProductionMachine:
    def __init__(self, logo_path=None):
        self.logo_path = logo_path    

    def process(self, video_path, audio_sync_data, script_steps, output_path, **kwargs):
        try:
            print(f"🎬 Đang ghép tiếng và logo cho: {video_path}")
            
            if not os.path.exists(video_path):
                print(f"❌ File video gốc không tồn tại: {video_path}")
                return False

            # Tăng thời gian đợi để Playwright nhả file hoàn toàn
            time.sleep(2) 
            
            # 1. Khởi tạo Video với kiểm tra an toàn
            video = VideoFileClip(video_path)
            if video is None or video.duration is None:
                print("❌ MoviePy không thể đọc được video. Kiểm tra codec .webm")
                return False
                
            v_fps = video.fps if video.fps else 24 # Fallback nếu fps bị None
            
            audio_clips = []
            # 2. Thu thập Audio (Sửa lỗi ép kiểu dữ liệu)
            for item in audio_sync_data:
                if not isinstance(item, dict): continue # Né NoneType
                
                f_path = item.get('file_path')
                # Đảm bảo start_at là float, mặc định 0.0
                try:
                    start_at = float(item.get('start_at', 0))
                except:
                    start_at = 0.0
                
                if f_path and os.path.exists(f_path):
                    a_clip = AudioFileClip(f_path).set_start(start_at)
                    audio_clips.append(a_clip)

            if not audio_clips:
                print("❌ Không có file audio hợp lệ để ghép!")
                video.close() # Đóng video ngay để tránh kẹt file
                return False
            
            # 3. Hợp nhất Audio
            final_audio = CompositeAudioClip(audio_clips)
            
            # 4. Khớp thời gian & Freeze Frame (Fix lỗi .get_frame)
            final_v = video
            if final_audio.duration > video.duration:
                # Lấy frame tại giây cuối cùng trừ đi 0.1 để an toàn
                last_moment = max(0, video.duration - 0.1)
                last_frame = video.get_frame(last_moment)
                freeze_dur = (final_audio.duration - video.duration) + 1.0
                
                freeze = (ImageClip(last_frame)
                          .set_duration(freeze_dur)
                          .set_fps(v_fps)) # Dùng v_fps đã check ở trên
                final_v = concatenate_videoclips([video, freeze])
            
            final_v = final_v.set_audio(final_audio)
            
            # 5. Gộp Logo
            all_layers = [final_v]
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path)
                        .resize(height=55)
                        .set_duration(final_v.duration)
                        .set_position(("right", "top"))
                        .set_opacity(0.8))
                all_layers.append(logo)

            # 6. Render (Dùng temp_audiofile để tránh lỗi quyền truy cập file trên Windows)
            final_result = CompositeVideoClip(all_layers)
            final_result.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac", # aac ổn định hơn libmp3lame trên một số hệ máy
                fps=v_fps, 
                preset="ultrafast",
                threads=4,
                temp_audiofile=os.path.join(os.path.dirname(output_path), "temp-audio.m4a"),
                remove_temp=True
            )
            
            # Dọn dẹp
            final_result.close()
            if final_v != video: final_v.close()
            video.close()
            for a in audio_clips: a.close()
            
            return True

        except Exception as e:
            print(f"❌ Lỗi hậu kỳ nghiêm trọng: {e}")
            import traceback
            traceback.print_exc() # In chi tiết lỗi để Vũ soi cho dễ
            return False