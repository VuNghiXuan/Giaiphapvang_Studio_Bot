from config import Config
from models.db_engine import DBEngine
import shutil

# 1. Dọn dẹp
if Config.DB_PATH.exists():
    Config.DB_PATH.unlink()
if Config.BASE_STORAGE.exists():
    shutil.rmtree(Config.BASE_STORAGE)

# 2. Khởi tạo lại
db = DBEngine() 
Config.init_folders()

print("🚀 HỆ THỐNG ĐÃ RESET SẠCH SẼ. SẴN SÀNG QUÉT DỮ LIỆU MỚI!")