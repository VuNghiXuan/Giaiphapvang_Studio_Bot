# import os
# import re
# import json
# import time
# from playwright.sync_api import sync_playwright
# from dotenv import load_dotenv

# load_dotenv()

# class GiaiphapvangScraper:
#     def __init__(self, output_file="data/knowledge_source.json"):
#         self.output_file = output_file
#         self.knowledge_data = {}
#         # Đảm bảo có thư mục data
#         os.makedirs(os.path.dirname(os.path.abspath(self.output_file)), exist_ok=True)

#     def save_to_file(self):
#         """Lưu và merge dữ liệu để không mất các module đã quét trước đó"""
#         existing_data = {}
#         if os.path.exists(self.output_file):
#             try:
#                 with open(self.output_file, 'r', encoding='utf-8') as f:
#                     existing_data = json.load(f)
#             except: pass
        
#         existing_data.update(self.knowledge_data)
#         with open(self.output_file, 'w', encoding='utf-8') as f:
#             json.dump(existing_data, f, ensure_ascii=False, indent=4)

#     def login(self, page):
#         print("🔑 Đang đăng nhập hệ thống...")
#         try:
#             page.goto("https://giaiphapvang.net/auth/jwt/sign-in/")
#             page.fill("input[name='email']", os.getenv("USER_EMAIL"))
#             page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
#             page.click("button[type='submit']")
#             page.wait_for_url("**/home/**", timeout=30000)
#             print("🏠 Đăng nhập thành công!")
#             page.wait_for_timeout(2000)
#             return True
#         except Exception as e:
#             print(f"❌ Đăng nhập thất bại: {e}")
#             return False

#     def get_home_modules(self, page):
#         """Hàm lấy danh mục Module từ trang chủ (Dùng cho GUI)"""
#         print("🔍 Đang lập danh mục Modules từ trang chủ...")
#         try:
#             page.wait_for_selector("a", timeout=10000)
#             modules = page.evaluate('''() => {
#                 return Array.from(document.querySelectorAll('a'))
#                     .filter(a => {
#                         const href = a.href.toLowerCase();
#                         const text = a.innerText.trim();
#                         return (href.includes('/dashboard') || href.includes('/trading')) && text.length > 2;
#                     })
#                     .map(a => ({ 
#                         text: a.innerText.trim().split('\\n')[0], 
#                         href: a.href 
#                     }));
#             }''')
#             # Loại bỏ các link rác
#             filtered = [m for m in modules if not any(x in m['text'] for x in ["Mua bán", "Đăng xuất", "Tin tức"])]
#             # Loại trùng lặp
#             unique_modules = {m['href']: m for m in filtered}.values()
#             return list(unique_modules)
#         except:
#             return []

#     def _get_hidden_row_actions(self, page):
#         """Quét menu 3 chấm trên dòng của DataGrid"""
#         hidden_actions = []
#         try:
#             three_dots_btn = page.query_selector(".MuiDataGrid-row [aria-label*='Thêm'], .MuiDataGrid-row button .MuiSvgIcon-root")
#             if three_dots_btn:
#                 three_dots_btn.click()
#                 try:
#                     page.wait_for_selector(".MuiMenu-list, [role='menu']:not(.MuiDataGrid-actionsCell)", timeout=1500)
#                     menu_items = page.query_selector_all(".MuiMenuItem-root, [role='menuitem']")
#                     for item in menu_items:
#                         text = page.evaluate("el => el.innerText", item).strip()
#                         if text: hidden_actions.append(text)
#                 except:
#                     inline_btns = three_dots_btn.query_selector_all("..//button[@aria-label]")
#                     for btn in inline_btns:
#                         hidden_actions.append(page.get_attribute(btn, "aria-label"))
#                 page.keyboard.press("Escape")
#         except: pass
#         return list(set(hidden_actions))

