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
        """Hàm xử lý đăng nhập"""
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

    def extract_structure(self, page, page_name):
        """Trích xuất cấu trúc thông minh: Liên kết Input-Label và Cột-Nút bấm"""
        print(f"  🕵️ Trích xuất: {page_name}")
        
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
            page.wait_for_selector("main, .MuiContainer-root, #root content", timeout=5000)
        except: 
            pass

        structure = page.evaluate('''() => {
            const mainContent = document.querySelector('main') || 
                                document.querySelector('.MuiBox-root:has(table, form)') || 
                                document.body;

            const getItems = (selector) => Array.from(mainContent.querySelectorAll(selector));
            
            return {
                // 1. Trích xuất nút bấm có phân loại (Nút hành động chính)
                buttons: getItems('button, [role="button"], .MuiButton-root')
                    .filter(el => el.innerText.trim().length > 0)
                    .map(el => ({ 
                        text: el.innerText.trim().split('\\n')[0], 
                        id: el.id,
                        is_submit: el.type === 'submit' || el.classList.contains('MuiButton-containedPrimary')
                    })),

                // 2. Trích xuất Input kèm theo Label chính xác để Bot biết "nhập vào đâu"
                inputs: getItems('input, textarea, select').map(el => {
                    let label = "";
                    if (el.id) {
                        label = document.querySelector(`label[for="${el.id}"]`)?.innerText;
                    }
                    if (!label) {
                        label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText;
                    }
                    if (!label && el.placeholder) label = el.placeholder;
                    
                    return { 
                        label: (label || el.name || "N/A").replace('*', '').trim(), 
                        name: el.name || el.id,
                        type: el.type,
                        placeholder: el.placeholder || ""
                    };
                }),

                // 3. Trích xuất Bảng kèm theo Action Mapping (Bot biết nút Xóa nằm ở cột nào)
                tables: getItems('table').map((t, i) => {
                    const headers = Array.from(t.querySelectorAll('thead th')).map(th => th.innerText.trim());
                    
                    // Lấy mẫu dòng đầu tiên để phân tích các nút chức năng (Sửa, Xóa)
                    const firstRowCells = Array.from(t.querySelectorAll('tbody tr:first-child td'));
                    const actionMap = firstRowCells.map((cell, index) => {
                        const btns = Array.from(cell.querySelectorAll('button, a, [role="button"]'))
                            .map(btn => ({
                                title: btn.getAttribute('title') || btn.getAttribute('aria-label') || btn.innerText.trim(),
                                icon: btn.querySelector('svg')?.getAttribute('data-testid') || "icon"
                            }));
                        
                        return btns.length > 0 ? { column: headers[index], actions: btns } : null;
                    }).filter(item => item !== null);

                    return {
                        index: i,
                        columns: headers,
                        row_actions: actionMap // Đây là "bản đồ" để Bot biết tìm nút ở cột nào
                    };
                })
            };
        }''')

        self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
        self.save_to_file()

    def expand_and_get_submenus(self, page):
        """Mở rộng Sidebar để lấy hết menu con"""
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
                    page.goto(href, wait_until="networkidle", timeout=20000)
                    page.wait_for_timeout(1000)
                    self.extract_structure(page, f"{app['text']}_{text}")
                except: pass
        except Exception as e:
            print(f"❌ Lỗi phân hệ {app['text']}: {e}")

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
            print(f"\n🏁 XONG! File lưu tại: {self.output_file}")

if __name__ == "__main__":
    GiaiphapvangScraper().run()