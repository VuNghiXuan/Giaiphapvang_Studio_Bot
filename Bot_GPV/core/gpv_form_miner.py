import asyncio
from pathlib import Path

class FormMiner:
    """
    Chuyên gia khai thác dữ liệu (Mining).
    Tự động quét giao diện, vét Form con thông qua các kịch bản JavaScript tách biệt.
    """
    def __init__(self, page, config_class, auth_instance=None):
        self.page = page
        self.auth = auth_instance
        self.config = config_class  # Nhận class Config từ hệ thống của Vũ
        self._script_cache = {}    # Cache lại script để không phải đọc file liên tục

    async def _get_js_content(self, filename):
        """Đọc và cache nội dung file JS"""
        if filename not in self._script_cache:
            js_path = self.config.get_javascript_path(filename)
            if js_path.exists():
                self._script_cache[filename] = js_path.read_text(encoding='utf-8')
            else:
                print(f"⚠️ Cảnh báo: Thiếu file {filename} tại {js_path}")
                self._script_cache[filename] = "() => []"
        return self._script_cache[filename]

    async def mine_current_interface(self):
        """Vét UI ở trang hiện tại VÀ tất cả các Iframes con"""
        combined_data = {"inputs": [], "tables": [], "buttons": []}
        
        # 1. Quét trang chính
        main_data = {
            "inputs": await self.page.evaluate(await self._get_js_content("extract_inputs.js")),
            "tables": await self.page.evaluate(await self._get_js_content("extract_tables.js")),
            "buttons": await self.page.evaluate(await self._get_js_content("extract_buttons.js"))
        }
        self._merge_metadata(combined_data, main_data)

        # 2. Quét xuyên Iframe (Quan trọng cho GPV)
        for frame in self.page.frames[1:]: # Bỏ qua frame chính đã quét
            try:
                frame_data = {
                    "inputs": await frame.evaluate(await self._get_js_content("extract_inputs.js")),
                    "tables": await frame.evaluate(await self._get_js_content("extract_tables.js")),
                    "buttons": await frame.evaluate(await self._get_js_content("extract_buttons.js"))
                }
                self._merge_metadata(combined_data, frame_data)
            except:
                continue
                
        return combined_data

    def _merge_metadata(self, target, source):
        for key in target:
            if isinstance(source.get(key), list):
                target[key].extend(source[key])
                
    async def start_mining(self, module_url, module_name):
        """Luồng chính có bổ sung logic mở Menu cho Vũ"""
        print(f"\n🚀 [START MINING] >>> {module_name} <<<")
        
        # 1. ĐIỀU HƯỚNG & MỞ MENU (CẢI TIẾN)
        # Nếu đang ở Dashboard, phải đi tìm Menu để click chứ không chỉ goto URL
        if "dashboard" in self.page.url or self.page.url != module_url:
            print(f"🌐 Đang tìm cách mở module: {module_name}")
            
            # MÁNH: Tìm menu có text giống module_name và click
            # GPV thường dùng thẻ span hoặc a trong sidebar
            menu_selector = f"//li[contains(@class, 'nav-item')]//span[contains(text(), '{module_name}')]"
            try:
                menu_item = self.page.locator(menu_selector).first
                if await menu_item.is_visible():
                    print(f"🖱️ Click vào Menu: {module_name}")
                    await menu_item.click()
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.wait_for_timeout(2000) # Chờ render bảng
                else:
                    # Nếu không thấy menu để click, thì mới dùng goto
                    await self.page.goto(module_url, wait_until="domcontentloaded")
            except Exception as e:
                print(f"⚠️ Không click được menu, dùng phương án goto: {str(e)}")
                await self.page.goto(module_url, wait_until="domcontentloaded")
                
        # 2. Vét dữ liệu lớp mặt
        print(f"🔎 1. Đang quét giao diện chính (Trang danh sách)...")
        deep_metadata = await self.mine_current_interface()
        
        # --- DEBUG PRINT ---
        print(f"   📊 Kết quả quét chính:")
        print(f"      - Inputs: {len(deep_metadata['inputs'])} trường")
        print(f"      - Tables: {len(deep_metadata['tables'])} bảng")
        print(f"      - Buttons: {len(deep_metadata['buttons'])} nút")

        # 3. Tìm nút "Thêm mới"
        add_btn_selector = "button:has-text('Thêm'), button:has-text('Tạo'), .btn-add, a:has-text('Thêm')"
        add_btn = self.page.locator(add_btn_selector).first
        
        if await add_btn.is_visible():
            box = await add_btn.bounding_box()
            style = await add_btn.evaluate('el => ({bg: window.getComputedStyle(el).backgroundColor, txt: el.innerText})')
            btn_label = style['txt'].strip()
            
            print(f"✨ 2. Phát hiện nút hành động: '{btn_label}'")
            deep_metadata["action_guide"] = {
                "step": "Mở Form nhập liệu",
                "btn_name": btn_label,
                "visual": f"Màu {style['bg']} tại {'phải' if box['x'] > 800 else 'trái'}",
                "coords": box
            }

            print(f"🖱️ Đang nhấn '{btn_label}' để đào sâu...")
            await add_btn.click()
            await self.page.wait_for_timeout(2000) # Chờ form load hẳn

            # 4. Vét dữ liệu bên trong Form
            print(f"🕵️ 3. Đang nội soi Form con (Modal/Popup)...")
            form_metadata = await self.mine_current_interface()
            deep_metadata["sub_form_details"] = form_metadata
            
            # --- DEBUG PRINT ---
            print(f"   📝 Chi tiết Form con:")
            print(f"      - Fields: {[f.get('label') for f in form_metadata['inputs'] if f.get('label')]}")
            print(f"      - Actions: {[b.get('label') for b in form_metadata['buttons'] if b.get('label')]}")
            
            # 5. Thoát Form
            print(f"🔙 Thoát Form về trang chủ...")
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(500)
        else:
            print(f"⚪ Không tìm thấy nút 'Thêm mới', bỏ qua bước nội soi Form.")

        # 6. Lưu kết quả
        await self._save_to_db(module_name, deep_metadata)
        print(f"✅ [FINISHED] Hoàn tất khai thác: {module_name}\n" + "="*50)
        return deep_metadata

    async def _save_to_db(self, name, data):
        """
        Vũ thay vì tự viết SQL ở đây, hãy gọi StudioController 
        để nó tự đẻ ra folder theo logic 'phân cấp'.
        """
        from models.controller import StudioController # Import tại đây để tránh vòng lặp
        ctrl = StudioController()
        
        # Giả định tutorial_id của dự án hiện tại là 1 (hoặc lấy từ session)
        t_id = 1 
        
        # Gọi hàm add_sub_content mà mình vừa sửa ở bước trước
        # Hàm này sẽ tự động biến "Hệ thống | Đối tác | Khách hàng" 
        # thành folder "he_thong/doi_tác/khach_hang"
        ctrl.add_sub_content(
            t_id=t_id,
            sub_title=name, 
            parent_folder=self.config.APP_SLUG,
            url=self.page.url,
            metadata=data,
            status="Đã quét" # Trạng thái mới sau khi Miner chạy xong
        )
        print(f"💾 [Miner]: Đã nạp tri thức và tạo cấu trúc folder cho '{name}'")