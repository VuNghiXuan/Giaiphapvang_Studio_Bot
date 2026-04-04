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
    def _get_default_metadata(self):
        """Khung Metadata chuẩn OMNI 2026 - Đồng bộ tuyệt đối với VisionMachine"""
        return {
            "navigation": {"url": "", "hierarchy": [], "current_page": ""},
            "state": {"has_overlay": False, "is_dialog_open": False, "errors": []},
            "layout": {
                "sidebar": {"items": [], "has_scroll": False},
                "main_content": {
                    "actions": [], "row_operations": [], "inputs": [], "tables": []
                },
                "active_form": None 
            },
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


    # def get_formatted_meta_for_ai(self, sub_id):
    #     """
    #     BỨC THƯ CHI TIẾT GỬI AI v2.0 - Biến Metadata thành Kịch bản điện ảnh.
    #     """
    #     try:
    #         sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
    #         if not sub or not sub['metadata']: return None
            
    #         meta = json.loads(sub['metadata'])
    #         nav = meta.get("navigation", {})
    #         layout = meta.get("layout", {})
    #         main = layout.get("main_content", {})
    #         active_form = layout.get("active_form", {})

    #         # --- 1. PHÂN TÍCH THỊ GIÁC (VISUAL ANALYSIS) ---
    #         sidebar_info = nav.get("sidebar", {})
    #         sidebar_desc = "Cố định bên trái"
    #         if sidebar_info.get("has_scroll"):
    #             sidebar_desc += " (Menu dài, cần cuộn chuột để thấy hết các mục)"

    #         # Phân tích Bảng & Trạng thái rỗng
    #         tables = main.get("tables", [])
    #         table_desc = []
    #         is_empty_state = True
    #         for t in tables:
    #             cols = t.get("columns", [])
    #             if cols: is_empty_state = False
    #             scroll = "Bảng rộng, cần hướng dẫn kéo thanh cuộn ngang" if t.get("needs_h_scroll") else "Hiển thị gọn trong màn hình"
    #             table_desc.append(f"Bảng có {len(cols)} cột [{', '.join(cols[:5])}...]. Đặc điểm: {scroll}.")

    #         # Phân tích nút quan trọng (Primary Actions)
    #         all_actions = main.get("actions", [])
    #         primary_btn = next((a for a in all_actions if a.get('is_primary')), None)
    #         special_actions = [a.get('label') for a in all_actions if any(x in a.get('label', '').lower() for x in ['xuất', 'cột', 'lọc', 'mật độ'])]

    #         # --- 2. PHÂN TÍCH FORM CHI TIẾT ---
    #         form_info = ""
    #         if active_form:
    #             fields = active_form.get('inputs', [])
    #             btns = active_form.get('actions', [])
    #             form_info = f"""
    #     - Tên Form/Dialog: {active_form.get('context_name', 'Form nhập liệu')}
    #     - Danh sách {len(fields)} trường: {', '.join([f"{i.get('label')} ({'Bắt buộc' if i.get('required') else 'Tùy chọn'})" for i in fields])}
    #     - Nút xác nhận: {', '.join([f"{b.get('label')} (Màu: {b.get('rect', {}).get('bg_color')})" for b in btns])}
    #     - Logic Validation: Nếu bỏ trống trường bắt buộc, hệ thống sẽ báo lỗi chữ đỏ tại label của trường đó.
    #             """

    #         # --- 3. SOẠN THẢO BỨC THƯ (PROMPT BIÊN KỊCH) ---
    #         prompt = f"""
    # # NHIỆM VỤ: VIẾT KỊCH BẢN QUAY PHIM & LỜI THOẠI HƯỚNG DẪN SỬ DỤNG
    # Mục tiêu: {sub['sub_title']}
    # Trạng thái trang: {"[TRANG TRỐNG - Hướng dẫn tạo mới dữ liệu]" if is_empty_state else "[CÓ DỮ LIỆU - Hướng dẫn quản lý/tra cứu]"}

    # ## 1. BỐI CẢNH (CONTEXT)
    # - URL: {nav.get('url')}
    # - Lộ trình: {" > ".join(nav.get('breadcrumbs', []))}
    # - Sidebar: {sidebar_desc}

    # ## 2. QUAN SÁT GIAO DIỆN (MAIN UI)
    # - Bảng dữ liệu: {'; '.join(table_desc) if table_desc else "Không phát hiện bảng."}
    # - Nút hành động chính: {primary_btn.get('label') if primary_btn else "Không có nút nổi bật."}
    # - Thao tác trên từng dòng: {", ".join([a.get('label') for a in main.get('row_operations', [])])}
    # - Công cụ: {", ".join(special_actions)} (Hướng dẫn người dùng Xuất Excel hoặc Ẩn/Hiện cột nếu cần).

    # ## 3. CHI TIẾT NỘI SOI FORM (DEEP SCAN)
    # {form_info if form_info else "- Không có Form đang mở hoặc không có Form ẩn."}

    # ## 4. YÊU CẦU KỊCH BẢN (STORYLINE)
    # Hãy soạn kịch bản chi tiết bao gồm:
    # 1. Lời thoại (Voice-over): Chuyên nghiệp, chậm rãi. (Ví dụ: "Chào mừng quý khách... Hãy nhìn vào nút {primary_btn.get('label') if primary_btn else 'Tạo mới'}...")
    # 2. Hành động (Action): Mô tả chính xác vị trí chuột (Dựa vào nhãn hoặc tọa độ trong JSON).
    # 3. Chỉ dẫn vật lý: Mô tả màu sắc nút (Hex color) để người xem dễ nhận diện.
    # 4. Xử lý tình huống: Nếu là Combobox, dặn người dùng "nhấn để chọn danh sách". Nếu nhấn Lưu lỗi, dặn "kiểm tra các ô báo đỏ".

    # Dữ liệu JSON thô để tham khảo tọa độ chính xác: {json.dumps(meta, ensure_ascii=False)}
    #         """
    #         return {"prompt_letter": prompt}
            
    #     except Exception as e:
    #         print(f"❌ Lỗi get_formatted_meta_for_ai: {e}")
    #         return None

   

   


    def get_formatted_meta_for_ai(self, sub_id):
        """
        [PHIÊN BẢN BIÊN KỊCH THÔNG MINH 2026 - CHỐNG ĐẠN 100%]
        Hợp nhất Metadata, phân tích trạng thái và ra lệnh kịch bản cho AI.
        """
        try:
            # 1. Truy vấn dữ liệu từ Database
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            
            # FIX LỖI: sqlite3.Row không có .get(). Ép về dict để an toàn tuyệt đối.
            if not row:
                print(f"⚠️ Warning: sub_id {sub_id} không tồn tại trong DB.")
                return None
            sub = dict(row) 

            # Kiểm tra trường metadata
            raw_metadata_str = sub.get('metadata')
            if not raw_metadata_str:
                print(f"⚠️ Warning: sub_id {sub_id} rỗng metadata.")
                return None
            
            # 2. Parse và Gọt sạch Metadata
            try:
                raw_meta = json.loads(raw_metadata_str)
            except json.JSONDecodeError:
                print(f"❌ Error: Metadata của {sub_id} không đúng định dạng JSON.")
                return None

            # Gọi hàm gọt metadata (Hàm này phải trả về dict, không được return None)
            clean_meta = self.clean_metadata_for_ai(raw_meta)
            
            # --- CHỐT CHẶN NONETYPE ---
            if not clean_meta:
                print(f"❌ Error: clean_metadata_for_ai trả về None cho sub_id {sub_id}")
                return None

            # Dùng .get() với giá trị mặc định cho tất cả để an toàn tuyệt đối
            p_info = clean_meta.get('page_info', {})
            form_data = clean_meta.get('form_to_fill', [])
            table = clean_meta.get('table_structure', {})
            all_actions = clean_meta.get('available_actions', [])
            
            # Trích xuất thông tin trạng thái
            is_dialog = p_info.get('is_dialog_open', False)
            has_data = table.get('has_data', False)
            
            # --- GOM TẤT CẢ NÚT BẤM (TOOLBAR + FORM) ---
            btn_labels = []
            if isinstance(all_actions, list):
                # Chỉ lấy label, bỏ trùng, bọc trong ngoặc vuông để AI dễ nhận diện
                btn_labels = sorted(list(set(
                    [f"[{a['label']}]" for a in all_actions if isinstance(a, dict) and a.get('label')]
                )))
            
            # --- LOGIC PHÂN TÍCH NGỮ CẢNH (TRÁNH AI BỊA ĐẶT) ---
            has_form = isinstance(form_data, list) and len(form_data) > 0
            
            if is_dialog or has_form:
                status_context = "[ĐANG TRONG FORM] -> Tập trung hướng dẫn điền thông tin chi tiết vào các ô nhập liệu."
                primary_flow = "Điền thông tin và kết thúc bằng nút Lưu."
            elif not has_data:
                status_context = "[TRANG TRỐNG] -> Dữ liệu chưa có. Phải hướng dẫn nhấn nút 'Tạo mới' hoặc 'Thêm' để bắt đầu."
                primary_flow = "Nhấn nút khởi tạo để mở Form nhập liệu."
            else:
                status_context = "[DANH SÁCH CÓ DỮ LIỆU] -> Trang đã có dữ liệu. Hướng dẫn cách xem, lọc hoặc quản lý."
                primary_flow = "Quan sát bảng dữ liệu và thực hiện các thao tác quản lý."

            
            # --- 3. SOẠN THẢO PROMPT CHIẾN THUẬT (BẢN CHUẨN HÓA ACTION) ---
            prompt = f"""
### 🎭 NHIỆM VỤ: BIÊN KỊCH CHO HỆ THỐNG "{sub.get('sub_title', 'Phần mềm quản lý')}"

---
### 📍 1. BỐI CẢNH (SYSTEM CONTEXT)
- **Vị trí hiện tại:** {" > ".join(p_info.get('breadcrumbs', []))}
- **Trạng thái:** {status_context}
- **NHIỆM VỤ:** Chỉ lập kịch bản cho các thành phần xuất hiện trong mục 2. TUYỆT ĐỐI không hướng dẫn các bước điều hướng bên ngoài (như click Menu, click trang chủ).

### 🔍 2. QUAN SÁT THỊ GIÁC (UI ANALYSIS)
- **Các nút:** {', '.join(btn_labels) if btn_labels else "Không có"}
- **Ô nhập liệu (Form):**
{self._format_form_for_ai(form_data)}

### 📝 3. YÊU CẦU ĐẦU RA (JSON ONLY)
Trả về 1 JSON ARRAY phẳng. 

**Cấu trúc 1 object mẫu (BẮT BUỘC ĐÚNG TÊN KEY):**
{{
    "step": 1, 
    "vo": "Lời thoại...", 
    "action": "type hoặc click", 
    "target_label": "Khớp 100% mục 2",
    "value": "Dữ liệu mẫu"
}}

**ĐIỀU KHOẢN NGHIÊM NGẶT:**
1. **Key "value":** Tuyệt đối không được viết thành "input_value" hay "data". Phải là "value".
2. **Ngữ cảnh:** Vì đang trong Form, bước 1 phải là ô nhập liệu đầu tiên (Mã chi nhánh). Không chào hỏi rườm rà.
3. **Dữ liệu mẫu:** Sử dụng dữ liệu thực tế ngành vàng bạc (VD: Mã: CH-01, Tên: Tiệm Vàng Kim Long, Địa chỉ: 123 Chợ Thiếc...).
4. **Action:** Chỉ dùng `type` cho ô nhập, `click` cho nút bấm.

**Chỉ trả về JSON. Không giải thích.**
"""
            return {
                "prompt_letter": prompt,
                "clean_metadata": clean_meta 
            }

        except Exception as e:
            print(f"❌ Lỗi nghiêm trọng tại get_formatted_meta_for_ai: {e}")
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

    def clean_metadata_for_ai(self, raw_data):
        """
        Gọt sạch tọa độ rác, lọc nút bấm ẩn, chỉ để lại dữ liệu nghiệp vụ.
        PHẢI CHẶN LỖI NONETYPE TẠI ĐÂY.
        """
        if not raw_data:
            return None

        # 1. Gom nút từ Layout (Toolbar)
        # Sử dụng .get() kèm default là {} để không bao giờ bị None
        layout_data = raw_data.get("layout", {})
        layout_actions = [
            {"label": a.get("label"), "type": "button"} 
            for a in layout_data.get("actions", [])
            if float(a.get("opacity", 1)) > 0 and a.get("is_visible") and a.get("label")
        ]

        # 2. Lọc Active Form - CHỖ GÂY LỖI ĐÃ ĐƯỢC FIX TẠI ĐÂY
        # Đảm bảo active_form luôn là một dict, kể cả khi raw_data không có key đó
        active_form = raw_data.get("active_form") or {} 
        
        # Bây giờ gọi .get() thoải mái vì active_form ít nhất là {}
        form_actions = [
            {"label": a.get("label"), "type": "button"}
            for a in active_form.get("actions", [])
            if a.get("label")
        ]

        # 3. Lọc Input Form
        form_inputs = [
            {
                "label": i.get("label"),
                "type": i.get("type"),
                "required": i.get("required", False)
            }
            for i in active_form.get("inputs", [])
            if i.get("label")
        ]
        
        # 4. Lọc Cấu trúc bảng
        tables = layout_data.get("tables", [])
        table_cols = tables[0].get("columns", []) if tables else []
        has_data = False
        if tables:
            has_data = tables[0].get("count", 0) > 0

        # 5. Hợp nhất Action
        all_available_actions = layout_actions + form_actions

        return {
            "page_info": {
                "url": raw_data.get("url"),
                "is_dialog_open": raw_data.get("state", {}).get("is_dialog_open", False),
                "breadcrumbs": raw_data.get("navigation", {}).get("breadcrumbs", [])
            },
            "available_actions": all_available_actions,
            "form_to_fill": form_inputs,
            "table_structure": {
                "columns": table_cols,
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