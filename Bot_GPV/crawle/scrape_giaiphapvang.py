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


    # def _save_step(self, project_name, module_name, form_title, data):
    #     """
    #     Lưu dữ liệu kiến thức vào file JSON riêng biệt cho từng Form.
    #     Cấu trúc: storage/Giai_Phap_Vang/Module_Form.json
    #     """
    #     try:
    #         # 1. Lấy đường dẫn chuẩn từ Config (Config này phải nhận đủ 3 tham số)
    #         file_path = Config.get_knowledge_path(project_name, module_name, form_title)
            
    #         # 2. Đảm bảo thư mục cha tồn tại
    #         os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
    #         # 3. Ghi dữ liệu (Ghi đè để cập nhật kiến thức mới nhất)
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             json.dump(data, f, ensure_ascii=False, indent=4)
                
    #         # Log ra để Vũ theo dõi tiến độ "mổ xẻ"
    #         print(f"      💾 Đã lưu kiến thức: {os.path.basename(file_path)}")
    #         return True
    #     except Exception as e:
    #         print(f"      ❌ Lỗi khi lưu file kiến thức: {e}")
    #         return False

    def _save_step(self, project_name, module_name, form_title, data):
        """
        Lưu dữ liệu kiến thức vào file JSON trong folder riêng của từng Form.
        Cấu trúc: storage/Project_Name/module_name/form_name/data.json
        """
        try:
            # 1. Tận dụng hàm slugify của Vũ trong Config để làm sạch tên folder
            # Giữ nguyên tên Project (thay khoảng trắng) theo logic cũ của Vũ
            proj_folder = project_name.replace(" ", "_")
            
            # Làm sạch tên Module và Form (ví dụ: 'Danh mục' -> 'danh_muc')
            clean_mod = Config.slugify_vietnamese(module_name)
            clean_form = Config.slugify_vietnamese(form_title)
            
            # 2. Xây dựng đường dẫn Folder: storage/Giai_Phap_Vang/danh_muc/khach_hang/
            form_dir = os.path.join(Config.BASE_STORAGE, proj_folder, clean_mod, clean_form)
            
            # Đảm bảo folder này tồn tại
            os.makedirs(form_dir, exist_ok=True)
            
            # 3. File kiến thức sẽ nằm cố định tên là data.json trong folder đó
            # Điều này giúp code render Video sau này cứ vào folder Form là thấy data.json
            file_path = os.path.join(form_dir, "data.json")
            
            # 4. Ghi dữ liệu (Ghi đè để cập nhật kiến thức mới nhất)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            # Log đường dẫn tương đối để Vũ dễ debug
            rel_path = os.path.relpath(file_path, Config.BASE_STORAGE)
            print(f"      💾 Đã lưu tri thức vào: {rel_path}")
            
            return True
        except Exception as e:
            print(f"      ❌ Lỗi khi thực hiện _save_step: {e}")
            return False
    

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
    

    def update_module_details(self, project_name, module_name, module_url):
        """Logic điều hướng để vét cạn các nút động"""
        results = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=500) 
            page = browser.new_page()
            
            if self.login(page):
                try:
                    page.goto(module_url, wait_until="networkidle")
                    self._expand_sidebar(page)
                    sub_links = self._get_sidebar_links(page)
                    
                    for link in sub_links:
                        if link['href'].strip('/') == module_url.strip('/'): continue
                        
                        print(f"🔍 Đang mổ xẻ: {link['text']}")
                        page.goto(link['href'], wait_until="networkidle")
                        
                        # Bước 1: Quét bề nổi (Trang danh sách)
                        structure = self._extract_page_structure(page)

                        # Bước 2: Bấm "Thêm mới" để vét trường ẩn
                        try:
                            add_btn = page.get_by_role("button").filter(has_text=re.compile(r"Tạo mới|Thêm", re.I)).first
                            if add_btn.is_visible():
                                add_btn.click()
                                page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=5000)
                                
                                # Quét sâu trong Form
                                deep_struct = self._extract_page_structure(page)
                                structure['form_fields'] = deep_struct['form_fields']
                                structure['actions'] = list(set(structure['actions'] + deep_struct['actions']))
                                
                                page.keyboard.press("Escape")
                                page.wait_for_timeout(500)
                        except: pass

                        # Bước 3: Bấm "Xuất" để vét định dạng file
                        try:
                            export_btn = page.get_by_role("button").filter(has_text=re.compile(r"Xuất|Export", re.I)).first
                            if export_btn.is_visible():
                                export_btn.click()
                                page.wait_for_timeout(600)
                                export_data = self._extract_page_structure(page)
                                structure['export_formats'] = export_data['export_formats']
                                page.keyboard.press("Escape")
                        except: pass

                        # Lưu kết quả
                        data_to_save = {
                            "module": module_name,
                            "form": link['text'],
                            "structure": structure,
                            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        results[link['text']] = data_to_save
                        self._save_step(project_name, module_name, link['text'], data_to_save)
                        
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
        """
        TRÌNH VÉT ĐA TẦNG: 
        1. Vét cột bảng (Columns)
        2. Vét nút bấm (Actions) - Nhận diện cả Icon-only
        3. Vét trường nhập liệu (Form Fields) - Lấy cả Type & Placeholder
        4. Vét định dạng xuất (Export formats) từ Menu đang mở
        """
        try: 
            # Đợi các thành phần UI chính xuất hiện
            page.wait_for_selector(".MuiDataGrid-root, .MuiInputBase-input, .MuiButton-root", timeout=5000)
        except: pass
        
        return page.evaluate('''() => {
            const getCleanText = (el) => {
                if (!el) return "";
                // Xử lý đặc biệt: lấy text, bỏ icon và các ký tự bắt buộc (*)
                return el.innerText.split('\\n')[0].replace(/[\\*\\•\\○]/g, '').trim();
            };
            
            const structure = {
                columns: [],
                form_fields: [],
                actions: [],        
                row_operations: [],
                export_formats: []
            };

            // --- 1. VÉT CỘT BẢNG ---
            document.querySelectorAll('.MuiDataGrid-columnHeaderTitle').forEach(h => {
                const txt = getCleanText(h);
                if(txt && !structure.columns.includes(txt)) structure.columns.push(txt);
            });

            // --- 2. XÁC ĐỊNH VÙNG ƯU TIÊN (Ưu tiên Form/Modal đang mở trước) ---
            const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
            const searchArea = activeOverlay || document.querySelector('main') || document.body;

            // --- 3. VÉT NÚT BẤM (Hỗ trợ Icon-only) ---
            searchArea.querySelectorAll('button, a, [role="button"]').forEach(b => {
                // Không lấy nút trong Sidebar nếu đang quét vùng nội dung chính
                if (!activeOverlay && (b.closest('nav') || b.closest('.MuiDrawer-root'))) return;

                let label = getCleanText(b) || b.getAttribute('aria-label') || b.title;
                
                // Thuật toán đoán nghĩa Icon nếu nút không có chữ (dành cho nút Sửa/Xóa/In)
                if (!label || label.length <= 1) {
                    const html = b.innerHTML.toLowerCase();
                    if (html.includes('edit') || html.includes('pencil')) label = "Sửa";
                    else if (html.includes('delete') || html.includes('trash')) label = "Xóa";
                    else if (html.includes('print')) label = "In";
                    else if (html.includes('add') || html.includes('plus')) label = "Thêm";
                    else if (html.includes('save') || html.includes('check')) label = "Lưu";
                    else if (html.includes('download') || html.includes('export')) label = "Xuất";
                }

                if (label && label.length > 1 && !label.includes('Settings')) {
                    if (b.closest('.MuiDataGrid-row')) {
                        if (!structure.row_operations.includes(label)) structure.row_operations.push(label);
                    } else {
                        if (!structure.actions.includes(label)) structure.actions.push(label);
                    }
                }
            });

            // --- 4. VÉT CHI TIẾT TRƯỜNG NHẬP LIỆU ---
            searchArea.querySelectorAll('.MuiFormControl-root, .MuiTextField-root, .MuiBox-root').forEach(container => {
                let labelTxt = "";
                let inputEl = container.querySelector('input, textarea, select, [role="combobox"]');
                const labelEl = container.querySelector('label, .MuiFormLabel-root');

                if (labelEl) {
                    labelTxt = getCleanText(labelEl);
                } else if (inputEl && inputEl.placeholder) {
                    labelTxt = inputEl.placeholder;
                }

                if (labelTxt && labelTxt.length > 1) {
                    if (!structure.form_fields.find(f => f.label === labelTxt)) {
                        structure.form_fields.push({
                            label: labelTxt,
                            type: inputEl ? (inputEl.type || inputEl.getAttribute('role') || 'text') : 'text',
                            placeholder: inputEl ? (inputEl.placeholder || "") : ""
                        });
                    }
                }
            });

            // --- 5. VÉT MENU XUẤT FILE (Nếu đang bấm nút Xuất) ---
            document.querySelectorAll('.MuiMenuItem-root, [role="menuitem"]').forEach(item => {
                const itemTxt = item.innerText.trim();
                const keywords = ['Excel', 'CSV', 'PDF', 'In', 'Export', 'Tải'];
                if (keywords.some(k => itemTxt.includes(k))) {
                    if (!structure.export_formats.includes(itemTxt)) {
                        structure.export_formats.push(itemTxt);
                    }
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
    
    def sync_deep_scan(self, ctrl, project_id, project_folder, module_name, module_url):
        """
        Quy trình Đào sâu vét cạn & Đồng bộ vào DB
        """
        # 1. Chạy trực tiếp method trong cùng class
        # Lưu ý: self ở đây chính là scraper
        deep_data = self.update_module_details(project_folder, module_name, module_url)
        
        if not deep_data:
            print(f"⚠️ Không lấy được dữ liệu cho Module: {module_name}")
            return False

        # 2. Lấy danh sách sub_contents hiện có từ DB
        existing_subs = ctrl.get_sub_contents(project_id)
        
        for form_name, f_data in deep_data.items():
            # Chuẩn hóa tiêu đề để so khớp (Ví dụ: "Danh mục|Khách hàng")
            full_title = f"{module_name}|{form_name}"
            
            # Tìm xem đã tồn tại trong DB chưa
            existing_item = next((s for s in existing_subs if s['sub_title'] == full_title), None)
            
            metadata_json = f_data.get('structure', {})
            form_url = f_data.get('url', module_url) # Lấy URL cụ thể của form nếu có

            if existing_item:
                # CẬP NHẬT: Đã có ID thì chỉ update kiến thức (metadata)
                print(f"🔄 Cập nhật tri thức mới cho: {full_title}")
                
                # Update Metadata (quan trọng nhất cho AI)
                ctrl.update_sub_content_metadata(existing_item['id'], metadata_json)
                
                # Update URL hoặc thông tin phụ (nếu hàm update_sub_content hỗ trợ)
                # Vũ kiểm tra lại các tham số truyền vào hàm này của mình nhé
                ctrl.update_sub_content(existing_item['id'], new_title=full_title, new_status=form_url)
            else:
                # THÊM MỚI: Form hoàn toàn mới chưa có trong DB
                print(f"✨ Thêm mới Form vào DB: {full_title}")
                ctrl.add_sub_content(
                    t_id=project_id,
                    sub_title=full_title,
                    parent_folder=project_folder,
                    metadata=metadata_json # Lưu luôn tri thức khi thêm mới
                )
                
        return True