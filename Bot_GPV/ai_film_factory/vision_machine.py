import os
import json
from datetime import datetime

class VisionMachine:
    def __init__(self):
        self.js_content = ""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(current_dir, 'scanner.js')
        
        try:
            if os.path.exists(js_path):
                with open(js_path, 'r', encoding='utf-8') as f:
                    self.js_content = f.read().strip()
                print(f"👁️ VisionMachine: Đã nạp tri thức từ scanner.js")
            else:
                print(f"❌ VisionMachine: Không tìm thấy file {js_path}")
        except Exception as e:
            print(f"❌ Vision Init Error: {e}")

    def scan_page(self, page):
        """
        Thực thi scanner.js (Async) và đợi kết quả metadata.
        """
        try:
            # Sửa script thành async lambda để await kết quả từ window.scanPage()
            script = f"""
            async () => {{
                {self.js_content}
                if (typeof window.scanPage === 'function') {{
                    return await window.scanPage();
                }} else if (typeof scanPage === 'function') {{
                    return await scanPage();
                }}
                return {{ error: 'Hàm scanPage không tồn tại' }};
            }}
            """
            # Playwright sẽ đợi Promise này resolve rồi mới gán vào data
            data = page.evaluate(script)
            
            if not data or not isinstance(data, dict): 
                data = {}
            
            # Gán timestamp và gia cố cấu trúc
            data['scanned_at'] = datetime.now().isoformat()
            for key in ['actions', 'form_fields', 'columns']:
                if key not in data: 
                    data[key] = []
            
            return data
        except Exception as e:
            print(f"❌ Vision Scan Error: {e}")
            return {"actions": [], "form_fields": [], "columns": [], "error": str(e)}