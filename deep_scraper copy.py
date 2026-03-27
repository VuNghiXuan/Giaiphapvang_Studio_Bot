import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

class StructureExtractor:
    def __init__(self, output_file="knowledge_source.json"):
        self.output_file = output_file
        self.knowledge_data = {}

    def save_to_file(self):
        """Lưu dữ liệu hiện tại xuống file ngay lập tức"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_data, f, ensure_ascii=False, indent=4)

    async def extract_page_structure(self, page, page_name):
        print(f"🕵️ Đang trích xuất cấu trúc: {page_name}...")
        
        # Chờ đợi các phần tử MUI render xong
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(3) # Chờ thêm 3s cho chắc ăn
        except:
            pass

        structure = await page.evaluate('''() => {
            const data = { buttons: [], inputs: [], links: [] };

            // Tìm nút: Lấy cả text bên trong các thẻ phức tạp của MUI
            document.querySelectorAll('button, [role="button"], a.MuiButton-root').forEach(el => {
                const text = el.innerText.trim().split('\\n')[0]; // Lấy dòng đầu tiên của text
                if (text && text.length < 50) {
                    data.buttons.push({ text, id: el.id });
                }
            });

            // Tìm Input: Ưu tiên lấy Label đi kèm
            document.querySelectorAll('input, textarea').forEach(el => {
                let label = "";
                const id = el.id;
                if (id) {
                    const labelEl = document.querySelector(`label[for="${id}"]`);
                    label = labelEl ? labelEl.innerText.trim() : "";
                }
                if (!label) label = el.getAttribute('placeholder') || el.getAttribute('name') || "Trường nhập liệu";
                
                data.inputs.push({
                    label: label,
                    name: el.getAttribute('name') || "",
                    type: el.type
                });
            });

            // Tìm Links: Chỉ lấy các link điều hướng chính
            document.querySelectorAll('a').forEach(el => {
                const text = el.innerText.trim();
                const href = el.getAttribute('href');
                if (text && href && !href.startsWith('http') && href !== '/') {
                    data.links.push({ text, href });
                }
            });

            return data;
        }''')

        # Chỉ lưu nếu có dữ liệu
        if structure['buttons'] or structure['inputs']:
            self.knowledge_data[page_name] = {
                "url": page.url,
                "structure": structure
            }
            self.save_to_file() # Ghi file luôn sau mỗi trang
            print(f"✅ Đã lưu dữ liệu trang {page_name}")
        else:
            print(f"⚠️ Trang {page_name} không có dữ liệu tương tác để lấy.")

    async def run(self):
        async with async_playwright() as p:
            # Tắt headless để Vũ nhìn thấy nó đang làm gì
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context(viewport={'width': 1366, 'height': 768})
            page = await context.new_page()

            # 1. Login
            print("🔑 Đang đăng nhập...")
            await page.goto("https://giaiphapvang.net/auth/jwt/sign-in/")
            await page.fill("input[name='email']", os.getenv("USER_EMAIL"))
            await page.fill("input[name='password']", os.getenv("USER_PASSWORD"))
            await page.click("button[type='submit']")
            
            # Đợi chuyển hướng sang home
            await page.wait_for_url("**/home/**", timeout=30000)
            print("🏠 Đã vào trang Home.")
            await asyncio.sleep(2)

            # 2. Lấy danh sách App (Lọc thoáng hơn)
            apps = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .filter(a => a.href.includes('/dashboard') || a.href.includes('/trading'))
                    .map(a => ({ text: a.innerText.trim(), href: a.href }));
            }''')

            if not apps:
                print("❌ Không tìm thấy App nào trên trang Home! Vũ kiểm tra lại selector thẻ 'a'.")
                # Thử quét trang hiện tại (Home) xem có gì không
                await self.extract_page_structure(page, "Trang_Home_Manual")
            else:
                print(f"📂 Tìm thấy {len(apps)} phân hệ.")

            for app in apps:
                app_name = app['text'].split('\\n')[0]
                try:
                    print(f"🚀 Vào App: {app_name}")
                    await page.goto(app['href'])
                    await self.extract_page_structure(page, f"App_{app_name}")
                    
                    # Quét nhanh các menu sidebar
                    sub_links = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('nav a, ul a'))
                            .filter(a => a.innerText.trim().length > 0)
                            .map(a => ({ text: a.innerText.trim().split('\\n')[0], href: a.href }))
                            .slice(0, 5); // Lấy 5 menu đầu tiên
                    }''')

                    for sub in sub_links:
                        print(f"  ∟ Quét: {sub['text']}")
                        await page.goto(sub['href'])
                        await self.extract_page_structure(page, f"{app_name}_{sub['text']}")
                    
                    await page.goto(app['href']) 
                except Exception as e:
                    print(f"❌ Lỗi tại {app_name}: {e}")

            await browser.close()
            print(f"🏁 XONG! File lưu tại: {os.path.abspath(self.output_file)}")

if __name__ == "__main__":
    extractor = StructureExtractor()
    asyncio.run(extractor.run())