import os
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, 
    ImageClip, CompositeAudioClip, concatenate_videoclips, 
    TextClip, ColorClip
)

class PostProductionMachine:
    def __init__(self, logo_path=None):
        self.logo_path = logo_path    


    def process(self, video_path, audio_sync_data, script_steps, output_path, **kwargs):
        try:
            print(f"🎬 Đang xử lý hậu kỳ cho: {video_path}")
            video = VideoFileClip(video_path)
            audio_clips = []
            subtitle_clips = []
            
            # 1. Tạo Audio Clips trước
            for i, item in enumerate(audio_sync_data):
                f_path = item.get('file_path')
                start_at = item.get('start_at', 0)
                if f_path and os.path.exists(f_path):
                    a_clip = AudioFileClip(f_path).set_start(start_at)
                    audio_clips.append(a_clip)

            if not audio_clips: return False
            
            # 2. Hợp nhất Audio & Xử lý Freeze Frame
            final_audio = CompositeAudioClip(audio_clips)
            final_v = video
            if final_audio.duration > video.duration:
                # Lấy frame cuối làm ảnh tĩnh
                last_frame = video.get_frame(video.duration - 0.1)
                freeze = (ImageClip(last_frame)
                          .set_duration(final_audio.duration - video.duration + 1.0) # Thêm 1s cho thư thả
                          .set_fps(video.fps))
                final_v = concatenate_videoclips([video, freeze])
            
            final_duration = final_v.duration

            # 3. Layer nền đen (Đặt duration theo final_duration)
            black_bg = (ColorClip(size=(video.w, 100), color=(0,0,0))
                        .set_opacity(0.5)
                        .set_position(('center', 'bottom'))
                        .set_duration(final_duration))

            # 4. Tạo Subtitles
            for i, item in enumerate(audio_sync_data):
                start_at = item.get('start_at', 0)
                txt = script_steps[i].get("speak") or script_steps[i].get("text", "")
                if txt and i < len(audio_clips):
                    # Lấy duration theo đúng file audio tương ứng
                    sub_dur = audio_clips[i].duration
                    sub = (TextClip(txt, fontsize=28, color='white', font='Arial-Bold',
                                    method='caption', size=(video.w*0.8, None))
                           .set_start(start_at)
                           .set_duration(sub_dur)
                           .set_position(('center', video.h - 75)))
                    subtitle_clips.append(sub)

            # 5. Gộp layer & Render
            all_layers = [final_v.set_audio(final_audio), black_bg] + subtitle_clips
            
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path).resize(height=50)
                        .set_duration(final_duration)
                        .set_position(("right", "top")).set_opacity(0.7))
                all_layers.append(logo)

            final_result = CompositeVideoClip(all_layers)
            final_result.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, logger=None)
            
            # DỌN DẸP RÁC (Cực kỳ quan trọng để không treo máy)
            final_result.close()
            video.close()
            for a in audio_clips: a.close()
            
            return True
        except Exception as e:
            print(f"❌ Post-Production Error: {e}")
            return False