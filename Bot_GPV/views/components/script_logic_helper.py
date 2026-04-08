import os
import json
from pathlib import Path
from config import Config

class ScriptLogicHelper:
    @staticmethod
    def _get_safe_folders(p, s):
        """
        Hàm nội bộ để bóc tách folder name chuẩn chỉnh.
        Thiết quân luật: Phải có sub_folder (định dạng ID_title) mới cho đi tiếp.
        """
        app_folder = p.get('folder_name') or p.get('project_folder')
        # BẮT BUỘC dùng sub_folder từ DB để khớp với cấu trúc vật lý
        sub_folder = s.get('sub_folder') 
        
        if not app_folder or not sub_folder:
            return None, None
        return app_folder, sub_folder

    @staticmethod
    def get_raw_video_path(p, s):
        """
        Lấy video gốc để đưa vào dây chuyền edit.
        """
        app, sub = ScriptLogicHelper._get_safe_folders(p, s)
        if not app:
            print("⚠️ [Logic]: Thiếu định danh folder. Kiểm tra lại DB.")
            return None, None

        # Truy xuất folder 'raw'
        video_dir = Config.get_path(app=app, module=sub, asset_type="raw")
        
        if video_dir.exists():
            # Tìm file video, ưu tiên mp4 rồi đến webm
            video_files = sorted(
                [f for f in video_dir.glob("*") if f.suffix in [".mp4", ".webm"]],
                key=lambda x: x.stat().st_mtime, reverse=True # Lấy file mới nhất
            )
            if video_files:
                return video_files[0], video_dir
        
        return None, video_dir

    @staticmethod
    def save_script_to_file(p, s, steps):
        """
        Lưu kịch bản JSON vào folder 'metadata'.
        """
        app, sub = ScriptLogicHelper._get_safe_folders(p, s)
        if not app: return None

        if not isinstance(steps, list): steps = []
        
        metadata_dir = Config.get_path(app=app, module=sub, asset_type="metadata")
        file_path = metadata_dir / "latest_script.json"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(steps, f, ensure_ascii=False, indent=4)
            
            print(f"✅ [Logic]: Đã chốt kịch bản tại: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ [Logic]: Lỗi ghi kịch bản: {e}")
            return None

    @staticmethod
    def load_latest_script(p, s):
        """
        Đọc lại kịch bản để AI hoặc User biên tập.
        """
        app, sub = ScriptLogicHelper._get_safe_folders(p, s)
        if not app: return []

        metadata_dir = Config.get_path(app=app, module=sub, asset_type="metadata")
        file_path = metadata_dir / "latest_script.json"
        
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    @staticmethod
    def check_script_exists(p, s):
        """
        Check nhanh để hiển thị trạng thái trên UI (ví dụ: Icon ✅/❌)
        """
        app, sub = ScriptLogicHelper._get_safe_folders(p, s)
        if not app: return False

        metadata_dir = Config.get_path(app=app, module=sub, asset_type="metadata")
        return (metadata_dir / "latest_script.json").exists()