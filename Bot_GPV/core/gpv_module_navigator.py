import asyncio
import re
import traceback
import json
from pathlib import Path
from playwright.async_api import async_playwright
from config import Config
from Bot_GPV.ai_film_factory.auth_machine import AuthMachine
from Bot_GPV.core.gpv_form_miner import FormMiner
from models.controller import StudioController


class ModuleNavigator:
    def __init__(self):
        self.auth = AuthMachine()
        self.target_domain = Config.TARGET_DOMAIN.replace("https://", "").replace("http://", "").split('/')[0]

    async def run_task(self, mode="HOME_SCAN", module_url=None, project_folder=None, modul_name=None, tutorial_id=None):
        """ Hệ điều hành trung tâm: Điều phối quét và ÉP LƯU dữ liệu """
        m_name = modul_name or "Chung"
        self._print_banner(mode, m_name)

        # [DEBUG-STEP 1]: Kiểm tra đầu vào quan trọng
        print(f"🔍 [DEBUG-TASK] Tutorial ID: {tutorial_id}")
        print(f"🔍 [DEBUG-TASK] Project Folder: {project_folder}")
        print(f"🔍 [DEBUG-TASK] Mode: {mode}")

        async with async_playwright() as p:
            page, browser = await self._setup_session(p)
            if not page: 
                print("❌ [DEBUG-TASK] Không khởi tạo được Browser/Page.")
                return {}

            results = {}
            try:
                if mode == "DEEP_SCAN":
                    print(f"🛰️  [DEBUG-TASK] Bắt đầu Deep Scan module: {m_name}")
                    results = await self._run_deep_scan(page, module_url, m_name)
                elif mode == "HOME_SCAN":
                    print(f"🏠 [DEBUG-TASK] Bắt đầu Home Scan...")
                    results = await self._run_home_scan(page)

                # [DEBUG-STEP 2]: Kiểm tra kết quả thu thập được
                results_count = len(results) if results else 0
                print(f"📊 [DEBUG-TASK] Kết quả quét xong: {results_count} items found.")
                
                if results_count > 0:
                    # In thử 1 key đầu tiên để xem cấu trúc
                    first_key = list(results.keys())[0]
                    print(f"📍 [DEBUG-TASK] Sample Data Key: {first_key}")

                await self._take_evidence(page, m_name, mode)

                # [DEBUG-STEP 3]: Kiểm tra điều kiện Archive
                print("🏁 [DEBUG-TASK] Đang kiểm tra điều kiện lưu trữ...")
                if not results:
                    print("⚠️  [DEBUG-TASK] Archive thất bại: 'results' bị RỖNG.")
                if not tutorial_id:
                    print("⚠️  [DEBUG-TASK] Archive thất bại: 'tutorial_id' bị THIẾU (None).")

                # ARCHIVE: Ép lưu vào Database và tạo cấu trúc Folder
                if results and tutorial_id:
                    print(f"📦 [DEBUG-TASK] Đang gọi _archive_results với {results_count} forms...")
                    await self._archive_results(results, mode, tutorial_id, project_folder)
                    print("✅ [DEBUG-TASK] Đã hoàn tất luồng gọi Archiver.")
                else:
                    print("🚫 [DEBUG-TASK] Bỏ qua bước Archiver do thiếu điều kiện.")

            except Exception as e:
                print(f"💥 [CRITICAL ERROR]: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                await browser.close()
                print("🔌 [DEBUG-TASK] Browser closed.")
                
        return results
    
    async def _archive_results(self, results, mode, t_id, p_folder):
        """ 
        Hàm trung gian kết nối Scraper với StudioController 
        Đảm bảo: Ghi DB -> Tạo Folder -> Ghi file JSON metadata
        """
        # from Bot_GPV.controllers.studio_controller import StudioController
        ctrl = StudioController()
        
        print(f"💾 [Archiver] Đang nạp dữ liệu vào dự án ID: {t_id}...")

        # TRƯỜNG HỢP 1: NỘI SOI SÂU (Dữ liệu trả về là Dict từ _run_deep_scan)
        if mode == "DEEP_SCAN" and isinstance(results, dict):
            count = 0
            for full_path, data in results.items():
                # Sử dụng chung 1 instance ctrl
                sub_id = ctrl.add_sub_content(
                    t_id=t_id,
                    sub_title=full_path,
                    parent_folder=p_folder,
                    url=data.get('url'),
                    metadata=data.get('metadata'),
                    status="Đã nội soi"
                )
                # Truyền luôn ctrl vào hàm save metadata để khỏi khởi tạo lại bên trong
                if sub_id:
                    self._save_metadata_to_json(sub_id, data.get('metadata'), p_folder, ctrl)
                    count += 1
            print(f"✅ [Archiver] Đã cập nhật {count} form nghiệp vụ.")

        # TRƯỜNG HỢP 2: QUÉT TRANG CHỦ (Dữ liệu thường là list module)
        elif mode == "HOME_SCAN":
            # Tùy vào hàm _run_home_scan của ông trả về list hay dict có key 'modules'
            modules = results if isinstance(results, list) else results.get('modules', [])
            
            for mod in modules:
                # mod thường có: { 'text': '...', 'href': '...' } hoặc { 'label': '...', 'url': '...' }
                title = mod.get('text') or mod.get('label')
                url = mod.get('href') or mod.get('url')
                
                ctrl.add_sub_content(
                    t_id=t_id,
                    sub_title=f"{title}|Home",
                    parent_folder=p_folder,
                    url=url,
                    status="Chờ nội soi"
                )
            print(f"✅ [Archiver] Đã thiết lập khung cho {len(modules)} module chính.")

        print(f"✅ [Archiver] Hoàn tất đồng bộ vật lý và logic.")

    def _save_metadata_to_json(self, sub_id, metadata, p_folder, ctrl):
        """Hàm phụ trợ ghi file JSON để AI đọc"""
        try:            
            # Lấy folder name từ DB dựa trên sub_id
            res = ctrl.db.execute("SELECT sub_folder FROM sub_contents WHERE id = ?", (sub_id,)).fetchone()
            if res and res['sub_folder']:
                folder_name = res['sub_folder']
                path_json = Config.get_path(app=p_folder, module=folder_name, asset_type="metadata") / "fields.json"
                
                # Đảm bảo folder tồn tại trước khi ghi
                path_json.parent.mkdir(parents=True, exist_ok=True)
                
                with open(path_json, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ [Archiver] Lỗi ghi file metadata: {e}")

    # --- NHÓM HÀM THIẾT LẬP (SETUP) ---

    async def _setup_session(self, p):
        """Khởi tạo trình duyệt và xử lý đăng nhập tập trung"""
        print(f"🌐 1. Khởi tạo Chromium...")
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print(f"🔑 2. Đang đăng nhập hệ thống...")
        if await self.auth.login(page):
            print(f"✅ Đăng nhập thành công!")
            return page, browser
        
        print("❌ [LỖI] Đăng nhập thất bại.")
        await browser.close()
        return None, None

    # --- NHÓM HÀM LOGIC QUÉT (SCAN LOGIC) ---

    async def _run_home_scan(self, page):
        """Logic dành riêng cho việc quét danh sách Module ngoài trang chủ"""
        print("🏠 3. [HomeScan] Đang quét danh sách module...")
        await page.wait_for_timeout(2000)
        results = await self._extract_home_modules(page)
        print(f"📦 Đã tìm thấy {len(results)} module.")
        return results

    async def _run_deep_scan(self, page, module_url, m_name):
        base_url = f"https://{self.target_domain}"
        final_url = module_url if module_url.startswith("http") else f"{base_url}/{module_url.lstrip('/')}"
        
        print(f"🛰️ 3. [DeepScan] Mục tiêu: {final_url}")
        
        try:
            await page.goto(final_url, wait_until="networkidle", timeout=60000)
            await self._prepare_sidebar_ui(page)

            sidebar_results = await self._extract_sidebar_deep(page, m_name)
            if not sidebar_results:
                return {}

            # Bước 4: Khai thác (Đảm bảo loop trả về Dict)
            all_module_data = await self._process_mining_loop(page, sidebar_results)

            processed_results = {}
            scan_time = Config.get_current_time()

            for full_path, mining_info in all_module_data.items():
                # Xử lý nếu mining_info là string (từ JSON cũ hoặc log)
                if isinstance(mining_info, str):
                    try:
                        import json
                        mining_info = json.loads(mining_info)
                    except: continue

                # QUAN TRỌNG: Nếu Miner chỉ trả về metadata, ta phải lấy URL từ sidebar_results
                current_url = mining_info.get("url") or sidebar_results.get(full_path, {}).get("url", "")

                processed_results[full_path] = {
                    "url": current_url,
                    "metadata": mining_info, 
                    "status": "Đã nội soi",
                    "scan_time": scan_time,
                    "module_group": m_name
                }

            print(f"✅ [DeepScan] Hoàn tất nội soi {len(processed_results)} mục.")
            return processed_results

        except Exception as e:
            print(f"💥 [DeepScan Error]: {str(e)}")
            return {}
        
    # --- NHÓM HÀM TIỆN ÍCH KHAI THÁC (MINING UTILS) ---

    async def _process_mining_loop(self, page, sidebar_results):
        """Vòng lặp đào dữ liệu - Đã tối ưu hiệu suất và độ trễ"""
        all_data = {}
        
        # Lọc danh sách mục tiêu
        items = [k for k in sidebar_results.keys() if k not in ["scan_time", "module_parent"]]
        total = len(items)

        for idx, full_path in enumerate(items):
            f_info = sidebar_results[full_path]
            if not (isinstance(f_info, dict) and f_info.get('url')): continue

            # Hiển thị tiến độ để ông dễ theo dõi trên console
            progress = ((idx + 1) / total) * 100
            print(f"[{progress:.1f}%] 📍 TIẾP CẬN: {full_path}")

            try:
                # 1. Điều hướng với cơ chế bắt lỗi timeout chặt chẽ
                try:
                    await page.goto(f_info['url'], wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    print(f"⚠️ Timeout trang {full_path}, thử đợi thêm networkidle...")
                    await page.wait_for_load_state("networkidle", timeout=5000)

                # Đợi một chút cho các hàm JavaScript render xong giao diện
                await page.wait_for_timeout(1500) 
                
                # 2. Khởi tạo miner cho mỗi lần đào (An toàn hơn cho bộ nhớ)
                miner = FormMiner(page, config_class=Config)
                
                # 3. ĐÀO (Nội soi)
                mining_result = await miner.start_mining(page.url, full_path)
                
                # 4. Kiểm tra nếu mining_result rỗng thì không nạp (tránh rác DB)
                if mining_result:
                    all_data[full_path] = {
                        "url": page.url,
                        "metadata": mining_result,
                        "status": "COMPLETED",
                        "index": idx
                    }
                    print(f"✅ Đã nạp {full_path} vào hàng chờ lưu trữ.")
                else:
                    print(f"❓ Cảnh báo: {full_path} không có dữ liệu metadata.")

            except Exception as e:
                print(f"❌ Lỗi nghiêm trọng tại mục {full_path}: {e}")
                continue # Tiếp tục với mục tiếp theo, không để chết cả script
                
        return all_data

    async def _prepare_sidebar_ui(self, page):
        """Làm sạch UI và đảm bảo Sidebar sẵn sàng"""
        try:
            # Đợi selector đặc trưng của sidebar (tùy chỉnh theo UI thực tế của ông)
            await page.wait_for_selector('.minimal__nav__li', timeout=5000)
            # Nhấn Escape để đóng các popup thông báo che khuất menu nếu có
            await page.keyboard.press("Escape") 
            await page.wait_for_timeout(500)
        except:
            print(f"⚠️ Cảnh báo: Sidebar không phản hồi selector chuẩn.")

    async def _take_evidence(self, page, m_name, mode):
        """Lưu screenshot làm bằng chứng"""
        asset_path = Config.get_path(m_name, asset_type="assets")
        save_path = asset_path / f"last_{mode.lower()}.jpg"
        await page.screenshot(path=str(save_path), quality=90)
        print(f"📸 Screenshot lưu tại: {save_path}")

    def _print_banner(self, mode, name):
        print(f"\n{'='*60}\n🤖 [ENGINE START] {mode} | {name}\n{'='*60}")

    async def _extract_sidebar_deep(self, page, modul_name):
        prefix = modul_name if modul_name else "Chung"
        js_path = Config.get_javascript_path("sidebar_script.js")

        if not js_path.exists():
            print(f"❌ Không tìm thấy script tại: {js_path}")
            return {}

        try:
            js_code = js_path.read_text(encoding='utf-8')
            await page.evaluate(js_code)
            await page.evaluate('window.sidebarScraper.expandAll()')
            await page.wait_for_timeout(800)
            
            results = await page.evaluate(f'window.sidebarScraper.extractData("{prefix}")')

            # --- DEBUG PRINTS MENU CHA/CON TẠI ĐÂY ---
            if results:
                print(f"\n📑 [SIDEBAR STRUCTURE] Module: {prefix}")
                # Giả sử cấu trúc results có key 'menus' chứa danh sách phẳng hoặc phân cấp
                # Ở đây tôi lọc các key có dấu '|' để in dạng cây
                for key in results.keys():
                    if "|" in key:
                        parts = key.split("|")
                        indent = "  " * (len(parts) - 1)
                        icon = "└──" if len(parts) > 1 else "📂"
                        print(f"{indent}{icon} {parts[-1]}")
                print(f"{'-'*30}\n")
            
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
    
    
    # --- NHÓM HÀM ĐIỀU HƯỚNG BỔ SUNG (NẾU CẦN CLICK VẬT LÝ) menu cha, con---
    async def navigate_and_mine(self, page, menu_structure):
        """
        Nếu trang web dùng cơ chế Click-to-Load thay vì URL trực tiếp.
        Hàm này sẽ trả về kết quả để có thể nạp vào _archive_results.
        """
        # from Bot_GPV.core.gpv_form_miner import FormMiner
        miner = FormMiner(page, config_class=Config)
        all_data = {}

        for parent in menu_structure:
            # Lưu ý: menu_structure cần có 'text' và 'selector' cho menu cha
            print(f"📂 Mở menu cha: {parent.get('text', 'N/A')}")
            try:
                # Kiểm tra selector trước khi click để tránh crash
                if parent.get('selector'):
                    await page.click(parent['selector'])
                    await page.wait_for_timeout(800)
                
                for sub in parent.get('subs', []):
                    full_path = f"{parent['text']}|{sub['text']}"
                    print(f"  ∟ 🖱️ Click menu con: {sub['text']}")
                    
                    # 1. Click vào menu con
                    await page.click(sub['selector'])
                    
                    # 2. Đợi giao diện load ổn định
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(2000) 

                    # 3. BẮT ĐẦU ĐÀO (Nội soi)
                    print(f"    🔎 Đang nội soi giao diện: {full_path}")
                    # Gọi miner từ instance đã tạo
                    mining_result = await miner.start_mining(page.url, full_path)
                    
                    # 4. Lưu vào kết quả chung (Dạng Dict để khớp với luồng lưu trữ)
                    all_data[full_path] = {
                        "url": page.url,
                        "metadata": mining_result,
                        "status": "Đã nội soi"
                    }
                    
            except Exception as e:
                print(f"❌ Lỗi điều hướng vật lý tại {parent.get('text')}: {e}")
        
        return all_data