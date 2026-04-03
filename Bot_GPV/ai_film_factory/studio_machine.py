import asyncio

class StudioMachine:
    def __init__(self, target_domain, vision_machine):
        self.target_domain = target_domain
        self.vision = vision_machine 

    
    async def execute_step(self, page, step, effect_engine=None):
        target_click = step.get("click")
        target_hover = step.get("hover")
        target_type = step.get("type")
        
        raw_target = target_click or target_hover or target_type
        if not raw_target: return

        # 2. Quét trạng thái UI
        metadata = await self.vision.scan_page(page)
        # Sửa lại cách lấy dữ liệu cho khớp với VisionMachine của Vũ
        active_form = metadata.get('active_form') or {}
        layout = metadata.get('layout') or {}
        
        # Check xem có Dialog đang chắn đường không
        has_dialog = await page.locator(".MuiDialog-root, [role='dialog']").is_visible()

        # 3. CHIẾN THUẬT SELECTOR THÔNG MINH
        # Nếu target là text thuần (không có dấu # hoặc .), ta bọc nó vào text selector
        is_selector = any(char in str(raw_target) for char in ['#', '.', '[', '>'])
        
        if not is_selector:
            # Biến text thành Playwright Text Selector
            base_selector = f"text='{raw_target}'"
        else:
            base_selector = raw_target

        if has_dialog:
            final_selector = f".MuiDialog-root >> {base_selector}"
        else:
            final_selector = base_selector

        try:
            # Tìm Element (Thêm bộ lọc visible để tránh lấy các element ẩn bên dưới)
            locator = page.locator(final_selector).visible.first
            await locator.wait_for(state="visible", timeout=5000)
            
            # Cuộn trang
            await locator.scroll_into_view_if_needed()
            box = await locator.bounding_box()
            if not box: return

            cx, cy = box['x'] + box['width']/2, box['y'] + box['height']/2
            
            # Di chuyển chuột (steps=20 giúp video trông tự nhiên hơn)
            await page.mouse.move(cx, cy, steps=20)

            # --- THỰC THI ---
            if target_type:
                value = str(step.get("value", ""))
                # Check Autocomplete từ metadata
                inputs = active_form.get('inputs', [])
                is_auto = any(raw_target in str(f.get('label')) for f in inputs if f.get('type') == 'autocomplete')

                await page.mouse.click(cx, cy)
                await asyncio.sleep(0.3)
                
                if is_auto:
                    await page.keyboard.type(value, delay=100)
                    # Chờ menu Autocomplete xuất hiện
                    try:
                        await page.wait_for_selector(".MuiAutocomplete-listbox", timeout=3000)
                        await page.keyboard.press("ArrowDown")
                        await page.keyboard.press("Enter")
                    except:
                        await page.keyboard.press("Enter") # Fallback nếu không thấy list
                else:
                    await page.keyboard.type(value, delay=80)

            elif target_click:
                if effect_engine:
                    await effect_engine.apply_spotlight(page, final_selector)
                await page.mouse.click(cx, cy)
                
            elif target_hover:
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Navigation Fallback cho: {raw_target}")
            await self._handle_navigation(page, raw_target)

        await page.wait_for_timeout(800)


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