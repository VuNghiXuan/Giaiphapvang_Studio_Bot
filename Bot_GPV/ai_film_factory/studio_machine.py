import asyncio
import random
from .effect_machine import EffectMachine # Đảm bảo đã import để dùng hiệu ứng

class StudioMachine:
    def __init__(self, target_domain, vision_machine):
        self.target_domain = target_domain
        self.vision = vision_machine 

    async def execute_step(self, page, step):
        """
        Thực thi một bước diễn xuất trên giao diện web.
        Đã gia cố để hiểu các key khác nhau từ AI (Llama/Groq/Gemini).
        """
        # 1. TRÍCH XUẤT DỮ LIỆU THÔNG MINH (Tránh NoneType)
        # AI có thể trả về 'target_label', 'selector', hoặc 'label'
        target_label = str(
            step.get("target_label") or 
            step.get("selector") or 
            step.get("label") or ""
        ).strip()
        
        action = str(step.get("action") or "click").lower()
        
        # AI có thể trả về 'value', 'text_input', hoặc 'data'
        value = str(
            step.get("value") or 
            step.get("text_input") or 
            step.get("data") or ""
        )
        
        # Nếu không có mục tiêu, coi như bước nhảy/chờ, trả về True
        if not target_label: 
            print("⚠️ Bước diễn không có mục tiêu (target_label), bỏ qua thực thi UI.")
            return True

        try:
            print(f"🎬 Đang diễn: {target_label} | Hành động: {action}")

            # --- CHIẾN THUẬT ĐỊNH DANH 3.0 (Fuzzy & Hybrid) ---
            # Thêm nhiều selector linh hoạt để không bị sót phần tử trên web
            locators_to_try = [
                page.get_by_role("button", name=target_label, exact=False),
                page.get_by_role("link", name=target_label, exact=False),
                page.get_by_label(target_label, exact=False),
                page.get_by_placeholder(target_label, exact=False),
                page.get_by_text(target_label, exact=False), 
                page.locator(f"p:has-text('{target_label}')"), 
                page.locator(f"span:has-text('{target_label}')"),
                page.locator(f"div:has-text('{target_label}')").first # Bổ sung thêm div
            ]

            final_locator = None
            for loc in locators_to_try:
                try:
                    count = await loc.count()
                    if count > 0:
                        # Tìm phần tử đầu tiên đang hiển thị (visible)
                        for i in range(count):
                            candidate = loc.nth(i)
                            if await candidate.is_visible():
                                final_locator = candidate
                                break
                    if final_locator: break
                except: continue

            if not final_locator:
                print(f"❌ Không tìm thấy phần tử nào khớp với: {target_label}")
                return False

            # 2. CHUẨN BỊ THỰC THI (Actionability)
            await final_locator.wait_for(state="visible", timeout=5000)
            await final_locator.scroll_into_view_if_needed()
            
            box = await final_locator.bounding_box()
            if not box:
                print(f"⚠️ Phần tử '{target_label}' không có tọa độ hiển thị.")
                return False

            cx = box['x'] + box['width'] / 2
            cy = box['y'] + box['height'] / 2
            
            # 3. HIỆU ỨNG DIỄN XUẤT (Để video sinh động)
            # Di chuyển chuột tới mục tiêu
            await page.mouse.move(cx, cy, steps=12)
            
            # Hiệu ứng Ripple/Click tại tọa độ
            if hasattr(EffectMachine, 'apply_click_effect'):
                await EffectMachine.apply_click_effect(page, cx, cy)
            
            # 4. THỰC HIỆN HÀNH ĐỘNG
            if any(k in action for k in ["type", "fill", "nhập", "điền"]):
                # Nhập liệu: Click -> Xóa -> Gõ từng phím
                await final_locator.click(force=True)
                await page.keyboard.press("Control+A") # Xóa sạch cũ
                await page.keyboard.press("Backspace")
                await page.keyboard.type(value, delay=random.randint(40, 80)) 
                await page.keyboard.press("Enter") 
            else:
                # Click chiến thuật: Thử click chuẩn, nếu bị che thì dùng tọa độ mouse
                try:
                    await final_locator.click(timeout=3000)
                except:
                    print(f"⚠️ Force click bằng tọa độ cho: {target_label}")
                    await page.mouse.click(cx, cy)
            
            # Nghỉ ngắn để UI phản hồi và video kịp ghi lại
            await asyncio.sleep(1.2) 
            return True

        except Exception as e:
            print(f"❌ Diễn hỏng tại '{target_label}': {e}")
            return False

    async def _handle_navigation(self, page, target_menu):
        """Hỗ trợ nhảy menu Sidebar nhanh"""
        clean_text = str(target_menu).replace("text=", "").strip("'\"")
        for role in ["menuitem", "link", "button"]:
            try:
                loc = page.get_by_role(role, name=clean_text, exact=False).first
                if await loc.count() > 0:
                    # Di chuyển tới và click có hiệu ứng
                    box = await loc.bounding_box()
                    if box:
                        await page.mouse.move(box['x']+5, box['y']+5, steps=10)
                        await EffectMachine.apply_click_effect(page, box['x']+5, box['y']+5)
                    await loc.click()
                    return True
            except: continue
        return False