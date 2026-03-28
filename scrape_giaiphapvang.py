# import os
# import re
# import json
# import time
# from playwright.sync_api import sync_playwright
# from dotenv import load_dotenv

# load_dotenv()

# class GiaiphapvangScraper:
#     def __init__(self, output_file="knowledge_source.json"):
#         self.output_file = output_file
#         self.knowledge_data = {}

#     def save_to_file(self):
#         with open(self.output_file, 'w', encoding='utf-8') as f:
#             json.dump(self.knowledge_data, f, ensure_ascii=False, indent=4)

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

#     def _get_hidden_row_actions(self, page):
#         """Hàm chuyên biệt để click và quét menu 3 chấm trên dòng của DataGrid"""
#         hidden_actions = []
#         try:
#             # Nhắm vào nút 3 chấm đầu tiên tìm thấy trong bảng
#             three_dots_btn = page.query_selector(".MuiDataGrid-row [aria-label*='Thêm'], .MuiDataGrid-row button .MuiSvgIcon-root")
#             if three_dots_btn:
#                 three_dots_btn.click()
#                 # Chờ menu xổ ra
#                 try:
#                     page.wait_for_selector(".MuiMenu-list, [role='menu']:not(.MuiDataGrid-actionsCell)", timeout=1500)
#                     menu_items = page.query_selector_all(".MuiMenuItem-root, [role='menuitem']")
#                     for item in menu_items:
#                         text = page.evaluate("el => el.innerText", item).strip()
#                         if text: hidden_actions.append(text)
#                 except:
#                     # Nếu là menu inline (không xổ popover)
#                     inline_btns = three_dots_btn.query_selector_all("..//button[@aria-label]")
#                     for btn in inline_btns:
#                         hidden_actions.append(page.get_attribute(btn, "aria-label"))
                
#                 page.keyboard.press("Escape")
#                 page.wait_for_timeout(300)
#         except: pass
#         return list(set(hidden_actions))

#     def _get_toolbar_actions(self, page):
#         """Hàm quét các nút chức năng trên đầu bảng (Xuất, Lọc, Cột...)"""
#         return page.evaluate('''() => {
#             const toolbar = document.querySelector('.MuiDataGrid-toolbarContainer');
#             if (!toolbar) return [];
#             return Array.from(toolbar.querySelectorAll('button'))
#                 .map(btn => btn.innerText.trim())
#                 .filter(txt => txt.length > 0);
#         }''')

#     def _scan_create_form(self, page):
#         """Hàm đột kích vào Form Tạo mới để lấy danh sách Input chi tiết"""
#         form_inputs = []
#         try:
#             # 1. Tìm nút Tạo mới (thường là nút duy nhất có text này ngoài bảng)
#             create_btn = page.get_by_role("button", name="Tạo mới", exact=True)
            
#             if create_btn.is_visible():
#                 print("     ✨ Phát hiện nút 'Tạo mới', đang thâm nhập Form...")
#                 create_btn.click()
                
#                 # 2. Chờ Form hoặc Dialog hiện lên
#                 page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=3000)
#                 page.wait_for_timeout(500) # Đợi hiệu ứng mở kết thúc

#                 # 3. Quét toàn bộ Input trong Form này
#                 form_inputs = page.evaluate('''() => {
#                     return Array.from(document.querySelectorAll('.MuiDialog-root input, .MuiDialog-root textarea, form input, form textarea'))
#                         .filter(el => el.type !== 'checkbox' && el.type !== 'hidden')
#                         .map(el => {
#                             let label = "";
#                             if (el.id) label = document.querySelector(`label[for="${el.id}"]`)?.innerText;
#                             if (!label) label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
#                             if (!label) label = el.placeholder || el.name;
#                             return { 
#                                 label: (label || "N/A").replace('*', '').trim(), 
#                                 name: el.name || el.id
#                             };
#                         });
#                 }''')

#                 print(f"     📝 Đã lấy được {len(form_inputs)} trường nhập liệu từ Form.")

#                 # 4. Thoát khỏi Form để không làm hỏng luồng quét tiếp theo
#                 page.keyboard.press("Escape")
#                 page.wait_for_timeout(500)
#         except Exception as e:
#             print(f"     ⚠️ Không thể quét Form Tạo mới: {e}")
#             # Đảm bảo thoát Form nếu có lỗi
#             page.keyboard.press("Escape")
            
#         return form_inputs

    
#     def _scan_create_form(self, page):
#         """Đột kích vào Form Tạo mới để lấy danh sách Input chi tiết"""
#         form_inputs = []
#         try:
#             # Tìm nút Tạo mới (chính xác text)
#             create_btn = page.get_by_role("button", name="Tạo mới", exact=True)
            
