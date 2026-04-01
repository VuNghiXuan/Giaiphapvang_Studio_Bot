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
        Bản cập nhật: Xử lý thông minh việc đóng Form sau khi quét sâu.
        """
        results = {}
        with sync_playwright() as p:
            # Dùng slow_mo=500 để mắt người kịp theo dõi và tránh bị firewall chặn
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
                        sub_links = [{"text": module_name, "href": module_url}]
                    
                    for link in sub_links:
                        # Tránh quét lại chính trang module cha
                        if not link['href'] or link['href'].strip('/') == module_url.strip('/'): 
                            continue
                        
                        print(f"🔍 [MỔ XẺ] : {link['text']}")
                        try:
                            page.goto(link['href'], wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(1500) 
                            
                            # --- BƯỚC 1: QUÉT BỀ NỔI ---
                            structure = self._extract_page_structure(page)

                            # --- BƯỚC 2: QUÉT SÂU (Form ẩn) ---
                            try:
                                # Selector nút Thêm mới linh hoạt hơn
                                add_btn = page.locator("button").filter(
                                    has_text=re.compile(r"Tạo mới|Thêm|Thêm mới|Add", re.I)
                                ).first
                                
                                if add_btn.is_visible(timeout=3000):
                                    print(f"   ➕ Phát hiện nút Thêm - Đang mở Form...")
                                    add_btn.click()
                                    
                                    # Chờ Dialog hoặc Drawer của MUI hiện ra
                                    page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, [role='dialog']", timeout=5000)
                                    page.wait_for_timeout(1000)
                                    
                                    deep_struct = self._extract_page_structure(page)
                                    
                                    if deep_struct and deep_struct.get('form_fields'):
                                        structure['form_fields'] = deep_struct['form_fields']
                                        # Hợp nhất actions mới (ví dụ nút Lưu, Hủy trong form)
                                        current_acts = [str(a) for a in structure.get('actions', [])]
                                        for act in deep_struct.get('actions', []):
                                            if str(act) not in current_acts:
                                                structure.setdefault('actions', []).append(act)
                                    
                                    # Nhấn Escape để đóng Form, quay lại trang Table
                                    page.keyboard.press("Escape")
                                    page.wait_for_timeout(800)
                            except:
                                pass # Không có nút thêm hoặc không mở được form thì thôi

                            # ĐÓNG GÓI
                            data_to_save = {
                                "module": module_name,
                                "form": link['text'],
                                "url": page.url,
                                "structure": structure, 
                                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            results[link['text']] = data_to_save
                            # Lưu file local để kiểm chứng
                            self._save_step(project_name, f"{module_name}_{link['text']}", data_to_save)
                            print(f"   ✅ Đã nạp xong tri thức cho: {link['text']}")

                        except Exception as inner_e:
                            print(f"   ❌ Lỗi trang con {link['text']}: {inner_e}")
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

    def _extract_page_structure(self, page):
        """
        Sử dụng VisionMachine để quét UI (Đã tối ưu logic Inject và Wait)
        """
        print(f"   👁️  VisionMachine đang 'nội soi' trang: {page.url}")
        metadata = {}
        
        try:
            # 1. Đảm bảo UI ổn định (Đợi các thành phần Material UI render xong)
            # Tăng timeout lên một chút vì mạng đôi khi lag khi tải Grid lớn
            try:
                page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiTable-root, form", timeout=8000)
            except:
                pass 

            # 2. KIỂM TRA & BƠM SCRIPT (Sửa lỗi đường dẫn động)
            # Thay vì hardcode path, tui lấy path tương đối từ file vision_machine hoặc thư mục gốc
            is_script_loaded = page.evaluate("typeof window.scanPage === 'function'")
            
            if not is_script_loaded:
                # Tìm file scanner.js nằm cùng thư mục với script này hoặc trong folder ai_film_factory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # Vũ kiểm tra lại đường dẫn này cho đúng với cấu trúc thư mục của ông nhé
                js_path = os.path.join(current_dir, "ai_film_factory", "scanner.js")
                
                if not os.path.exists(js_path):
                    # Fallback tìm ở thư mục hiện tại
                    js_path = "scanner.js"

                if os.path.exists(js_path):
                    with open(js_path, "r", encoding="utf-8") as f:
                        # Bơm script vào window object
                        page.add_script_tag(content=f.read())
                else:
                    print(f"❌ Không tìm thấy file scanner.js tại: {js_path}")
                    return {"error": "Missing scanner.js"}

            # 3. GỌI QUÉT (Sử dụng cấu trúc đồng bộ từ VisionMachine đã fix)
            # Nếu scanner.js của ông trả về Promise, dùng await. Nếu không, gọi trực tiếp.
            metadata = page.evaluate("window.scanPage()")

            # 4. GIA CỐ DỮ LIỆU TRẢ VỀ
            if metadata and isinstance(metadata, dict):
                metadata['form_id'] = self._infer_form_id(page)
                # Đảm bảo các key quan trọng luôn tồn tại để tránh lỗi crash ở các hàm sau
                for key in ['actions', 'form_fields', 'columns', 'layout']:
                    if key not in metadata or metadata[key] is None:
                        metadata[key] = []
            else:
                print("⚠️ Cảnh báo: scanner.js trả về dữ liệu không hợp lệ (không phải dict).")
                metadata = {"actions": [], "form_fields": [], "columns": [], "layout": []}

        except Exception as e:
            print(f"      ❌ Lỗi VisionMachine tại {page.url}: {e}")
            # Trả về cấu trúc rỗng để không làm hỏng luồng chạy của loop bên ngoài
            metadata = {"actions": [], "form_fields": [], "columns": [], "error": str(e)}
                
        return metadata
    
    def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
        """Đào sâu và đồng bộ - Bản gia cố chống mất dữ liệu tri thức"""
        print(f"🚀 [DEEP SCAN] Đang mổ xẻ Module: {module_name}")
        
        # 1. Thực hiện quét (Hàm này đã được Vũ tối ưu ở bước trước)
        deep_data = self.update_module_details(project_folder, module_name, module_url)
        
        if not deep_data: 
            print(f"⚠️ Module {module_name} không có dữ liệu form con hoặc lỗi truy cập.")
            return False

        # 2. Lấy dữ liệu hiện tại từ DB để so khớp
        existing_subs = ctrl.get_sub_contents(project_id)
        success_count = 0
        
        for form_name, f_data in deep_data.items():
            if not f_data: continue
            
            # Đồng nhất cách đặt tiêu đề: Module|Form
            full_title = f"{module_name}|{form_name}"
            existing_item = next((s for s in existing_subs if s['sub_title'] == full_title), None)
            
            form_url = f_data.get('url') or module_url
            metadata_json = f_data.get('structure', {})

            # KIỂM TRA CHẶN: Nếu quét ra metadata rỗng mà item đã tồn tại, 
            # có thể là do lỗi render trang, không nên đè metadata rỗng vào DB.
            if existing_item and not metadata_json.get('form_fields') and not metadata_json.get('columns'):
                print(f"  ⚠️ Bỏ qua update '{full_title}': Metadata quét được bị rỗng (nghi ngờ lỗi render).")
                continue

            try:
                if existing_item:
                    # CẬP NHẬT: Ưu tiên giữ lại metadata cũ nếu cái mới bị lỗi (logic phòng thủ)
                    res = ctrl.update_sub_content(
                        sub_id=existing_item['id'], 
                        new_url=form_url, 
                        new_metadata=metadata_json,
                        new_status="scanned" # Đánh dấu là đã quét xong kiến thức
                    )
                else:
                    # THÊM MỚI:
                    res = ctrl.add_sub_content(
                        t_id=project_id,
                        sub_title=full_title,
                        parent_folder=project_folder,
                        url=form_url,
                        metadata=metadata_json
                    )
                
                if res: 
                    success_count += 1
                    
            except Exception as e:
                print(f"   ❌ Lỗi DB khi xử lý Form '{full_title}': {e}")
                
        print(f"📊 Hoàn tất! Đã đồng bộ tri thức: {success_count}/{len(deep_data)} forms.")
        return True