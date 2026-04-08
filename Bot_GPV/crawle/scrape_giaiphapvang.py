# # 1. Thư viện hệ thống (Standard Libraries)
# import os
# import re
# import json
# import time
# from datetime import datetime
# import asyncio

# # 2. Thư viện bên thứ ba (Third-party)
# from playwright.async_api import async_playwright
# from PIL import Image # pip install Pillow
# from dotenv import load_dotenv

# # 3. Các Module nội bộ (Local Modules)
# from config import Config
# from Bot_GPV.ai_film_factory.vision_machine import VisionMachine
# from Bot_GPV.ai_film_factory.auth_machine import AuthMachine
# from .ui_navigator import UIMapNavigator

# load_dotenv()

# class GiaiphapvangScraper:
#     def __init__(self):
#         # Khởi tạo thông qua Config để đảm bảo thư mục storage luôn đúng
#         Config.init_folders()
#         self.vision = VisionMachine()
#         self.auth = AuthMachine(vision_machine=self.vision)
#         print(f"🚀 Scraper sẵn sàng. Hệ thống lưu trữ: {Config.BASE_STORAGE}")

#     def _get_form_dir(self, project_folder, sub_title, asset_type=None):
#         """Sửa lại để tự dọn dẹp ký tự đặc biệt gây lỗi Windows Path"""
#         parts = [p.strip() for p in sub_title.split('|')]
#         module_name = self._clean_path(parts[0]) if len(parts) > 1 else "General"
#         form_name = self._clean_path(parts[-1]) 

#         return Config.get_path(
#             app=project_folder, 
#             module=module_name, 
#             form=form_name, 
#             asset_type=asset_type
#         )
    
#     def _clean_path(self, text):
#         """Dọn dẹp ký tự cấm trên Windows và thay dấu phân cách menu"""
#         # Thay | thành _ và xóa các ký tự đặc biệt
#         text = text.replace('|', '_').replace(' ', '_')
#         return re.sub(r'[\\/*?:"<>|]', '_', text).strip()
    
#     def _save_step(self, project_folder, sub_title, data):
#         try:
#             meta_dir = self._get_form_dir(project_folder, sub_title, "metadata")
#             file_path = meta_dir / "structure.json"
#             with open(file_path, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, ensure_ascii=False, indent=4)
#             return str(meta_dir)
#         except Exception as e:
#             print(f"❌ [Scraper]: Lỗi lưu JSON tại {sub_title}: {e}")
#             return None
    
#     async def save_and_compress_screenshot(self, page, project_folder, sub_title):
#         try:
#             assets_dir = self._get_form_dir(project_folder, sub_title, "assets")
#             final_img_path = assets_dir / "scout_report.jpg"
#             temp_png_path = assets_dir / "raw_temp.png"
            
#             await page.screenshot(path=str(temp_png_path))
            
#             with Image.open(temp_png_path) as img:
#                 rgb_img = img.convert("RGB")
#                 rgb_img.thumbnail((1280, 1280)) 
#                 rgb_img.save(str(final_img_path), "JPEG", quality=60)
            
#             if temp_png_path.exists():
#                 temp_png_path.unlink()
                
#             return str(final_img_path)
#         except Exception as e:
#             print(f"⚠️ Lỗi chụp ảnh cho {sub_title}: {e}")
#             return None
    

#     async def get_home_modules(self, project_folder): # Thêm project_folder vào đây
#         """
#         CẤP ĐỘ 1: Quét trang chủ để lấy danh sách Module chính.
#         """
#         if project_folder is None:
#             project_folder = Config.APP_SLUG

#         modules = []
#         async with async_playwright() as p:
#             browser = await p.chromium.launch(headless=False, slow_mo=50)
#             context = await browser.new_context()
#             page = await context.new_page()
            
#             try:
#                 # 1. Thực hiện Login
#                 if await self.auth.login(page):
#                     print("🏠 Đã vào trang chủ. Đang kiểm tra trạng thái UI...")
                    
#                     try:
#                         await page.wait_for_load_state("networkidle", timeout=10000)
#                     except:
#                         pass 
                    
