from playwright.async_api import async_playwright
import traceback
import os

# Import các thành phần hệ thống
from config import Config
from .session_manager import SessionManager
from .web_scraper import WebScraper
from .data_archiver import DataArchiver
from Bot_GPV.core.gpv_deep_form_miner import DeepFormMiner
from Bot_GPV.core.engine.menu_child import MenuChild

class ModuleOrchestrator:
    def __init__(self, config_class=None, controller_instance=None):
        """
        Khởi tạo điều phối viên với đầy đủ đồ nghề.
        """
        self.config = config_class if config_class else Config
        self.ctrl = controller_instance
        self.session = SessionManager()
        
        # 1. FIX DOMAIN: Lấy domain an toàn
        raw_domain = self.config.TARGET_DOMAIN
        clean_domain = raw_domain.replace("https://", "").replace("http://", "").split('/')[0]
        
        # 2. KHỞI TẠO CÁC BỘ PHẬN (Truyền ctrl vào Archiver để ghi DB)
        self.scraper = WebScraper(clean_domain)
        self.archiver = DataArchiver(
            config_class=self.config, 
            controller_instance=self.ctrl
        )

    async def run(self, mode="HOME_SCAN", module_url=None, project_folder=None, modul_name="Chung", tutorial_id=None):
        """ 
        Điều phối chính: Quản lý vòng đời Browser và luồng dữ liệu 
        """
        async with async_playwright() as p:
            # Khởi tạo browser
            page, browser = await self.session.create_session(p)
            
            if not page: 
                print("❌ Không thể khởi tạo session. Hủy task.")
                return {}
            
            results = {}
            try:
                # --- CHẾ ĐỘ 1: QUÉT TRANG CHỦ ---
                if mode == "HOME_SCAN":
                    print(f"🏠 [Orchestrator] Bắt đầu quét trang chủ...")
                    results = await self.scraper.scan_home_modules(page)
                
                # --- CHẾ ĐỘ 2: NỘI SOI SÂU (DEEP SCAN) ---
                elif mode == "DEEP_SCAN":
                    print(f"🛰️ [Orchestrator] Bắt đầu nội soi module: {modul_name}")
                    if not module_url:
                        print("⚠️ Lỗi: mode DEEP_SCAN yêu cầu module_url.")
                    else:
                        # Kết quả trả về từ luồng deep mining là một DICT chuẩn
                        results = await self._deep_mining_flow(page, module_url, modul_name)

                # --- LƯU TRỮ DỮ LIỆU ---
                if results and tutorial_id:
                    print(f"📦 [Orchestrator] Đang chuyển dữ liệu sang bộ phận lưu trữ...")
                    
                    # Gọi archiver để ghi DB và lưu file fields.json
                    await self.archiver.archive(
                        results=results, 
                        mode=mode, 
                        tutorial_id=tutorial_id, 
                        project_folder=project_folder,
                        modul_name=modul_name
                    )
                    print("✅ [Orchestrator] Hoàn tất luồng xử lý.")
                else:
                    print("⚠️ [Orchestrator] Không có kết quả hoặc thiếu tutorial_id để lưu.")

            except Exception as e:
                print(f"💥 [Orchestrator Error]: {str(e)}")
                traceback.print_exc()
            finally:
                if browser:
                    await browser.close()
                    print("🔌 Browser đã đóng.")
        
        return results

    async def _deep_mining_flow(self, page, url, m_name):
        """ 
        Luồng đào sâu: Sidebar -> Duyệt từng trang -> Miner bóc tách 
        """
        try:
            # 1. Quét cấu trúc Sidebar để lấy danh sách URL con
            await page.goto(url, wait_until="networkidle", timeout=60000)
            sidebar = await self.scraper.scan_sidebar_structure(page, m_name)
            
            if not sidebar: 
                print("⚠️ Không tìm thấy cấu trúc Sidebar.")
                return {}

            # Chuẩn bị Dictionary kết quả theo format Archiver mong đợi
            # Format: { "Path | Name": { "url": "...", "metadata": {...} } }
            deep_results = {}
            
            items = [k for k in sidebar.keys() if "|" in k]

            # 2. Khởi tạo Miner
            miner = DeepFormMiner(page, config_class=self.config)

            for idx, path in enumerate(items):
                info = sidebar[path]
                if not info.get('url'): continue

                # Sử dụng MenuChild để quản lý dữ liệu cho sạch
                child = MenuChild(path_name=path, url=info['url'], module_name=m_name)
                print(f"[{idx+1}/{len(items)}] 📍 Đang nội soi: {child.name}")

                try:
                    # Di chuyển tới trang con
                    await page.goto(child.url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500) # Đợi UI render thêm chút

                    # Miner thực thi quét Form, Table, Button
                    # Miner PHẢI trả về một DICT, không được trả về STRING
                    mined_metadata = await miner.start_mining(page.url, child.name)
                    
                    # Đóng gói vào deep_results
                    deep_results[path] = {
                        "url": child.url,
                        "metadata": mined_metadata if isinstance(mined_metadata, dict) else {"raw_data": mined_metadata}
                    }

                except Exception as inner_e:
                    print(f"⚠️ Lỗi tại mục {child.name}: {inner_e}")
                    continue 

            return deep_results

        except Exception as e:
            print(f"💥 Lỗi luồng Deep Mining: {e}")
            traceback.print_exc()
            return {}