#             if create_btn.is_visible():
#                 print("     ✨ Phát hiện nút 'Tạo mới', đang thâm nhập Form...")
#                 create_btn.click()
                
#                 # Chờ Dialog hoặc Drawer của MUI hiện lên (thường dùng cho form thêm mới)
#                 # Timeout ngắn thôi, nếu không có thì bỏ qua
#                 try:
#                     page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=3000)
#                     page.wait_for_timeout(500) # Đợi animation một chút
#                 except:
#                     pass

#                 # Quét sạch các input bên trong Form/Dialog
#                 form_inputs = page.evaluate('''() => {
#                     // Chỉ quét trong container đang nổi lên (Dialog/Drawer) hoặc form
#                     const container = document.querySelector('.MuiDialog-root, .MuiDrawer-root, form');
#                     if (!container) return [];

#                     return Array.from(container.querySelectorAll('input, textarea, select'))
#                         .filter(el => {
#                             const type = el.type;
#                             return type !== 'checkbox' && type !== 'hidden' && type !== 'radio';
#                         })
#                         .map(el => {
#                             let label = "";
#                             // Tìm label theo ID hoặc bọc ngoài (MUI standard)
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

#                 if form_inputs:
#                     print(f"     📝 Đã bóc tách {len(form_inputs)} trường dữ liệu từ Form.")

#                 # Thoát Form bằng phím Escape để về lại trang chính
#                 page.keyboard.press("Escape")
#                 page.wait_for_timeout(500)
#         except Exception as e:
#             print(f"     ⚠️ Lỗi khi quét Form: {e}")
#             page.keyboard.press("Escape")
            
#         return form_inputs


#     def extract_structure(self, page, page_name):
#         print(f"  🕵️ Đang trích xuất: {page_name}")
        
#         try:
#             # Chờ các thành phần UI cốt lõi của MUI xuất hiện
#             page.wait_for_selector(".MuiDataGrid-root, .MuiButton-root, input, .MuiTab-root", timeout=8000)
#             page.wait_for_timeout(2000) 
#         except:
#             print(f"     ⚠️ Trang {page_name} load chậm hoặc không có dữ liệu chuẩn.")

#         row_actions = self._get_hidden_row_actions(page)
#         toolbar_actions = self._get_toolbar_actions(page)

#         structure = page.evaluate('''() => {
#             const clean = (txt) => {
#                 if (!txt) return "";
#                 // Lấy dòng đầu, xóa dấu *, xóa icon rác, xóa khoảng trắng thừa
#                 return txt.split('\\n')[0].replace(/[\\*\\•]/g, '').replace(/\\s+/g, ' ').trim();
#             };

#             const navKeywords = ['Thông tin công ty', 'Nhập hàng', 'Giá vốn', 'Kho & Quầy', 'Danh mục', 'Hệ thống', 'Cấu hình', 'Báo cáo', 'Quản lý'];
            
#             const allElements = Array.from(document.querySelectorAll('button, [role="button"], .MuiButton-root, .MuiTab-root'));

#             // 1. Tách Navigation/Tabs
#             const navigationTabs = allElements.filter(el => {
#                 const txt = clean(el.innerText);
#                 const isNavZone = el.closest('nav') || el.closest('.MuiDrawer-root') || el.closest('.MuiAppBar-root') || el.closest('.MuiTabs-root');
#                 // Chỉ lấy nếu nằm trong vùng Nav hoặc khớp từ khóa và dài hơn 1 ký tự (loại bỏ phím tắt "S")
#                 return (isNavZone || navKeywords.some(k => txt.includes(k))) && txt.length > 1;
#             }).map(el => clean(el.innerText));

#             // 2. Page Actions (Nút thao tác chính)
#             const pageActions = allElements.filter(el => {
#                 const txt = clean(el.innerText);
#                 if (txt.length <= 1) return false;

#                 const isInsideGrid = el.closest('.MuiDataGrid-root');
#                 const isInsideNav = el.closest('nav') || el.closest('.MuiDrawer-root') || el.closest('.MuiAppBar-root') || el.closest('.MuiTabs-root');
#                 const isPagination = el.closest('.MuiTablePagination-root');
#                 const isNavLink = navKeywords.some(k => txt === k);

#                 return !isInsideGrid && !isInsideNav && !isPagination && !isNavLink;
#             }).map(el => ({ text: clean(el.innerText) }));

#             // 3. Quét Bảng
#             const tables = Array.from(document.querySelectorAll('.MuiDataGrid-root, table')).map(grid => ({
#                 type: grid.tagName === 'TABLE' ? 'Table' : 'DataGrid',
#                 columns: Array.from(grid.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th'))
#                             .map(h => clean(h.innerText))
#                             .filter(h => h && !['STT', 'Chức năng', 'Thao tác'].includes(h))
#             }));

