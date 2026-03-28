import os

class Config:
    # --- THÔNG TIN HỆ THỐNG TARGET ---
    TARGET_DOMAIN = "https://giaiphapvang.net" # Sau này đổi domain chỉ cần sửa 1 chỗ này
    APP_NAME = "Giải Pháp Vàng"
    
    # --- CẤU HÌNH MARKETING & BRANDING ---
    # Slogan mặc định lấy từ đây, không cần gõ tay lại nhiều lần
    DEFAULT_SLOGAN = "Ứng dụng vàng, giải pháp toàn diện cho ngành kim hoàn"
    
    # Danh sách nghiệp vụ chuẩn (AI Scenarios)
    # Vũ có thể thêm bớt loại hướng dẫn ở đây, GUI sẽ tự cập nhật theo
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
    
    # File chứa toàn bộ kiến thức đã crawl (Knowledge Base)
    KNOWLEDGE_JSON_PATH = os.path.join(BASE_STORAGE, "knowledge_source.json")

    @classmethod
    def init_folders(cls):
        for path in [cls.BASE_STORAGE]:
            if not os.path.exists(path):
                os.makedirs(path)

# Khởi tạo thư mục
Config.init_folders()

# --- CẤU HÌNH AI PROVIDERS ---
# (Giữ nguyên phần API Key của Vũ ở dưới...)