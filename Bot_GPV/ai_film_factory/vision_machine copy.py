import os
import json
from datetime import datetime
from config import Config 
import asyncio

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
       
    async def scan_page(self, page, is_async=True):
        bot_name = "🎭 [Bot Diễn Viên]" if is_async else "🕵️ [Bot Trinh Sát]"
        
        # 1. KIỂM TRA SINH TỒN (Quan trọng nhất để tránh WebSocketClosedError)
        if page.is_closed():
            print(f"🛑 {bot_name}: Trình duyệt đã đóng, hủy quét tại {page.url}")
            return None

        print(f"{bot_name}: Đang nội soi giao diện...")
        
        try:
            # 2. ĐỢI MẠNG RẢNH (Phải có await và bọc try-catch nội bộ)
            try:
                # Giảm timeout xuống một chút để tránh treo WebSocket của Streamlit
                await page.wait_for_load_state('networkidle', timeout=10000) 
            except Exception:
                print(f"⚠️ {bot_name}: Timeout load mạng, quét cưỡng chế...")

            # 3. THỰC THI SCRIPT VỚI CƠ CHẾ BẢO VỆ
            data = None
            for attempt in range(2):
                try:
                    # Kiểm tra lại lần nữa trước khi evaluate
                    if page.is_closed(): break 

                    # CẤY BIẾN ĐỊNH DANH TRƯỚC KHI QUÉT
                    acting_js = "true" if is_async else "false"
                    await page.evaluate(f"window.isBotActing = {acting_js};")
                    
                    
                    data = await page.evaluate(self.scanner_script) 
                    
                    if data and isinstance(data, dict) and "error" not in data:
                        break
                except Exception as eval_e:
                    # Nếu lỗi do trình duyệt đóng bất ngờ (Target closed)
                    if "closed" in str(eval_e).lower() or "context" in str(eval_e).lower():
                        print(f"🛑 {bot_name}: Trình duyệt sập giữa chừng.")
                        return None
                    print(f"🔄 {bot_name}: Thử lại hiệp {attempt + 1} do: {eval_e}")
                
                await asyncio.sleep(1)

            # 4. KIỂM TRA DỮ LIỆU CUỐI CÙNG
            if not data or (isinstance(data, dict) and "error" in data):
                msg = data.get('error', 'No data') if data else "Empty result"
                print(f"🛑 {bot_name} Lỗi quét trang: {msg}")
                return None 

            # 5. ĐÓNG GÓI DỮ LIỆU (Giữ nguyên logic của Vũ)
            result = {
                "url": page.url,
                "layout": data.get("main_content", data.get("layout", {})),
                "navigation": data.get("navigation", {}),
                "active_form": data.get("active_form", {}),
                "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"✅ {bot_name}: Nội soi thành công.")
            return result

        except Exception as e:
            print(f"❌ Lỗi tổng tại VisionMachine: {e}")
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