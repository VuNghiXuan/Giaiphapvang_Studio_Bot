import os
import asyncio
from config import Config
from dotenv import load_dotenv

# Load lại env để chắc chắn ăn được USER_EMAIL, USER_PASSWORD
load_dotenv()

class AuthMachine:
    def __init__(self, vision_machine=None):
        self.vision = vision_machine
        self.target_domain = getattr(Config, 'TARGET_DOMAIN', "https://giaiphapvang.net")
        self.email = os.getenv("USER_EMAIL")
        self.password = os.getenv("USER_PASSWORD")

    async def login(self, page):
        """
        Quy trình đăng nhập thông minh: 
        Tự động Retry, đợi Selector thay vì đợi NetworkIdle để tránh Timeout.
        """
        if not self.email or not self.password:
            print("❌ Lỗi: Thiếu USER_EMAIL hoặc USER_PASSWORD trong file .env")
            return False

        base_url = self.target_domain.rstrip('/')
        login_url = f"{base_url}/auth/jwt/sign-in/"
        
        print(f"🔑 Đang đăng nhập hệ thống: {base_url}")

        for attempt in range(1, 4): # Thử lại tối đa 3 lần
            try:
                # Dùng 'domcontentloaded' thay vì 'networkidle' để load nhanh hơn, đỡ treo
                await page.goto(login_url, wait_until="domcontentloaded", timeout=20000)
                
                # Chờ input xuất hiện mới điền (Chắc chắn trang đã render)
                await page.wait_for_selector("input[name='email']", timeout=10000)
                
                # Điền thông tin với độ trễ nhẹ cho giống người
                await page.fill("input[name='email']", self.email)
                await asyncio.sleep(0.5)
                await page.fill("input[name='password']", self.password)
                await asyncio.sleep(0.5)
                
                print(f"🚀 [Attempt {attempt}] Đang gửi form đăng nhập...")
                await page.click("button[type='submit']")

                # Thay vì wait_for_url (đôi khi URL ko đổi ngay), 
                # hãy đợi 1 phần tử đặc trưng của Dashboard hiện ra (ví dụ Sidebar hoặc Avatar)
                success_element = ".main-sidebar, .MuiDrawer-root, [class*='sidebar'], .MuiAvatar-root"
                await page.wait_for_selector(success_element, timeout=15000)
                
                print("🏠 Đăng nhập thành công! Đã vào Dashboard.")
                await asyncio.sleep(1) # Nghỉ 1s cho ổn định giao diện
                return True

            except Exception as e:
                print(f"⚠️ Lần {attempt} thất bại: {str(e)[:100]}")
                if attempt < 3:
                    print("🔄 Đang thử lại...")
                    await asyncio.sleep(2)
                else:
                    print("❌ Quá số lần thử, dừng quy trình đăng nhập.")
        
        return False