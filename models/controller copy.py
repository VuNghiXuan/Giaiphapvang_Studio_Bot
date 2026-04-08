import os
import shutil
from datetime import datetime
import json
from config import Config
from .db_engine import DBEngine
import traceback

class StudioController:
    def __init__(self):
        self.db = DBEngine()

    # --- QUẢN LÝ DỰ ÁN LỚN (TUTORIALS) ---
    def create_tutorial(self, title):
        folder_name = "".join([c if c.isalnum() else "_" for c in title])
        full_path = os.path.join(Config.BASE_STORAGE, folder_name)
        try:
            res = self.db.execute("SELECT MAX(position) as max_pos FROM tutorials").fetchone()
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0
            
            self.db.execute(
                "INSERT INTO tutorials (title, folder_name, position) VALUES (?, ?, ?)", 
                (title, folder_name, next_pos)
            )
            os.makedirs(full_path, exist_ok=True)
            self.db.commit()
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
            full_path = os.path.join(Config.BASE_STORAGE, folder_name)
            if os.path.exists(full_path): shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_tutorial: {e}")
            return False

    # --- HELPERS ---
    # def _get_default_metadata(self):
    #     """Khung Metadata chuẩn OMNI 2026 - Đồng bộ tuyệt đối với VisionMachine"""
    #     return {
    #         "navigation": {"url": "", "hierarchy": [], "current_page": ""},
    #         "state": {"has_overlay": False, "is_dialog_open": False, "errors": []},
    #         "layout": {
    #             "sidebar": {"items": [], "has_scroll": False},
    #             "main_content": {
    #                 "actions": [], "row_operations": [], "inputs": [], "tables": []
    #             },
    #             "active_form": None 
    #         },
    #         "scanned_at": ""
    #     }

    def _get_default_metadata(self):
        return {
            "navigation": {"url": "", "breadcrumbs": [], "sidebar_items": []},
            "state": {"is_dialog_open": False, "has_data": False},
            "layout": {"actions": [], "inputs": [], "tables": []},
            "scanned_at": ""
        }
    
    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None):
        try:
            # Check trùng URL để tránh tạo rác
            if url and url.strip() != "":
                existing = self.db.fetchone(
                    "SELECT id FROM sub_contents WHERE tutorial_id = ? AND url = ?", 
                    (t_id, url)
                )
                if existing: return existing['id'] 

            res = self.db.fetchone("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0

            # Khởi tạo Metadata
            final_metadata = self._get_default_metadata()
            if isinstance(metadata, dict):
                final_metadata.update(metadata)
            
            meta_str = json.dumps(final_metadata, ensure_ascii=False)

            query = """
                INSERT INTO sub_contents (tutorial_id, sub_title, sub_folder, position, status, url, metadata)
                VALUES (:t_id, :title, '', :pos, 'Chưa quay', :url, :meta)
            """
            cursor = self.db.execute(query, {
                "t_id": t_id, "title": sub_title, "pos": next_pos, 
                "url": str(url or ""), "meta": meta_str
            })
            new_id = cursor.lastrowid

            # Tạo cấu trúc thư mục chuẩn cho Video Production
            safe_title = "".join([c if c.isalnum() else "_" for c in sub_title])
            unique_folder_name = f"{new_id}_{safe_title}"
            self.db.execute("UPDATE sub_contents SET sub_folder = ? WHERE id = ?", (unique_folder_name, new_id))

            full_sub_path = os.path.join(Config.BASE_STORAGE, parent_folder, unique_folder_name)
            for sub_f in ["raw", "outputs", "assets", "metadata"]:
                os.makedirs(os.path.join(full_sub_path, sub_f), exist_ok=True)
            
            self.db.commit()
            return new_id
        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            self.db.rollback()
            return False

    def update_sub_content(self, sub_id: int, **kwargs):
        """
        Hàm vạn năng: Cập nhật thông tin cơ bản VÀ bồi đắp Metadata tri thức.
        """
        try:
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: return False

            # 1. Khôi phục Metadata hiện tại từ DB
            try:
                old_meta = json.loads(current['metadata']) if current['metadata'] else self._get_default_metadata()
            except:
                old_meta = self._get_default_metadata()

            # 2. Xử lý Metadata mới từ VisionMachine (nếu có)
            new_meta = kwargs.get('metadata')
            if new_meta and isinstance(new_meta, dict):
                # CẬP NHẬT TRỰC DIỆN: Ghi đè các nhánh tri thức mới nhất từ VisionMachine
                # Navigation: URL, Breadcrumb...
                if "navigation" in new_meta:
                    old_meta["navigation"].update(new_meta["navigation"])
                
                # Layout: Các nút bấm, ô nhập liệu cào được
                if "layout" in new_meta:
                    # Nếu có active_form (vừa nội soi xong), ta ưu tiên giữ lại form đó
                    old_meta["layout"].update(new_meta["layout"])
                
                # State: Trạng thái UI
                if "state" in new_meta:
                    old_meta["state"].update(new_meta["state"])

                old_meta['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current['metadata']

            # 3. Quản lý Trạng thái (Status)
            status = kwargs.get('status') or current['status']
            # Nếu vừa nạp Metadata vào và status đang là 'Chưa quay' -> Chuyển thành 'Đã quét'
            if new_meta and status == 'Chưa quay':
                status = 'Đã quét'

            # 4. Thực thi UPDATE
            params = {
                "id": sub_id,
                "title": kwargs.get('title') or current['sub_title'],
                "status": status,
                "url": str(kwargs.get('url') or current['url'] or ""),
                "meta": final_meta_str
            }

            self.db.execute("""
                UPDATE sub_contents 
                SET sub_title = :title, status = :status, url = :url, metadata = :meta 
                WHERE id = :id
            """, params)
            
            self.db.commit()
            print(f"💾 [DB] Đã cập nhật tri thức cho SubID: {sub_id}")
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
    def get_formatted_meta_for_ai(self, sub_id):
        """
        [PHIÊN BẢN STUDIO CHUYÊN NGHIỆP - FIX LUỒNG NAVIGATION]
        Hợp nhất: Metadata + Navigation Flow (Đăng nhập > Menu > Submenu) + Business Logic.
        """
        try:
            # 1. Lấy dữ liệu Content từ DB
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: return None
            sub = dict(row)

            # 2. Parse và làm sạch Metadata
            raw_meta = json.loads(sub.get('metadata', '{}'))
            clean_meta = self.clean_metadata_for_ai(raw_meta)
            
            # 3. Chuẩn bị Luồng điều hướng (Navigation Path)
            p_info = clean_meta['page_info']
            # Kết hợp Đăng nhập + Sidebar Path để tạo thành chuỗi hành động
            # Ví dụ: ["Đăng nhập", "Hệ thống", "Thông tin công ty", "Chi nhánh"]
            full_navigation_flow = ["Đăng nhập thành công"] + p_info.get('sidebar_path', [])
            
            sidebar_desc = " > ".join(full_navigation_flow)
            
            input_labels = [i['label'] for i in clean_meta['form_to_fill']]
            all_actions = clean_meta['available_actions']
            action_labels = [a['label'] for a in all_actions]
            if 'Lưu' not in action_labels: action_labels.append('Lưu')

            # Nút mở form
            primary_btn = next((a for a in all_actions if any(kw in a['label'].lower() for kw in ['tạo', 'thêm', 'mới'])), None)
            p_btn_label = primary_btn['label'] if primary_btn else "Tạo mới"

            # Trạng thái UI
            is_dialog = p_info.get('is_dialog_open', False)

            # --- 4. SOẠN THẢO PROMPT "ĐẠO DIỄN VŨ" ---
            prompt = f"""
### 🎬 STUDIO PRODUCTION: {sub.get('sub_title')}
**Slogan:** {sub.get('slogan', 'Giải Pháp Vàng - Quản lý thông minh')}
**Mục tiêu Workflow:** {sub.get('workflow_custom', 'Hướng dẫn người dùng thao tác từ lúc đăng nhập')}

---
### 📍 1. BỐI CẢNH & LỘ TRÌNH ĐIỀU HƯỚNG (PHẢI THEO ĐÚNG THỨ TỰ)
Lộ trình thực tế để đến được màn hình này:
**{sidebar_desc}**

---
### ✍️ 2. GHI CHÚ TỪ ĐẠO DIỄN VŨ
> {sub.get('director_notes', 'Diễn đạt tự nhiên, tập trung vào sự tiện lợi.')}
> **Lưu ý:** AI phải bắt đầu từ bước xác nhận Đăng nhập thành công, sau đó mới đi vào các menu.

---
### 🔍 3. DANH SÁCH NHÃN KỸ THUẬT (KHỚP 100%)
- **Luồng Menu:** {", ".join([f"'{l}'" for l in full_navigation_flow])}
- **Input Form:** {", ".join([f"'{l}'" for l in input_labels])}
- **Nút hành động:** {", ".join([f"'{l}'" for l in action_labels])}

---
### 📝 4. YÊU CẦU KỊCH BẢN (JSON ARRAY ONLY)
Trả về một mảng JSON phẳng. Thực hiện theo 4 GIAI ĐOẠN:

**GIAI ĐOẠN A: KHỞI ĐẦU**
- Bước 1: Thông báo đăng nhập thành công và chào mừng (kèm slogan).

**GIAI ĐOẠN B: ĐIỀU HƯỚNG SIDEBAR**
- Dựa vào lộ trình: {sidebar_desc}.
- Tạo các bước click tuần tự vào từng thẻ/menu con để mở đúng trang mục tiêu.

**GIAI ĐOẠN C: MỞ FORM & NHẬP LIỆU**
- Nếu trang chưa mở Form (is_dialog=False), phải có bước click '{p_btn_label}'.
- Nhập liệu các trường: {", ".join(input_labels)} bằng dữ liệu mẫu ngành vàng thực tế.

**GIAI ĐOẠN D: HOÀN TẤT**
- Click 'Lưu' và đưa ra lời kết thân thiện.

**Ví dụ:**
[
  {{"step": 1, "vo": "Chào mừng bạn đến với phần mềm Giải Pháp Vàng. Sau khi đăng nhập thành công, tại trang Home...", "action": "click", "target_label": "Hệ thống", "value": ""}},
  {{"step": 2, "vo": "Bạn nhấn vào menu Thông tin công ty, sau đó chọn Chi nhánh.", "action": "click", "target_label": "Chi nhánh", "value": ""}}
]
"""
            return {
                "prompt_letter": prompt, 
                "clean_metadata": clean_meta,
                "sub_data": sub 
            }

        except Exception as e:
            print(f"❌ Lỗi get_formatted_meta_for_ai: {e}")
            import traceback
            traceback.print_exc()
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
        """
        Gọt sạch tọa độ, chỉ để lại nhãn (labels) và LỘ TRÌNH LUỒNG (Navigation Flow).
        """
        if not raw_data: return self._get_default_metadata()

        # 1. Bóc tách lộ trình
        nav = raw_data.get("navigation", {})
        sidebar_path = nav.get("breadcrumbs") or nav.get("hierarchy") or []

        # 2. Bóc tách các nút bấm (Actions)
        layout = raw_data.get("layout", {})
        active_form = raw_data.get("active_form") or {}
        
        # Nếu có form, ưu tiên lấy actions của form trước
        raw_actions = layout.get("actions", [])
        if active_form:
            raw_actions = active_form.get("actions", []) + raw_actions

        # Lọc trùng label để AI không bị loạn
        seen_labels = set()
        clean_actions = []
        for a in raw_actions:
            lbl = a.get("label")
            if lbl and lbl not in seen_labels:
                clean_actions.append({
                    "label": lbl, 
                    "is_primary": a.get("is_primary", False)
                })
                seen_labels.add(lbl)

        # 3. Bóc tách ô nhập liệu (Ưu tiên Form nếu đang mở)
        raw_inputs = active_form.get("inputs", []) if active_form else layout.get("inputs", [])
        clean_inputs = [
            {"label": i.get("label"), "type": i.get("type", "text"), "required": i.get("required", False)}
            for i in raw_inputs if i.get("label")
        ]

        # 4. Kiểm tra trạng thái bảng
        tables = layout.get("tables", [])
        has_data = False
        if tables and isinstance(tables, list):
            has_data = tables[0].get("count", 0) > 0

        return {
            "page_info": {
                "url": raw_data.get("url"),
                "is_dialog_open": raw_data.get("state", {}).get("is_dialog_open", False) or bool(active_form),
                "sidebar_path": sidebar_path
            },
            "available_actions": clean_actions,
            "form_to_fill": clean_inputs,
            "table_structure": {
                "has_data": has_data
            }
        }
    
    def delete_sub_content(self, sub_id, folder_name, sub_folder):
        try:
            self.db.execute("DELETE FROM sub_contents WHERE id = ?", (sub_id,))
            self.db.commit()
            full_path = os.path.join(Config.BASE_STORAGE, folder_name, sub_folder)
            if os.path.exists(full_path): shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_sub_content: {e}")
            return False

    def update_sub_content_metadata(self, sub_id, metadata):
        return self.update_sub_content(sub_id, metadata=metadata)