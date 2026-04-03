import os
import json
from datetime import datetime
from config import Config 

class VisionMachine:
    def __init__(self):
        """
        Khởi tạo 'con mắt' AI để quét metadata từ trình duyệt.
        """
        self.scanner_script = ""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(current_dir, 'scanner.js')
        
        try:
            if os.path.exists(js_path):
                print('--- [👁️] Đang nạp tri thức từ scanner.js ---')
                with open(js_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Bọc nội dung vào khối Async Try-Catch để an toàn trên Browser
                self.scanner_script = f"""
                async () => {{
                    try {{
                        {content}
                        if (typeof scanPage === 'function') {{
                            return await scanPage();
                        }} else {{
                            return {{ error: 'Hàm scanPage không tồn tại trong scanner.js' }};
                        }}
                    }} catch (e) {{
                        return {{ error: 'JS Runtime Error: ' + e.message, stack: e.stack }};
                    }}
                }}
                """
                print(f"✅ VisionMachine: Sẵn sàng nội soi hệ thống.")
            else:
                print(f"⚠️ VisionMachine Warning: Không tìm thấy {js_path}")
                self.scanner_script = "async () => { return { error: 'Missing scanner.js' }; }"
        except Exception as e:
            print(f"❌ Vision Init Error: {e}")
            self.scanner_script = "async () => { return { error: 'Init script failed' }; }"
       


    async def scan_page(self, page, is_async=True): # Chuyển hẳn sang async def
        bot_name = "🎭 [Bot Diễn Viên]" if is_async else "🕵️ [Bot Trinh Sát]"
        print(f"{bot_name}: Đang nội soi giao diện...")
        
        try:
            # 1. ĐỢI MẠNG RẢNH (Phải có await)
            print(f"{bot_name}: Đang đợi dữ liệu tải xong (Network Idle)...")
            try:
                await page.wait_for_load_state('networkidle', timeout=15000) 
            except Exception:
                print(f"⚠️ {bot_name}: Đợi quá lâu, tiến hành quét cưỡng chế...")

            # 2. THỰC THI SCRIPT (Bắt buộc phải await page.evaluate)
            data = None
            for attempt in range(2):
                # QUAN TRỌNG: Phải có await ở đây!
                data = await page.evaluate(self.scanner_script) 
                
                # Kiểm tra data thật sau khi đã await
                if data and isinstance(data, dict) and "error" not in data:
                    break
                
                print(f"🔄 {bot_name}: Thử lại lần {attempt + 1}...")
                import asyncio
                await asyncio.sleep(1) # Dùng asyncio.sleep thay vì time.sleep

            # 3. XỬ LÝ HẬU KỲ
            if not data or (isinstance(data, dict) and "error" in data):
                msg = data.get('error', 'No data') if data else "Empty result"
                print(f"🛑 {bot_name} Lỗi quét trang tại {page.url}: {msg}")
                return None 

            # 4. TRẢ VỀ CỤC DATA CHUẨN
            result = {
                "url": page.url,
                "layout": data.get("main_content", data.get("layout", {})),
                "navigation": data.get("navigation", {}),
                "active_form": data.get("active_form", {}),
                "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"✅ {bot_name}: Đã lấy Metadata thành công.")
            return result

        except Exception as e:
            print(f"❌ Lỗi thực thi VisionMachine tại {bot_name}: {e}")
            return None

    
    async def check_health(self, page):
        """
        Kiểm tra nhanh xem trang có khả dụng (có UI) không.
        Sử dụng kết quả từ scan_page để đánh giá trạng thái trang.
        """
        # 1. Gọi hàm nội soi (Đảm bảo có await vì scan_page là async)
        data = await self.scan_page(page, is_async=True) 
        
        # 2. Kiểm tra nếu không lấy được dữ liệu
        if not data or not isinstance(data, dict):
            return False, ["Hệ thống quét bị lỗi hoặc trang không phản hồi."]
        
        # 3. Trích xuất dữ liệu an toàn (Dùng 'or {}' để tránh lỗi .get() trên None)
        layout = data.get('layout') or {}
        active_form = data.get('active_form') or {}
        
        # 4. Xác định nội dung chính đang hiển thị (Ưu tiên Form nếu đang mở)
        # Nếu layout có actions thì lấy layout, không thì soi vào Form
        main_content = layout if layout.get('actions') else active_form
        
        # 5. Kiểm tra các thành phần "sống" của UI
        # Check actions (nút bấm), inputs (ô nhập liệu) ở vùng nội dung chính
        has_actions = len(main_content.get('actions', [])) > 0
        has_inputs = len(main_content.get('inputs', [])) > 0
        
        # Check bảng dữ liệu (thường nằm trong layout)
        has_tables = len(layout.get('tables', [])) > 0

        # 6. Kết luận: Nếu không có nút, không có ô nhập, cũng chẳng có bảng -> Trang trống
        if not (has_actions or has_inputs or has_tables):
            return False, ["Trang trống (Empty State) hoặc chưa load xong các thành phần UI."]
            
        # Mọi thứ ổn định
        return True, []