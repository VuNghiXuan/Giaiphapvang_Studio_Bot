# 1. Thư viện hệ thống (Standard Libraries)
import os
import re
import json
import time
from datetime import datetime

# 2. Thư viện bên thứ ba (Third-party)
from playwright.sync_api import sync_playwright
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
    

    def save_and_compress_screenshot(self, page, save_path):
        """Nén ảnh an toàn để AI đọc, tránh tốn dung lượng"""
        try:
            temp_path = save_path.replace(".jpg", "_raw.png")
            page.screenshot(path=temp_path)
            
            with Image.open(temp_path) as img:
                # Chuyển sang RGB trước khi lưu JPEG để tránh lỗi kênh Alpha
                rgb_img = img.convert("RGB")
                rgb_img.thumbnail((1280, 1280)) 
                rgb_img.save(save_path, "JPEG", quality=60)
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"⚠️ Không nén được ảnh: {e}")

    def login(self, page):
        print(f"🔑 Đang đăng nhập hệ thống: {Config.TARGET_DOMAIN}")
        try:
            # Sử dụng Domain từ Config để tạo link login
            login_url = f"{Config.TARGET_DOMAIN.rstrip('/')}/auth/jwt/sign-in/"
            page.goto(login_url)
            
            # Lấy thông tin đăng nhập từ biến môi trường (os.getenv)
            page.fill("input[name='email']", os.getenv("USER_EMAIL"))
            page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
            page.click("button[type='submit']")
            
            # Chờ chuyển hướng thành công
            page.wait_for_url("**/home/**", timeout=30000)
            print("🏠 Đăng nhập thành công!")
            page.wait_for_timeout(1000)
            return True
        except Exception as e:
            print(f"❌ Đăng nhập thất bại: {e}")
            return False
        

    def get_home_modules(self):
        """CẤP ĐỘ 1: Vét sạch Module lớn từ trang chủ"""
        
        modules = []
        with sync_playwright() as p:
            # headless=True nếu Vũ muốn chạy ngầm, False để xem nó quét
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            if self.login(page):
                print("🔍  [🕵️ Bot Tiền Trạm] tìm kiếm danh sách nghiệp vụ...")
                try:
                    page.wait_for_selector(".MuiGrid-item", timeout=10000)
                except: pass

                # Chỉ lấy các link thuộc domain mình quản lý
                modules = page.evaluate(f'''() => {{
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .map(a => ({{ 
                            text: a.innerText.trim().split('\\n')[0], 
                            href: a.href 
                        }}))
                        .filter(m => m.text.length > 2 && m.href.includes('{Config.TARGET_DOMAIN}'));
                }}''')
                
                # Loại bỏ rác
                exclude_keywords = ["Đăng xuất", "Profile", "Thông báo", "Cài đặt", "Setting"]
                unique_modules = {}
                for m in modules:
                    if not any(k.lower() in m['text'].lower() for k in exclude_keywords):
                        unique_modules[m['href']] = m
                
                modules = list(unique_modules.values())
                print(f" [🕵️ Bot Tiền Trạm]  Đã tìm thấy {len(modules)} Modules nghiệp vụ ")
            browser.close()
        return modules

    def update_module_details(self, project_name, module_name, module_url):
        """
        Logic điều hướng: Kết hợp Playwright để di chuyển và VisionMachine để vét tri thức.
        """
        results = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500) 
            context = browser.new_context()
            page = context.new_page()
            
            if self.login(page):
                try:
                    print(f"🚀 [🎥 Bot phân cảnh] Truy cập Module: {module_name}")
                    page.goto(module_url, wait_until="networkidle", timeout=60000)
                    self._expand_sidebar(page)
                    sub_links = self._get_sidebar_links(page)
                    
                    if not sub_links:
                        print(f"⚠️ Không tìm thấy link con trong Sidebar của {module_name}")
                    
                    for link in sub_links:
                        if not link['href'] or link['href'].strip('/') == module_url.strip('/'): 
                            continue
                        
                        print(f"🔍 [MỔ XẺ] : {link['text']}")
                        try:
                            # 1. Di chuyển tới trang con
                            page.goto(link['href'], wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(2000) # Đợi React/MUI render xong UI
                            actual_form_url = page.url 

                            # BƯỚC 1: QUÉT BỀ NỔI (Table, Grid, Nút chung)
                            # Sử dụng VisionMachine để lấy cấu trúc ban đầu
                            structure = self._extract_page_structure(page)

                            # BƯỚC 2: QUÉT SÂU (Bấm 'Thêm mới' để vét Input Fields)
                            try:
                                add_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Tạo mới|Thêm|Thêm mới", re.I)
                                ).first
                                
                                if add_btn.is_visible(timeout=3000):
                                    print(f"   ➕ Đang mở Form ẩn để vét Fields...")
                                    add_btn.click()
                                    # Chờ Dialog/Drawer đặc trưng của hệ thống Vàng
                                    page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=5000)
                                    page.wait_for_timeout(1000)
                                    
                                    # Gọi VisionMachine lần 2 để lấy các trường trong Form
                                    deep_struct = self._extract_page_structure(page)
                                    
                                    # HỢP NHẤT DỮ LIỆU TRI THỨC
                                    if deep_struct:
                                        # Lấy danh sách fields từ form ẩn
                                        structure['form_fields'] = deep_struct.get('form_fields', [])
                                        
                                        # Bổ sung các nút bấm mới xuất hiện (Lưu, Hủy, In phiếu...)
                                        current_actions = [str(a) for a in structure.get('actions', [])]
                                        for new_act in deep_struct.get('actions', []):
                                            if str(new_act) not in current_actions:
                                                structure.setdefault('actions', []).append(new_act)
                                    
                                    # Đóng form để quét trang tiếp theo
                                    page.keyboard.press("Escape")
                                    page.wait_for_timeout(500)
                            except Exception as form_e:
                                print(f"   ℹ️ Trang không có form ẩn hoặc lỗi quét sâu: {form_e}")

                            # BƯỚC 3: QUÉT ĐỊNH DẠNG XUẤT (Export)
                            try:
                                export_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Xuất|Export", re.I)
                                ).first
                                if export_btn.is_visible(timeout=2000):
                                    export_btn.click()
                                    page.wait_for_timeout(800)
                                    export_meta = self._extract_page_structure(page)
                                    structure['export_formats'] = export_meta.get('export_formats', [])
                                    page.keyboard.press("Escape")
                            except: pass

                            # ĐÓNG GÓI DỮ LIỆU ĐỂ LƯU DB
                            data_to_save = {
                                "module": module_name,
                                "form": link['text'],
                                "url": actual_form_url,
                                "structure": structure, # Metadata "vét cạn" nằm ở đây
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            results[link['text']] = data_to_save
                            
                            # Lưu file vật lý để backup tri thức
                            self._save_step(project_name, module_name, data_to_save, link['text'])
                            print(f"   ✅ Đã nạp xong tri thức cho: {link['text']}")

                        except Exception as inner_e:
                            print(f"   ❌ Lỗi trang con {link['text']} (Bỏ qua): {inner_e}")
                            continue
                            
                except Exception as e:
                    print(f"❌ Lỗi nghiêm trọng tại Module {module_name}: {e}")
            
            browser.close()
        
        return results
    
    def _expand_sidebar(self, page):
        """Mở rộng các menu cha trong Sidebar"""
        selectors = [".MuiListItemButton-root:not(a)", ".minimal__nav__item__root:not(a)"]
        for sel in selectors:
            items = page.query_selector_all(sel)
            for item in items:
                if item.get_attribute("aria-expanded") != "true":
                    try: 
                        item.click()
                        page.wait_for_timeout(500)
                    except: pass

    def _get_sidebar_links(self, page):
        """Lấy danh sách text và href từ Sidebar"""
        return page.evaluate('''() => {
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

    # def _extract_page_structure(self, page):
    #     """
    #     Sử dụng VisionMachine để quét UI theo chuẩn OMNI METADATA 2026
    #     """
    #     print(f" 👁️ VisionMachine đang nội soi: {page.url}")
        
    #     try:
    #         # 1. Đợi UI ổn định (Material UI/MUI)
    #         page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiTable-root", timeout=5000)
            
    #         # 2. Gọi VisionMachine thực thi Script "Vét cạn"
    #         # Lưu ý: Hàm này phải trả về đúng cấu trúc JSON mà mình đã thiết kế
    #         metadata = self.vision.scan_page(page) 

    #         if metadata:
    #             # 3. Hợp nhất thêm các thông tin định danh
    #             metadata['form_id'] = self._infer_form_id(page)
    #             metadata['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
    #             # Gia cố các key quan trọng để AI không bị lỗi khi đọc
    #             if 'layout' not in metadata: metadata['layout'] = {}
    #             if 'navigation' not in metadata: 
    #                 metadata['navigation'] = {"url": page.url, "current_page": page.title()}
                
    #             return metadata
        
    #     except Exception as e:
    #         print(f" ❌ Lỗi nội soi tại {page.url}: {e}")
            
    #     return {"error": "Scan failed", "layout": {"main_content": {"actions": [], "inputs": []}}}
    
    async def _extract_page_structure(self, page):       
        
        """
        SỬA LỖI TIMEOUT: Nâng cấp cơ chế đợi UI ổn định cho trang nặng.
        """
        print(f" 👁️ VisionMachine đang nội soi: {page.url}")
        
        try:
            # 1. ĐỢI UI (Nhớ thêm await vào các hàm của page nếu con Trinh Sát đang dùng Async)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiTable-root, button", timeout=15000)
            except Exception:
                print(f" ⚠️ Cảnh báo: UI chưa hoàn toàn ổn định nhưng vẫn tiến hành nội soi...")

            # 2. GỌI VISION MACHINE (Đã có await - Chuẩn!)
            metadata = await self.vision.scan_page(page, is_async=True)

            if metadata:
                # 3. Hợp nhất thêm các thông tin định danh
                # Đảm bảo dùng .get() để không bị Crash nếu metadata rỗng
                metadata['form_id'] = self._infer_form_id(page)
                metadata['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Gia cố các key quan trọng
                if 'layout' not in metadata: 
                    # Nếu JS trả về main_content thay vì layout, ta gộp nó lại
                    metadata['layout'] = metadata.get('main_content', {})
                
                if 'navigation' not in metadata: 
                    metadata['navigation'] = {"url": page.url, "current_page": page.title()}
                
                return metadata
        
        except Exception as e:
            print(f" ❌ Lỗi nội soi tại {page.url}: {e}")
            
        return {"error": "Scan failed", "layout": {"main_content": {"actions": [], "inputs": []}}}
    
    def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
        """Đào sâu và đồng bộ tri thức vào Database"""
        print(f"🚀 [DEEP SCAN] Đang mổ xẻ và nạp DB Module: {module_name}")
        
        # 1. Chạy quy trình quét (Playwright sẽ click Thêm/Sửa để lấy metadata ẩn)
        deep_data = self.update_module_details(project_folder, module_name, module_url)
        
        if not deep_data: 
            print(f"⚠️ Module {module_name} không có dữ liệu hoặc lỗi.")
            return False

        success_count = 0
        for form_name, f_data in deep_data.items():
            # Tên định danh duy nhất trong DB: "Kế toán|Danh mục khách hàng"
            full_title = f"{module_name}|{form_name}"
            
            # Lấy metadata "vét cạn" (structure) đã được gom ở bước update_module_details
            metadata_obj = f_data.get('structure', {})
            form_url = f_data.get('url') or module_url

            # Logic phòng thủ: Không lưu nếu metadata quá rỗng (tránh đè dữ liệu tốt bằng dữ liệu lỗi)
            if not metadata_obj.get('layout', {}).get('main_content', {}).get('actions'):
                if not metadata_obj.get('layout', {}).get('main_content', {}).get('inputs'):
                    print(f" ⚠️ Bỏ qua {full_title}: Metadata rỗng.")
                    continue

            try:
                # Tìm xem sub_content này đã có trong DB chưa
                existing_subs = ctrl.get_sub_contents(project_id)
                existing_item = next((s for s in existing_subs if s['sub_title'] == full_title), None)

                if existing_item:
                    # UPDATE: Cập nhật metadata mới nhất vào DB
                    res = ctrl.update_sub_content(
                        sub_id=existing_item['id'], 
                        new_url=form_url, 
                        new_metadata=metadata_obj, # Đây là nơi lưu Object JSON cực lớn
                        new_status="scanned"
                    )
                else:
                    # INSERT: Thêm mới hoàn toàn
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
                
        print(f"📊 Xong! Đã nạp {success_count} 'túi tri thức' vào Database.")
        return True