#     def _get_toolbar_actions(self, page):
#         """Quét các nút trên đầu bảng (Xuất, Lọc...)"""
#         return page.evaluate('''() => {
#             const toolbar = document.querySelector('.MuiDataGrid-toolbarContainer');
#             if (!toolbar) return [];
#             return Array.from(toolbar.querySelectorAll('button'))
#                 .map(btn => btn.innerText.trim())
#                 .filter(txt => txt.length > 0);
#         }''')

#     def _scan_create_form(self, page):
#         """Đột kích vào Form Tạo mới để vét Input"""
#         form_inputs = []
#         try:
#             create_btn = page.get_by_role("button", name="Tạo mới", exact=True)
#             if create_btn.is_visible():
#                 print("     ✨ Phát hiện nút 'Tạo mới', đang thâm nhập Form...")
#                 create_btn.click()
#                 try:
#                     page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=3000)
#                     page.wait_for_timeout(500)
#                 except: pass

#                 form_inputs = page.evaluate('''() => {
#                     const container = document.querySelector('.MuiDialog-root, .MuiDrawer-root, form');
#                     if (!container) return [];
#                     return Array.from(container.querySelectorAll('input, textarea, select'))
#                         .filter(el => el.type !== 'checkbox' && el.type !== 'hidden' && el.type !== 'radio')
#                         .map(el => {
#                             let label = "";
#                             if (el.id) label = document.querySelector(`label[for="${el.id}"]`)?.innerText;
#                             if (!label) label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
#                             if (!label) label = el.placeholder || el.name;
#                             return { 
#                                 label: (label || "N/A").replace('*', '').trim().split('\\n')[0], 
#                                 name: el.name || el.id,
#                                 type: el.type
#                             };
#                         });
#                 }''')
#                 page.keyboard.press("Escape")
#                 page.wait_for_timeout(500)
#         except Exception as e:
#             print(f"     ⚠️ Lỗi khi quét Form: {e}")
#             page.keyboard.press("Escape")
#         return form_inputs

#     def extract_structure(self, page, page_name):
#         """Hàm lõi trích xuất cấu trúc chi tiết của 1 trang cụ thể"""
#         print(f"  🕵️ Đang trích xuất: {page_name}")
#         try:
#             page.wait_for_selector(".MuiDataGrid-root, .MuiButton-root, input, .MuiTab-root", timeout=8000)
#             page.wait_for_timeout(1500) 
#         except: pass

#         row_actions = self._get_hidden_row_actions(page)
#         toolbar_actions = self._get_toolbar_actions(page)

#         structure = page.evaluate('''() => {
#             const clean = (txt) => txt ? txt.split('\\n')[0].replace(/[\\*\\•]/g, '').replace(/\\s+/g, ' ').trim() : "";
#             const navKeywords = ['Thông tin công ty', 'Nhập hàng', 'Giá vốn', 'Kho & Quầy', 'Danh mục', 'Hệ thống', 'Cấu hình', 'Báo cáo', 'Quản lý'];
#             const allElements = Array.from(document.querySelectorAll('button, [role="button"], .MuiButton-root, .MuiTab-root'));

#             const navigationTabs = allElements.filter(el => {
#                 const txt = clean(el.innerText);
#                 const isNavZone = el.closest('nav') || el.closest('.MuiDrawer-root') || el.closest('.MuiAppBar-root') || el.closest('.MuiTabs-root');
#                 return (isNavZone || navKeywords.some(k => txt.includes(k))) && txt.length > 1;
#             }).map(el => clean(el.innerText));

#             const pageActions = allElements.filter(el => {
#                 const txt = clean(el.innerText);
#                 if (txt.length <= 1) return false;
#                 const isInsideGrid = el.closest('.MuiDataGrid-root');
#                 const isInsideNav = el.closest('nav') || el.closest('.MuiDrawer-root') || el.closest('.MuiAppBar-root') || el.closest('.MuiTabs-root');
#                 const isPagination = el.closest('.MuiTablePagination-root');
#                 return !isInsideGrid && !isInsideNav && !isPagination;
#             }).map(el => ({ text: clean(el.innerText) }));

