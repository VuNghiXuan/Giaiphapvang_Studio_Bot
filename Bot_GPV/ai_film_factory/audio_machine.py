import asyncio
import os
import time
import edge_tts
from pathlib import Path
# from dotenv import load_dotenv
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, 
    ImageClip, CompositeAudioClip, concatenate_videoclips
)

# Load biến môi trường
# load_dotenv()

# ==========================================
# 1. CỖ MÁY ÂM THANH (TTS)
# ==========================================
class AudioMachine:
    def __init__(self, voice="vi-VN-HoaiMyNeural"):
        self.voice = voice

    async def generate(self, text, output_path):
        """Tạo giọng đọc AI từ văn bản"""
        if not text:
            return 0.5
        communicate = edge_tts.Communicate(text, self.voice, rate="+0%") #-5%
        await communicate.save(output_path)
        
        # Trả về thời lượng audio để đồng bộ
        with AudioFileClip(output_path) as clip:
            return clip.duration
