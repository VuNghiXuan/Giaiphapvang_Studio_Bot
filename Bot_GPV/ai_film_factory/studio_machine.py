import asyncio

class StudioMachine:
    def __init__(self, target_domain, vision_machine):
        self.target_domain = target_domain
        self.vision = vision_machine 

    async def execute_step(self, page, step, vision_machine):
        """
        [PHIÊN BẢN STUDIO ĐIỆN ẢNH 2026]
        Đã fix lỗi nhầm Header Table và lỗi Locator.fill trên thẻ Div.
        """
        target_label = str(step.get("target_label", ""))
        action = str(step.get("action", "click")).lower()
        value = str(step.get("value", ""))

        try:
            if not target_label:
                print("⚠️ Bỏ qua bước: Không có target_label")
                return True # Vẫn trả về True để kịch bản tiếp tục

            print(f"🎬 Diễn bước: {target_label} ({action})...")

            # --- CHIẾN THUẬT ĐỊNH DANH THÔNG MINH ---
            if "type" in action:
                # Ưu tiên 1: Tìm chính xác label gắn với input (Chuẩn Material UI)
                # Dùng get_by_label giúp né hoàn toàn các thẻ Div tiêu đề bảng
                locator = page.get_by_label(target_label, exact=True).first
                
                # Ưu tiên 2: Nếu không thấy label, tìm input/textarea nằm gần text đó
                if await locator.count() == 0:
                    locator = page.locator(f"input:near(:text('{target_label}'))").first
            else:
                # Đối với Click (Nút bấm): Ưu tiên tìm role button để né text rác
                locator = page.get_by_role("button", name=target_label).first
                
                # Nếu không tìm thấy button, mới dùng text selector truyền thống
                if await locator.count() == 0:
                    selector = f"text='{target_label}' >> visible=true"
                    locator = page.locator(selector).first

            # --- THỰC THI ---
            # Chờ tối đa 5s để phần tử sẵn sàng
            await locator.wait_for(state="visible", timeout=5000)
            
            box = await locator.bounding_box()
            if box:
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2
                
                # Di chuyển chuột thực tế (để MoviePy quay được cảnh di chuyển)
                await page.mouse.move(cx, cy, steps=15)
                
                if "type" in action:
                    # Đảm bảo focus trước khi fill để trigger các event JS của trang
                    await locator.click() 
                    await locator.fill(value)
                    # Nhấn Tab để báo hiệu nhập xong (giúp Material UI lưu state)
                    await page.keyboard.press("Tab") 
                    print(f"⌨️  Đã nhập '{value}' vào {target_label}")
                else:
                    await page.mouse.click(cx, cy)
                    print(f"✅ Đã Click: {target_label}")
                
                # Nghỉ một chút để video quay kịp khoảnh khắc
                await asyncio.sleep(0.5) 
                return True
            else:
                print(f"⚠️ Không lấy được tọa độ cho: {target_label}")
                return False

        except Exception as e:
            print(f"❌ Lỗi thực thi bước '{target_label}': {e}")
            # Chụp ảnh màn hình lúc lỗi để debug nếu cần
            # await page.screenshot(path=f"error_{target_label}.png")
            return False
            
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