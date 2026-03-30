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
        if not os.path.exists(Config.BASE_STORAGE):
            os.makedirs(Config.BASE_STORAGE, exist_ok=True)
        print("🚀 Scraper sẵn sàng: Chế độ đào sâu vét cạn (Deep Scan).")

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
    

    # def update_module_details(self, project_name, module_name, module_url):
    #     """Logic điều hướng để vét cạn các nút động và lấy URL thực tế"""
    #     results = {}
    #     with sync_playwright() as p:
    #         # headless=False để Vũ quan sát quá trình "mổ xẻ"
    #         browser = p.chromium.launch(headless=False, slow_mo=500) 
    #         context = browser.new_context()
    #         page = context.new_page()
            
    #         if self.login(page):
    #             try:
    #                 print(f"🚚 Đang truy cập Module: {module_url}")
    #                 page.goto(module_url, wait_until="networkidle")
    #                 self._expand_sidebar(page)
    #                 sub_links = self._get_sidebar_links(page)
                    
    #                 if not sub_links:
    #                     print(f"⚠️ Không tìm thấy link con nào trong Sidebar của {module_name}")
                    
    #                 for link in sub_links:
    #                     # Bỏ qua nếu là link trang chủ của module hoặc link rỗng
    #                     if not link['href'] or link['href'].strip('/') == module_url.strip('/'): 
    #                         continue
                        
    #                     print(f"🔍 [MỔ XẺ] : {link['text']}")
    #                     try:
    #                         # Di chuyển tới trang con
    #                         page.goto(link['href'], wait_until="networkidle", timeout=60000)
    #                         page.wait_for_timeout(1000) # Chờ một chút cho JS render xong hoàn toàn
                            
    #                         # QUAN TRỌNG: Lấy URL thực tế sau khi trang đã load (đề phòng redirect)
    #                         actual_form_url = page.url 
    #                         print(f"   📍 Link thực tế: {actual_form_url}")

    #                         # Bước 1: Quét bề nổi (Trang danh sách/Table)
    #                         structure = self._extract_page_structure(page)

    #                         # Bước 2: Bấm "Thêm mới" để vét các trường trong Form ẩn
    #                         try:
    #                             # Tìm nút Thêm/Tạo mới (Case insensitive)
    #                             add_btn = page.get_by_role("button").filter(has_text=re.compile(r"Tạo mới|Thêm|Thêm mới", re.I)).first
    #                             if add_btn.is_visible():
    #                                 print(f"   ➕ Đang mở Form 'Thêm mới' để quét trường dữ liệu...")
    #                                 add_btn.click()
    #                                 # Chờ Dialog hoặc Form xuất hiện
    #                                 page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=5000)
    #                                 page.wait_for_timeout(500)
                                    
    #                                 # Quét sâu trong Form
    #                                 deep_struct = self._extract_page_structure(page)
    #                                 structure['form_fields'] = deep_struct['form_fields']
                                    
    #                                 # Hợp nhất Actions (nút bấm trong form như Lưu, Hủy)
    #                                 existing_action_labels = [a.get('label') if isinstance(a, dict) else a for a in structure['actions']]
    #                                 for action in deep_struct['actions']:
    #                                     label = action.get('label') if isinstance(action, dict) else action
    #                                     if label not in existing_action_labels:
    #                                         structure['actions'].append(action)
                                    
    #                                 # Đóng Form để về lại trang chính
    #                                 page.keyboard.press("Escape")
    #                                 page.wait_for_timeout(500)
    #                         except Exception as e:
    #                             print(f"   ℹ️ Không có form 'Thêm mới' hoặc lỗi quét form: {e}")

    #                         # Bước 3: Bấm "Xuất" để vét định dạng file (nếu có)
    #                         try:
    #                             export_btn = page.get_by_role("button").filter(has_text=re.compile(r"Xuất|Export", re.I)).first
    #                             if export_btn.is_visible():
    #                                 export_btn.click()
    #                                 page.wait_for_timeout(800)
    #                                 export_data = self._extract_page_structure(page)
    #                                 structure['export_formats'] = export_data['export_formats']
    #                                 page.keyboard.press("Escape")
    #                         except: pass

    #                         # ĐÓNG GÓI DỮ LIỆU: Đảm bảo url không bao giờ là None
    #                         data_to_save = {
    #                             "module": module_name,
    #                             "form": link['text'],
    #                             "url": actual_form_url if actual_form_url else link['href'],
    #                             "structure": structure,
    #                             "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    #                         }
                            
    #                         # Cực kỳ quan trọng: Gán vào dictionary kết quả để trả về cho sync_deep_scan
    #                         results[link['text']] = data_to_save
                            
    #                         # Lưu file vật lý (Backup tri thức)
    #                         self._save_step(project_name, module_name, link['text'], data_to_save)
    #                         print(f"   ✅ Hoàn thành mổ xẻ: {link['text']}")

    #                     except Exception as inner_e:
    #                         print(f"   ❌ Lỗi khi quét trang con {link['text']}: {inner_e}")
    #                         continue
                            
    #             except Exception as e:
    #                 print(f"❌ Lỗi nghiêm trọng tại Module {module_name}: {e}")
            
    #         browser.close()
        
    #     # Trả về kết quả chứa đầy đủ URL và Metadata
    #     return results

    def update_module_details(self, project_name, module_name, module_url):
        """
        Logic điều hướng để vét cạn các nút động và lấy URL thực tế.
        Đã gia cố: Chống crash khi vênh tham số và tự phục hồi khi lỗi driver trang con.
        """
        results = {}
        with sync_playwright() as p:
            # Chạy có giao diện để dễ quan sát, slow_mo giúp ổn định tương tác
            browser = p.chromium.launch(headless=False, slow_mo=500) 
            context = browser.new_context()
            page = context.new_page()
            
            if self.login(page):
                try:
                    print(f"[🎥Bot phân cảnh] Đang truy cập Module: {module_url}")
                    # Tăng timeout và wait_until để tránh lỗi Connection Closed khi mạng chậm
                    page.goto(module_url, wait_until="networkidle", timeout=60000)
                    self._expand_sidebar(page)
                    sub_links = self._get_sidebar_links(page)
                    
                    if not sub_links:
                        print(f"⚠️ Không tìm thấy link con nào trong Sidebar của {module_name}")
                    
                    for link in sub_links:
                        # Bỏ qua nếu là link trang chủ của module hoặc link rỗng
                        if not link['href'] or link['href'].strip('/') == module_url.strip('/'): 
                            continue
                        
                        print(f"🔍 [MỔ XẺ] : {link['text']}")
                        try:
                            # Di chuyển tới trang con với timeout an toàn
                            page.goto(link['href'], wait_until="domcontentloaded", timeout=60000)
                            # Chờ thêm một chút cho các framework như React/MUI render hết DOM
                            page.wait_for_timeout(1500) 
                            
                            # Lấy URL thực tế sau khi trang đã load (đề phòng redirect bảo mật)
                            actual_form_url = page.url 
                            print(f"   📍 Link thực tế: {actual_form_url}")

                            # Bước 1: Quét bề nổi (Trang danh sách/Table)
                            structure = self._extract_page_structure(page)

                            # Bước 2: Bấm "Thêm mới" để vét các trường trong Form ẩn
                            try:
                                # Tìm nút Thêm/Tạo mới bằng Regex (không phân biệt hoa thường)
                                add_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Tạo mới|Thêm|Thêm mới", re.I)
                                ).first
                                
                                if add_btn.is_visible(timeout=3000):
                                    print(f"   ➕ Đang mở Form 'Thêm mới' để quét trường dữ liệu...")
                                    add_btn.click()
                                    # Chờ Dialog hoặc Form xuất hiện (phổ biến trong hệ thống của Vũ)
                                    page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=5000)
                                    page.wait_for_timeout(800)
                                    
                                    # Quét sâu trong Form để lấy các input fields
                                    deep_struct = self._extract_page_structure(page)
                                    structure['form_fields'] = deep_struct['form_fields']
                                    
                                    # Hợp nhất các nút bấm (Actions) trong form vào danh sách chung
                                    existing_labels = [a.get('label') if isinstance(a, dict) else a for a in structure['actions']]
                                    for action in deep_struct['actions']:
                                        label = action.get('label') if isinstance(action, dict) else action
                                        if label not in existing_labels:
                                            structure['actions'].append(action)
                                    
                                    # Đóng Form bằng phím Escape để tránh kẹt giao diện cho trang sau
                                    page.keyboard.press("Escape")
                                    page.wait_for_timeout(500)
                            except Exception as form_e:
                                print(f"   ℹ️ Không có form 'Thêm mới' hoặc lỗi quét form: {form_e}")

                            # Bước 3: Bấm "Xuất" để vét định dạng file (nếu có nút Export)
                            try:
                                export_btn = page.get_by_role("button").filter(
                                    has_text=re.compile(r"Xuất|Export", re.I)
                                ).first
                                if export_btn.is_visible(timeout=2000):
                                    export_btn.click()
                                    page.wait_for_timeout(800)
                                    export_data = self._extract_page_structure(page)
                                    structure['export_formats'] = export_data['export_formats']
                                    page.keyboard.press("Escape")
                            except: 
                                pass

                            # ĐÓNG GÓI DỮ LIỆU
                            data_to_save = {
                                "module": module_name,
                                "form": link['text'],
                                "url": actual_form_url,
                                "structure": structure,
                                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            results[link['text']] = data_to_save
                            
                            # LƯU FILE VẬT LÝ: Đã fix vênh tham số nhờ *args ở hàm _save_step
                            # Lưu ý: Truyền đúng cấu trúc folder để StudioController dễ đọc
                            self._save_step(project_name, module_name, data_to_save, link['text'])
                            print(f"   ✅ Hoàn thành mổ xẻ: {link['text']}")

                        except Exception as inner_e:
                            # Nếu lỗi ở 1 trang con (ví dụ: Timeout), log lại và nhảy sang trang con tiếp theo
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

    def _extract_page_structure(self, page):
        """
        TRÌNH VÉT ĐA TẦNG: 
        Trích xuất Metadata chi tiết để làm 'não' cho AI điều khiển Browser sau này.
        """
        try: 
            # Chờ một trong các thành phần chính xuất hiện (Bảng, Input, hoặc Nút)
            page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiButton-root", timeout=5000)
        except: 
            pass
        
        return page.evaluate('''() => {
            const getCleanText = (el) => {
                if (!el) return "";
                // Lấy dòng đầu tiên, xóa các ký tự đặc biệt thường gặp ở label/button (dấu sao bắt buộc, icon...)
                return el.innerText.split('\\n')[0].replace(/[\\*\\•\\○]/g, '').trim();
            };

            const getSelector = (el) => {
                // 1. Ưu tiên Name vì Name trong Form thường cố định theo Backend
                if (el.name) return `[name="${el.name}"]`;
                
                // 2. Ưu tiên Aria-label nếu có (thường dùng cho các nút Icon)
                const ariaLabel = el.getAttribute('aria-label');
                if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
                
                // 3. Nếu có ID và không phải ID tự sinh của MUI (MUI sinh ID kiểu mui-1, mui-2...)
                if (el.id && !el.id.startsWith('mui-')) return `#${el.id}`;
                
                return ""; 
            };
            
            const structure = {
                columns: [],        // Các cột của bảng
                form_fields: [],     // Các trường nhập liệu
                actions: [],         // Các nút chức năng (Thêm, Xuất, Lưu...)
                row_operations: [],  // Các nút trên từng dòng (Sửa, Xóa...)
                export_formats: []   // Các định dạng file khi bấm nút Xuất
            };

            // --- 1. VÉT CỘT BẢNG (Dữ liệu hiển thị) ---
            document.querySelectorAll('.MuiDataGrid-columnHeaderTitle').forEach(h => {
                const txt = getCleanText(h);
                if(txt && !structure.columns.includes(txt)) structure.columns.push(txt);
            });

            // XÁC ĐỊNH KHU VỰC ƯU TIÊN: Nếu có Popup (Dialog/Drawer) đang mở thì chỉ vét trong đó
            const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
            const searchArea = activeOverlay || document.querySelector('main') || document.body;

            // --- 2. VÉT NÚT BẤM (Kèm Logic đoán Icon cho AI) ---
            searchArea.querySelectorAll('button, a, [role="button"]').forEach(b => {
                // Nếu không có popup, bỏ qua các nút thuộc sidebar/nav để tránh rác menu chính
                if (!activeOverlay && (b.closest('nav') || b.closest('[class*="sidebar"]'))) return;

                let label = getCleanText(b) || b.getAttribute('aria-label') || b.title;
                
                // Logic đoán nút dựa trên nội dung HTML (Icon) hoặc Class nếu Label trống
                if (!label || label.length <= 1) {
                    const html = b.innerHTML.toLowerCase();
                    const cls = b.className.toLowerCase();
                    if (html.includes('edit') || cls.includes('edit')) label = "Sửa";
                    else if (html.includes('delete') || html.includes('trash') || cls.includes('delete')) label = "Xóa";
                    else if (html.includes('save') || cls.includes('save')) label = "Lưu";
                    else if (html.includes('add') || html.includes('plus')) label = "Thêm";
                    else if (html.includes('download') || html.includes('export')) label = "Xuất file";
                    else if (html.includes('print')) label = "In";
                    else if (html.includes('close') || html.includes('cancel')) label = "Đóng";
                }

                if (label && label.length > 1) {
                    const btnData = {
                        label: label,
                        selector: getSelector(b) || `button:has-text("${label}")`,
                        is_primary: b.classList.contains('MuiButton-containedPrimary') || b.classList.contains('MuiButton-contained')
                    };

                    // Phân loại: Nút thao tác trên từng dòng bảng hay nút chức năng trang
                    if (b.closest('.MuiDataGrid-row')) {
                        if (!structure.row_operations.find(o => o.label === label)) 
                            structure.row_operations.push(btnData);
                    } else {
                        if (!structure.actions.find(a => a.label === label)) 
                            structure.actions.push(btnData);
                    }
                }
            });

            // --- 3. VÉT TRƯỜNG NHẬP LIỆU (Input, Select, AutoComplete) ---
            searchArea.querySelectorAll('.MuiFormControl-root, .MuiTextField-root, .MuiInputBase-root').forEach(container => {
                let inputEl = container.querySelector('input, textarea, select, [role="combobox"]');
                if (!inputEl) return;

                const labelEl = container.querySelector('label, .MuiFormLabel-root');
                let labelTxt = labelEl ? getCleanText(labelEl) : (inputEl.placeholder || inputEl.getAttribute('aria-label') || "");

                if (labelTxt && labelTxt.length > 1) {
                    if (!structure.form_fields.find(f => f.label === labelTxt)) {
                        structure.form_fields.push({
                            label: labelTxt,
                            type: inputEl.type || inputEl.getAttribute('role') || 'text',
                            selector: getSelector(inputEl) || `input[placeholder*="${labelTxt}"]`,
                            required: container.innerHTML.includes('Mui-required') || inputEl.required || false,
                            placeholder: inputEl.placeholder || ""
                        });
                    }
                }
            });

            // --- 4. VÉT ĐỊNH DẠNG XUẤT FILE (Chỉ vét khi menu Export đang bật) ---
            document.querySelectorAll('.MuiMenuItem-root, [role="menuitem"]').forEach(item => {
                const itemTxt = item.innerText.trim();
                const formats = ['Excel', 'CSV', 'PDF', 'In ấn', 'Download'];
                if (formats.some(k => itemTxt.includes(k))) {
                    if (!structure.export_formats.find(e => e.label === itemTxt)) {
                        structure.export_formats.push({
                            label: itemTxt,
                            selector: `text="${itemTxt}"`
                        });
                    }
                }
            });

            return structure;
        }''')
    
    
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