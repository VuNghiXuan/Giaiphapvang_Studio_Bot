import asyncio
import os
import time
from playwright.async_api import async_playwright

class BrowserAgent:
    def __init__(self, output_dir="recordings"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    async def _init_browser(self, p):
        """Khởi tạo trình duyệt và ngữ cảnh"""
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=self.output_dir,
            ignore_https_errors=True
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        return browser, context, page

    async def capture_page_context(self, page):
        """'Cào' toàn bộ thông tin các phần tử có thể tương tác trên trang hiện tại"""
        # Đợi một chút cho UI (như MUI) render xong hoàn toàn
        await asyncio.sleep(1.5) 
        
        elements = await page.evaluate('''() => {
            const interactiveSelectors = 'a, button, input, [role="button"], [role="link"], h1, h2, h6, .MuiTypography-root';
            const items = [];
            document.querySelectorAll(interactiveSelectors).forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                    items.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.placeholder || "").trim(),
                        href: el.getAttribute('href') || "",
                        id: el.id,
                        name: el.getAttribute('name') || "",
                        role: el.getAttribute('role') || "",
                        class: el.className
                    });
                }
            });
            return items;
        }''')
        return elements

    async def execute_step(self, page, step, scenario_name):
        """Xử lý từng loại hành động cụ thể"""
        action = step.get("action")
        selector = step.get("selector")
        value = step.get("value", "")
        
        if action == "goto":
            await page.goto(selector, wait_until="networkidle", timeout=60000)
            
        elif action == "click":
            await page.wait_for_selector(selector, state="visible", timeout=15000)
            # Hover trước khi click để tạo hiệu ứng video tự nhiên
            await page.hover(selector)
            await page.click(selector)
            
        elif action == "fill":
            await page.wait_for_selector(selector, state="visible")
            await page.click(selector) # Focus vào field (quan trọng cho MUI)
            await page.fill(selector, value)
            
        elif action == "wait":
            try:
                # Nếu là số giây
                seconds = float(value)
                await asyncio.sleep(seconds)
            except ValueError:
                # Nếu là Selector
                print(f"⏳ Chờ phần tử: {value}")
                try:
                    await page.wait_for_selector(value, state="visible", timeout=20000)
                except Exception:
                    screenshot_path = os.path.join(self.output_dir, f"timeout_{int(time.time())}.png")
                    await page.screenshot(path=screenshot_path)
                    raise Exception(f"Timeout chờ {value}. Ảnh debug tại: {screenshot_path}")

    async def run_scenario(self, scenario_name, steps):
        """Hàm điều khiển chính: Chạy kịch bản và thu thập dữ liệu thông minh"""
        async with async_playwright() as p:
            browser, context, page = await self._init_browser(p)
            action_logs = []
            start_time = asyncio.get_event_loop().time()

            try:
                for step in steps:
                    current_time = round(asyncio.get_event_loop().time() - start_time, 2)
                    desc = step.get("description", "Thao tác")
                    
                    print(f"[{current_time}s] >>> {desc}")

                    # 1. Thực hiện thao tác
                    await self.execute_step(page, step, scenario_name)

                    # 2. SAU KHI THAO TÁC: Cào ngay dữ liệu trang hiện tại
                    # Đây là chìa khóa để AI biết bước tiếp theo phải làm gì
                    current_context = await self.capture_page_context(page)

                    # 3. Ghi log chi tiết bao gồm cả 'mắt nhìn' của Bot
                    action_logs.append({
                        "start": current_time,
                        "description": desc,
                        "action": step.get("action"),
                        "page_url": page.url,
                        "captured_elements": current_context # Toàn bộ thẻ/nút trên trang mới
                    })

                    await asyncio.sleep(1) # Nghỉ giữa hiệp cho video mượt

                # Xử lý video cuối cùng
                video_raw_path = await self._finalize_video(browser, context, scenario_name)
                return video_raw_path, action_logs

            except Exception as e:
                print(f"❌ Lỗi quy trình: {e}")
                await browser.close()
                return None, None

    async def _finalize_video(self, browser, context, scenario_name):
        """Đóng browser và xử lý file video đầu ra"""
        video = await context.pages[0].video.path()
        final_name = os.path.join(self.output_dir, f"{scenario_name}_raw.webm")
        
        await context.close()
        await browser.close()

        if os.path.exists(final_name):
            os.remove(final_name)
        if os.path.exists(video):
            os.rename(video, final_name)
        return final_name