#                     await page.keyboard.press("Escape")
#                     await page.wait_for_timeout(1000)

#                     # 4. CHỐT CHẶN: Đợi Selector
#                     try:
#                         await page.wait_for_selector("nav, .MuiListItem-root, a[href*='/']", timeout=15000)
#                     except Exception as e:
#                         # ✅ ĐÃ FIX: Lưu vào folder logs của dự án
#                         log_dir = Config.get_path(app=project_folder, asset_type="logs")
#                         debug_path = log_dir / "error_timeout_home.jpg"
#                         await page.screenshot(path=str(debug_path))
#                         print(f"❌ Timeout trang chủ. Đã chụp ảnh debug tại: {debug_path}")
#                         return []

#                     # 5. TRÍCH XUẤT MODULES (Giữ nguyên logic evaluate của ông)
#                     target_domain = Config.TARGET_DOMAIN.replace("https://", "").replace("http://", "").rstrip('/')
#                     raw_links = await page.evaluate(f'''() => {{
#                         const links = Array.from(document.querySelectorAll('a[href], .MuiListItem-button, .MuiGrid-item a'));
#                         return links.map(a => {{
#                             const textEl = a.querySelector('.MuiListItemText-primary') || a;
#                             let cleanText = textEl.innerText.trim().split('\\n')[0];
#                             let href = a.href || a.getAttribute('data-href') || "";
#                             return {{ text: cleanText, href: href }};
#                         }})
#                         .filter(m => m.text.length > 2 && m.href.includes('{target_domain}'));
#                     }}''')
                    
#                     # 6. LỌC TRÙNG (Giữ nguyên)
#                     unique_modules = {}
#                     exclude_keywords = ["đăng xuất", "cài đặt", "hướng dẫn", "thông báo", "profile", "user"]
#                     for m in raw_links:
#                         text_lower = m['text'].lower()
#                         if not any(k in text_lower for k in exclude_keywords):
#                             if m['text'] not in unique_modules:
#                                 unique_modules[m['text']] = m
                    
#                     modules = list(unique_modules.values())
                    
#                     # 7. ✅ ĐÃ FIX: Lưu ảnh scan thành công vào folder assets của Dashboard
#                     # Coi Dashboard là một nghiệp vụ để AI dễ quản lý
#                     home_assets = self._get_form_dir(project_folder, "Home|Dashboard", "assets")
#                     final_scan_path = home_assets / "last_home_scan.jpg"
                    
#                     await page.screenshot(path=str(final_scan_path))
#                     print(f"✅ Tìm thấy {len(modules)} Modules. Ảnh scan lưu tại: {final_scan_path}")

#             except Exception as e:
#                 print(f"❌ Lỗi hệ thống trong get_home_modules: {e}")
#             finally:
#                 await browser.close()
                
#         return modules
    
#     #-------Xử lý vét cạn, vét sâu form ----------------
#     async def _extract_unique_sub_links(self, raw_links, base_url):
#         """
#         THIẾT QUÂN LUẬT: Lọc dựa trên Text + URL để không bỏ sót Form.
#         """
#         unique_links = []
#         seen_identifiers = set() # Dùng cả Text và URL để định danh
        
#         # Chuẩn hóa URL gốc
#         base_path = base_url.split('?')[0].rstrip('/')

#         for link in raw_links:
#             # Làm sạch URL con
#             href = link['href'].split('?')[0].rstrip('/')
#             text = link['text'].strip()
            
#             # Tạo ID duy nhất bằng cách kết hợp Text và URL (slugified)
#             identifier = f"{text}_{href}"
            
#             if identifier not in seen_identifiers:
#                 seen_identifiers.add(identifier)
#                 unique_links.append(link)
                
#         return unique_links

#     async def _dissect_single_form(self, page, project_folder, module_name, link_data):
#         """CẤP ĐỘ 2.1: Đi sâu vào từng Form và trích xuất tri thức."""
#         # link_data bây giờ có: text, href, full_path
#         form_name = link_data['text']
#         full_path = link_data['full_path'] # Dạng: Module|Cha|Con
        
