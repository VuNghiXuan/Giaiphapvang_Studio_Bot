import os
import re
import unicodedata
from pathlib import Path
import datetime

class Config:
    # ==========================================
    # 1. THÔNG TIN HỆ THỐNG
    # ==========================================
    TARGET_DOMAIN = "https://giaiphapvang.net"
    APP_NAME = "Ứng Dụng Vàng"
    APP_SLUG = 'ung_dung_vang'

    @classmethod
    def get_current_time(cls):
        """Trả về chuỗi thời gian hiện tại theo định dạng VN"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==========================================
    # 2. ĐƯỜNG DẪN HỆ THỐNG (PATHS)
    # ==========================================
    ROOT_DIR = Path(__file__).parent.absolute()
    BASE_STORAGE = ROOT_DIR / "storage"
    DB_PATH = ROOT_DIR / "database.db"
    AI_CACHE_PATH = BASE_STORAGE / "ai_scripts_cache.json"

    @classmethod
    def get_javascript_path(cls, filename):
        """Trả về đối tượng Path để Engine có thể dùng .exists() và .read_text()"""
        return cls.ROOT_DIR / "Bot_GPV" / "js" / filename

    @classmethod
    def get_javascript(cls, filename):
        """Alias cho get_javascript_path để tương thích code cũ"""
        return cls.get_javascript_path(filename)

    # ==========================================
    # 3. CÔNG CỤ CHUẨN HÓA (UTILITIES)
    # ==========================================
    @staticmethod
    def slugify(text, max_length=40): # Tăng lên 40 để tên module không bị cụt
        if not text: return "unknown"
        
        # 1. Tách ID ở đầu (Ví dụ: "49 | Ngân hàng" -> ID="49", Text="Ngân hàng")
        prefix_id = ""
        # Regex tìm số ở đầu, theo sau là các ký tự ngăn cách như |, _, -, hoặc khoảng trắng
        id_match = re.match(r'^(\d+)[_\s|.-]*(.*)', text.strip())
        
        if id_match:
            prefix_id = id_match.group(1) + "_"
            text = id_match.group(2)

        # 2. Chuẩn hóa tiếng Việt (Bỏ dấu)
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = text.replace('đ', 'd').replace('Đ', 'D')
        
        # 3. Làm sạch chữ: bỏ ký tự đặc biệt, thay khoảng trắng bằng gạch dưới
        text = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '_', text.lower()).strip('_')
        
        # 4. Cắt ngắn tên chữ (không tính ID) để folder gọn
        clean_text = text[:max_length].rstrip('_')
        
        return f"{prefix_id}{clean_text}"

    @classmethod
    def get_path(cls, *args, **kwargs):
        """
        Tạo folder phân cấp: storage/ung_dung_vang/cap_1/cap_2/assets
        Truyền vào: Config.get_path("49 | Hệ thống | Ngân hàng", asset_type="assets")
        """
        target_path = cls.BASE_STORAGE / cls.APP_SLUG
        asset_type = kwargs.get('asset_type')

        if args and args[0]:
            # Tách chuỗi theo dấu | để tạo folder lồng nhau
            full_str = str(args[0])
            parts = [p.strip() for p in full_str.split('|') if p.strip()]
            
            for part in parts:
                target_path = target_path / cls.slugify(part)
        
        # Thêm folder con cuối cùng nếu có (ví dụ: assets, logs)
        if asset_type:
            target_path = target_path / asset_type
            
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    @classmethod
    def init_folders(cls):
        cls.BASE_STORAGE.mkdir(parents=True, exist_ok=True)
        print(f"📂 Hệ thống lưu trữ sẵn sàng tại: {cls.BASE_STORAGE}")

# Tự động khởi tạo folder gốc khi load Config
Config.init_folders()