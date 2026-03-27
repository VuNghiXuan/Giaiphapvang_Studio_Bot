import asyncio
import os
import json
import traceback
import sys
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

class StructureExtractor:
    def __init__(self, output_file="knowledge_source.json"):
        self.output_file = output_file
        # Thống nhất dùng 1 biến kết quả duy nhất
        self.results = {}
        # Danh sách các từ khóa nút cần "đào sâu"
        self.action_keywords = ["Thêm", "Sửa", "Lập phiếu", "Chi tiết", "Cấu hình"]
        self.exclude_keywords = ["Đóng", "Hủy", "X", "Close", "Cancel"]

    def save_to_json(self):
        """Hàm ghi dữ liệu chuẩn xác vào file JSON"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=4)
            print(f"\n✅ [KẾT THÚC] Đã lưu tri thức vào: {self.output_file}")
        except Exception as e:
            print(f"❌ Lỗi khi ghi file: {e}")

    async def extract_page_content(self, page):
        """Trích xuất Buttons, Inputs, Tables trong trang hiện tại"""
        return await page.evaluate('''() => {
            const data = { buttons: [], inputs: [], tables: [] };
            
            // Lấy nút (Dùng .push thay vì .append của Python)
            document.querySelectorAll('main button, .content button, .MuiContainer-root button').forEach(btn => {
                const txt = btn.innerText.trim().split('\\n')[0];
                if (txt && txt.length < 30) data.buttons.push(txt);
            });

            // Lấy nhãn Input
            document.querySelectorAll('label, .MuiFormLabel-root').forEach(lb => {
                const txt = lb.innerText.trim();
                if (txt) data.inputs.push(txt);
            });

            // Lấy tiêu đề bảng
            document.querySelectorAll('th').forEach(th => {
                const txt = th.innerText.trim();
                if (txt && !data.tables.includes(txt)) data.tables.push(txt);
            });

            return data;
        }''')

    async def run(self):
        async with async_playwright() as p:
            # Chạy có giao diện để mày quan sát nó click
            browser = await p.chromium.launch(headless=False, slow_mo=300)
            context = await browser.new_context()
            page = await context.new_page()

            # Lờ đi các lỗi vặt của web để không treo Bot
            page.on("pageerror", lambda exc: print(f"⚠️ Web Alert (Bỏ qua): {exc}"))

            try:
                # --- BƯỚC 1: ĐĂNG NHẬP ---
                print("🔑 [BƯỚC 1] Đang đăng nhập hệ thống...")
                await page.goto("https://giaiphapvang.net/auth/jwt/sign-in/", timeout=60000)
                await page.fill("input[name='email']", os.getenv("USER_EMAIL"))
                await page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
                await page.click("button[type='submit']")
                
                # Chờ chuyển trang Dashboard
                await page.wait_for_url("**/dashboard/**", timeout=30000)
                print("🔓 Đăng nhập thành công!")

                # --- BƯỚC 2: LẤY CÁC PHÂN HỆ CHÍNH ---
                apps = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .filter(a => a.href.includes('/dashboard') || a.href.includes('/settings') || a.href.includes('/administrator'))
                        .map(a => ({ text: a.innerText.trim(), href: a.href }));
                }''')

                for app in apps:
                    print(f"\n🌍 [BƯỚC 2] Vào phân hệ: {app['text']}")
                    await page.goto(app['href'])
                    await asyncio.sleep(3)

                    # --- BƯỚC 3: QUÉT SIDEBAR ---
                    menu_names = await page.evaluate('''() => {
                        const items = Array.from(document.querySelectorAll('.MuiListItem-root, .sidebar li, a[class*="MuiListItemButton"]'));
                        return [...new Set(items.map(el => el.innerText.trim().split('\\n')[0]))].filter(t => t.length > 2);
                    }''')

                    for menu_name in menu_names:
                        print(f"  📍 [BƯỚC 3] Click Menu: '{menu_name}'")
                        try:
                            # Tìm và click chính xác vào menu text
                            target_item = page.get_by_text(menu_name, exact=True).first
                            if await target_item.is_visible():
                                await target_item.click()
                                await asyncio.sleep(2)
                                
                                # --- BƯỚC 4: LẤY TRI THỨC TRANG ---
                                print(f"    🔍 [BƯỚC 4] Đang trích xuất: {page.url}")
                                content = await self.extract_page_content(page)
                                
                                key = f"{app['text']}_{menu_name}"
                                self.results[key] = {
                                    "url": page.url,
                                    "content": content,
                                    "timestamp": str(asyncio.get_event_loop().time())
                                }
                            else:
                                print(f"    ⚠️ Bỏ qua '{menu_name}' (không thấy trên UI)")
                        except Exception as e:
                            print(f"    ❌ Lỗi menu {menu_name}: {e}")

            except Exception as e:
                print(f"🔥 Lỗi nghiêm trọng: {e}")
                traceback.print_exc()
            finally:
                await browser.close()
                self.save_to_json()

# Xử lý vòng lặp asyncio cho Windows (Python 3.13)
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    extractor = StructureExtractor()
    try:
        asyncio.run(extractor.run())
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise e