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
        """
        Hàm hậu kỳ chuẩn:
        - video_path: Đường dẫn video thô từ StudioMachine
        - audio_sync_data: Danh sách thời gian bắt đầu của từng câu thoại
        - script_steps: Nội dung kịch bản để vẽ Subtitle
        """
        try:
            print(f"🎬 Đang xử lý hậu kỳ cho: {video_path}")
            video = VideoFileClip(video_path)
            audio_clips = []
            subtitle_clips = []
            
            # Layer nền đen mờ phía dưới cho Subtitle dễ đọc
            black_bg = (ColorClip(size=(video.w, 120), color=(0,0,0))
                        .set_opacity(0.6)
                        .set_position(('center', 'bottom'))
                        .set_duration(video.duration))

            for i, item in enumerate(audio_sync_data):
                f_path = item.get('file_path')
                start_at = item.get('start_at', 0)
                
                if f_path and os.path.exists(f_path):
                    # 1. Âm thanh
                    a_clip = AudioFileClip(f_path).set_start(start_at)
                    audio_clips.append(a_clip)
                    
                    # 2. Subtitle (Lấy từ key 'speak' trong JSON của Vũ)
                    txt = script_steps[i].get("speak", "")
                    if txt:
                        sub = (TextClip(txt, fontsize=30, color='white', font='Arial',
                                       method='caption', size=(video.w*0.8, None))
                               .set_start(start_at)
                               .set_duration(a_clip.duration)
                               .set_position(('center', video.h - 80)))
                        subtitle_clips.append(sub)

            if not audio_clips:
                return False

            # Hợp nhất Audio
            final_audio = CompositeAudioClip(audio_clips)
            
            # Đồng bộ chiều dài video nếu thoại dài hơn hành động
            final_v = video
            if final_audio.duration > video.duration:
                last_frame = video.get_frame(video.duration - 0.1)
                freeze = ImageClip(last_frame).set_duration(final_audio.duration - video.duration + 0.5).set_fps(video.fps)
                final_v = concatenate_videoclips([video, freeze])

            video_with_audio = final_v.set_audio(final_audio)
            
            # Gộp các layer
            all_layers = [video_with_audio, black_bg] + subtitle_clips
            
            # Thêm Logo nếu có
            if self.logo_path and os.path.exists(self.logo_path):
                logo = (ImageClip(self.logo_path).resize(height=40)
                        .set_duration(video_with_audio.duration)
                        .set_position(("right", "top")).set_opacity(0.8))
                all_layers.append(logo)

            final_result = CompositeVideoClip(all_layers)
            final_result.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, logger=None)
            
            return True
        except Exception as e:
            print(f"❌ Post-Production Error: {e}")
            return False