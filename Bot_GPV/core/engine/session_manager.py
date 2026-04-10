from playwright.async_api import async_playwright
from config import Config
from Bot_GPV.ai_film_factory.auth_machine import AuthMachine

class SessionManager:
    def __init__(self):
        self.auth = AuthMachine()

    async def create_session(self, p):
        print(f"🌐 Khởi tạo Chromium...")
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print(f"🔑 Đang đăng nhập hệ thống...")
        if await self.auth.login(page):
            print(f"✅ Đăng nhập thành công!")
            return page, browser
        
        await browser.close()
        return None, None