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
        """Trích xuất chi tiết: Input, Button và đặc biệt là các Icon Action (Sửa/Xóa)"""
        print(f"  🕵️ Trích xuất: {page_name}")
        try:
            page.wait_for_selector("table, form, main", timeout=5000)
        except: pass

        structure = page.evaluate('''() => {
            const mainContent = document.querySelector('main') || document.body;
            
            // Hàm đoán hành động của nút dựa trên Icon hoặc Class
            const guessAction = (btn) => {
                const h = btn.innerHTML.toLowerCase();
                const t = btn.innerText.toLowerCase().trim();
                const a = (btn.getAttribute('aria-label') || btn.getAttribute('title') || "").toLowerCase();
                const c = btn.className.toLowerCase();
                
                if (t) return t; // Nếu có chữ thì lấy chữ luôn
                
                // Nếu không có chữ, soi Icon/Attribute
                if (h.includes('edit') || a.includes('edit') || a.includes('sửa') || c.includes('edit')) return 'Sửa (Edit)';
                if (h.includes('delete') || h.includes('trash') || a.includes('xóa') || c.includes('delete')) return 'Xóa (Delete)';
                if (h.includes('print') || a.includes('in')) return 'In (Print)';
                if (h.includes('visibility') || a.includes('xem')) return 'Xem (View)';
                if (h.includes('download') || a.includes('tải')) return 'Tải về';
                
                return a || "Nút chức năng"; 
            };

            const getItems = (sel) => Array.from(mainContent.querySelectorAll(sel));

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
                    const rows = Array.from(t.querySelectorAll('tbody tr')).slice(0, 1); // Chỉ soi dòng đầu để lấy cấu trúc
                    
                    let row_actions = [];
                    rows.forEach((row) => {
                        Array.from(row.querySelectorAll('td')).forEach((cell, idx) => {
                            // Tìm tất cả các thẻ có khả năng là nút bấm trong cell (button, a, svg bọc trong div)
                            const btns = Array.from(cell.querySelectorAll('button, a, [role="button"], .MuiIconButton-root'));
                            if (btns.length > 0) {
                                row_actions.push({
                                    column: headers[idx] || `Cột ${idx+1}`,
                                    actions: btns.map(btn => guessAction(btn))
                                });
                            }
                        });
                    });
                    return { index: i, columns: headers, row_actions };
                })
            };
        }''')
        self.knowledge_data[page_name] = {"url": page.url, "structure": structure}
        self.save_to_file()

    def expand_sidebar(self, page):
        """Mở tất cả các mục menu đóng trên Sidebar"""
        items = page.query_selector_all(".MuiListItemButton-root:not(a), .minimal__nav__item__root:not(a)")
        for item in items:
            try:
                if item.get_attribute("aria-expanded") != "true":
                    item.click()
                    page.wait_for_timeout(300)
            except: continue

    def scan_app(self, page, app):
        # Danh sách các trang bạn muốn bỏ qua (đang phát triển)
        skip_list = ["Mua bán", "Tin tức", "Hướng dẫn sử dụng", "Điều khoản sử dụng", "Chính sách bảo mật"]
        
        if any(x in app['text'] for x in skip_list):
            print(f"⏩ BỎ QUA (Đang phát triển/Không cần thiết): {app['text']}")
            return

        print(f"\n🚀 ĐANG QUÉT PHÂN HỆ: {app['text']}")
        try:
            # Thay đổi networkidle thành domcontentloaded để tránh Timeout
            response = page.goto(app['href'], wait_until="domcontentloaded", timeout=20000)
            
            # Kiểm tra nếu trang lỗi 404 hoặc không phản hồi
            if not response or response.status >= 400:
                print(f"⚠️ Trang {app['text']} trả về lỗi {response.status if response else 'No Response'}. Bỏ qua.")
                return

            # Đợi thêm 1 chút cho các component Mui hiện ra
            page.wait_for_timeout(2000)
            
            # Kiểm tra xem trang có nội dung không (tránh trang trắng)
            is_empty = page.evaluate('() => document.body.innerText.length < 100')
            if is_empty:
                print(f"⚠️ Trang {app['text']} có vẻ trống. Bỏ qua.")
                return

            self.extract_structure(page, f"Trang_Chu_{app['text']}")
            
            self.expand_sidebar(page)
            
            # Lấy link sidebar
            links = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('nav a, .MuiCollapse-root a, [class*="sidebar"] a'))
                    .filter(a => a.innerText.trim().length > 1 && a.href.startsWith('http'))
                    .map(a => ({ text: a.innerText.split('\\n')[0].trim(), href: a.href }));
            }''')

            unique_links = {l['href']: l['text'] for l in links}
            for href, text in unique_links.items():
                if href.strip('/') == app['href'].strip('/'): continue
                
                print(f"    ∟ Đang quét: {text}")
                try:
                    # Trang con cũng dùng domcontentloaded cho nhanh
                    page.goto(href, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(1500) # Chờ render
                    self.extract_structure(page, f"{app['text']}_{text}")
                except Exception as e:
                    print(f"    ⚠️ Lỗi nhẹ tại {text}, tiếp tục trang sau...")
        except Exception as e:
            print(f"❌ Lỗi nặng tại phân hệ {app['text']}: {e}")

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            if self.login(page):
                print("🔍 Đang tìm kiếm các phân hệ trên màn hình chính...")
                # Chờ một lúc để các Icon phân hệ kịp load
                page.wait_for_timeout(3000) 

                # Logic lấy App thoáng hơn: Lấy các link có icon hoặc nằm trong grid chính
                apps = page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .filter(a => {
                            const href = a.getAttribute('href') || "";
                            // Loại bỏ các link không phải phân hệ (login, logout, trang chủ rỗng)
                            const isNotGarbage = !href.includes('auth') && !href.includes('sign-out') && href.length > 1;
                            // Thường các icon phân hệ sẽ có text bên trong hoặc nằm trong thẻ div/svg
                            const hasText = a.innerText.trim().length > 0;
                            return isNotGarbage && hasText;
                        })
                        .map(a => ({ 
                            text: a.innerText.trim().split('\\n')[0], 
                            href: a.href 
                        }));
                }''')

                # Lọc trùng và chuẩn hóa
                unique_apps = {}
                for a in apps:
                    # Chỉ lấy các app có tên rõ ràng và không phải link hướng dẫn/hỗ trợ
                    if a['text'] and len(a['text']) > 2 and a['href'] not in unique_apps:
                        unique_apps[a['href']] = a['text']
                
                print(f"📊 Tìm thấy {len(unique_apps)} phân hệ: {list(unique_apps.values())}")

                if not unique_apps:
                    print("⚠️ Vẫn không tìm thấy phân hệ nào. Đang thử quét sidebar trực tiếp...")
                    # Nếu màn hình Home không có, thử lấy từ Sidebar đang hiển thị
                    self.scan_app(page, {'text': 'Trang_Chu', 'href': page.url})
                else:
                    for href, text in unique_apps.items():
                        self.scan_app(page, {'text': text, 'href': href})

            browser.close()
            print(f"\n🏁 HOÀN TẤT!")

if __name__ == "__main__":
    GiaiphapvangScraper().run()