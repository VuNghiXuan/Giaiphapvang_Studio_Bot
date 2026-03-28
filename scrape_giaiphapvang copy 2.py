import os
import json
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

class GiaiphapvangScraper:
    def __init__(self, output_file="knowledge_source.json"):
        self.output_file = output_file
        self.knowledge_data = {}

    def save_to_file(self):
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_data, f, ensure_ascii=False, indent=4)

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

    def _get_hidden_row_actions(self, page):
        """Hàm chuyên biệt để click và quét menu 3 chấm trên dòng của DataGrid"""
        hidden_actions = []
        try:
            # Nhắm vào nút 3 chấm đầu tiên tìm thấy trong bảng
            three_dots_btn = page.query_selector(".MuiDataGrid-row [aria-label*='Thêm'], .MuiDataGrid-row button .MuiSvgIcon-root")
            if three_dots_btn:
                three_dots_btn.click()
                # Chờ menu xổ ra
                try:
                    page.wait_for_selector(".MuiMenu-list, [role='menu']:not(.MuiDataGrid-actionsCell)", timeout=1500)
                    menu_items = page.query_selector_all(".MuiMenuItem-root, [role='menuitem']")
                    for item in menu_items:
                        text = page.evaluate("el => el.innerText", item).strip()
                        if text: hidden_actions.append(text)
                except:
                    # Nếu là menu inline (không xổ popover)
                    inline_btns = three_dots_btn.query_selector_all("..//button[@aria-label]")
                    for btn in inline_btns:
                        hidden_actions.append(page.get_attribute(btn, "aria-label"))
                
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        except: pass
        return list(set(hidden_actions))

    def _get_toolbar_actions(self, page):
        """Hàm quét các nút chức năng trên đầu bảng (Xuất, Lọc, Cột...)"""
        return page.evaluate('''() => {
            const toolbar = document.querySelector('.MuiDataGrid-toolbarContainer');
            if (!toolbar) return [];
            return Array.from(toolbar.querySelectorAll('button'))
                .map(btn => btn.innerText.trim())
                .filter(txt => txt.length > 0);
        }''')

    def _scan_create_form(self, page):
        """Hàm đột kích vào Form Tạo mới để lấy danh sách Input chi tiết"""
        form_inputs = []
        try:
            # 1. Tìm nút Tạo mới (thường là nút duy nhất có text này ngoài bảng)
            create_btn = page.get_by_role("button", name="Tạo mới", exact=True)
            
            if create_btn.is_visible():
                print("     ✨ Phát hiện nút 'Tạo mới', đang thâm nhập Form...")
                create_btn.click()
                
                # 2. Chờ Form hoặc Dialog hiện lên
                page.wait_for_selector(".MuiDialog-root, .MuiDrawer-root, form", timeout=3000)
                page.wait_for_timeout(500) # Đợi hiệu ứng mở kết thúc

                # 3. Quét toàn bộ Input trong Form này
                form_inputs = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('.MuiDialog-root input, .MuiDialog-root textarea, form input, form textarea'))
                        .filter(el => el.type !== 'checkbox' && el.type !== 'hidden')
                        .map(el => {
                            let label = "";
                            if (el.id) label = document.querySelector(`label[for="${el.id}"]`)?.innerText;
                            if (!label) label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
                            if (!label) label = el.placeholder || el.name;
                            return { 
                                label: (label || "N/A").replace('*', '').trim(), 
                                name: el.name || el.id
                            };
                        });
                }''')

                print(f"     📝 Đã lấy được {len(form_inputs)} trường nhập liệu từ Form.")

                # 4. Thoát khỏi Form để không làm hỏng luồng quét tiếp theo
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as e:
            print(f"     ⚠️ Không thể quét Form Tạo mới: {e}")
            # Đảm bảo thoát Form nếu có lỗi
            page.keyboard.press("Escape")
            
        return form_inputs

    
    def extract_structure(self, page, page_name):
        print(f"  🕵️ Đang trích xuất: {page_name}")
        
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
            page.wait_for_timeout(1000) 
        except: pass

        row_actions = self._get_hidden_row_actions(page)
        toolbar_actions = self._get_toolbar_actions(page)

        structure = page.evaluate('''() => {
            const getSafeAttr = (el, attr) => (el.getAttribute(attr) || "").trim();
            
            // 1. Định nghĩa "Blacklist" cho các nút điều hướng/giao diện
            const navKeywords = [
                'Thông tin công ty', 'Nhập hàng', 'Giá vốn', 'Kho & Quầy', 
                'Danh mục', 'Hệ thống', 'Cấu hình', 'Báo cáo', 'Quản lý'
            ];

            const allButtons = Array.from(document.querySelectorAll('button, [role="button"], .MuiButton-root'));

            // 2. Tách Navigation/Tabs (Nút để di chuyển giữa các phân hệ)
            const navElements = allButtons.filter(el => {
                const txt = el.innerText.trim();
                return el.closest('.MuiTabs-root') || 
                       el.closest('.MuiList-root') || 
                       navKeywords.some(key => txt.includes(key));
            }).map(el => el.innerText.trim().split('\\n')[0]);

            // 3. Tách Page Actions (Chỉ giữ lại nút chức năng: Tạo mới, Lưu, Hủy, In...)
            const pageActions = allButtons.filter(el => {
                const txt = el.innerText.trim();
                const isInsideGrid = el.closest('.MuiDataGrid-root');
                // Nút được giữ lại: Không nằm trong bảng và không thuộc blacklist điều hướng
                const isNav = el.closest('.MuiTabs-root') || 
                              el.closest('.MuiList-root') || 
                              navKeywords.some(key => txt.includes(key));
                
                return txt.length > 1 && !isInsideGrid && !isNav;
            }).map(el => ({ text: el.innerText.trim().split('\\n')[0] }));

            // 4. Quét Bảng (Giữ nguyên)
            const tables = Array.from(document.querySelectorAll('.MuiDataGrid-root, table')).map(grid => ({
                type: grid.tagName === 'TABLE' ? 'Table' : 'DataGrid',
                columns: Array.from(grid.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th'))
                              .map(h => h.innerText.trim())
                              .filter(h => h.length > 0)
            }));

            return {
                page_actions: pageActions, 
                navigation_tabs: [...new Set(navElements)],
                tables: tables,
                inputs: Array.from(document.querySelectorAll('input, textarea, select'))
                    .filter(el => {
                        const isPagination = el.closest('.MuiTablePagination-root');
                        const isSearchInsideGrid = el.closest('.MuiDataGrid-toolbarContainer');
                        return el.type !== 'checkbox' && !isPagination && !isSearchInsideGrid;
                    })
                    .map(el => {
                        let label = "";
                        if (el.id) label = document.querySelector(`label[for="${el.id}"]`)?.innerText;
                        if (!label) label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
                        if (!label) label = el.placeholder || el.name;
                        return { 
                            label: (label || "N/A").replace('*', '').trim(), 
                            name: el.name || el.id
                        };
                    })
            };
        }''')

        # Gắn kết quả bổ sung
        structure['row_actions_hidden'] = row_actions
        if structure['tables'] and toolbar_actions:
            structure['tables'][0]['toolbar_actions'] = toolbar_actions

        self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
        self.save_to_file()
        print(f"     ✅ Xong: {len(structure['page_actions'])} nút lệnh, {len(structure['navigation_tabs'])} mục điều hướng.")

    def expand_and_get_submenus(self, page):
        print("  🔍 Đang mở rộng Sidebar...")
        expandable_selectors = [".MuiListItemButton-root:not(a)", ".minimal__nav__item__root:not(a)"]
        for selector in expandable_selectors:
            try:
                for item in page.query_selector_all(selector):
                    if item.get_attribute("aria-expanded") != "true":
                        item.click()
                        page.wait_for_timeout(400)
            except: continue

        return page.evaluate('''() => {
            return Array.from(document.querySelectorAll('nav a, .MuiCollapse-root a, [class*="sidebar"] a'))
                .filter(a => a.innerText.trim().length > 1 && a.href.startsWith('http'))
                .map(a => ({ text: a.innerText.split('\\n')[0].trim(), href: a.href }));
        }''')

    def scan_app(self, page, app):
        print(f"\n🚀 PHÂN HỆ: {app['text']}")
        try:
            page.goto(app['href'], wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            self.extract_structure(page, f"App_{app['text']}")
            
            sub_links = self.expand_and_get_submenus(page)
            unique_links = {link['href']: link['text'] for link in sub_links}

            for href, text in list(unique_links.items()):
                if href.strip('/') == app['href'].strip('/'): continue
                print(f"    ∟ Chi tiết: {text}")
                try:
                    page.goto(href, wait_until="networkidle", timeout=20000)
                    page.wait_for_timeout(1500) # Chờ thêm cho chắc
                    self.extract_structure(page, f"{app['text']}_{text}")
                except: pass
        except Exception as e:
            print(f"❌ Lỗi phân hệ {app['text']}: {e}")

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            if self.login(page):
                # Chờ màn hình dashboard load
                page.wait_for_selector("a", timeout=10000)
                
                apps = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .filter(a => {
                            const href = a.href.toLowerCase();
                            return (href.includes('/dashboard') || href.includes('/trading')) && a.innerText.trim().length > 2;
                        })
                        .map(a => ({ text: a.innerText.trim().split('\\n')[0], href: a.href }));
                }''')

                # Loại trùng app
                unique_apps = {a['href']: a['text'] for a in apps}
                
                for href, text in unique_apps.items():
                    if any(x in text for x in ["Mua bán", "Đăng xuất", "Tin tức"]): continue
                    self.scan_app(page, {'text': text, 'href': href})

            browser.close()
            print(f"\n🏁 XONG! File lưu tại: {self.output_file}")

if __name__ == "__main__":
    GiaiphapvangScraper().run()