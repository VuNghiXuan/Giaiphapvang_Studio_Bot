import os
import json
import asyncio
from datetime import datetime
from config import Config 

class VisionMachine:
    def __init__(self):
        self.scanner_script = ""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(current_dir, 'scanner.js')
        
        try:
            if os.path.exists(js_path):
                print('--- [👁️] Đang nạp tri thức từ scanner.js ---')
                with open(js_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                self.scanner_script = f"""
                async () => {{
                    try {{
                        {content}
                        if (typeof scanPage === 'function') {{
                            return await scanPage();
                        }}
                        return {{ error: 'Hàm scanPage không tồn tại' }};
                    }} catch (e) {{
                        return {{ error: 'JS Error: ' + e.message }};
                    }}
                }}
                """
                print(f"✅ VisionMachine: Đã sẵn sàng.")
            else:
                self.scanner_script = "async () => { return { error: 'Missing scanner.js' }; }"
        except Exception as e:
            print(f"❌ Vision Init Error: {e}")

    async def _execute_scan(self, page, is_acting: bool):
        """Hàm thực thi lõi - Trái tim của hệ thống quét"""
        bot_tag = "🎭 [Bot Diễn Viên]" if is_acting else "🕵️ [Bot Trinh Sát]"
        
        if page.is_closed():
            print(f"🛑 {bot_tag}: Trình duyệt đã đóng.")
            return None

        try:
            # 1. Đợi trạng thái mạng ổn định
            try:
                await page.wait_for_load_state('networkidle', timeout=8000) 
            except:
                pass 

            # 2. Cấy vai diễn vào Browser trước khi thực thi
            await page.evaluate(f"window.isBotActing = {'true' if is_acting else 'false'};")

            # 3. Thực thi nội soi
            data = await page.evaluate(self.scanner_script)
            
            if not data or "error" in data:
                print(f"🛑 {bot_tag} Lỗi: {data.get('error', 'No data')}")
                return None

            # 4. Đóng gói kết quả chuẩn hóa
            return {
                "url": page.url,
                "mode": "ACTOR" if is_acting else "SCOUT",
                "layout": data.get("main_content", {}),
                "navigation": data.get("navigation", {}),
                "active_form": data.get("active_form", {}),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"❌ {bot_tag} Exception: {e}")
            return None

    async def scout_report(self, page):
        """
        NHIỆM VỤ BOT TRINH SÁT:
        - Quét sâu (Deep Scan), tự click vào các nút 'Thêm/Sửa' để lấy Metadata của Form ẩn.
        - Phục vụ giai đoạn lập kịch bản sản xuất.
        """
        print("🕵️ [Bot Trinh Sát]: Đang đi thám thính cấu trúc trang...")
        return await self._execute_scan(page, is_acting=False)

    async def actor_view(self, page):
        """
        NHIỆM VỤ BOT DIỄN VIÊN:
        - Quét nhanh bề mặt (Current View), lấy tọa độ chính xác để AI tương tác.
        - Phục vụ giai đoạn quay phim/quay màn hình video tự động.
        """
        print("🎭 [Bot Diễn Viên]: Đang đo đạc tọa độ để diễn...")
        return await self._execute_scan(page, is_acting=True)

    
    async def check_health(self, page):
        """Kiểm tra nhanh xem trang có rỗng hay không bằng Actor View"""
        data = await self.actor_view(page)
        if not data: return False, ["Lỗi kết nối"]
        
        layout = data.get('layout', {})
        has_ui = len(layout.get('actions', [])) > 0 or len(layout.get('inputs', [])) > 0
        
        if not has_ui:
            return False, ["Trang trống hoặc chưa load UI"]
        return True, []