#         # 1. Di chuyển và ổn định UI
#         await page.goto(link_data['href'], wait_until="networkidle", timeout=45000)
#         await page.wait_for_timeout(1500) 
#         await page.keyboard.press("Escape") 

#         # 2. Định danh thư mục logs (Fix Errno 22 bằng cách slugify full_path ở đây)
#         # Thay đổi dấu '|' thành '_' khi tạo folder thực tế
#         safe_folder_name = full_path.replace('|', '_').replace(' ', '_')
#         form_log_dir = self._get_form_dir(project_folder, safe_folder_name, "logs")
        
#         # 3. Gọi Vision Machine quét cấu trúc (Sử dụng AI để đọc UI)
#         structure = await self.vision.scout_report(
#             page, 
#             context={
#                 "target_dir": str(form_log_dir),
#                 "app": project_folder,
#                 "module": module_name,
#                 "form": form_name
#             }
#         )

#         # 4. Vét cạn thuộc tính kỹ thuật (Dành cho Dev)
#         technical_elements = await self._dissect_form_elements(page)
        
#         # Gộp cả 2: Tri thức từ AI (Vision) + Dữ liệu kỹ thuật (DOM)
#         full_metadata = {
#             "ui_vision": structure,
#             "dom_technical": technical_elements
#         }

#         # 5. Chụp ảnh & Nén
#         await self.save_and_compress_screenshot(page, project_folder, safe_folder_name)
        
#         # 6. Đóng gói dữ liệu để lưu DB
#         data_to_save = {
#             "project": project_folder,
#             "module": module_name,
#             "form": full_path, # Lưu full path vào DB để sau này search cho dễ
#             "url": page.url,
#             "metadata": full_metadata,
#             "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
        
#         # 7. Lưu file JSON
#         self._save_step(project_folder, safe_folder_name, data_to_save)
        
#         return full_path, data_to_save

#     # --- 3. HÀM ĐIỀU PHỐI "VÉT CẠN" (Update lại hàm cũ của Vũ) ---
#     async def update_module_details(self, project_folder, module_name, module_url):
#         results = {}
        
#         # Đọc sẵn đồ nghề vào RAM để nạp cho nhanh và ổn định
#         try:
#             with open("Bot_GPV/ai_film_factory/js/base_utils.js", 'r', encoding='utf-8') as f:
#                 utils_js = f.read()
#         except Exception as e:
#             print(f"❌ Không tìm thấy file base_utils.js: {e}")
#             return results

#         async with async_playwright() as p:
#             # slow_mo=100 để ông kịp nhìn thấy nó đang click cái gì
#             browser = await p.chromium.launch(headless=False, slow_mo=100)
#             page = await browser.new_page()
#             nav = UIMapNavigator(page) 

#             try:
#                 # Bước 0: Đăng nhập
#                 if not await self.auth.login(page): 
#                     print("❌ Đăng nhập thất bại, hủy nội soi.")
#                     return results

#                 print(f"🚀 [START] Nội soi Module: {module_name}")
#                 await page.goto(module_url, wait_until="networkidle")
                
#                 # Bước 1: Bung sidebar vật lý (Có in log click bên trong hàm này)
#                 await self._expand_sidebar(page)
                
#                 # Bước 2: Lấy cây UI từ scout_engine.js
#                 ui_tree = await nav.get_ui_tree()
                
#                 all_tasks = []
#                 print(f"\n--- [BẢN ĐỒ SIDEBAR: {module_name}] ---")
#                 for parent in ui_tree:
#                     p_title = parent.get('title', 'Menu Gốc')
                    
#                     # Check nếu menu cha có link (không phải chỉ là folder)
#                     if parent.get('href') and parent['href'] not in ["#", "javascript:void(0)"]:
#                         all_tasks.append({
#                             'text': p_title,
#                             'href': parent['href'],
#                             'full_path': f"{module_name}|{p_title}"
#                         })
#                         print(f"📁 [Cha+Link] {p_title} -> {parent['href']}")
#                     else:
#                         print(f"📁 [Cha] {p_title}")

