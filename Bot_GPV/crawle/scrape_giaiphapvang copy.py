import os
import re
import json
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

class GiaiphapvangScraper:
    def __init__(self, output_file="data/knowledge_source.json"):
        self.output_file = os.path.abspath(output_file)
        # Đảm bảo có thư mục data
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        self.knowledge_data = {}

    def _save_step(self, new_data):
        """Lưu và merge dữ liệu liên tục để tránh mất công quét nếu bị crash"""
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
        print("🔑 Đang đăng nhập hệ thống...")
        try:
            page.goto("https://giaiphapvang.net/auth/jwt/sign-in/")
            page.fill("input[name='email']", os.getenv("USER_EMAIL"))
            page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
            page.click("button[type='submit']")
            page.wait_for_url("**/home/**", timeout=30000)
            print("🏠 Đăng nhập thành công!")
            page.wait_for_timeout(2000)
            return True
        except Exception as e:
            print(f"❌ Đăng nhập thất bại: {e}")
            return False
        

    def get_home_modules(self):
        """CẤP ĐỘ 1: Vét sạch Module lớn"""
        modules = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            if self.login(page):
                print("🔍 Đang đợi trang chủ load danh sách nghiệp vụ...")
                # Chờ element chứa các module hiện ra (thường là Grid của MUI)
                try:
                    page.wait_for_selector(".MuiGrid-item", timeout=10000)
                    page.wait_for_timeout(1000) # Nghỉ 1s cho chắc
                except: pass

                modules = page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .map(a => ({ 
                            text: a.innerText.trim().split('\\n')[0], 
                            href: a.href 
                        }))
                        .filter(m => m.text.length > 2 && m.href.includes('/'));
                }''')
                
                # Chỉ loại bỏ những cái chắc chắn là hệ thống, không loại bỏ nghiệp vụ
                exclude_keywords = ["Đăng xuất", "Profile", "Thông báo", "Setting"]
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
            # slow_mo giúp Playwright không bị hệ thống coi là bot quá nhanh
            browser = p.chromium.launch(headless=False, slow_mo=400) 
            page = browser.new_page()
            
            if self.login(page):
                print(f"🚀 Bắt đầu thâm nhập: {module_name}")
                try:
                    page.goto(module_url, wait_until="networkidle", timeout=60000)
                    
                    # 1. Mở rộng toàn bộ Sidebar để thấy link con
                    self._expand_sidebar(page)
                    
                    # 2. Lấy link các Form con
                    sub_links = self._get_sidebar_links(page)
                    
                    # 3. Quét chi tiết từng Form
                    for link in sub_links:
                        # Bỏ qua link chính nó (trang chủ module)
                        if link['href'].strip('/') == module_url.strip('/'): continue
                        
                        print(f"   ∟ Đang phân tích Form: {link['text']}")
                        try:
                            page.goto(link['href'], wait_until="networkidle", timeout=30000)
                            # Trích xuất cấu trúc (Bảng, Form, Input...)
                            structure = self._extract_page_structure(page)
                            
                            key_name = f"{module_name}|{link['text']}"
                            results[link['text']] = {
                                "module": module_name,
                                "url": link['href'],
                                "structure": structure,
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            # Lưu từng bước (merge vào JSON)
                            self._save_step({key_name: results[link['text']]})
                            
                        except Exception as e:
                            print(f"      ⚠️ Lỗi quét trang {link['text']}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"❌ Lỗi truy cập Module {module_name}: {e}")
            
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