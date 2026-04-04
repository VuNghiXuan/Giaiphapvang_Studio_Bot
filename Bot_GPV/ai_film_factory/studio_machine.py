import asyncio
import random

class StudioMachine:
    def __init__(self, target_domain, vision_machine):
        self.target_domain = target_domain
        self.vision = vision_machine 

    async def execute_step(self, page, step):
        target_label = str(step.get("target_label", ""))
        action = str(step.get("action", "click")).lower()
        value = str(step.get("value", ""))

        try:
            if not target_label: return True

            print(f"🎬 Đang diễn: {target_label} | Hành động: {action}")

            # --- CHIẾN THUẬT ĐỊNH DANH 2.0 ---
            locator = None
            if "type" in action or "fill" in action:
                # Ưu tiên Label (Chuẩn MUI)
                locator = page.get_by_label(target_label, exact=True).first
                if await locator.count() == 0:
                    # Tìm theo Placeholder nếu không có label
                    locator = page.get_by_placeholder(target_label, exact=False).first
            else:
                # Đối với Click: Ưu tiên Button hoặc Link (Né text tĩnh)
                locator = page.get_by_role("button", name=target_label, exact=False).first
                if await locator.count() == 0:
                    locator = page.get_by_role("link", name=target_label, exact=False).first

            # Fallback cuối cùng: Dùng Text selector nhưng giới hạn các thẻ có thể click
            if not locator or await locator.count() == 0:
                locator = page.locator(f"text='{target_label}' >> visible=true").first

            # --- THỰC THI & QUAY PHIM ---
            await locator.wait_for(state="visible", timeout=6000)
            
            box = await locator.bounding_box()
            if box:
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2
                
                # Di chuyển chuột "người" hơn (random steps từ 15-25)
                await page.mouse.move(cx, cy, steps=random.randint(15, 25))
                
                if "type" in action or "fill" in action:
                    # Click để lấy focus, sau đó xóa trắng trước khi điền (cho chắc ăn)
                    await locator.click()
                    await locator.fill("") # Clear nội dung cũ nếu có
                    await page.keyboard.type(value, delay=50) # Type từ từ để lên video đẹp hơn
                    await page.keyboard.press("Enter") 
                else:
                    # Hiệu ứng Click từ EffectMachine sẽ được trigger tại đây
                    await page.mouse.click(cx, cy)
                
                # Để khán giả kịp nhìn thấy kết quả
                await asyncio.sleep(0.8) 
                return True
            
            return False

        except Exception as e:
            print(f"❌ Diễn hỏng tại '{target_label}': {e}")
            return False

    async def _handle_navigation(self, page, target_menu):
        """Tự động tìm Menu Sidebar bất kể cấu trúc class"""
        clean_text = str(target_menu).replace("text=", "").strip("'\"")
        # Tìm bất kỳ thẻ nào có role 'menuitem' hoặc 'link' chứa text đó
        for role in ["menuitem", "link", "button"]:
            try:
                loc = page.get_by_role(role, name=clean_text, exact=False).first
                if await loc.count() > 0:
                    await loc.click()
                    print(f"📂 Nav thành công qua role {role}: {clean_text}")
                    return True
            except: continue
        return False