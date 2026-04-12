import asyncio
from pathlib import Path

class DeepFormMiner:
    """
    Chuyên gia khai thác dữ liệu (Mining).
    Tự động quét giao diện, vét Form con và phá giải các Menu ẩn trong Table.
    """
    def __init__(self, page, config_class, auth_instance=None):
        self.page = page
        self.auth = auth_instance
        self.config = config_class  # Nhận class Config từ hệ thống của Vũ
        self._script_cache = {}     # Cache lại script để không phải đọc file liên tục

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
        
        # Lấy nội dung script một lần để dùng nhiều lần
        js_inputs = await self._get_js_content("extract_inputs.js")
        js_tables = await self._get_js_content("extract_tables.js")
        js_buttons = await self._get_js_content("extract_buttons.js")

        # 1. Quét trang chính
        main_data = {
            "inputs": await self.page.evaluate(js_inputs),
            "tables": await self.page.evaluate(js_tables),
            "buttons": await self.page.evaluate(js_buttons)
        }
        self._merge_metadata(combined_data, main_data)

        # 2. Quét xuyên Iframe (Quan trọng cho các hệ thống ERP/Jewelry của Vũ)
        for frame in self.page.frames[1:]: 
            try:
                frame_data = {
                    "inputs": await frame.evaluate(js_inputs),
                    "tables": await frame.evaluate(js_tables),
                    "buttons": await frame.evaluate(js_buttons)
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
        """
        LUỒNG NỘI SOI: Quét trang hiện tại -> Vét nút ẩn Table -> Nội soi Form Thêm mới.
        """
        print(f"\n🚀 [MINER] Đang nội soi thực thể: {module_name}")
        
        # 1. KIỂM TRA ĐIỀU HƯỚNG
        # Orchestrator thường đã điều hướng rồi, nhưng ta kiểm tra lại cho chắc
        if self.page.url == "about:blank":
            print(f"🌐 Điều hướng bổ sung tới: {module_url}")
            await self.page.goto(module_url, wait_until="networkidle", timeout=60000)
        
        await self.page.wait_for_timeout(1500) # Đợi UI ổn định

        # 2. QUÉT GIAO DIỆN LỚP MẶT (Bảng, nút, input hiện có)
        print(f"🔎 [1/3] Đang quét giao diện lớp mặt...")
        deep_metadata = await self.mine_current_interface()
        
        # 3. VÉT NÚT ẨN TRONG BẢNG (Sửa, Xóa, Ngưng sử dụng...)
        if deep_metadata.get("tables"):
            print(f"🕵️ [2/3] Phát hiện {len(deep_metadata['tables'])} bảng, đang tìm menu ẩn...")
            deep_metadata["tables"] = await self._mine_hidden_table_actions(deep_metadata["tables"])

        # 4. NỘI SOI FORM CON (Nhấn 'Thêm mới' để xem bên trong có input gì)
        # Selector tập trung vào các nút đặc trưng của hệ thống GPV
        add_btn_selector = "button:has-text('Thêm'), button:has-text('Tạo'), .btn-add, a:has-text('Thêm'), [title*='Thêm']"
        add_btn = self.page.locator(add_btn_selector).first
        
        if await add_btn.is_visible():
            btn_label = (await add_btn.inner_text()).strip() or "Thêm mới"
            print(f"✨ [3/3] Phát hiện nút hành động: '{btn_label}'. Đang tiến hành nội soi Form...")
            
            try:
                await add_btn.click()
                await self.page.wait_for_timeout(2000) # Đợi Modal/Popup hiện ra

                # Quét dữ liệu bên trong Form (Modal)
                form_metadata = await self.mine_current_interface()
                deep_metadata["sub_form_details"] = form_metadata
                
                print(f"✅ Đã thu thập xong cấu trúc Form con.")
                
                # Thoát Form để trả lại trạng thái sạch cho trang
                await self.page.keyboard.press("Escape")
                await self.page.wait_for_timeout(800)
            except Exception as e:
                print(f"⚠️ Không thể nội soi Form: {e}")
        else:
            print(f"⚪ Không thấy nút 'Thêm mới', kết thúc sớm bước nội soi Form.")

        # LƯU Ý: Không gọi _save_to_db ở đây nữa. 
        # Kết quả sẽ được trả về cho Orchestrator để đưa sang Archiver lưu một lần duy nhất.
        print(f"✅ [FINISHED] Hoàn tất khai thác: {module_name}\n" + "-"*30)
        return deep_metadata

    async def _mine_hidden_table_actions(self, tables_metadata):
        """
        NÂNG CẤP: Tìm nút 'Thao tác' trong bảng, click để quét nút ẩn.
        """
        # Đọc script một lần duy nhất trước khi vào vòng lặp (Tăng tốc)
        js_buttons = await self._get_js_content("extract_buttons.js")
        
        for table in tables_metadata:
            # Tìm các trigger menu (ví dụ: nút có icon ba chấm, hoặc chữ 'Thao tác')
            triggers = [a for a in table.get("actions_detected", []) if a.get("is_trigger_menu")]
            
            if not triggers:
                continue

            # Chỉ thử nghiệm trên dòng đầu tiên để lấy cấu trúc (tiết kiệm thời gian)
            trigger = triggers[0]
            try:
                trigger_btn = self.page.locator(trigger['selector']).first
                if await trigger_btn.is_visible():
                    await trigger_btn.click()
                    await self.page.wait_for_timeout(1000) 

                    # Quét các nút mới xuất hiện (thường là Portal/Dropdown tách rời khỏi table)
                    new_buttons = await self.page.evaluate(js_buttons)
                    
                    # Lọc lấy các nút nằm ở lớp ngoài cùng (body) - đặc trưng của Dropdown menu
                    hidden_actions = [b for b in new_buttons if b['visual']['position'] == 'body']
                    table["hidden_actions_mined"] = hidden_actions
                    
                    print(f"   ✅ Vét thành công {len(hidden_actions)} nút ẩn (Sửa, Xóa...) cho bảng.")
                    
                    # Đóng menu
                    await self.page.keyboard.press("Escape")
            except Exception as e:
                print(f"   ⚠️ Lỗi khi vét nút ẩn: {str(e)}")
                
        return tables_metadata

    # async def _save_to_db(self, name, data):
    #     """Gọi StudioController để tự động phân cấp folder"""
    #     try:
    #         from models.controller import StudioController 
    #         ctrl = StudioController()
    #         t_id = 1 # Lấy từ context thực tế của Vũ
            
    #         ctrl.add_sub_content(
    #             t_id=t_id,
    #             sub_title=name, 
    #             parent_folder=self.config.APP_SLUG,
    #             url=self.page.url,
    #             metadata=data,
    #             status="Đã quét"
    #         )
    #         print(f"💾 [Miner]: Đã nạp tri thức vào DB cho '{name}'")
    #     except Exception as e:
    #         print(f"❌ Lỗi lưu DB: {str(e)}")