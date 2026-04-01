import os
import json
from pathlib import Path
from config import Config

class ScriptLogicHelper:
    @staticmethod
    def get_raw_video_path(p, s):
        """Dò tìm file video gốc và thư mục assets"""
        storage_root = Path(Config.BASE_STORAGE)
        p_name = p.get('project_folder') or p.get('folder_name') or ""
        s_name = s.get('sub_folder', "")

        possible_paths = [
            storage_root / p_name / s_name,
            storage_root / Config.slugify_vietnamese(p_name) / Config.slugify_vietnamese(s_name)
        ]

        target_dir = possible_paths[0]
        for path in possible_paths:
            if path.exists():
                target_dir = path
                break

        if target_dir.exists():
            for item in os.listdir(target_dir):
                if "raw" in item.lower():
                    return target_dir / item, target_dir
        return None, target_dir

    @staticmethod
    def save_script_to_file(target_dir, steps):
        """Lưu kịch bản JSON vào thư mục assets"""
        asset_dir = target_dir / "assets"
        asset_dir.mkdir(parents=True, exist_ok=True)
        file_path = asset_dir / "latest_script.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(steps, f, ensure_ascii=False, indent=4)
        return file_path