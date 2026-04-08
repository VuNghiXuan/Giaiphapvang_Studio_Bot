import os
import json
import sqlite3
import asyncio
from datetime import datetime
from config import Config 

class VisionMachine:
    def __init__(self):
        # Thiết lập đường dẫn JS
        self.js_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js')
        # Cache scripts để không phải đọc file liên tục
        self._scripts_cache = {}
        print(f"--- [👁️] VisionMachine khởi tạo thành công tại: {self.js_dir} ---")

    def _get_combined_script(self, engine_type):
        """
        Kết hợp base_utils + engine chuyên biệt.
        engine_type: 'scout_engine' hoặc 'actor_engine'
        """
        if engine_type in self._scripts_cache:
            return self._scripts_cache[engine_type]

        try:
            base_utils_path = os.path.join(self.js_dir, 'base_utils.js')
            engine_path = os.path.join(self.js_dir, f'{engine_type}.js')

            js_code = ""
            # 1. Nạp Utils
            if os.path.isfile(base_utils_path):
                with open(base_utils_path, 'r', encoding='utf-8') as f:
                    js_code += f.read() + "\n"
            
            # 2. Nạp Engine
            if os.path.isfile(engine_path):
                with open(engine_path, 'r', encoding='utf-8') as f:
                    js_code += f.read()
            else:
                raise FileNotFoundError(f"Không tìm thấy file: {engine_path}")

            # 3. Đóng gói vào Anonymous Async Function
            final_script = f"""
            async () => {{
                try {{
                    {js_code}
                    if (typeof scanPage === 'function') {{
                        return await scanPage();
                    }}
                    return {{ error: 'Hàm scanPage() không tồn tại trong {engine_type}' }};
                }} catch (e) {{
                    return {{ error: 'JS Exception in {engine_type}: ' + e.stack }};
                }}
            }}
            """
            self._scripts_cache[engine_type] = final_script
            return final_script
        except Exception as e:
            return f"async () => {{ return {{ error: 'Python Load Error: {str(e)}' }}; }}"

    async def _execute_scan(self, page, is_acting: bool, context: dict = None):
        if context is None: context = {}
        tag = "🎭 [Actor]" if is_acting else "🕵️ [Scout]"
        
        if page.is_closed():
            print(f"🛑 {tag}: Browser closed.")
            return None

        try:
            # --- FIX LỖI .catch(): Dùng try/except chuẩn Python ---
            try:
                # Chờ network ổn định tối đa 3 giây
                await page.wait_for_load_state('networkidle', timeout=3000)
            except Exception:
                # Nếu timeout thì cứ tiếp tục, không sao cả
                pass
            
            # Lấy script tương ứng
            engine_name = "actor_engine" if is_acting else "scout_engine"
            script = self._get_combined_script(engine_name)
            
            # Tiêm biến môi trường
            await page.evaluate(f"window.isBotActing = {'true' if is_acting else 'false'};")
            
            # Chạy script (Nên dùng wait_for_function nếu cần đợi kết quả JS)
            data = await page.evaluate(script)
            
            if not data or "error" in data:
                print(f"⚠️ {tag} JS Error: {data.get('error') if data else 'Null output'}")
                return data

            # --- QUẢN LÝ TÀI NGUYÊN ---
            crumbs = data.get("navigation", {}).get("breadcrumbs", [])
            form_identity = context.get("form", crumbs[-1] if crumbs else "Main_Dashboard")
            
            storage_dir = context.get("target_dir")
            if not storage_dir:
                sub_folder = context.get("parent_folder", "General_Session")
                storage_dir = os.path.join(Config.BASE_STORAGE, sub_folder, "vision_assets")
            
            os.makedirs(storage_dir, exist_ok=True)
            
            mode_prefix = "actor" if is_acting else "scout"
            file_name = f"{mode_prefix}_{form_identity.replace(' ', '_')}_view.png"
            full_path = os.path.join(storage_dir, file_name)
            
            await page.screenshot(path=full_path)
            relative_screenshot = os.path.relpath(full_path, Config.BASE_STORAGE)

            return {
                "session": {
                    "url": page.url,
                    "app": context.get("app", "Giaiphapvang"),
                    "form": form_identity,
                    "mode": "ACTOR" if is_acting else "SCOUT",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "navigation": data.get("navigation", {}),
                "main_content": data.get("main_content", {}), 
                "active_form": data.get("active_form", {}),
                "environment": {
                    "screenshot": relative_screenshot,
                    "viewport": page.viewport_size
                }
            }

        except Exception as e:
            print(f"❌ {tag} System Error: {e}")
            return None

    # --- WRAPPERS ---
    async def scout_report(self, page, context=None):
        """Dùng để quét toàn bộ hệ thống tạo Knowledge Base"""
        res = await self._execute_scan(page, is_acting=False, context=context)
        if res and "error" not in res:
            await self.save_to_knowledge(res)
        return res

    async def actor_view(self, page, context=None):
        """Dùng trong lúc đang quay phim/diễn viên hành động"""
        res = await self._execute_scan(page, is_acting=True, context=context)
        if res and "error" not in res:
            await self.save_to_knowledge(res)
        return res

    async def save_to_knowledge(self, scan_result):
        """Lưu tri thức vào SQLite"""
        if not scan_result: return
        
        ss = scan_result["session"]
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                cursor = conn.cursor()
                # Tự động tạo bảng nếu chưa có
                cursor.execute('''CREATE TABLE IF NOT EXISTS knowledge_base 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     app_name TEXT, 
                     form_name TEXT, 
                     metadata_json TEXT, 
                     screenshot_path TEXT, 
                     url TEXT, 
                     updated_at DATETIME,
                     UNIQUE(app_name, form_name, url))''')

                # Upsert dữ liệu (Nếu trùng URL + Form thì cập nhật bản mới nhất)
                sql = '''INSERT INTO knowledge_base 
                         (app_name, form_name, metadata_json, screenshot_path, url, updated_at)
                         VALUES (?, ?, ?, ?, ?, ?)
                         ON CONFLICT(app_name, form_name, url) DO UPDATE SET
                         metadata_json=excluded.metadata_json,
                         screenshot_path=excluded.screenshot_path,
                         updated_at=excluded.updated_at'''
                
                cursor.execute(sql, (
                    ss["app"], 
                    ss["form"],
                    json.dumps(scan_result, ensure_ascii=False),
                    scan_result["environment"]["screenshot"],
                    ss["url"],
                    ss["timestamp"]
                ))
                conn.commit()
        except Exception as e:
            print(f"❌ [DB Error]: {e}")