#                     # Lấy menu con
#                     for child in parent.get('children', []):
#                         all_tasks.append({
#                             'text': child['title'],
#                             'href': child['href'],
#                             'full_path': f"{module_name}|{p_title}|{child['title']}"
#                         })
#                         print(f"   └─ 📄 [Con] {child['title']} -> {child['href']}")
#                 print(f"---------------------------------------\n")

#                 # Bước 3: Duyệt từng nhiệm vụ (Form con)
#                 for task in all_tasks:
#                     print(f"🔍 [Mổ xẻ] Đang vào: '{task['text']}'")
#                     try:
#                         # Đi tới URL của form
#                         await page.goto(task['href'], wait_until="networkidle", timeout=60000)
                        
#                         # CHỐT CHẶN: Đợi cho đến khi phần thân của trang web (MUI Content) hiện ra
#                         # Điều này cực kỳ quan trọng để tránh lỗi "querySelectorAll of null"
#                         try:
#                             await page.wait_for_selector("main, .MuiContainer-root, form, table", timeout=8000)
#                         except:
#                             print(f"   ⚠️ Cảnh báo: Trang '{task['text']}' load quá lâu hoặc không có container chuẩn.")

#                         # Nạp lại utils (phòng thủ innerText đã sửa) ngay tại trang hiện tại
#                         await page.evaluate(utils_js)
                        
#                         # Gọi hàm mổ xẻ nội bộ
#                         name, data = await self._dissect_single_form_internal(
#                             page, project_folder, module_name, task
#                         )
                        
#                         if name:
#                             input_count = len(data.get('inputs', []))
#                             action_count = len(data.get('actions', []))
#                             print(f"   ✅ Xong: {input_count} inputs, {action_count} actions.")
#                             results[name] = data
#                         else:
#                             print(f"   ⚠️ Không lấy được metadata cho: {task['text']}")
                            
#                     except Exception as e:
#                         print(f"   ❌ Lỗi tại {task['text']}: {str(e)[:150]}")
#                         continue

#                 print(f"🏁 [FINISH] Hoàn tất Module {module_name}. Tổng cộng trinh sát được {len(results)} form.")

#             except Exception as e:
#                 print(f"❌ [CRITICAL] Lỗi hệ thống: {e}")
#             finally:
#                 await browser.close()
                
#         return results
    

#     async def _dissect_single_form_internal(self, page, project_folder, module_name, link_data):
#         """Hàm nội bộ để thực hiện quét 1 form cụ thể"""
#         full_path = link_data['full_path']
        
#         await page.wait_for_timeout(1000) 
#         await page.keyboard.press("Escape") 

#         # Tạo folder logs an toàn
#         form_log_dir = self._get_form_dir(project_folder, full_path, "logs")
        
#         # Gọi Vision Machine quét cấu trúc
#         structure = await self.vision.scout_report(
#             page, 
#             context={
#                 "target_dir": str(form_log_dir),
#                 "app": project_folder,
#                 "module": module_name,
#                 "form": link_data['text']
#             }
#         )

#         technical_elements = await self._dissect_form_elements(page)
        
#         full_metadata = {
#             "ui_vision": structure,
#             "dom_technical": technical_elements
#         }

#         # Lưu ảnh và dữ liệu
#         await self.save_and_compress_screenshot(page, project_folder, full_path)
        
#         data_to_save = {
#             "project": project_folder,
#             "module": module_name,
#             "form": full_path,
#             "url": page.url,
#             "metadata": full_metadata,
#             "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
        
#         self._save_step(project_folder, full_path, data_to_save)
#         return full_path, data_to_save
    

#     async def _dissect_form_elements(self, page):
#         return await page.evaluate('''() => {
#             const elements = Array.from(document.querySelectorAll('input, select, textarea, button'));
#             return elements.map(el => ({
#                 tag: el.tagName,
#                 id: el.id,
#                 name: el.name,
#                 type: el.type,
#                 placeholder: el.placeholder || '',
#                 label: el.labels ? el.labels[0].innerText : (el.getAttribute('aria-label') || ''),
#                 value: el.value || ''
#             }));
#         }''')
    

    
#     # --- Các hàm bổ trợ sidebar giữ nguyên nhưng dùng await cho query ---
#     async def _expand_sidebar(self, page):
#         print("📂 [DEBUG] Đang rà soát các danh mục cha để bung Sidebar...")
#         try:
#             # Inject đồ nghề trước
#             for js_file in ["base_utils.js", "scout_engine.js"]:
#                 path = f"Bot_GPV/ai_film_factory/js/{js_file}"
#                 with open(path, 'r', encoding='utf-8') as f:
#                     await page.evaluate(f.read())

