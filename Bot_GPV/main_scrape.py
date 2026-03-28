# import os
# import sys
# import time
# import re
# from dotenv import load_dotenv
# from playwright.sync_api import sync_playwright

# # Đảm bảo Python tìm thấy folder 'crawle'
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(BASE_DIR)

# from Bot_GPV.crawle.discovery import Discovery
# from Bot_GPV.crawle.app_extractor import AppExtractor

# # Load biến môi trường từ gốc dự án
# load_dotenv(os.path.join(BASE_DIR, '.env'))

# def get_data_path():
#     data_dir = os.path.join(BASE_DIR, "data")
#     if not os.path.exists(data_dir):
#         os.makedirs(data_dir)
#     return data_dir

# def login(page):
#     print("🔑 Đang đăng nhập hệ thống...")
#     try:
#         # Sử dụng URL mới ông vừa cập nhật
#         page.goto("https://giaiphapvang.net/auth/jwt/sign-in/", timeout=60000)
        
#         # Đợi các ô input sẵn sàng
#         page.wait_for_selector("input[name='email']", timeout=15000)
        
#         page.fill("input[name='email']", os.getenv("USER_EMAIL"))
#         page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
#         page.click("button[type='submit']")
        
#         # Đợi URL chuyển sang home
#         page.wait_for_url("**/home/**", timeout=30000)
#         print("🏠 Đăng nhập thành công!")
        
#         # Nghỉ một chút để hệ thống tải Sidebar
#         page.wait_for_timeout(3000)
#         return True
#     except Exception as e:
#         print(f"❌ Đăng nhập thất bại: {e}")
#         return False

# def main():
#     data_path = get_data_path()
    
#     with sync_playwright() as p:
#         # Thêm args maximized và slow_mo để tránh bị hệ thống chặn
#         browser = p.chromium.launch(headless=False, args=["--start-maximized"], slow_mo=300)
#         # Ép viewport lớn để Sidebar không bị ẩn vào nút Toggle (Mobile view)
#         context = browser.new_context(viewport={'width': 1920, 'height': 1080})
#         page = context.new_page()
        
#         try:
#             if not login(page):
#                 print("🛑 Dừng chương trình do không thể đăng nhập.")
#                 return

#             # Bước 1: Khám phá danh mục App
#             discovery = Discovery(page)
#             apps = discovery.run()
            
#             if not apps:
#                 print("⚠️ Không tìm thấy module nào! Có thể do Sidebar chưa load kịp.")
#                 return

#             # Bước 2: Đi sâu vào từng App
#             extractor = AppExtractor()
            
#             for app_name in apps.keys():
#                 print(f"\n🚀 Tiến vào: {app_name}")
                
#                 try:
#                     # Click vào Menu item. Force=True để vượt qua các lớp che phủ của MUI
#                     # Dùng regex để khớp chính xác tên app, tránh click nhầm
#                     page.click(f"text={app_name}", force=True, timeout=10000)
#                     page.wait_for_load_state("networkidle")
                    
#                     # Trích xuất dữ liệu chi tiết
#                     extractor.extract_structure(page, app_name)
#                     time.sleep(1.5) 
                    
#                 except Exception as inner_e:
#                     print(f"⚠️ Bỏ qua {app_name}: {inner_e}")
#                     # Nếu lỗi click, quay lại trang home để tiếp tục danh sách
#                     page.goto("https://giaiphapvang.net/home/")
#                     continue
                
#             print(f"\n✨ HOÀN THÀNH! Dữ liệu tại: {data_path}")
            
#         except Exception as e:
#             print(f"❌ Lỗi hệ thống: {e}")
#         finally:
#             print("👋 Đang đóng trình duyệt trong 5s...")
#             time.sleep(5)
#             browser.close()

# if __name__ == "__main__":
#     main()