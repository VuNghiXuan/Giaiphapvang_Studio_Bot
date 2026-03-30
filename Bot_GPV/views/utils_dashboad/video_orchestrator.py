import asyncio
import edge_tts
import os

# Thêm vào trong Class AIHandler
async def prepare_voice_assets(self, script_steps, output_dir):
    """
    Duyệt qua các bước, lọc ra các hành động 'speak' 
    và dùng edge-tts để tạo file mp3 cho từng bước.
    """
    os.makedirs(output_dir, exist_ok=True)
    voice = "vi-VN-HoaiMyNeural"
    
    tasks = []
    for i, step in enumerate(script_steps):
        text = step.get("text") or step.get("speech")
        if text:
            # Tạo file name theo số thứ tự để Bot dễ gọi: 0_speech.mp3, 1_speech.mp3
            file_path = os.path.join(output_dir, f"{i}_voice.mp3")
            # Lưu path vào chính cái step đó để tí nữa Playwright lấy ra dùng
            step["voice_path"] = file_path 
            
            # Tạo task chạy song song cho nhanh
            communicate = edge_tts.Communicate(text, voice, rate="+10%")
            tasks.append(communicate.save(file_path))
            
    if tasks:
        await asyncio.gather(*tasks)
        print(f"🎙️ Đã chuẩn bị xong {len(tasks)} file lồng tiếng cho Hoài My.")
    return script_steps