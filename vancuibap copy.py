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
            return True
        except Exception as e:
            print(f"❌ Lỗi đăng nhập: {e}")
            return False

    def extract_structure(self, page, page_name):
        """Trích xuất cấu trúc với logic nhận diện nút Sửa/Xóa nâng cao"""
        print(f"  🕵️ Trích xuất: {page_name}")
        
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
            page.wait_for_selector("table", timeout=3000) # Ưu tiên chờ bảng xuất hiện
        except: pass

        structure = page.evaluate('''() => {
            const mainContent = document.querySelector('main') || document.body;

            // Hàm hỗ trợ đoán tên nút bấm dựa trên Icon hoặc Class
            const guessButtonAction = (btn) => {
                const html = btn.innerHTML.toLowerCase();
                const text = btn.innerText.toLowerCase();
                const className = btn.className.toLowerCase();
                const ariaLabel = (btn.getAttribute('aria-label') || "").toLowerCase();

                if (html.includes('edit') || ariaLabel.includes('edit') || className.includes('edit') || text.includes('sửa')) 
                    return 'Sửa (Edit)';
                if (html.includes('delete') || html.includes('trash') || ariaLabel.includes('delete') || className.includes('error') || text.includes('xóa')) 
                    return 'Xóa (Delete)';
                if (html.includes('visibility') || html.includes('eye') || text.includes('xem')) 
                    return 'Xem (View)';
                if (html.includes('print') || text.includes('in')) 
                    return 'In (Print)';
                
                return ariaLabel || text || "Hành động khác";
            };

            const getItems = (selector) => Array.from(mainContent.querySelectorAll(selector));
            
            return {
                buttons: getItems('button, [role="button"], .MuiButton-root')
                    .filter(el => el.innerText.trim().length > 0)
                    .map(el => ({ text: el.innerText.trim().split('\\n')[0], id: el.id })),

                inputs: getItems('input, textarea, select').map(el => {
                    let label = el.id ? document.querySelector(`label[for="${el.id}"]`)?.innerText : "";
                    if (!label) label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
                    return { 
                        label: (label || el.placeholder || el.name || "N/A").replace('*', '').trim(), 
                        name: el.name || el.id,
                        type: el.type 
                    };
                }),

                tables: getItems('table').map((t, i) => {
                    const headers = Array.from(t.querySelectorAll('thead th')).map(th => th.innerText.trim());
                    
                    // Phân tích dòng đầu tiên để tìm các nút thao tác
                    const firstRow = t.querySelector('tbody tr');
                    let row_actions = [];

                    if (firstRow) {
                        const cells = Array.from(firstRow.querySelectorAll('td'));
                        cells.forEach((cell, colIndex) => {
                            const btns = Array.from(cell.querySelectorAll('button, a, [role="button"]'));
                            if (btns.length > 0) {
                                row_actions.push({
                                    column_name: headers[colIndex] || `Cột ${colIndex + 1}`,
                                    column_index: colIndex,
                                    actions: btns.map(btn => guessButtonAction(btn))
                                });
                            }
                        });
                    }

                    return {
                        index: i,
                        columns: headers,
                        row_actions: row_actions
                    };
                })
            };
        }''')

        self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
        self.save_to_file()

    def expand_and_get_submenus(self, page):
        """Mở rộng Sidebar để thấy menu con"""
        expandable = page.query_selector_all(".MuiListItemButton-root:not(a), .minimal__nav__item__root:not(a)")
        for item in expandable:
            try:
                if item.get_attribute("aria-expanded") != "true":
                    item.click()
                    page.wait_for_timeout(300)
            except: continue
        return page.evaluate('''() => {
            return Array.from(document.querySelectorAll('nav a, .MuiCollapse-root a'))
                .filter(a => a.innerText.trim().length > 1 && a.href.startsWith('http'))
                .map(a => ({ text: a.innerText.split('\\n')[0].trim(), href: a.href }));
        }''')

    def scan_app(self, page, app):
        print(f"\n🚀 PHÂN HỆ: {app['text']}")
        try:
            page.goto(app['href'], wait_until="domcontentloaded")
            self.extract_structure(page, f"App_{app['text']}")
            
            sub_links = self.expand_and_get_submenus(page)
            unique_links = {link['href']: link['text'] for link in sub_links}

            for href, text in list(unique_links.items())[:20]:
                if href.strip('/') == app['href'].strip('/'): continue
                print(f"    ∟ Chi tiết: {text}")
                try:
                    page.goto(href, wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(1000)
                    self.extract_structure(page, f"{app['text']}_{text}")
                except: pass
        except Exception as e:
            print(f"❌ Lỗi: {e}")

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            if self.login(page):
                page.wait_for_selector("a[href*='/dashboard'], a[href*='/trading']", timeout=10000)
                apps = page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .filter(a => a.href.includes('/dashboard') || a.href.includes('/trading'))
                        .map(a => ({ text: a.innerText.trim().split('\\n')[0], href: a.href }));
                }''')
                for app in apps:
                    if any(x in app['text'] for x in ["Mua bán", "Đăng xuất"]): continue
                    self.scan_app(page, app)
            browser.close()
            print(f"\n🏁 XONG! Kiểm tra row_actions trong file: {self.output_file}")

if __name__ == "__main__":
    GiaiphapvangScraper().run()