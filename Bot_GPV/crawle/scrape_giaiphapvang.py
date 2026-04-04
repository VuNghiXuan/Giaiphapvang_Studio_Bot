# 1. Thư viện hệ thống (Standard Libraries)
import os
import re
import json
import time
from datetime import datetime
import asyncio

# 2. Thư viện bên thứ ba (Third-party)
from playwright.async_api import async_playwright
from PIL import Image # pip install Pillow
from dotenv import load_dotenv

# 3. Các Module nội bộ (Local Modules)
from config import Config
from Bot_GPV.ai_film_factory.vision_machine import VisionMachine

load_dotenv()

class GiaiphapvangScraper:
    def __init__(self):
        if not os.path.exists(Config.BASE_STORAGE):
            os.makedirs(Config.BASE_STORAGE, exist_ok=True)
        print("🚀 Scraper sẵn sàng: Chế độ đào sâu vét cạn (Deep Scan).")

        self.vision = VisionMachine()

    def _save_step(self, project_folder, sub_title, data, *args, **kwargs):
        """
        Gia cố: Hứng mọi tham số thừa để tránh lỗi 'positional arguments'.
        """
        try:
            # Làm sạch tên folder: chỉ giữ chữ và số
            folder_name = "".join([c if c.isalnum() else "_" for c in sub_title])
            form_dir = os.path.join(Config.BASE_STORAGE, project_folder, folder_name)
            
            os.makedirs(form_dir, exist_ok=True)
            file_path = os.path.join(form_dir, "data.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            return True
        except Exception as e:
            print(f"❌ [Scraper]: Lỗi lưu JSON tại {sub_title}: {e}")
            return False
    

    # def save_and_compress_screenshot(self, page, save_path):
    #     """Nén ảnh an toàn để AI đọc, tránh tốn dung lượng"""
    #     try:
    #         temp_path = save_path.replace(".jpg", "_raw.png")
    #         page.screenshot(path=temp_path)
            
    #         with Image.open(temp_path) as img:
    #             # Chuyển sang RGB trước khi lưu JPEG để tránh lỗi kênh Alpha
    #             rgb_img = img.convert("RGB")
    #             rgb_img.thumbnail((1280, 1280)) 
    #             rgb_img.save(save_path, "JPEG", quality=60)
            
    #         if os.path.exists(temp_path):
    #             os.remove(temp_path)
    #     except Exception as e:
    #         print(f"⚠️ Không nén được ảnh: {e}")
    
    async def save_and_compress_screenshot(self, page, save_path):
        try:
            temp_path = save_path.replace(".jpg", "_raw.png")
            await page.screenshot(path=temp_path) # THÊM AWAIT
            # ... phần xử lý Pillow giữ nguyên vì Pillow chạy sync OK ...
            with Image.open(temp_path) as img:
                rgb_img = img.convert("RGB")
                rgb_img.thumbnail((1280, 1280)) 
                rgb_img.save(save_path, "JPEG", quality=60)
            if os.path.exists(temp_path): os.remove(temp_path)
        except Exception as e:
            print(f"⚠️ Không nén được ảnh: {e}")

    # def login(self, page):
    #     print(f"🔑 Đang đăng nhập hệ thống: {Config.TARGET_DOMAIN}")
    #     try:
    #         # Sử dụng Domain từ Config để tạo link login
    #         login_url = f"{Config.TARGET_DOMAIN.rstrip('/')}/auth/jwt/sign-in/"
    #         page.goto(login_url)
            
    #         # Lấy thông tin đăng nhập từ biến môi trường (os.getenv)
    #         page.fill("input[name='email']", os.getenv("USER_EMAIL"))
    #         page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
    #         page.click("button[type='submit']")
            
    #         # Chờ chuyển hướng thành công
    #         page.wait_for_url("**/home/**", timeout=30000)
    #         print("🏠 Đăng nhập thành công!")
    #         page.wait_for_timeout(1000)
    #         return True
    #     except Exception as e:
    #         print(f"❌ Đăng nhập thất bại: {e}")
    #         return False
    
    async def login(self, page):
        print(f"🔑 Đang đăng nhập hệ thống: {Config.TARGET_DOMAIN}")
        try:
            login_url = f"{Config.TARGET_DOMAIN.rstrip('/')}/auth/jwt/sign-in/"
            await page.goto(login_url) # THÊM AWAIT
            
            await page.fill("input[name='email']", os.getenv("USER_EMAIL")) # THÊM AWAIT
            await page.fill("input[name='password']", os.getenv("USER_PASSWORD")) # THÊM AWAIT
            await page.click("button[type='submit']") # THÊM AWAIT
            
            await page.wait_for_url("**/home/**", timeout=30000) # THÊM AWAIT
            print("🏠 Đăng nhập thành công!")
            await page.wait_for_timeout(1000)
            return True
        except Exception as e:
            print(f"❌ Đăng nhập thất bại: {e}")
            return False
        

    async def get_home_modules(self):
        """CẤP ĐỘ 1: Vét sạch Module lớn từ trang chủ (Tiền trạm)"""
        
        modules = []
        # 1. Khởi tạo Playwright trong môi trường async
        async with async_playwright() as p:
            # 2. Mở trình duyệt (để headless=False nếu ông muốn quan sát nó chạy)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 3. ĐĂNG NHẬP: Nhớ phải có await vì login là hàm async
                is_logged_in = await self.login(page)
                
                if is_logged_in:
                    print("🔍 [🕵️ Bot Tiền Trạm] Đang quét danh sách nghiệp vụ tại trang chủ...")
                    
                    # 4. Đợi selector đặc trưng của trang chủ xuất hiện (ví dụ các box Grid của MUI)
                    try:
                        await page.wait_for_selector(".MuiGrid-item", timeout=15000)
                    except Exception:
                        print("⚠️ Cảnh báo: Không tìm thấy .MuiGrid-item, có thể trang chủ dùng cấu trúc khác.")

                    # 5. TRÍCH XUẤT LINK: Chạy Script JS trong trình duyệt
                    # Sử dụng Config.TARGET_DOMAIN để đảm bảo không lấy link ngoài
                    target_domain = Config.TARGET_DOMAIN.replace("https://", "").replace("http://", "").rstrip('/')
                    
                    raw_links = await page.evaluate(f'''() => {{
                        const links = Array.from(document.querySelectorAll('a'));
                        return links
                            .map(a => ({{ 
                                text: a.innerText.trim().split('\\n')[0], 
                                href: a.href 
                            }}))
                            .filter(m => 
                                m.text.length > 2 && 
                                m.href.includes('{target_domain}') &&
                                !m.href.endsWith('#')
                            );
                    }}''')
                    
                    # 6. HẬU XỬ LÝ: Loại bỏ các mục rác và trùng lặp
                    exclude_keywords = ["Đăng xuất", "Logout", "Profile", "Thông báo", "Cài đặt", "Setting", "Home", "Trang chủ"]
                    unique_modules = {}
                    
                    for m in raw_links:
                        # Kiểm tra xem text có chứa từ khóa loại trừ không
                        is_excluded = any(k.lower() in m['text'].lower() for k in exclude_keywords)
                        
                        if not is_excluded:
                            # Dùng href làm key để đảm bảo không bị trùng link
                            unique_modules[m['href']] = m
                    
                    modules = list(unique_modules.values())
                    print(f"✅ [🕵️ Bot Tiền Trạm] Đã tìm thấy {len(modules)} Modules nghiệp vụ khả dụng.")
                
                else:
                    print("❌ [🕵️ Bot Tiền Trạm] Dừng quét do đăng nhập thất bại.")

            except Exception as e:
                print(f"❌ [🕵️ Bot Tiền Trạm] Lỗi hệ thống: {e}")
            
            finally:
                # 7. Luôn đóng trình duyệt để giải phóng RAM
                await browser.close()
                
        return modules
    
    async def update_module_details(self, project_name, module_name, module_url):
        """
        Logic điều hướng: Kết hợp Playwright để di chuyển và VisionMachine để vét tri thức.
        """
        results = {}
        # 1. PHẢI LÀ async with
        async with async_playwright() as p:
            # 2. Tất cả khởi tạo phải có await
            browser = await p.chromium.launch(headless=False, slow_mo=500) 
            context = await browser.new_context()
            page = await context.new_page()
            
            # Giả định hàm login của Vũ cũng đã được sửa thành async (nên có await)
            # Nếu login chưa async thì bỏ await chỗ này
            if await self.login(page): 
                try:
                    print(f"🚀 [🎥 Bot phân cảnh] Truy cập Module: {module_name}")
                    # 3. await cho điều hướng
                    await page.goto(module_url, wait_until="networkidle", timeout=60000)
                    
                    # Các hàm bổ trợ này nếu bên trong có dùng lệnh của page thì cũng phải async/await
                    await self._expand_sidebar(page) 
                    sub_links = await self._get_sidebar_links(page)
                    
                    if not sub_links:
                        print(f"⚠️ Không tìm thấy link con trong Sidebar của {module_name}")
                    
                    for link in sub_links:
                        if not link['href'] or link['href'].strip('/') == module_url.strip('/'): 
                            continue
                        
                        print(f"🔍 [MỔ XẺ] : {link['text']}")
                        try:
                            # 4. await cho trang con
                            await page.goto(link['href'], wait_until="domcontentloaded", timeout=60000)
                            await page.wait_for_timeout(2000) 
                            actual_form_url = page.url 

                            # BƯỚC 1: QUÉT BỀ NỔI
                            structure = await self._extract_page_structure(page)

                            # BƯỚC 2: QUÉT SÂU
                            try:
                                add_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Tạo mới|Thêm|Thêm mới", re.I)
                                ).first
                                
                                if await add_btn.is_visible(timeout=3000):
                                    print(f"   ➕ Đang mở Form ẩn để vét Fields...")
                                    await add_btn.click()
                                    await page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=5000)
                                    await page.wait_for_timeout(1000)
                                    
                                    deep_struct = await self._extract_page_structure(page)
                                    
                                    if deep_struct:
                                        structure['form_fields'] = deep_struct.get('form_fields', [])
                                        current_actions = [str(a) for a in structure.get('actions', [])]
                                        for new_act in deep_struct.get('actions', []):
                                            if str(new_act) not in current_actions:
                                                structure.setdefault('actions', []).append(new_act)
                                    
                                    await page.keyboard.press("Escape")
                                    await page.wait_for_timeout(500)
                            except Exception as form_e:
                                print(f"   ℹ️ Trang không có form ẩn hoặc lỗi quét sâu: {form_e}")

                            # BƯỚC 3: QUÉT ĐỊNH DẠNG XUẤT
                            try:
                                export_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Xuất|Export", re.I)
                                ).first
                                if await export_btn.is_visible(timeout=2000):
                                    await export_btn.click()
                                    await page.wait_for_timeout(800)
                                    export_meta = await self._extract_page_structure(page)
                                    structure['export_formats'] = export_meta.get('export_formats', [])
                                    await page.keyboard.press("Escape")
                            except: pass

                            # ĐÓNG GÓI DỮ LIỆU
                            data_to_save = {
                                "module": module_name,
                                "form": link['text'],
                                "url": actual_form_url,
                                "structure": structure,
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            results[link['text']] = data_to_save
                            self._save_step(project_name, module_name, data_to_save, link['text'])
                            print(f"   ✅ Đã nạp xong tri thức cho: {link['text']}")

                        except Exception as inner_e:
                            print(f"   ❌ Lỗi trang con {link['text']} (Bỏ qua): {inner_e}")
                            continue
                            
                except Exception as e:
                    print(f"❌ Lỗi nghiêm trọng tại Module {module_name}: {e}")
            
            await browser.close()
        
        return results
    
    # 3. Sửa Sidebar thành Async
    async def _expand_sidebar(self, page):
        selectors = [".MuiListItemButton-root:not(a)", ".minimal__nav__item__root:not(a)"]
        for sel in selectors:
            items = await page.query_selector_all(sel) # THÊM AWAIT
            for item in items:
                if await item.get_attribute("aria-expanded") != "true": # THÊM AWAIT
                    try: 
                        await item.click() # THÊM AWAIT
                        await page.wait_for_timeout(500)
                    except: pass

    async def _get_sidebar_links(self, page):
        # THÊM AWAIT cho evaluate
        return await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('nav a, [class*="sidebar"] a'));
            return links.filter(a => a.innerText.trim().length > 1 && a.href.startsWith('http'))
                        .map(a => ({ 
                            text: a.innerText.split('\\n')[0].trim(), 
                            href: a.href 
                        }));
        }''')

    def _infer_form_id(self, page):
        """
        Hàm phụ để định danh Form, giúp AI biết đây là nghiệp vụ nào.
        """
        try:
            # Lấy phần cuối của URL để làm ID (ví dụ: /danh-muc-hang-hoa -> danh-muc-hang-hoa)
            url_part = page.url.split('/')[-1].split('?')[0] or "home"
            # Kết hợp với tiêu đề trang để tạo ID duy nhất
            page_title = page.title().replace(" ", "_")
            return f"{url_part}_{page_title}"
        except:
            return "unknown_form"

   
    
    # async def _extract_page_structure(self, page):       
        
    #     """
    #     SỬA LỖI TIMEOUT: Nâng cấp cơ chế đợi UI ổn định cho trang nặng.
    #     """
    #     print(f" 👁️ VisionMachine đang nội soi: {page.url}")
        
    #     try:
    #         # 1. ĐỢI UI (Nhớ thêm await vào các hàm của page nếu con Trinh Sát đang dùng Async)
    #         try:
    #             await page.wait_for_load_state("networkidle", timeout=20000)
    #             await page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiTable-root, button", timeout=15000)
    #         except Exception:
    #             print(f" ⚠️ Cảnh báo: UI chưa hoàn toàn ổn định nhưng vẫn tiến hành nội soi...")

    #         # 2. GỌI VISION MACHINE (Đã có await - Chuẩn!)
    #         metadata = await self.vision.scout_report(page)

    #         if metadata:
    #             # 3. Hợp nhất thêm các thông tin định danh
    #             # Đảm bảo dùng .get() để không bị Crash nếu metadata rỗng
    #             metadata['form_id'] = self._infer_form_id(page)
    #             metadata['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
    #             # Gia cố các key quan trọng
    #             if 'layout' not in metadata: 
    #                 # Nếu JS trả về main_content thay vì layout, ta gộp nó lại
    #                 metadata['layout'] = metadata.get('main_content', {})
                
    #             if 'navigation' not in metadata: 
    #                 metadata['navigation'] = {"url": page.url, "current_page": page.title()}
                
    #             return metadata
        
    #     except Exception as e:
    #         print(f" ❌ Lỗi nội soi tại {page.url}: {e}")
            
    #     return {"error": "Scan failed", "layout": {"main_content": {"actions": [], "inputs": []}}}

    async def _extract_page_structure(self, page):       
        """
        Nâng cấp cơ chế đợi UI ổn định cho trang nặng.
        """
        print(f" 👁️ VisionMachine đang nội soi: {page.url}")
        
        try:
            # 1. Đợi UI xuất hiện (Dùng những selector đặc trưng của hệ thống Vàng)
            try:
                # Đợi mạng rảnh và các thành phần chính của MUI/Grid xuất hiện
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, button", timeout=10000)
            except Exception:
                print(f" ⚠️ UI chưa hoàn toàn ổn định nhưng vẫn tiến hành nội soi...")

            # 2. GỌI VISION MACHINE (Sửa lỗi truyền tham số thừa)
            metadata = await self.vision.scout_report(page)

            if metadata:
                # 3. Hợp nhất thêm các thông tin định danh
                metadata['form_id'] = self._infer_form_id(page)
                
                # Đảm bảo layout luôn tồn tại để tránh lỗi Database sau này
                if not metadata.get('layout'):
                    metadata['layout'] = metadata.get('active_form') or {}
                
                return metadata
        
        except Exception as e:
            print(f" ❌ Lỗi nội soi tại {page.url}: {e}")
            
        # Trả về cấu trúc rỗng chuẩn để không gây lỗi cho các hàm xử lý sau
        return {
            "error": "Scan failed", 
            "layout": {"actions": [], "inputs": [], "tables": []},
            "navigation": {"url": page.url}
        }

    async def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
        """Đào sâu và đồng bộ tri thức vào Database"""
        print(f"🚀 [DEEP SCAN] Đang mổ xẻ Module: {module_name}")
        
        # Chạy mổ xẻ từng link con trong module
        deep_data = await self.update_module_details(project_folder, module_name, module_url)
        
        if not deep_data: 
            print(f"⚠️ Module {module_name} không có dữ liệu hoặc lỗi.")
            return False

        success_count = 0
        for form_name, f_data in deep_data.items():
            full_title = f"{module_name}|{form_name}"
            # Lấy metadata trực tiếp từ structure
            metadata_obj = f_data.get('structure', {})
            form_url = f_data.get('url') or module_url

            # Kiểm tra xem có 'hàng' để lưu không (tránh lưu rác)
            layout = metadata_obj.get('layout', {})
            has_actions = len(layout.get('actions', [])) > 0
            has_inputs = len(layout.get('inputs', [])) > 0 or len(metadata_obj.get('active_form', {}).get('inputs', [])) > 0

            if not (has_actions or has_inputs):
                print(f" ⚠️ Bỏ qua {full_title}: Không tìm thấy tương tác UI.")
                continue

            try:
                # Nếu ctrl là thư viện SQL sync (sqlite3, mysql-connector) thì giữ nguyên
                # Nếu dùng Database Async thì nhớ thêm 'await' ở đây
                existing_subs = ctrl.get_sub_contents(project_id)
                existing_item = next((s for s in existing_subs if s['sub_title'] == full_title), None)

                if existing_item:
                    res = ctrl.update_sub_content(
                        sub_id=existing_item['id'], 
                        new_url=form_url, 
                        new_metadata=metadata_obj, 
                        new_status="scanned"
                    )
                else:
                    res = ctrl.add_sub_content(
                        t_id=project_id,
                        sub_title=full_title,
                        parent_folder=project_folder,
                        url=form_url,
                        metadata=metadata_obj
                    )
                
                if res: success_count += 1
                    
            except Exception as e:
                print(f" ❌ Lỗi DB tại {full_title}: {e}")
                
        print(f"📊 Hoàn tất! Đã nạp {success_count} túi tri thức nghiệp vụ.")
        return True
    
    
    # async def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
    #     """Đào sâu và đồng bộ tri thức vào Database"""
    #     print(f"🚀 [DEEP SCAN] Đang mổ xẻ và nạp DB Module: {module_name}")
        
    #     # 1. PHẢI CÓ await để đợi Playwright quét xong
    #     deep_data = await self.update_module_details(project_folder, module_name, module_url)
        
    #     if not deep_data: 
    #         print(f"⚠️ Module {module_name} không có dữ liệu hoặc lỗi.")
    #         return False

    #     success_count = 0
    #     for form_name, f_data in deep_data.items():
    #         full_title = f"{module_name}|{form_name}"
    #         metadata_obj = f_data.get('structure', {})
    #         form_url = f_data.get('url') or module_url

    #         # Logic phòng thủ giữ nguyên
    #         if not metadata_obj.get('layout', {}).get('main_content', {}).get('actions'):
    #             if not metadata_obj.get('layout', {}).get('main_content', {}).get('inputs'):
    #                 print(f" ⚠️ Bỏ qua {full_title}: Metadata rỗng.")
    #                 continue

    #         try:
    #             # 2. Lưu ý: Nếu các hàm trong 'ctrl' (Database) cũng là async, ông phải thêm await vào trước chúng.
    #             # Nếu 'ctrl' là thư viện sync (như pymysql, sqlite3 thông thường) thì giữ nguyên như dưới:
    #             existing_subs = ctrl.get_sub_contents(project_id)
    #             existing_item = next((s for s in existing_subs if s['sub_title'] == full_title), None)

    #             if existing_item:
    #                 res = ctrl.update_sub_content(
    #                     sub_id=existing_item['id'], 
    #                     new_url=form_url, 
    #                     new_metadata=metadata_obj, 
    #                     new_status="scanned"
    #                 )
    #             else:
    #                 res = ctrl.add_sub_content(
    #                     t_id=project_id,
    #                     sub_title=full_title,
    #                     parent_folder=project_folder,
    #                     url=form_url,
    #                     metadata=metadata_obj
    #                 )
                
    #             if res: success_count += 1
                    
    #         except Exception as e:
    #             print(f" ❌ Lỗi DB tại {full_title}: {e}")
                
    #     print(f"📊 Xong! Đã nạp {success_count} 'túi tri thức' vào Database.")
    #     return True