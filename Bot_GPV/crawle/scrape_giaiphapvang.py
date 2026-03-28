import os
import re
import json
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from config import Config
from PIL import Image # pip install Pillow

load_dotenv()

class GiaiphapvangScraper:
    def __init__(self):
        # Lấy đường dẫn file từ Config thay vì hardcode
        self.output_file = Config.KNOWLEDGE_JSON_PATH
        # Đảm bảo thư mục storage tồn tại
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

    def _save_step(self, new_data):
        """Lưu và merge dữ liệu liên tục"""
        existing_data = {}
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except: pass
        
        existing_data.update(new_data)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)

    

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
                print("🔍 Đang vét danh sách nghiệp vụ...")
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
                print(f"✅ Đã vét xong: Tìm thấy {len(modules)} Modules nghiệp vụ.")
            browser.close()
        return modules
    

    def update_module_details(self, module_name, module_url):
        """CẤP ĐỘ 2: Chui sâu vào 1 Module để vét sạch Form con"""
        results = {}
        with sync_playwright() as p:
            # slow_mo để tránh bị chặn và giúp UI kịp render
            browser = p.chromium.launch(headless=False, slow_mo=500) 
            page = browser.new_page()
            
            if self.login(page):
                print(f"🚀 Thâm nhập Module: {module_name}")
                try:
                    page.goto(module_url, wait_until="networkidle", timeout=60000)
                    self._expand_sidebar(page)
                    sub_links = self._get_sidebar_links(page)
                    
                    for link in sub_links:
                        # Tránh loop vô tận vào trang chính của module
                        if link['href'].strip('/') == module_url.strip('/'): continue
                        
                        print(f"   ∟ Đang quét: {link['text']}")
                        try:
                            page.goto(link['href'], wait_until="networkidle", timeout=30000)
                            structure = self._extract_page_structure(page)
                            
                            key_name = f"{module_name}|{link['text']}"
                            form_data = {
                                "module": module_name,
                                "url": link['href'],
                                "structure": structure,
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            results[link['text']] = form_data
                            
                            # Lưu ngay lập tức vào file JSON trung tâm
                            self._save_step({key_name: form_data})
                            
                        except Exception as e:
                            print(f"      ⚠️ Lỗi trang {link['text']}: {e}")
                    print(f"\n🏁 Đã cập nhật xong toàn bộ module con và các nút")        
                except Exception as e:
                    print(f"❌ Lỗi Module {module_name}: {e}")
            
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

    def _extract_page_structure(self, page):
        """Trích xuất chi tiết cấu trúc trang (MUI DataGrid & Forms)"""
        # Chờ ít nhất 1 element đặc trưng của MUI xuất hiện
        try: page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiButton-root", timeout=10000)
        except: pass
        
        return page.evaluate('''() => {
            const getCleanText = (el) => el ? el.innerText.split('\\n')[0].replace(/[\\*\\•]/g, '').trim() : "";
            
            const structure = {
                columns: [],
                form_fields: [],
                actions: []
            };

            // 1. Lấy cột của bảng DataGrid
            document.querySelectorAll('.MuiDataGrid-columnHeaderTitle').forEach(h => {
                const txt = getCleanText(h);
                if(txt) structure.columns.push(txt);
            });

            // 2. Lấy các nút chức năng (Tạo mới, Xuất file...)
            document.querySelectorAll('button.MuiButton-root').forEach(b => {
                const txt = getCleanText(b);
                if(txt && txt.length > 2) structure.actions.push(txt);
            });

            // 3. Lấy các label của Input trong Form
            document.querySelectorAll('.MuiFormControl-root').forEach(f => {
                const label = f.querySelector('label');
                const input = f.querySelector('input, textarea');
                if(label && input) {
                    structure.form_fields.push({
                        label: getCleanText(label),
                        name: input.name || input.id
                    });
                }
            });

            return structure;
        }''')
    
    

    def save_and_compress_screenshot(self, page, save_path):
        # 1. Chụp ảnh tạm
        temp_path = save_path.replace(".png", "_raw.png")
        page.screenshot(path=temp_path)
        
        # 2. Dùng Pillow để nén
        with Image.open(temp_path) as img:
            # Chuyển về RGB và Resize nhỏ lại (ví dụ rộng 1280px là đủ nhìn)
            img = img.convert("RGB")
            img.thumbnail((1280, 1280)) 
            # Lưu dạng JPEG chất lượng 60% cho cực nhẹ
            img.save(save_path, "JPEG", quality=60)
        
        # 3. Xóa file tạm
        os.remove(temp_path)