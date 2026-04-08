import os
import asyncio
import json
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from config import Config

class StudioCrawler:
    """Tầng 1: File Excel Tổng - Quản lý lộ trình và xác thực"""
    def __init__(self, auth_provider=None):
        if auth_provider is None:
            from Bot_GPV.ai_film_factory.auth_machine import AuthMachine
            self.auth = AuthMachine()
        else:
            self.auth = auth_provider
            
        self.results = {}
        # Nạp base_utils.js
        self.js_path = os.path.join(os.getcwd(), "Bot_GPV", "ai_film_factory", "js", "base_utils.js")
        print(f"📂 [System]: Nạp tiện ích cơ sở từ: {self.js_path}")
        with open(self.js_path, 'r', encoding='utf-8') as f:
            self.utils_js = f.read()

    # --- HÀM QUÉT LẺ (Cái này để sửa lỗi Streamlit của ông nè) ---
    async def scan_module(self, module_name, module_url):
        """Quét lẻ một module cụ thể từ UI Streamlit"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=50)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                if not await self.auth.login(page): 
                    return {}

                print(f"🚀 [Module]: {module_name} - Khởi tạo lộ trình quét lẻ...")
                sidebar = SidebarArchitect(page, self.utils_js)
                tasks = await sidebar.expand_and_collect_tasks(module_url, module_name)
                
                if not tasks:
                    print(f"⚠️ Không tìm thấy link trong Sidebar của {module_name}.")
                    return {}

                navigator = SurfaceNavigator(page, self.utils_js)
                module_results = {}
                for task in tasks:
                    metadata = await navigator.deep_scan_page(task)
                    if metadata:
                        module_results[task['full_path']] = metadata
                        print(f"   ✅ Đã quét xong: {task['full_path']}")
                
                return module_results

            except Exception as e:
                print(f"❌ Lỗi tại scan_module ({module_name}): {e}")
                return {}
            finally:
                await browser.close()

    # --- HÀM QUÉT TỰ HÀNH (VÉT CẠN) ---
    async def autonomous_system_scan(self):
        """VÉT CẠN TỰ ĐỘNG: Tự động thâm nhập toàn bộ modules."""
        print("\n🕵️ [VisionMachine]: Bắt đầu chế độ tự hành...")
        final_all_data = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, args=["--disable-web-security"])
            context = await browser.new_context()
            page = await context.new_page()

            try:
                if not await self.auth.login(page): 
                    print("❌ Dừng quy trình: Không thể đăng nhập.")
                    return {}

                await page.wait_for_selector('.MuiCard-root, .module-card', timeout=30000)
                all_modules = await page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('.module-card, [role="button"], .MuiCard-root'); 
                        return Array.from(cards).map(c => ({
                            name: c.innerText.split('\\n')[0].trim(),
                            url: c.getAttribute('href') || c.querySelector('a')?.getAttribute('href')
                        })).filter(m => m.url && m.url !== '#' && m.name !== "");
                    }
                """)

                print(f"✅ Tìm thấy {len(all_modules)} Module mục tiêu.")

                for mod in all_modules:
                    mod_name = mod['name']
                    print(f"\n🚀 Đang thâm nhập Module: {mod_name}")
                    
                    sidebar = SidebarArchitect(page, self.utils_js)
                    tasks = await sidebar.expand_and_collect_tasks(mod['url'], mod_name)
                    
                    if not tasks:
                        await page.goto(Config.TARGET_DOMAIN, wait_until="domcontentloaded")
                        continue

                    navigator = SurfaceNavigator(page, self.utils_js)
                    for task in tasks:
                        try:
                            metadata = await navigator.deep_scan_page(task)
                            if metadata:
                                final_all_data[task['full_path']] = metadata
                                print(f"   ✅ Metadata OK: {task['full_path']}")
                        except Exception as e:
                            print(f"   ⚠️ Lỗi trang {task['name']}: {e}")

                    print(f"🏠 Quay về Dashboard...")
                    await page.goto(Config.TARGET_DOMAIN, wait_until="domcontentloaded")
                    await asyncio.sleep(1.5) 

            except Exception as e:
                print(f"❌ Lỗi hệ thống: {e}")
            finally:
                await browser.close()

        return final_all_data

class SidebarArchitect:
    def __init__(self, page, utils_js):
        self.page = page
        self.utils_js = utils_js

    async def expand_and_collect_tasks(self, url, module_name):
        full_url = urljoin(Config.TARGET_DOMAIN, url)
        await self.page.goto(full_url, wait_until="networkidle", timeout=60000)
        await self.page.evaluate(self.utils_js)
        
        print(f"🔄 Đang ép bung Sidebar cho {module_name}...")
        await self.page.evaluate("window.utils.expandAllMenus()")
        await asyncio.sleep(2) 

        ui_tree = await self.page.evaluate("window.nav.get_ui_tree()")
        return self._flatten_tree(ui_tree or [], module_name)

    def _flatten_tree(self, tree, module_name):
        flat = []
        for item in tree:
            # Nếu cha có link thực (hiếm gặp ở Subheader nhưng cứ phòng hờ)
            if item.get('href') and item['href'] not in ["#", "javascript:void(0)"]:
                flat.append({
                    'url': item['href'], 
                    'name': item['title'], 
                    'full_path': f"{module_name}|{item['title']}"
                })
            
            # Hốt sạch con
            for child in item.get('children', []):
                # Tạo đường dẫn đầy đủ: Module|Cha|Con
                path = f"{module_name}|{item['title']}|{child['title']}"
                flat.append({
                    'url': child['href'], 
                    'name': child['title'], 
                    'full_path': path
                })
        return flat

class SurfaceNavigator:
    def __init__(self, page, utils_js):
        self.page = page
        self.utils_js = utils_js

    async def deep_scan_page(self, task):
        try:
            print(f"   🔍 Đang nội soi: {task['name']}")
            full_url = urljoin(Config.TARGET_DOMAIN, task['url'])
            await self.page.goto(full_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(1.5) 
            await self.page.keyboard.press("Escape") 
            
            dissector = ElementDissector(self.page, self.utils_js)
            return await dissector.extract_all_metadata()
        except Exception as e:
            return None

class ElementDissector:
    def __init__(self, page, utils_js):
        self.page = page
        self.utils_js = utils_js
        self.scanner_path = os.path.join(os.getcwd(), "Bot_GPV", "ai_film_factory", "js", "scout_engine.js")

    async def extract_all_metadata(self):
        with open(self.scanner_path, 'r', encoding='utf-8') as f:
            scanner_js = f.read()
        await self.page.evaluate(self.utils_js)
        await self.page.evaluate(scanner_js)
        
        metadata = await self.page.evaluate("""
            async () => {
                if (typeof window.scanPage === 'function') {
                    return await window.scanPage(); 
                } else if (typeof window.utils !== 'undefined') {
                    const container = document.querySelector('main, form, .MuiContainer-root, #content') || document.body;
                    return window.utils.internalScan(container);
                }
                return {error: 'Script not ready'};
            }
        """)
        return json.loads(metadata) if isinstance(metadata, str) else metadata