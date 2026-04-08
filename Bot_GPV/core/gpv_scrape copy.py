import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config
from Bot_GPV.ai_film_factory.auth_machine import AuthMachine

class GPVEngine:
    def __init__(self):
        self.auth = AuthMachine()
        self.target_domain = Config.TARGET_DOMAIN.replace("https://", "").replace("http://", "").split('/')[0]

    async def run_task(self, mode="HOME_SCAN", module_url=None, project_folder=None, modul_name=None):
        """
        Hệ điều hành trung tâm:
        - mode="HOME_SCAN": Quét 17 Modules ở trang chủ.
        - mode="DEEP_SCAN": Quét chi tiết Sidebar của một Module.
        """
        if not project_folder: project_folder = Config.APP_SLUG
        
        results = {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=100)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                if await self.auth.login(page):
                    # Nếu là DEEP_SCAN thì phải nhảy vào URL của Module đó trước
                    if mode == "DEEP_SCAN" and module_url:
                        await page.goto(module_url, wait_until="networkidle")
                        # Thay vì wait_for_timeout cố định, hãy đợi selector đặc trưng của Sidebar
                        try:
                            await page.wait_for_selector('.MuiList-root', timeout=2000)
                        except:
                            print("⚠️ Sidebar load hơi chậm, vẫn tiếp tục quét...")
                        
                        await page.wait_for_timeout(2000) # Đợi thêm tí cho animation ổn định
                        await page.keyboard.press("Escape") # Đóng các popup che khuất

                    if mode == "HOME_SCAN":
                        results = await self._extract_home_modules(page)
                    else:
                        # TRUYỀN modul_name vào đây để đánh nhãn
                        results = await self._extract_sidebar_deep(page, modul_name)

                    # Chụp ảnh báo cáo_extract_sidebar_deep
                    asset_path = Config.get_path(app=project_folder, module="System", form="Scanner", asset_type="assets")
                    await page.screenshot(path=str(asset_path / f"last_{mode.lower()}.jpg"))

            except Exception as e:
                print(f"❌ [GPVEngine] Lỗi: {e}")
            finally:
                await browser.close()
        return results

    async def _extract_sidebar_deep(self, page, modul_name):
        prefix = f"{modul_name}" if modul_name else "Chung"
        
        # 1. Đọc file JS (Ông có thể để code đọc file này ở __init__ cho nhanh)
        # js_path = Path(__file__).parent.parent / "ai_film_factory" / "js" / "sidebar_script.js"
        js_path = Config.get_javascript("sidebar_script.js")

        # Kiểm tra lại để chắc chắn không lỗi nữa
        if not js_path.exists():
            print(f"❌ Vẫn không tìm thấy file tại: {js_path}")
        else:
            print(f"✅ Đã kết nối thành công: {js_path}")
        


        js_code = js_path.read_text(encoding='utf-8')

        # 2. Bơm code vào trang
        await page.evaluate(js_code)

        # 3. Gọi hàm JS đã nạp
        await page.evaluate('window.sidebarScraper.expandAll()')
        
        # 4. Lấy kết quả
        results = await page.evaluate(f'window.sidebarScraper.extractData("{prefix}")')
        
        return results
    
    async def _extract_home_modules(self, page):
        """
        Logic Cấp 1: Quét xuyên tất cả Iframe để tìm Module bằng script ngoài.
        """
        all_links = []
        
        # 1. Xác định đường dẫn file JS (nằm trong ai_film_factory/js/)
        # Giả sử file python này đang ở thư mục 'core'
        base_path = Path(__file__).parent.parent 
        # js_file_path = base_path / "ai_film_factory" / "js" / "extract_modules.js"
        js_file_path = Config.get_javascript("extract_modules.js")
        
        if not js_file_path.exists():
            print(f"❌ Không tìm thấy script: {js_file_path}")
            return []

        # Đọc nội dung script
        js_script = js_file_path.read_text(encoding='utf-8')

        # 2. Lấy tất cả các Frames đang có trên trang
        frames = page.frames
        print(f"🕵️ Đang quét Module trên {len(frames)} frames...")

        for frame in frames:
            try:
                # Thực thi script JS đã đọc từ file
                raw = await frame.evaluate(js_script)
                if raw:
                    all_links.extend(raw)
            except Exception as e:
                # Bỏ qua các frame dính lỗi Cross-origin (bảo mật browser)
                continue 

        # 3. Lọc lại theo đặc điểm của Giải Pháp Vàng (Python Logic)
        unique = {}
        exclude_keywords = ["đăng xuất", "cài đặt", "hướng dẫn", "thông báo", "profile", "user"]
        
        for m in all_links:
            # Làm sạch các ký tự đặc biệt bằng Regex Python
            text_clean = re.sub(r'[•○+►]', '', m['text']).strip()
            href = m['href'].lower()
            
            # Điều kiện lọc Module đặc thù
            if '/module/' in href or (self.target_domain in href and len(text_clean) > 2):
                if not any(k in text_clean.lower() for k in exclude_keywords):
                    if text_clean not in unique:
                        unique[text_clean] = {"text": text_clean, "href": m['href']}

        return list(unique.values())

       

    