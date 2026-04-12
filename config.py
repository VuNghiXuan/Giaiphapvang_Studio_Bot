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
        Tạo folder: storage/[tên_dự_án]/[module]/[form]/[asset_type]
        """
        # 1. Lấy project_slug từ tham số truyền vào (đây là tên folder trong DB)
        project_slug = kwargs.get('project_slug')
        
        if not project_slug:
            project_slug = cls.APP_SLUG
        else:
            # Luôn slugify để đảm bảo không có khoảng trắng/dấu tiếng Việt
            project_slug = cls.slugify(str(project_slug))

        # 2. Đường dẫn gốc: storage/ungdungvang
        target_path = cls.BASE_STORAGE / project_slug
        asset_type = kwargs.get('asset_type')

        # 3. Xử lý các cấp con (Hệ thống | Thiết lập | Chi nhánh)
        if args and args[0]:
            parts = [p.strip() for p in str(args[0]).split('|') if p.strip()]
            for p in parts:
                slug = cls.slugify(p)
                if slug:
                    target_path = target_path / slug
        
        # 4. Thêm loại asset (metadata, videos, audios)
        if asset_type:
            target_path = target_path / asset_type
            
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    @classmethod
    def get_asset_path(cls, module_name, form_name, asset_type="videos"):
        # 1. Chuẩn hóa (Bỏ project_name vì đã có APP_SLUG làm gốc)
        safe_m = cls.slugify(module_name)
        safe_f = cls.slugify(form_name)
        
        # 2. Xây dựng Path chuẩn: storage/ung_dung_vang/he_thong/danh_muc_khach_hang/videos
        base = cls.BASE_STORAGE / cls.APP_SLUG / safe_m / safe_f
        
        if asset_type:
            base = base / asset_type
            
        base.mkdir(parents=True, exist_ok=True)
        return base # Trả về Path object luôn cho tiện

    @classmethod
    def init_folders(cls):
        cls.BASE_STORAGE.mkdir(parents=True, exist_ok=True)
        print(f"📂 Hệ thống lưu trữ sẵn sàng tại: {cls.BASE_STORAGE / cls.APP_SLUG}")

# Tự động chạy khi import
Config.init_folders()