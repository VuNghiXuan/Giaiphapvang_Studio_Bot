from playwright.async_api import async_playwright
import traceback
from config import Config
from .session_manager import SessionManager
from .web_scraper import WebScraper
from .data_archiver import DataArchiver
from Bot_GPV.core.gpv_form_miner import FormMiner

class ModuleOrchestrator:
    def __init__(self):
        self.session = SessionManager()
        
        # FIX: Lấy domain an toàn, không bị IndexError: list index out of range
        raw_domain = Config.TARGET_DOMAIN
        clean_domain = raw_domain.replace("https://", "").replace("http://", "").split('/')[0]
        
        self.scraper = WebScraper(clean_domain)
        self.archiver = DataArchiver()

    async def run(self, mode="HOME_SCAN", module_url=None, project_folder=None, modul_name="Chung", tutorial_id=None):
        """ 
        Điều phối chính: Quản lý vòng đời Browser và luồng dữ liệu 
        """
        async with async_playwright() as p:
            page, browser = await self.session.create_session(p)
            if not page: 
                print("❌ Không thể khởi tạo session. Hủy task.")
                return {}
            
            results = {}
            try:
                if mode == "HOME_SCAN":
                    print(f"🏠 [Orchestrator] Bắt đầu quét trang chủ...")
                    results = await self.scraper.scan_home_modules(page)
                
                elif mode == "DEEP_SCAN":
                    print(f"🛰️ [Orchestrator] Bắt đầu nội soi module: {modul_name}")
                    if not module_url:
                        print("⚠️ Lỗi: mode DEEP_SCAN yêu cầu module_url.")
                    else:
                        results = await self._deep_mining_flow(page, module_url, modul_name)

                # --- ĐIỂM CẬP NHẬT QUAN TRỌNG: TRUYỀN modul_name SANG ARCHIVER ---
                if results and tutorial_id:
                    print(f"📦 [Orchestrator] Đang chuyển dữ liệu sang bộ phận lưu trữ...")
                    # Chúng ta truyền thêm modul_name vào đây
                    await self.archiver.archive(
                        results=results, 
                        mode=mode, 
                        tutorial_id=tutorial_id, 
                        project_folder=project_folder,
                        modul_name=modul_name  # 👈 THÊM THAM SỐ NÀY
                    )
                    print("✅ [Orchestrator] Hoàn tất luồng xử lý.")
                else:
                    print("⚠️ [Orchestrator] Không có kết quả hoặc thiếu tutorial_id để lưu.")

            except Exception as e:
                print(f"💥 [Orchestrator Error]: {str(e)}")
                traceback.print_exc()
            finally:
                await browser.close()
                print("🔌 Browser đã đóng.")
        
        return results

    async def _deep_mining_flow(self, page, url, m_name):
        """ 
        Luồng đào sâu: Sidebar -> Duyệt từng trang -> Miner bóc tách 
        """
        try:
            # 1. Đi tới trang module để lấy sidebar
            await page.goto(url, wait_until="networkidle", timeout=60000)
            sidebar = await self.scraper.scan_sidebar_structure(page, m_name)
            
            if not sidebar:
                print(f"⚠️ Không tìm thấy cấu trúc sidebar cho module: {m_name}")
                return {}

            final_data = {}
            # Lọc bỏ các key metadata của sidebar scraper nếu có (như scan_time)
            items = [k for k in sidebar.keys() if "|" in k]
            total = len(items)

            print(f"🚀 Bắt đầu đào {total} mục con...")

            for idx, path in enumerate(items):
                info = sidebar[path]
                if not isinstance(info, dict) or not info.get('url'):
                    continue

                print(f"[{idx+1}/{total}] 📍 Đang nội soi: {path}")
                
                try:
                    # Điều hướng đến form con
                    await page.goto(info['url'], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500) # Đợi render JS ổn định

                    # Khởi tạo Miner để bóc tách form hiện tại
                    miner = FormMiner(page, config_class=Config)
                    meta = await miner.start_mining(page.url, path)
                    
                    if meta:
                        final_data[path] = {
                            "url": page.url,
                            "metadata": meta,
                            "status": "Đã nội soi"
                        }
                    else:
                        print(f"❓ Cảnh báo: Mục {path} không có dữ liệu fields.")

                except Exception as inner_e:
                    print(f"⚠️ Lỗi tại mục {path}: {inner_e}")
                    continue # Bị lỗi trang này thì bỏ qua, đào trang tiếp theo

            return final_data

        except Exception as e:
            print(f"💥 Lỗi luồng Deep Mining: {e}")
            return {}