#             # Tìm các mục có khả năng là menu cha
#             menu_items = await page.locator(".MuiListItem-root, .MuiButtonBase-root, [role='button']").all()
            
#             click_count = 0
#             for item in menu_items:
#                 # Lấy thông tin label của item để print cho ông xem
#                 label = await item.evaluate("el => window.utils.getCleanText(el)")
                
#                 is_expandable = await item.evaluate('''(el) => {
#                     const hasArrow = el.querySelector('svg[data-testid="ExpandMoreIcon"], .MuiCollapse-indicator, .ant-menu-submenu-arrow');
#                     const noHref = !el.querySelector('a') || el.querySelector('a').getAttribute('href') === '#';
#                     return !!(hasArrow || noHref);
#                 }''')
                
#                 if is_expandable and label:
#                     print(f"   👉 [Click] Đang bung danh mục: '{label}'")
#                     try:
#                         await item.click()
#                         click_count += 1
#                         await page.wait_for_timeout(400) # Đợi animation MUI
#                     except: pass

#             print(f"✅ Sidebar đã kích hoạt xong ({click_count} lần click).")
#         except Exception as e:
#             print(f"⚠️ Lỗi khi bung Sidebar: {e}")


#     # --- 2. NÂNG CẤP: LẤY LINK SIDEBAR (Không bỏ sót) ---
#     async def _get_sidebar_links(self, page):
#         """
#         PHIÊN BẢN VÉT CẠN 3.0: 
#         Truy quét link và tự động gán nhãn Menu Cha cho từng Menu Con.
#         """
#         print("🔍 Đang truy quét và phân loại link nghiệp vụ...")
        
#         # Đợi animation bung menu xong xuôi
#         await page.wait_for_timeout(1200)
        
#         sidebar_selector = ".MuiDrawer-root, nav, [role='navigation'], .sidebar"

#         return await page.evaluate(f'''(sel) => {{
#             const sidebar = document.querySelector(sel) || document.body;
            
#             // Lấy tất cả các item trong sidebar theo đúng thứ tự hiển thị
#             const items = Array.from(sidebar.querySelectorAll('.MuiListItem-root, .MuiListItemButton-root, li, a'));
            
#             let currentParent = "General"; // Mặc định nếu không tìm thấy cha
#             const results = [];

#             items.forEach(el => {{
#                 const isLink = el.tagName === 'A' || el.querySelector('a');
#                 const text = el.innerText.trim().split('\\n')[0];

#                 if (!isLink && text && text.length > 2) {{
#                     // Nếu là một nút/div có chữ nhưng KHÔNG phải link -> Đây là Menu Cha
#                     // Chặn các từ khóa rác
#                     if (!['đăng xuất', 'theme', 'màu', 'setting'].some(k => text.toLowerCase().includes(k))) {{
#                         currentParent = text;
#                     }}
#                 }} else if (isLink) {{
#                     const anchor = el.tagName === 'A' ? el : el.querySelector('a');
                    
#                     if (anchor && anchor.href) {{
#                         // Lấy text sạch của menu con
#                         const textEl = anchor.querySelector('.MuiListItemText-primary, span, p') || anchor;
#                         let cleanText = textEl.innerText.trim().split('\\n')[0];
                        
#                         if (!cleanText || cleanText.length < 2) {{
#                             cleanText = anchor.getAttribute('aria-label') || anchor.title || "Unnamed";
#                         }}

#                         // Chỉ lấy nếu link đang hiển thị (đã được bung)
#                         const isVisible = anchor.offsetWidth > 0 && anchor.offsetHeight > 0;

#                         if (isVisible && 
#                             !anchor.href.includes('#') && 
#                             !anchor.href.endsWith('/home') &&
#                             !anchor.href.toLowerCase().includes('logout')) {{
                            
