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
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1.5, # Giúp chữ trong video to rõ hơn
            record_video_dir=self.output_dir,
            ignore_https_errors=True
        )
        page = await context.new_page()
        # Để 30s là đủ, 60s hơi lâu nếu web bị lỗi thực sự
        page.set_default_timeout(30000) 
        return browser, context, page

    async def capture_page_context(self, page):
        """'Cào' thông tin: Thêm bước tự động cuộn trang để UI load hết"""
        await asyncio.sleep(1) # Đợi UI ổn định
        
        elements = await page.evaluate('''() => {
            const interactiveSelectors = 'a, button, input, [role="button"], [role="link"], .MuiTypography-root, .ant-menu-item';
            const items = [];
            document.querySelectorAll(interactiveSelectors).forEach(el => {
                // Tự động cuộn tới phần tử để nó 'visible' thực sự
                // el.scrollIntoView({block: "nearest"}); 
                
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none') {
                    items.push({
                        tag: el.tagName,
                        text: (el.innerText || el.value || el.placeholder || "").trim(),
                        id: el.id,
                        role: el.getAttribute('role') || "",
                        class: el.className
                    });
                }
            });
            return items;
        }''')
        return elements

    async def execute_step(self, page, step, scenario_name):
        action = step.get("action")
        selector = step.get("selector")
        value = step.get("value", "")
        
        # Tạo locator thông minh hơn
        # Nếu selector là một chuỗi text đơn thuần, ta bọc nó lại
        if not (selector.startswith('.') or selector.startswith('#') or selector.startswith('//')):
            # Tìm theo text một cách linh hoạt (không phân biệt hoa thường)
            target_locator = page.get_by_text(selector, exact=False).first
        else:
            target_locator = page.locator(selector).first

        if action == "goto":
            await page.goto(selector, wait_until="networkidle", timeout=60000)
            
        elif action == "click":
            # --- CẢI TIẾN: Đợi, Cuộn, Hover rồi mới Click ---
            try:
                await target_locator.wait_for(state="visible", timeout=10000)
                await target_locator.scroll_into_view_if_needed()
                await target_locator.hover()
                await asyncio.sleep(0.5) # Để video thấy rõ chuột đang di chuyển tới
                await target_locator.click()
            except Exception as e:
                print(f"⚠️ Không click được '{selector}': {e}")
                # Chụp ảnh lỗi ngay lúc này để Vũ xem tại sao nó timeout
                await page.screenshot(path=f"error_click_{int(time.time())}.png")
                raise e
            
        elif action == "fill":
            await target_locator.wait_for(state="visible", timeout=10000)
            await target_locator.scroll_into_view_if_needed()
            await target_locator.click() # Focus cho chắc (nhất là với MUI/AntD)
            await target_locator.fill(value)
            
        elif action == "wait":
            # (Giữ nguyên logic cũ của Vũ)
            await asyncio.sleep(float(value))

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