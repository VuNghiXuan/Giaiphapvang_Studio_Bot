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
        """Vét toàn bộ UI hiện tại: Inputs, Tables, Buttons"""
        return {
            "inputs": await self.page.evaluate(await self._get_js_content("extract_inputs.js")),
            "tables": await self.page.evaluate(await self._get_js_content("extract_tables.js")),
            "buttons": await self.page.evaluate(await self._get_js_content("extract_buttons.js"))
        }

    async def start_mining(self, module_url, module_name):
        """Luồng chính: Điều hướng -> Vét trang chính -> Mở Form con -> Vét Form con"""
        print(f"⛏️ [PageMiner] Đang khai thác Module: {module_name}")
        
        # 1. Đảm bảo đang ở đúng trang cần đào
        if self.page.url != module_url:
            await self.page.goto(module_url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(2000)

        # 2. Vét dữ liệu lớp mặt (Trang danh sách/Dashboard)
        deep_metadata = await self.mine_current_interface()
        
        # 3. Tìm nút "Thêm mới" hoặc "Tạo" để đào sâu vào Form
        add_btn_selector = "button:has-text('Thêm'), button:has-text('Tạo'), .btn-add, a:has-text('Thêm')"
        add_btn = self.page.locator(add_btn_selector).first
        
        if await add_btn.is_visible():
            box = await add_btn.bounding_box()
            style = await add_btn.evaluate('el => ({bg: window.getComputedStyle(el).backgroundColor, txt: el.innerText})')
            
            # Ghi chú lại cách vào Form để AI sau này biết đường hướng dẫn user
            deep_metadata["action_guide"] = {
                "step": "Mở Form nhập liệu",
                "btn_name": style['txt'].strip(),
                "visual": f"Nút màu {style['bg']} tại {'phía phải' if box['x'] > 800 else 'phía trái'}",
                "coords": box
            }

            print(f"➕ [PageMiner] Nhấn '{style['txt'].strip()}' để vét Form con...")
            await add_btn.click()
            await self.page.wait_for_timeout(1500) # Chờ form load

            # 4. Vét dữ liệu bên trong Form (Modal/Popup)
            form_metadata = await self.mine_current_interface()
            deep_metadata["sub_form_details"] = form_metadata
            
            # 5. Thoát Form để về trạng thái ban đầu
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(500)

        # 6. Lưu kết quả
        await self._save_to_db(module_name, deep_metadata)
        return deep_metadata

    async def _save_to_db(self, name, data):
        """
        Vũ triển khai lưu vào SQLite ở đây.
        Gợi ý: Lưu name, url, và json.dumps(data) vào table 'module_metadata'
        """
        print(f"💾 [Database] Metadata của '{name}' đã được lưu kho.")