#                             results.push({{
#                                 text: cleanText,
#                                 href: anchor.href,
#                                 parent: currentParent // Gắn thẻ cha vào đây
#                             }});
#                         }}
#                     }}
#                 }}
#             }});
            
#             // Lọc trùng cuối cùng dựa trên kết hợp Cha + Con + Link
#             return results.filter((v, i, a) => 
#                 a.findIndex(t => (t.text === v.text && t.parent === v.parent)) === i
#             );
#         }}''', sidebar_selector)

#     def _infer_form_id(self, page):
#         """
#         Hàm phụ để định danh Form, giúp AI biết đây là nghiệp vụ nào.
#         """
#         try:
#             # Lấy phần cuối của URL để làm ID (ví dụ: /danh-muc-hang-hoa -> danh-muc-hang-hoa)
#             url_part = page.url.split('/')[-1].split('?')[0] or "home"
#             # Kết hợp với tiêu đề trang để tạo ID duy nhất
#             page_title = page.title().replace(" ", "_")
#             return f"{url_part}_{page_title}"
#         except:
#             return "unknown_form"

#     async def _extract_page_structure(self, page): 
#         # Sử dụng VisionMachine để soi cấu trúc
#         print(f" 👁️ VisionMachine đang nội soi: {page.url}")
#         try:
#             # Đợi UI ổn định
#             await page.wait_for_load_state("networkidle", timeout=10000)
#             metadata = await self.vision.scout_report(page)
#             return metadata or {}
#         except:
#             return {"error": "Vision scan failed"}
        
#     async def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
#         """
#         Đào sâu và đồng bộ vào DB - Tối ưu hóa: Giảm thiểu truy vấn DB (O(1) lookup)
#         """
#         # 1. Chạy quét nội soi (Bước tốn thời gian nhất)
#         deep_data = await self.update_module_details(project_folder, module_name, module_url)
#         if not deep_data: 
#             return False

#         success_count = 0
        
#         try:
#             # 2. CHỐT CHẶN HIỆU NĂNG: Lấy toàn bộ danh sách hiện có trong DB 1 lần duy nhất
#             # Thay vì query trong vòng lặp, ta lấy ra và map thành Dictionary để tìm kiếm nhanh
#             existing_list = ctrl.get_sub_contents(project_id) or []
            
#             # Tạo bản đồ tìm kiếm nhanh: sub_title -> item_data
#             # Giúp việc kiểm tra "đã tồn tại chưa" chỉ tốn O(1) thay vì duyệt mảng O(n)
#             existing_map = {item['sub_title']: item for item in existing_list}
            
#             print(f"🔄 Đang đồng bộ {len(deep_data)} Form vào Database...")

#             # 3. Duyệt qua dữ liệu vừa quét được
#             for form_name, f_data in deep_data.items():
#                 full_title = f"{module_name}|{form_name}"
                
#                 try:
#                     # Kiểm tra nhanh trên RAM
#                     item = existing_map.get(full_title)

#                     if item:
#                         # UPDATE nếu đã tồn tại
#                         res = ctrl.update_sub_content(
#                             sub_id=item['id'], 
#                             new_url=f_data['url'], 
#                             new_metadata=f_data['metadata'], 
#                             new_status="scanned"
#                         )
#                     else:
#                         # ADD NEW nếu chưa có
#                         res = ctrl.add_sub_content(
#                             t_id=project_id,
#                             sub_title=full_title,
#                             parent_folder=project_folder, 
#                             url=f_data['url'],
#                             metadata=f_data['metadata'],
#                             status="scanned"
#                         )
                    
#                     if res: 
#                         success_count += 1
                        
#                 except Exception as e:
#                     print(f"❌ Lỗi xử lý DB cho {full_title}: {e}")
#                     continue

#         except Exception as e:
#             print(f"❌ Lỗi nghiêm trọng khi truy xuất danh sách DB: {e}")
#             return False

#         print(f"✅ Đồng bộ hoàn tất: {success_count}/{len(deep_data)} Form.")
#         return success_count > 0