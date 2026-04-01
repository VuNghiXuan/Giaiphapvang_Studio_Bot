import os
import json
from datetime import datetime

class VisionMachine:
    
       
    def __init__(self):
        """
        Khởi tạo 'con mắt' AI. 
        """
         
        self.scanner_script = ""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        js_path = os.path.join(current_dir, 'scanner.js')
        
        try:
            if os.path.exists(js_path):
                with open(js_path, 'r', encoding='utf-8') as f:
                    # Đọc toàn bộ nội dung scanner.js
                    content = f.read().strip()
                    
                    # SỬA Ở ĐÂY: Định nghĩa hàm scanPage VÀ thực thi nó luôn
                    # Chúng ta gán thẳng nội dung file JS vào, sau đó gọi hàm ở cuối
                    self.scanner_script = f"""
                    () => {{
                        {content}
                        if (typeof scanPage === 'function') {{
                            return scanPage();
                        }} else {{
                            return {{ error: 'Hàm scanPage không tồn tại trong scanner.js' }};
                        }}
                    }}
                    """
                print(f"👁️  VisionMachine: Đã nạp xong scanner.js (Bản Sync - Fix Scope)")
            else:
                self.scanner_script = "() => { return {state: {errors: ['No JS file']}}; }"
        except Exception as e:
            print(f"❌ Vision Init Error: {e}")

    def scan_page(self, page):
        """
        QUÉT ĐỒNG BỘ: Không dùng async/await. 
        Khi gọi page.evaluate, nó sẽ trả về kết quả ngay lập tức.
        """
        try:
            # 1. Thực thi script scanner.js trên trình duyệt
            data = page.evaluate(self.scanner_script)
            
            # 2. Xử lý dữ liệu trả về (Đảm bảo là dict để không lỗi gán key)
            if not data or not isinstance(data, dict):
                data = {}

            # 3. Gán timestamp (Vì data là dict thực, gán thoải mái không sợ lỗi coroutine)
            data['scanned_at'] = datetime.now().isoformat()
            
            # 4. Gia cố cấu trúc dữ liệu để tránh lỗi Key ở các Bot sau
            if 'state' not in data or data['state'] is None:
                data['state'] = {"has_overlay": False, "errors": []}
            
            for key in ['actions', 'form_fields']:
                if key not in data or data[key] is None:
                    data[key] = []
            
            return data
            
        except Exception as e:
            print(f"❌ Vision Error khi đang quét trang: {e}")
            return {"state": {"has_overlay": False, "errors": [str(e)]}, "actions": [], "form_fields": []}

    def check_health(self, page):
        """
        Kiểm tra nhanh xem trang có bị lỗi đỏ (Validation) không.
        """
        # GỌI ĐỒNG BỘ: Không dùng await
        data = self.scan_page(page)
        
        errors = data.get('state', {}).get('errors', [])
        if errors:
            return False, errors
        return True, []