#             // 4. Quét Inputs
#             const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
#                 .filter(el => {
#                     const isSystemField = el.closest('.MuiTablePagination-root') || el.closest('.MuiDataGrid-toolbarContainer');
#                     return el.type !== 'hidden' && el.type !== 'checkbox' && !isSystemField;
#                 })
#                 .map(el => {
#                     let label = "";
#                     const labelEl = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
#                     const parentLabel = el.closest('.MuiFormControl-root')?.querySelector('label');
                    
#                     label = clean(labelEl?.innerText || parentLabel?.innerText || el.placeholder || el.name || "N/A");
                    
#                     return { 
#                         label: label, 
#                         name: el.name || el.id || "unknown"
#                     };
#                 }).filter(i => i.label !== "N/A" && i.name !== "unknown");

#             return {
#                 page_actions: [...new Set(pageActions.map(a => JSON.stringify(a)))].map(s => JSON.parse(s)), 
#                 navigation_tabs: [...new Set(navigationTabs)],
#                 tables: tables,
#                 inputs: inputs
#             };
#         }''')

#         # Hậu kỳ: Dọn dẹp toolbar_actions bằng Python
#         if structure.get('tables') and toolbar_actions:
#             cleaned_toolbar = []
#             for action in toolbar_actions:
#                 if action:
#                     # Xử lý chuỗi rác như "0\\nBộ lọc" -> "Bộ lọc"
#                     name_only = action.split('\n')[0]
#                     clean_name = re.sub(r'[0-9]', '', name_only).strip()
#                     if clean_name and len(clean_name) > 1:
#                         cleaned_toolbar.append(clean_name)
            
#             if structure['tables']:
#                 structure['tables'][0]['toolbar_actions'] = cleaned_toolbar

#         structure['row_actions_hidden'] = row_actions
        
#         # Kiểm tra nút "Tạo mới" để kích hoạt scan form
#         has_create_btn = any(btn['text'] == 'Tạo mới' for btn in structure['page_actions'])
#         structure['create_form_fields'] = self._scan_create_form(page) if has_create_btn else []

#         # Lưu kết quả
#         self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
#         self.save_to_file()
        
#         detail = f", {len(structure['create_form_fields'])} fields" if has_create_btn else ""
#         print(f"     ✅ Hoàn tất: {len(structure['page_actions'])} actions, {len(structure['tables'])} tables{detail}.")
    
    
#     def expand_and_get_submenus(self, page):
#         print("  🔍 Đang mở rộng Sidebar...")
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

#     def scan_app(self, page, app):
#         print(f"\n🚀 PHÂN HỆ: {app['text']}")
#         try:
#             page.goto(app['href'], wait_until="networkidle", timeout=30000)
#             page.wait_for_timeout(2000)
#             self.extract_structure(page, f"App_{app['text']}")
            
#             sub_links = self.expand_and_get_submenus(page)
#             unique_links = {link['href']: link['text'] for link in sub_links}

#             for href, text in list(unique_links.items()):
#                 if href.strip('/') == app['href'].strip('/'): continue
#                 print(f"    ∟ Chi tiết: {text}")
#                 try:
#                     page.goto(href, wait_until="networkidle", timeout=20000)
#                     page.wait_for_timeout(1500) # Chờ thêm cho chắc
#                     self.extract_structure(page, f"{app['text']}_{text}")
#                 except: pass
#         except Exception as e:
#             print(f"❌ Lỗi phân hệ {app['text']}: {e}")

#     def run(self):
#         with sync_playwright() as p:
#             browser = p.chromium.launch(headless=False)
#             page = browser.new_page()
#             if self.login(page):
#                 # Chờ màn hình dashboard load
#                 page.wait_for_selector("a", timeout=10000)
                
#                 apps = page.evaluate('''() => {
#                     return Array.from(document.querySelectorAll('a'))
#                         .filter(a => {
#                             const href = a.href.toLowerCase();
#                             return (href.includes('/dashboard') || href.includes('/trading')) && a.innerText.trim().length > 2;
#                         })
#                         .map(a => ({ text: a.innerText.trim().split('\\n')[0], href: a.href }));
#                 }''')

#                 # Loại trùng app
#                 unique_apps = {a['href']: a['text'] for a in apps}
                
#                 for href, text in unique_apps.items():
#                     if any(x in text for x in ["Mua bán", "Đăng xuất", "Tin tức"]): continue
#                     self.scan_app(page, {'text': text, 'href': href})

#             browser.close()
#             print(f"\n🏁 XONG! File lưu tại: {self.output_file}")

# if __name__ == "__main__":
#     GiaiphapvangScraper().run()