import os
import re
import unicodedata

class Config:
    # --- THÔNG TIN HỆ THỐNG TARGET ---
    TARGET_DOMAIN = "https://giaiphapvang.net"
    APP_NAME = "Ứng Dụng Vàng"
    
    # --- CẤU HÌNH MARKETING & BRANDING ---
    DEFAULT_SLOGAN = "Ứng dụng vàng, giải pháp toàn diện cho ngành kim hoàn"
    
    # --- CẤU HÌNH AI & NGHIỆP VỤ ---
    # Để trống để người dùng tự nhập biến tấu cho từng bài
    DEFAULT_AI_NOTES = "" 

    AI_SCENARIOS = [
        {"id": "ADD", "label": "Hướng dẫn Thêm mới", "icon": "➕"},
        {"id": "EDIT", "label": "Chỉnh sửa thông tin", "icon": "📝"},
        {"id": "DEL", "label": "Xóa/Hủy dữ liệu", "icon": "🗑️"},
        {"id": "SEARCH", "label": "Tra cứu & Bộ lọc", "icon": "🔍"},
        {"id": "REPORT", "label": "Xuất báo cáo", "icon": "📊"},
        {"id": "FLOW", "label": "Kết nối quy trình", "icon": "🔗"}
    ]

    # --- ĐƯỜNG DẪN LƯU TRỮ (Paths) ---
    BASE_STORAGE = os.path.abspath("./storage")
    SCRIPTS_DIR_NAME = "scripts"
    RAW_DIR_NAME = "raw"
    DB_PATH = os.path.abspath("database.db")
    
    # File Cache chứa kịch bản AI đã soạn
    AI_CACHE_PATH = os.path.join(BASE_STORAGE, "ai_scripts_cache.json")

    @staticmethod
    def slugify_vietnamese(text):
        """Chuyển 'Hệ thống' thành 'He_thong' để đặt tên file an toàn"""
        if not text: return "unknown"
        # 1. Tách dấu ra khỏi chữ cái
        text = unicodedata.normalize('NFD', text)
        # 2. Loại bỏ các ký tự dấu
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        # 3. Thay đ bằng d
        text = text.replace('đ', 'd').replace('Đ', 'D')
        # 4. Chuyển sang chữ thường, thay khoảng trắng và ký tự lạ bằng gạch dưới
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '_', text)
        return text

    @classmethod
    def get_knowledge_path(cls, project_name, module_name, form_name):
        """
        Tạo đường dẫn: storage/Giai_Phap_Vang/he_thong_chi_nhanh.json
        """
        # Chuẩn hóa tên thư mục dự án (Ví dụ: Giai_Phap_Vang)
        proj_folder = project_name.replace(" ", "_")
        
        # Chuẩn hóa tên file sạch dấu (Ví dụ: he_thong_chi_nhanh.json)
        clean_mod = cls.slugify_vietnamese(module_name)
        clean_form = cls.slugify_vietnamese(form_name)
        file_name = f"{clean_mod}_{clean_form}.json"
        
        full_folder_path = os.path.join(cls.BASE_STORAGE, proj_folder)
        
        if not os.path.exists(full_folder_path):
            os.makedirs(full_folder_path, exist_ok=True)
            
        return os.path.join(full_folder_path, file_name)

    @classmethod
    def init_folders(cls):
        if not os.path.exists(cls.BASE_STORAGE):
            os.makedirs(cls.BASE_STORAGE, exist_ok=True)

# Khởi tạo
Config.init_folders()