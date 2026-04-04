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
            
            # Đợi file video thô ổn định
            time.sleep(1.5) 
            video = VideoFileClip(video_path)
            
            audio_clips = []
            
            # 1. Thu thập các file Audio 
            # (Subtitle đã được quay trực tiếp vào video thô nhờ EffectMachine)
            for i, item in enumerate(audio_sync_data):
                f_path = item.get('file_path')
                start_at = item.get('start_at', 0)
                
                if f_path and os.path.exists(f_path):
                    a_clip = AudioFileClip(f_path).set_start(start_at)
                    audio_clips.append(a_clip)

            if not audio_clips:
                print("❌ Không có file audio để ghép!")
                return False
            
            # 2. Hợp nhất Audio
            final_audio = CompositeAudioClip(audio_clips)
            
            # 3. Khớp thời gian (Freeze Frame nếu voice dài hơn video)
            final_v = video
            if final_audio.duration > video.duration:
                # Lấy frame cuối làm ảnh tĩnh
                last_frame = video.get_frame(video.duration - 0.1)
                freeze_dur = (final_audio.duration - video.duration) + 1.0
                
                freeze = (ImageClip(last_frame)
                          .set_duration(freeze_dur)
                          .set_fps(video.fps))
                final_v = concatenate_videoclips([video, freeze])
            
            # Gán toàn bộ audio vào video
            final_v = final_v.set_audio(final_audio)
            final_duration = final_v.duration

            # 4. Gộp Logo (ImageClip dùng thư viện Pillow có sẵn, không cần ImageMagick)
            all_layers = [final_v]
            
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path)
                        .resize(height=55) # Tăng kích thước logo một chút cho sang
                        .set_duration(final_duration)
                        .set_position(("right", "top"))
                        .set_opacity(0.8))
                all_layers.append(logo)

            # 5. Render file cuối
            final_result = CompositeVideoClip(all_layers)
            final_result.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="libmp3lame", # MP3 ổn định nhất cho voice
                fps=24, 
                logger=None,
                threads=4
            )
            
            # 6. Dọn dẹp bộ nhớ
            final_result.close()
            final_v.close()
            video.close()
            for a in audio_clips: a.close()
            
            print(f"✅ Xong! Subtitle và Hiệu ứng đã có sẵn trong video từ Browser.")
            return True

        except Exception as e:
            print(f"❌ Lỗi hậu kỳ: {e}")
            return False