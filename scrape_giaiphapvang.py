import asyncio
import os
from dotenv import load_dotenv
from core.selector_scraper import SelectorScraper

# Load biến môi trường (Lấy tài khoản từ .env)
load_dotenv()

async def main():
    # 1. Khởi tạo Scraper
    scraper = SelectorScraper()
    
    # 2. Cấu hình kịch bản muốn cào
    scenario_name = "giaiphapvang_home"
    url = "https://giaiphapvang.net/auth/jwt/sign-in/"
    
    # Lấy tài khoản từ .env
    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")

    if not email or not password:
        print("❌ Lỗi: Chưa cấu hình USER_EMAIL hoặc USER_PASSWORD trong file .env")
        return

    print(f"🎬 --- BẮT ĐẦU CÀO SELECTORS CHO: {scenario_name.upper()} ---")

    # Bước 1: Gọi hàm cào
    elements = await scraper.get_interactive_elements(url, email, password)
    
    # Bước 2: Xuất ra bảng
    scraper.export_selectors_table(elements, scenario_name)

if __name__ == "__main__":
    asyncio.run(main())

# D:\ThanhVu\AI_code\Giaiphapvang_Studio_Bot\scrape_giaiphapvang.py