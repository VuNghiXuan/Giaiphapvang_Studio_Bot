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
    APP_SLUG = 'ung_dung_vang'
    ROOT_DIR = Path(__file__).parent.absolute()
    DB_PATH = ROOT_DIR / "database.db"
    BASE_STORAGE = ROOT_DIR / "storage"
    SLOGANT = 'Giải Pháp Toàn Diện Cho Ngành Kim Hoàn'

    # Danh sách các từ khóa gây loãng, sẽ bị loại bỏ khỏi tên folder
    REDUNDANT_KEYWORDS = ['chung', 'default', 'home', 'mac_dinh']

    @classmethod
    def get_current_time(cls):
        """Trả về chuỗi thời gian hiện tại theo định dạng VN"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==========================================
    # 2. ĐƯỜNG DẪN HỆ THỐNG (PATHS)
    # ==========================================
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
    def slugify(text, max_length=40):
        if not text: return ""
        
        # Chuẩn hóa tiếng Việt & bỏ dấu
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn').replace('đ', 'd').replace('Đ', 'D')
        
        # Làm sạch ký tự đặc biệt
        text = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
        
        # Chuyển về snake_case
        slug = re.sub(r'[\s-]+', '_', text.lower()).strip('_')
        
        # NGOẠI LỆ: Nếu gặp các từ khóa thiết lập, gom về 'settings' cho chuyên nghiệp
        if slug in ['chung', 'default', 'thiet_lap', 'cai_dat']:
            return 'settings'
            
        return slug[:max_length]

    @classmethod
    def get_path(cls, *args, **kwargs):
        """
        Tạo folder: storage/ung_dung_vang/he_thong/settings/thong_tin_cong_ty/metadata
        Phân cấp đúng theo Menu thực tế.
        """
        target_path = cls.BASE_STORAGE / cls.APP_SLUG
        asset_type = kwargs.get('asset_type')

        if args and args[0]:
            # Tách chuỗi theo dấu | (Ví dụ: Hệ thống | Chung | Thông tin công ty)
            parts = [p.strip() for p in str(args[0]).split('|') if p.strip()]
            
            for p in parts:
                slug = cls.slugify(p)
                if slug:
                    target_path = target_path / slug
        
        if asset_type:
            target_path = target_path / asset_type
            
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    @classmethod
    def init_folders(cls):
        cls.BASE_STORAGE.mkdir(parents=True, exist_ok=True)
        print(f"📂 Hệ thống lưu trữ sẵn sàng tại: {cls.BASE_STORAGE / cls.APP_SLUG}")

# Tự động chạy khi import
Config.init_folders()