#             const tables = Array.from(document.querySelectorAll('.MuiDataGrid-root, table')).map(grid => ({
#                 type: grid.tagName === 'TABLE' ? 'Table' : 'DataGrid',
#                 columns: Array.from(grid.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th')).map(h => clean(h.innerText))
#             }));

#             const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
#                 .filter(el => el.type !== 'hidden' && el.type !== 'checkbox' && !el.closest('.MuiTablePagination-root'))
#                 .map(el => ({
#                     label: clean(document.querySelector(`label[for="${el.id}"]`)?.innerText || el.placeholder || el.name || "N/A"),
#                     name: el.name || el.id || "unknown"
#                 })).filter(i => i.label !== "N/A");

#             return { page_actions: pageActions, navigation_tabs: [...new Set(navigationTabs)], tables, inputs };
#         }''')

#         # Cleanup toolbar actions
#         if structure['tables'] and toolbar_actions:
#             structure['tables'][0]['toolbar_actions'] = [re.sub(r'[0-9]', '', a.split('\n')[0]).strip() for a in toolbar_actions if a]

#         structure['row_actions_hidden'] = row_actions
        
#         # Kiểm tra và quét Form
#         has_create_btn = any(btn['text'] == 'Tạo mới' for btn in structure['page_actions'])
#         structure['create_form_fields'] = self._scan_create_form(page) if has_create_btn else []

#         self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
#         self.save_to_file()
#         print(f"     ✅ Xong: {len(structure['page_actions'])} actions, {len(structure['create_form_fields'])} form fields.")

#     def expand_and_get_submenus(self, page):
#         """Mở rộng Sidebar để lấy link các trang con"""
#         print("   🔍 Đang mở rộng Sidebar...")
#         expandable_selectors = [".MuiListItemButton-root:not(a)", ".minimal__nav__item__root:not(a)"]
#         for selector in expandable_selectors:
#             try:
#                 for item in page.query_selector_all(selector):
#                     if item.get_attribute("aria-expanded") != "true":
#                         item.click()
#                         page.wait_for_timeout(400)
#             except: continue

#         return page.evaluate('''() => {
#             return Array.from(document.querySelectorAll('nav a, .MuiCollapse-root a, [class*="sidebar"] a'))
#                 .filter(a => a.innerText.trim().length > 1 && a.href.startsWith('http'))
#                 .map(a => ({ text: a.innerText.split('\\n')[0].trim(), href: a.href }));
#         }''')

#     def update_module_logic(self, module_text, module_href):
#         """Hàm chính để nút UPDATE trên GUI gọi vào"""
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=False, slow_mo=300)
#             context = browser.new_context(no_viewport=True)
#             page = context.new_page()
            
#             try:
#                 if self.login(page):
#                     print(f"\n🚀 CẬP NHẬT CHI TIẾT: {module_text}")
#                     page.goto(module_href, wait_until="networkidle", timeout=30000)
#                     page.wait_for_timeout(2000)
                    
#                     # Quét trang chủ của phân hệ
#                     self.extract_structure(page, f"App_{module_text}")
                    
#                     # Tìm và quét tất cả trang con
#                     sub_links = self.expand_and_get_submenus(page)
#                     unique_links = {link['href']: link['text'] for link in sub_links}

#                     for href, text in unique_links.items():
#                         if href.strip('/') == module_href.strip('/'): continue
#                         print(f"   ∟ Chi tiết: {text}")
#                         try:
#                             page.goto(href, wait_until="networkidle", timeout=20000)
#                             self.extract_structure(page, f"{module_text}_{text}")
#                         except: pass
                    
#                     print(f"\n🏁 Đã cập nhật xong toàn bộ module: {module_text}")
#             except Exception as e:
#                 print(f"❌ Lỗi trong quá trình Update: {e}")
#             finally:
#                 browser.close()