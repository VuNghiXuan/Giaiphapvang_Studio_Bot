import asyncio

class StudioMachine:
    def __init__(self, target_domain, vision_machine):
        self.target_domain = target_domain
        self.vision = vision_machine 

    async def execute_step(self, page, step, effect_engine=None):
        # 1. Bóc tách kịch bản
        target_click = step.get("click")
        target_hover = step.get("hover")
        target_type = step.get("type")
        target_highlight = step.get("highlight")
        
        raw_target = target_click or target_hover or target_type or target_highlight
        if not raw_target: return

        # 2. Quét trạng thái UI thực tế để lấy "Nhãn lực" mới nhất
        metadata = await self.vision.scan_page(page)
        state = metadata.get('state', {})
        has_dialog = state.get('has_overlay', False)

        # 3. CHIẾN THUẬT SELECTOR (Nâng cấp từ bản của Vũ)
        final_selector = raw_target
        
        # Ép Bot tập trung vào Dialog nếu đang mở (Tránh thanh Search nền)
        if has_dialog:
            # Nếu raw_target đã là selector phức tạp, ta bọc nó lại
            final_selector = f".MuiDialog-root {raw_target}, [role='dialog'] {raw_target}"
        elif "Hệ thống" in str(raw_target) or "Chi nhánh" in str(raw_target):
            final_selector = f".MuiDrawer-root :text-is('{raw_target}'), .MuiListItemButton-root:has-text('{raw_target}')"

        try:
            # Tìm Element
            locator = page.locator(final_selector).visible.first
            await locator.wait_for(state="visible", timeout=5000)
            
            # --- XỬ LÝ CUỘN (Scroll) CHO BẢNG DÀI ---
            await locator.scroll_into_view_if_needed()
            
            box = await locator.bounding_box()
            if not box: return

            cx, cy = box['x'] + box['width']/2, box['y'] + box['height']/2
            
            # Di chuyển chuột mượt (Vũ làm đoạn này rất tốt, tui giữ nguyên)
            await page.mouse.move(cx, cy, steps=20)
            await asyncio.sleep(0.2)

            # --- THỰC THI HÀNH ĐỘNG ---

            # 1. TYPE (Nâng cấp cho Autocomplete của Giai Pháp Vàng)
            if target_type:
                value = str(step.get("value", ""))
                # Kiểm tra trong metadata xem ô này có phải Autocomplete không
                is_auto = any(f['label'] in raw_target for f in metadata['content']['form_fields'] if f.get('is_autocomplete'))
                
                await page.mouse.click(cx, cy)
                await asyncio.sleep(0.3)
                
                if is_auto:
                    # Logic: Gõ -> Đợi list -> Enter
                    await page.keyboard.type(value, delay=100)
                    await page.wait_for_timeout(500) # Đợi menu xổ xuống
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
                    print(f"💎 Autocomplete Select '{value}' -> {raw_target}")
                else:
                    await page.keyboard.type(value, delay=80)
                    print(f"⌨️ Type '{value}' -> {raw_target}")

            # 2. CLICK
            elif target_click:
                if effect_engine and hasattr(effect_engine, 'apply_spotlight'):
                    await effect_engine.apply_spotlight(page, final_selector)
                
                await page.mouse.click(cx, cy)
                print(f"🖱️ Click -> {raw_target}")
                
                # Nếu click xong mà mở Dialog, đợi xíu cho nó render
                await asyncio.sleep(0.5)

            # 3. HOVER
            elif target_hover:
                await asyncio.sleep(0.8) 
                print(f"👁️ Hover -> {raw_target}")

            # 4. HẬU KIỂM (Health Check)
            is_ok, errors = await self.vision.check_health(page)
            if not is_ok: print(f"🚨 UI Error: {errors}")

        except Exception as e:
            print(f"⚠️ Fallback Trình tự cho: {raw_target}")
            await self._handle_navigation(page, raw_target)

        await page.wait_for_timeout(800) # Nghỉ để clip không bị giật

    async def _handle_navigation(self, page, target_menu):
        """Hàm cứu cánh khi Bot bị lạc đường"""
        clean_text = str(target_menu).replace("text=", "").strip("'\"")
        # Thử click bằng text thuần túy trong Sidebar
        try:
            loc = page.locator(f".MuiListItemButton-root:has-text('{clean_text}')").visible.first
            if await loc.count() > 0:
                await loc.click()
                print(f"📂 Nav Fallback thành công: {clean_text}")
                return True
        except: return False