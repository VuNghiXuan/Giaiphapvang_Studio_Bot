import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config
from Bot_GPV.ai_film_factory.auth_machine import AuthMachine
from Bot_GPV.core.gpv_form_miner import FormMiner

class ModuleNavigator:
    def __init__(self):
        self.auth = AuthMachine()
        self.target_domain = Config.TARGET_DOMAIN.replace("https://", "").replace("http://", "").split('/')[0]

    async def run_task(self, mode="HOME_SCAN", module_url=None, project_folder=None, modul_name=None):
        """
        Hệ điều hành trung tâm của Engine:
        - Bàn giao quyền điều hướng cho AuthMachine.login.
        - Chỉ thực thi quét sau khi Dashboard đã hiện ra.
        """
        m_name = modul_name if modul_name else "Chung"
        results = {}

        # Lấy domain gốc để ghép link module nếu cần
        base_url = str(Config.TARGET_DOMAIN).strip().rstrip('/')
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        async with async_playwright() as p:
            # 1. Khởi tạo trình duyệt
            browser = await p.chromium.launch(headless=False, slow_mo=100)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()

            try:
                print(f"🚀 [Engine] Bắt đầu phiên làm việc: {mode}")

                # 2. GỌI LOGIN (ĐỂ AUTH TỰ ĐIỀU HƯỚNG ĐẾN LOGIN_URL)
                # Tuyệt đối không page.goto trước dòng này để tránh xung đột
                if await self.auth.login(page):
                    
                    # --- CHẾ ĐỘ 1: QUÉT CHI TIẾT MODULE (DEEP_SCAN) ---
                    if mode == "DEEP_SCAN" and module_url:
                        # 1. Chuẩn hóa URL Module
                        final_module_url = module_url
                        if not module_url.startswith("http"):
                            final_module_url = f"{base_url}/{module_url.lstrip('/')}"
                        
                        print(f"📡 [DeepScan] Di chuyển tới: {final_module_url}")
                        
                        # Điều hướng đến trang module
                        await page.goto(final_module_url, wait_until="domcontentloaded")
                        
                        # 2. Đợi sidebar ổn định (đặc trưng của GPV)
                        try:
                            await page.wait_for_selector('.minimal__nav__li', timeout=2000)
                        except:
                            print(f"⚠️ Sidebar của {m_name} load hơi chậm hoặc không có sidebar đặc thù.")

                        await page.wait_for_timeout(1000)
                        await page.keyboard.press("Escape") # Đóng các thông báo/modal che khuất ban đầu nếu có

                        # 3. QUÉT SIDEBAR (Để lấy danh sách menu con nếu cần)
                        sidebar_results = await self._extract_sidebar_deep(page, m_name)
                        
                        # 4. KÍCH HOẠT "THỢ ĐÀO" (FormMiner) - ĐÂY LÀ CHỖ GỌI QUAN TRỌNG NHẤT
                        # from .page_miner import FormMiner # Đảm bảo file page_miner.py nằm cùng thư mục
                        
                        miner = FormMiner(page, config_class=Config)
                        
                        # Thực hiện vét sạch dữ liệu trang (Table, Input) và tự động vào Form con
                        mining_results = await miner.start_mining(final_module_url, m_name)

                        # 5. TỔNG HỢP KẾT QUẢ
                        results = {
                            "module_info": sidebar_results,
                            "ui_metadata": mining_results,
                            "scan_time": Config.get_current_time() # Giả sử config có hàm này
                        }
                        
                        print(f"✅ [DeepScan] Hoàn tất vét dữ liệu cho {m_name}")

                    # --- CHẾ ĐỘ 2: QUÉT TRANG CHỦ (HOME_SCAN) ---
                    elif mode == "HOME_SCAN":
                        print("🕵️ [HomeScan] Đang hốt danh sách Modules...")
                        # Đợi tí cho các icon module (thường là iframe/image) kịp render
                        await page.wait_for_timeout(2000)
                        results = await self._extract_home_modules(page)

                    # --- 3. LƯU SCREENSHOT ---
                    asset_path = Config.get_path(m_name, asset_type="assets")
                    save_path = asset_path / f"last_{mode.lower()}.jpg"
                    await page.screenshot(path=str(save_path), quality=90)
                    print(f"📸 Screenshot đã lưu: {save_path}")

                else:
                    print("❌ [Engine] Dừng task vì AuthMachine không thể vào Dashboard.")

            except Exception as e:
                print(f"❌ [Engine Lỗi]: {str(e)}")
            
            finally:
                print("🏁 [Engine] Đóng trình duyệt.")
                await browser.close()

        return results
    
    async def _extract_sidebar_deep(self, page, modul_name):
        prefix = modul_name if modul_name else "Chung"
        
        # 1. Lấy đường dẫn file JS từ Config
        # Giả sử Config.get_javascript_path() trả về đối tượng Path
        js_path = Config.get_javascript_path("sidebar_script.js")

        if not js_path.exists():
            print(f"❌ Không tìm thấy script tại: {js_path}")
            return {}

        print(f"✅ Đã kết nối script: {js_path.name}")

        try:
            # 2. Đọc và Bơm code vào trang
            js_code = js_path.read_text(encoding='utf-8')
            await page.evaluate(js_code)

            # 3. Thực thi: Mở menu và Đợi render
            # Tao khuyên nên gom expandAll và extractData thành 1 dòng evaluate 
            # để tránh mất context nếu trang bị reload nhẹ
            await page.evaluate('window.sidebarScraper.expandAll()')
            
            # Đợi thêm 1 chút sau khi expand để đảm bảo DOM đã ổn định
            await page.wait_for_timeout(500)
            
            # 4. Lấy kết quả
            results = await page.evaluate(f'window.sidebarScraper.extractData("{prefix}")')
            return results

        except Exception as e:
            print(f"❌ Lỗi khi thực thi JS Scraper: {e}")
            return {}
    
    async def _extract_home_modules(self, page):
        """
        Logic Cấp 1: Quét xuyên tất cả Iframe để tìm Module.
        """
        all_links = []
        # Đổi thành get_javascript_path để chắc chắn nhận về đối tượng Path
        js_file_path = Config.get_javascript_path("extract_modules.js")
        
        if not js_file_path.exists():
            print(f"❌ Không tìm thấy script: {js_file_path}")
            return []

        # Chỉ đọc text khi chắc chắn file tồn tại
        js_script = js_file_path.read_text(encoding='utf-8')
        
        frames = page.frames
        print(f"🕵️ Đang quét trên {len(frames)} frames...")

        for frame in frames:
            try:
                raw = await frame.evaluate(js_script)
                if raw and isinstance(raw, list):
                    all_links.extend(raw)
            except:
                continue 

        unique = {}
        exclude_keywords = ["đăng xuất", "cài đặt", "hướng dẫn", "thông báo", "profile", "user", "trang chủ", "login"]
        
        for m in all_links:
            # Check kỹ dữ liệu đầu vào từ JS
            if not m or 'text' not in m or 'href' not in m: continue
            
            text_clean = re.sub(r'[•○+►]', '', str(m['text'])).strip()
            href = str(m['href'])
            
            if len(text_clean) > 2:
                # Kiểm tra domain thông minh hơn
                is_module = '/module/' in href.lower()
                is_internal = self.target_domain.lower() in href.lower() or href.startswith('/')
                
                if (is_module or is_internal) and not any(k in text_clean.lower() for k in exclude_keywords):
                    if text_clean not in unique:
                        # Chuẩn hóa URL
                        if href.startswith('/'):
                            full_href = f"https://{self.target_domain.strip('/')}{href}"
                        else:
                            full_href = href
                        unique[text_clean] = {"text": text_clean, "href": full_href}

        print(f"✅ Đã tìm thấy {len(unique)} Module khả dụng.")
        return list(unique.values())
       