# import os
# import asyncio
# import json
# from playwright.async_api import async_playwright
# from Bot_GPV.ai_film_factory.auth_machine import AuthMachine

# class StudioScanner:
#     """Tầng 1: File Excel Tổng - Quản lý lộ trình và xác thực"""
#     def __init__(self):
#         self.auth = AuthMachine()
#         self.results = {}
#         # Đọc sẵn file JS để nạp vào trình duyệt khi cần
#         js_path = "Bot_GPV/ai_film_factory/js/base_utils.js"
#         with open(js_path, 'r', encoding='utf-8') as f:
#             self.utils_js = f.read()

#     async def scan_module(self, module_name, module_url):
#         async with async_playwright() as p:
#             # Headless=False để Vũ dễ dàng quan sát quá trình "bung" Sidebar
#             browser = await p.chromium.launch(headless=False, slow_mo=50)
#             context = await browser.new_context()
#             page = await context.new_page()
            
#             try:
#                 # BƯỚC 0: ĐĂNG NHẬP (Giao hoàn toàn cho AuthMachine)
#                 if not await self.auth.login(page): 
#                     print("❌ Đăng nhập thất bại. Dừng quét.")
#                     return {}

#                 # BƯỚC 1: BUNG VÀ THU THẬP LINK (SidebarArchitect)
#                 print(f"🚀 [Module]: {module_name} - Khởi tạo lộ trình...")
#                 sidebar = SidebarArchitect(page, self.utils_js)
#                 tasks = await sidebar.expand_and_collect_tasks(module_url, module_name)
                
#                 if not tasks:
#                     print("⚠️ Không tìm thấy link nào trong Sidebar.")
#                     return {}

#                 # BƯỚC 2: DUYỆT TỪNG TRANG CON (SurfaceNavigator)
#                 for task in tasks:
#                     navigator = SurfaceNavigator(page, self.utils_js)
#                     metadata = await navigator.deep_scan_page(task)
                    
#                     if metadata:
#                         self.results[task['full_path']] = metadata
#                         print(f"✅ Đã quét xong: {task['full_path']}")

#             except Exception as e:
#                 print(f"❌ Lỗi nghiêm trọng tại StudioScanner: {e}")
#             finally:
#                 await browser.close()
            
#             return self.results

# class SidebarArchitect:
#     """Tầng 2: Bảng tính (Sheet) - Quản lý Sidebar và phân cấp Menu"""
#     def __init__(self, page, utils_js):
#         self.page = page
#         self.utils_js = utils_js

#     async def expand_and_collect_tasks(self, url, module_name):
#         await self.page.goto(url, wait_until="networkidle")
#         await self.page.wait_for_timeout(1000) # Chờ MUI ổn định
        
#         # Click bung tất cả các Folder (Menu cha)
#         # Sử dụng selector đặc trưng của MUI ListItem có icon ExpandMore
#         expandable_items = await self.page.query_selector_all(".MuiListItem-root, .MuiButtonBase-root")
        
#         for item in expandable_items:
#             # Kiểm tra xem item có phải là folder (có mũi tên mà không có href)
#             is_folder = await item.evaluate('''(el) => {
#                 const hasArrow = el.querySelector('svg[data-testid*="Expand"]');
#                 const noLink = !el.closest('a') && (!el.getAttribute('href') || el.getAttribute('href') === '#');
#                 return hasArrow && noLink;
#             }''')
            
#             if is_folder:
#                 try:
#                     await item.click()
#                     await self.page.wait_for_timeout(300) # Đợi animation bung
#                 except: pass

#         # Nạp JS Scout để lấy cấu trúc cây UI
#         await self.page.evaluate(self.utils_js)
#         # window.nav.get_ui_tree là hàm JS Vũ đã viết trong base_utils.js
#         ui_tree = await self.page.evaluate("window.nav.get_ui_tree()")
        
#         return self._flatten_tree(ui_tree or [], module_name)

#     def _flatten_tree(self, tree, module_name):
#         flat = []
#         for item in tree:
#             # Nếu mục gốc có href (Link trực tiếp không con)
#             if item.get('href') and item['href'] != "#":
#                 flat.append({
#                     'url': item['href'],
#                     'name': item['title'],
#                     'full_path': f"{module_name}|{item['title']}"
#                 })
            
#             # Xử lý các con
#             for child in item.get('children', []):
#                 if child.get('href') and child['href'] != "#":
#                     flat.append({
#                         'url': child['href'],
#                         'name': child['title'],
#                         'full_path': f"{module_name}|{item['title']}|{child['title']}"
#                     })
#         return flat

# class SurfaceNavigator:
#     """Tầng 3: Vùng dữ liệu (Range) - Quản lý Main Content và Thanh cuộn"""
#     def __init__(self, page, utils_js):
#         self.page = page
#         self.utils_js = utils_js

#     async def deep_scan_page(self, task):
#         try:
#             print(f"   🔍 Đang nội soi: {task['name']}")
#             await self.page.goto(task['url'], wait_until="networkidle", timeout=60000)
            
#             # Xử lý các Pop-up hoặc thông báo che khuất
#             await self.page.keyboard.press("Escape")
            
#             # Ép React render bằng cách cuộn
#             await self._auto_scroll_to_reveal()
            
#             # Tầng 4: Bóc tách thực tế
#             dissector = ElementDissector(self.page, self.utils_js)
#             return await dissector.extract_all_metadata()
#         except Exception as e:
#             print(f"⚠️ Không thể quét trang {task['name']}: {e}")
#             return None

#     async def _auto_scroll_to_reveal(self):
#         """Cuộn trang thông minh để tìm phần tử ẩn (Virtual Scroll)"""
#         await self.page.evaluate("""
#             async () => {
#                 const main = document.querySelector('main') || document.body;
#                 for (let i = 0; i < 3; i++) {
#                     window.scrollBy(0, 400);
#                     await new Promise(r => setTimeout(r, 400));
#                 }
#                 window.scrollTo(0, 0); // Quay lại đầu trang để chụp ảnh/quét
#             }
#         """)

# class ElementDissector:
#     """Tầng 4: Ô (Cell) - Trích xuất thuộc tính chi tiết nhất (Inputs, Buttons, Tables)"""
#     def __init__(self, page, utils_js):
#         self.page = page
#         self.utils_js = utils_js

#     async def extract_all_metadata(self):
#         # Nạp lại JS cho context trang con mới
#         await self.page.evaluate(self.utils_js)
        
#         # Thực hiện quét sâu DOM
#         metadata = await self.page.evaluate("""
#             () => {
#                 // Ưu tiên quét Container chính, nếu không thấy thì quét toàn bộ body
#                 const container = document.querySelector('main, form, .MuiContainer-root, .ant-layout-content') || document.body;
                
#                 // Trả về kết quả từ hàm internalScan đã định nghĩa trong base_utils.js
#                 if (typeof window.internalScan === 'function') {
#                     return window.internalScan(container);
#                 } else {
#                     return { error: "window.internalScan not found in base_utils.js" };
#                 }
#             }
#         """)
#         return metadata