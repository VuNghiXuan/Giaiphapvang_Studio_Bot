import os
import re
import shutil
from datetime import datetime
import json
from config import Config
from .db_engine import DBEngine
import traceback
import streamlit as st

class StudioController:
    def __init__(self):
        self.db = DBEngine()

    # --- QUẢN LÝ DỰ ÁN LỚN (TUTORIALS) ---
    def create_tutorial(self, title):
        # Sử dụng slugify từ Config để đồng nhất cách đặt tên folder
        folder_name = Config.slugify(title) 
        
        try:
            # 1. Kiểm tra DB
            existing = self.db.fetchone("SELECT id FROM tutorials WHERE folder_name = ?", (folder_name,))
            if not existing:
                res = self.db.execute("SELECT MAX(position) as max_pos FROM tutorials").fetchone()
                next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0
                
                self.db.execute(
                    "INSERT INTO tutorials (title, folder_name, position) VALUES (?, ?, ?)", 
                    (title, folder_name, next_pos)
                )
                self.db.commit()

            # 2. Tạo folder vật lý thông qua Config (Tự động mkdir -p)
            Config.get_path(app=folder_name)
            
            return True
        except Exception as e:
            print(f"❌ Lỗi create_tutorial: {e}")
            return False
        
    def get_all_tutorials(self):
        try:
            return self.db.execute("SELECT * FROM tutorials ORDER BY position ASC").fetchall()
        except Exception as e:
            print(f"❌ Lỗi get_all_tutorials: {e}")
            return []

    def delete_tutorial(self, t_id, folder_name):
        try:
            self.db.execute("DELETE FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            self.db.execute("DELETE FROM tutorials WHERE id = ?", (t_id,))
            self.db.commit()
            
            # Xóa folder vật lý bằng Pathlib
            full_path = Config.get_path(app=folder_name)
            if full_path.exists():
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_tutorial: {e}")
            return False
        
    # --- HELPERS ---   
    # def _to_safe_folder_name(self, text):
    #     if not text: return "unnamed"
    #     # 1. Chuyển tiếng Việt có dấu thành không dấu (đơn giản hóa)
    #     # Nếu có thư viện unidecode thì dùng, không thì dùng regex cơ bản
    #     s = text.lower()
    #     s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    #     s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    #     s = re.sub(r'[ìíịỉĩ]', 'i', s)
    #     s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    #     s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    #     s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    #     s = re.sub(r'[đ]', 'd', s)
    #     # 2. Thay thế ký tự đặc biệt và khoảng trắng bằng gạch dưới
    #     s = re.sub(r'[^a-z0-9\s]', '', s)
    #     s = re.sub(r'\s+', '_', s).strip('_')
    #     return s
    
    def _get_default_metadata(self):
        return {
            "page_info": {"url": "", "is_dialog_open": False, "sidebar_path": []},
            "available_actions": [], 
            "form_to_fill": [],
            "table_structure": {"has_data": False}, 
            "scanned_at": ""
        }
    
    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None, status="Chưa quay", module_name="Chung"):
        """
        Phiên bản Nâng cấp: Tự động xây dựng folder + Ghi nhận Module chính xác.
        """
        try:
            # 1. Tính toán vị trí hiển thị (Position)
            res = self.db.fetchone("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0
            
            # 2. Xử lý Metadata mặc định
            # Đảm bảo hàm _get_default_metadata() của ông vẫn tồn tại nhé
            final_metadata = self._get_default_metadata()
            if isinstance(metadata, dict): 
                final_metadata.update(metadata)
            
            # 3. XÂY DỰNG ĐƯỜNG DẪN LOGIC (Logic Path)
            # Tách chuỗi theo dấu '|' và làm sạch từng phần
            parts = [Config.slugify(p.strip()) for p in sub_title.split('|')]
            
            # Quy tắc đặc biệt của ông: 'chung' -> 'settings'
            if len(parts) > 1 and parts[1] == "chung": 
                parts[1] = "settings"
                
            logic_path = "/".join(parts)
            
            # 4. INSERT VÀO DATABASE (Đã thêm module_name)
            cursor = self.db.execute(
                """
                INSERT INTO sub_contents 
                (tutorial_id, module_name, sub_title, sub_folder, position, status, url, metadata) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t_id, 
                    module_name, # 👈 Đưa tên Module vào đây để Dashboard hiển thị chuẩn
                    sub_title, 
                    logic_path, 
                    next_pos, 
                    status, 
                    str(url or ""), 
                    json.dumps(final_metadata, ensure_ascii=False)
                )
            )
            new_id = cursor.lastrowid

            # 5. TẠO CẤU TRÚC THƯ MỤC VẬT LÝ (Giữ nguyên logic "Phòng thủ đa tầng")
            app_slug = parent_folder if parent_folder else Config.APP_SLUG
            base_module_path = Config.BASE_STORAGE / app_slug / logic_path
            
            assets_structure = ["raw", "outputs", "assets", "metadata"]
            
            for folder_type in assets_structure:
                target_path = base_module_path / folder_type
                target_path.mkdir(parents=True, exist_ok=True)
            
            self.db.commit()
            print(f"✅ [StudioDB]: Đã tạo thành công Form '{sub_title}' (Module: {module_name})")
            return new_id

        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {str(e)}")
            self.db.rollback()
            return False

    # --- CẬP NHẬT TRÍ THỨC (Đây là chỗ quan trọng để đồng bộ ảnh) ---
    def update_sub_content(self, sub_id: int, **kwargs):
        """
        Cập nhật tri thức mới cho Form. 
        Đồng bộ hóa metadata từ VisionMachine và Module danh mục.
        """
        try:
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: return False

            # 1. MAPPING THAM SỐ (Bổ sung module_name để không lọt lưới)
            new_url = kwargs.get('new_url') or kwargs.get('url')
            new_metadata = kwargs.get('new_metadata') or kwargs.get('metadata')
            new_status = kwargs.get('new_status') or kwargs.get('status')
            new_title = kwargs.get('new_title') or kwargs.get('title')
            new_module = kwargs.get('module_name') or kwargs.get('new_module') # 👈 THÊM DÒNG NÀY

            # 2. XỬ LÝ METADATA (Merge thông minh - Giữ nguyên logic của ông)
            old_meta = json.loads(current['metadata']) if current.get('metadata') else self._get_default_metadata()
            
            if new_metadata and isinstance(new_metadata, dict):
                if "environment" in new_metadata:
                    if "environment" not in old_meta: old_meta["environment"] = {}
                    old_meta["environment"].update(new_metadata["environment"])
                
                for key in ["session", "navigation", "main_content", "active_form"]:
                    if key in new_metadata: 
                        old_meta[key] = new_metadata[key]

                old_meta['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current['metadata']

            # 3. QUẢN LÝ TRẠNG THÁI (Status)
            status = new_status or current['status']
            if new_metadata and status == 'Chưa quay': 
                status = 'Đã quét'

            # 4. THỰC THI (SQL cập nhật thêm module_name)
            self.db.execute("""
                UPDATE sub_contents 
                SET sub_title = :title, 
                    status = :status, 
                    url = :url, 
                    metadata = :meta,
                    module_name = :mod_name  -- 👈 THÊM CỘT NÀY VÀO SQL
                WHERE id = :id
            """, {
                "id": sub_id, 
                "title": new_title or current['sub_title'],
                "status": status, 
                "url": str(new_url or current['url'] or ""),
                "meta": final_meta_str,
                "mod_name": new_module or current.get('module_name') # 👈 GÁN GIÁ TRỊ VÀO ĐÂY
            })
            
            self.db.commit()
            print(f"✅ [StudioDB]: ID {sub_id} đã nạp tri thức và cập nhật Module thành công.")
            return True

        except Exception as e:
            print(f"❌ Lỗi update_sub_content: {e}")
            self.db.rollback()
            return False
        
    def get_sub_contents(self, tutorial_id):
        try:
            rows = self.db.fetchall("SELECT * FROM sub_contents WHERE tutorial_id = ? ORDER BY position ASC", (tutorial_id,))
            results = []
            for row in rows:
                item = dict(row)
                try: meta = json.loads(item['metadata']) if item['metadata'] else {}
                except: meta = {}

                content = meta.get('content', {})
                state = meta.get('state', {})
                scroll = state.get('scroll_status', {})

                item['summary'] = {
                    "fields": len(content.get('form_fields', [])),
                    "actions": len(content.get('primary_actions', [])) + len(content.get('row_operations', [])),
                    "has_scroll": scroll.get('sidebar_can_scroll') or scroll.get('table_horizontal_scroll'),
                    "is_dialog": state.get('is_dialog_open', False)
                }
                item['metadata'] = meta
                results.append(item)
            return results
        except Exception as e:
            print(f"❌ Lỗi get_sub_contents: {e}")
            return []




    # --- HÀM BIÊN KỊCH: TRÁI TIM CỦA HỆ THỐNG ---
    def get_formatted_meta_for_ai(self, sub_id, director_notes="", target_goal="Thêm mới"):
        """
        Rút gọn tri thức và tích hợp ý đồ đạo diễn để AI soạn kịch bản chuẩn xác.
        target_goal: Thêm mới, Chỉnh sửa, Xóa, Xem báo cáo...
        """
        try:
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: return None
            sub = dict(row)

            raw_meta = json.loads(sub.get('metadata', '{}'))
            
            # --- 🔍 CHUYỂN ĐỔI DỮ LIỆU SANG NHÃN CHUẨN ---
            # Ưu tiên lấy từ sub_form_details (data ông đã quét), nếu không có mới lấy active_form
            form_data = raw_meta.get('sub_form_details') or raw_meta.get('active_form') or {}
            
            page_info = raw_meta.get('page_info', {})
            navigation = page_info.get('sidebar_path', [])
            
            # Lấy nhãn input (Bỏ rác "Không xác định")
            raw_inputs = form_data.get('inputs', [])
            form_inputs = [i['label'] for i in raw_inputs if i.get('label') and i.get('label') != "Không xác định"]
            
            # Lấy nhãn nút bấm
            form_buttons = [b.get('text') for b in form_data.get('buttons', []) if b.get('text')]
            main_buttons = [b.get('text') for b in raw_meta.get('buttons', []) if b.get('text')]
            
            # Slogan thương hiệu của ông Vũ
            slogan = Config.SLOGANT

            # --- 🎭 XÂY DỰNG PROMPT BIÊN KỊCH CHI TIẾT ---
            prompt = f"""
    ### 🎬 KỊCH BẢN VIDEO: {sub.get('sub_title')}
    **Slogan:** {slogan}
    **Mục tiêu nghiệp vụ:** {target_goal} (Đảm bảo các bước diễn phải phục vụ mục tiêu này).

    ---
    ### 📍 LỘ TRÌNH DI CHUYỂN (NAVIGATION)
    Trang Chủ -> {' -> '.join(navigation) if navigation else 'Vào module tương ứng'}

    ---
    ### 🔍 TRI THỨC HỆ THỐNG (LABELS CÓ THẬT)
    - **Các ô nhập liệu phát hiện:** {', '.join(form_inputs) or 'Không có'}
    - **Các nút bấm có thể tương tác:** {', '.join(list(set(main_buttons + form_buttons))) or 'Không có'}

    ---
    ### ✍️ LƯU Ý TỪ ĐẠO DIỄN VŨ:
    {director_notes if director_notes else "Thực hiện đúng luồng nghiệp vụ chuẩn, thao tác dứt khoát."}

    ---
    ### 📝 YÊU CẦU ĐẦU RA (JSON FORMAT):
    Hãy viết kịch bản JSON gồm 3 giai đoạn:
    1. **DI CHUYỂN**: Các bước click menu để vào đúng màn hình.
    2. **TƯƠNG TÁC**: Nhấn nút để mở form (ví dụ: Tạo mới), nhập liệu vào các trường [{', '.join(form_inputs)}] và chọn các giá trị mẫu phù hợp.
    3. **KẾT THÚC**: Nhấn nút xác nhận (Lưu/Cập nhật) và đọc câu slogan kết thúc.

    **Yêu cầu:** Chỉ được sử dụng các Label đã liệt kê ở trên. Tự suy luận giá trị nhập (value) phù hợp với nhãn trường.
    """
            return {
                "prompt_letter": prompt.strip(),
                "sub_id": sub_id,
                "raw_metadata": sub.get('metadata')
            }
        except Exception as e:
            print(f"❌ Lỗi biên kịch AI: {e}")
            return None

    def _format_form_for_ai(self, form_data):
        """Định dạng danh sách Form để AI dễ đọc"""
        if not isinstance(form_data, list):
            return "  - Không có form đang mở hoặc không phát hiện ô nhập liệu."
        
        lines = []
        for f in form_data:
            req = "[Bắt buộc]" if f.get('required') else ""
            lines.append(f"  - {f['label']} (Loại: {f['type']}) {req}")
        return "\n".join(lines) if lines else "  - Không có form đang mở."

    

    # --- HÀM QUAN TRỌNG: LÀM SẠCH DỮ LIỆU ĐỂ "MỚM" CHO AI ---
    def clean_metadata_for_ai(self, raw_data):
        if not raw_data: 
            return self._get_default_metadata()

        # 1. Bóc tách lộ trình (Navigation)
        nav = raw_data.get("navigation", {})
        # Thử lấy từ breadcrumbs, nếu không có thì hierarchy, không có nữa thì mảng rỗng
        sidebar_path = nav.get("breadcrumbs") or nav.get("hierarchy") or []

        # 2. Bóc tách Actions & Inputs
        main_content = raw_data.get("main_content", {})
        active_form = raw_data.get("active_form") or {}
        
        # Gom actions (Ưu tiên form trước)
        raw_actions = active_form.get("actions", []) + main_content.get("actions", [])
        clean_actions = []
        seen = set()
        for a in raw_actions:
            lbl = a.get("label")
            if lbl and lbl not in seen:
                clean_actions.append({"label": lbl, "is_primary": a.get("is_primary", False)})
                seen.add(lbl)

        # Gom inputs
        raw_inputs = active_form.get("inputs", []) if active_form else main_content.get("inputs", [])
        clean_inputs = [
            {"label": i.get("label"), "type": i.get("type", "text"), "required": i.get("required", False)}
            for i in raw_inputs if i.get("label")
        ]

        # Trả về ĐÚNG cấu trúc mà hàm get_formatted_meta_for_ai yêu cầu
        return {
            "page_info": {
                "url": raw_data.get("url") or raw_data.get("session", {}).get("url", ""),
                "is_dialog_open": raw_data.get("environment", {}).get("is_dialog", False) or bool(active_form),
                "sidebar_path": sidebar_path
            },
            "available_actions": clean_actions,
            "form_to_fill": clean_inputs,
            "table_structure": {
                "has_data": len(main_content.get("tables", [])) > 0
            }
        }
    
    def delete_sub_content(self, sub_id, folder_name, sub_folder):
        """
        FIX 3: Xóa cực kỳ an toàn, kiểm tra tồn tại trước khi rmtree
        """
        try:
            # Xóa trong DB trước
            self.db.execute("DELETE FROM sub_contents WHERE id = ?", (sub_id,))
            self.db.commit()
            
            if sub_folder:
                # Trỏ thẳng vào thư mục theo sub_folder trong DB
                full_path = Config.BASE_STORAGE / Config.APP_SLUG / sub_folder
                if full_path.exists() and full_path.is_dir():
                    shutil.rmtree(full_path)
                    print(f"🗑️ Đã xóa folder: {full_path}")
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_sub_content: {e}")
            return False

    def update_sub_content_metadata(self, sub_id, metadata):
        return self.update_sub_content(sub_id, metadata=metadata)
    
    def get_sub_by_title(self, title, t_id):
        sql = "SELECT * FROM sub_contents WHERE sub_title = ? AND tutorial_id = ?"
        return self.db.execute(sql, (title, t_id)).fetchone()
    
    def move_sub_content(self, sub_id, direction):
        """
        Thay đổi thứ tự hiển thị của sub_content (Form)
        Sửa lỗi: Ép kiểu sqlite3.Row sang dict để sử dụng được hàm .get()
        """
        try:
            # 1. Lấy item hiện tại từ DBEngine
            row = self.db.get_sub_content_by_id(sub_id)
            if not row:
                print(f"⚠️ Không tìm thấy sub_content với ID: {sub_id}")
                return False
            
            # Chuyển đổi sang dict để dùng .get() và tránh lỗi AttributeError
            current_item = dict(row)
            
            # Đảm bảo lấy đúng tutorial_id và position (mặc định là 0 nếu None)
            t_id = current_item.get('tutorial_id')
            current_pos = current_item.get('position')
            if current_pos is None: current_pos = 0

            # 2. Tìm item hàng xóm (phía trên hoặc phía dưới)
            target_row = self.db.get_neighbor_item(t_id, current_pos, direction)
            
            if target_row:
                target_item = dict(target_row)
                target_id = target_item.get('id')
                target_pos = target_item.get('position')

                if target_id is not None and target_pos is not None:
                    # 3. Thực hiện đổi chỗ position trong Database
                    # Gán position của thằng hàng xóm cho thằng hiện tại
                    self.db.update_position(sub_id, target_pos)
                    # Gán position cũ của thằng hiện tại cho thằng hàng xóm
                    self.db.update_position(target_id, current_pos)
                    
                    self.db.commit() # Lưu thay đổi xuống file DB
                    print(f"✅ Đã đổi chỗ ID {sub_id} ({current_pos}) với ID {target_id} ({target_pos})")
                    return True
            else:
                print(f"ℹ️ Không có item nào ở phía {direction} để đổi chỗ.")
                
        except Exception as e:
            print(f"❌ Lỗi move_sub_content: {e}")
            if hasattr(self.db, 'rollback'):
                self.db.rollback()
                
        return False
    
    # Trong file StudioController
    def get_all_modules(self):
        # Ưu tiên lấy từ cột module_name
        query = "SELECT DISTINCT module_name FROM sub_contents WHERE module_name IS NOT NULL"
        result = self.db.fetchall(query)
        
        if not result or len(result) == 0:
            # Nếu chưa có dữ liệu ở cột mới, dùng tạm logic cũ để người dùng không thấy trống
            query_backup = "SELECT DISTINCT sub_title FROM sub_contents WHERE sub_title LIKE '%|Home%'"
            res_backup = self.db.fetchall(query_backup)
            return sorted(list(set([r['sub_title'].split('|')[0].strip() for r in res_backup])))
            
        return [row['module_name'] for row in result]

    def get_forms_by_module(self, module_name):
        """Lấy danh sách form theo module"""
        query = "SELECT sub_title FROM sub_contents WHERE module_name = ?"
        try:
            result = self.db.fetchall(query, (module_name,))
            if not result: return []
            return [{"sub_title": row['sub_title']} for row in result]
        except Exception as e:
            print(f"Lỗi get_forms_by_module: {e}")
            return []
    