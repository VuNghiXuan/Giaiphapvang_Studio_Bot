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


    # def get_formatted_meta_for_ai(self, sub_id):
    #     """
    #     [PHIÊN BẢN BIÊN KỊCH THÔNG MINH 2026 - CHỐNG ĐẠN 100%]
    #     Hợp nhất Metadata, phân tích lộ trình Sidebar và ép AI đi theo 3 giai đoạn.
    #     """
    #     try:
    #         # 1. Truy vấn dữ liệu từ Database
    #         row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            
    #         if not row:
    #             print(f"⚠️ Warning: sub_id {sub_id} không tồn tại trong DB.")
    #             return None
    #         sub = dict(row) 

    #         raw_metadata_str = sub.get('metadata')
    #         if not raw_metadata_str:
    #             print(f"⚠️ Warning: sub_id {sub_id} rỗng metadata.")
    #             return None
            
    #         # 2. Parse và Gọt sạch Metadata
    #         try:
    #             raw_meta = json.loads(raw_metadata_str)
    #         except json.JSONDecodeError:
    #             print(f"❌ Error: Metadata của {sub_id} không đúng định dạng JSON.")
    #             return None

    #         # Làm sạch dữ liệu thông qua hàm helper
    #         clean_meta = self.clean_metadata_for_ai(raw_meta)
    #         if not clean_meta:
    #             print(f"❌ Error: clean_metadata_for_ai trả về None cho sub_id {sub_id}")
    #             return None

    #         # --- TRÍCH XUẤT THÔNG TIN ĐIỀU HƯỚNG (SIDEBAR & BREADCRUMBS) ---
    #         p_info = clean_meta.get('page_info', {})
    #         nav = p_info.get('navigation', {})
    #         breadcrumbs = p_info.get('breadcrumbs', [])
            
    #         # Lấy danh sách menu sidebar từ metadata quét được
    #         sidebar_items = clean_meta.get('sidebar_menu', [])
    #         sidebar_desc = " > ".join(sidebar_items) if sidebar_items else "Trang chủ"
            
    #         # --- TRÍCH XUẤT THÔNG TIN UI ---
    #         form_data = clean_meta.get('form_to_fill', [])
    #         table = clean_meta.get('table_structure', {})
    #         all_actions = clean_meta.get('available_actions', [])
            
    #         # Kiểm tra trạng thái
    #         is_dialog = p_info.get('is_dialog_open', False)
    #         is_empty_state = not table.get('has_data', False)
    #         has_form = isinstance(form_data, list) and len(form_data) > 0
            
    #         # Tìm nút hành động chính (Ưu tiên nút Tạo mới/Thêm)
    #         primary_btn = next((a for a in all_actions if any(x in a.get('label', '').lower() for x in ['tạo', 'thêm', 'mới'])), None)
    #         if not primary_btn and all_actions:
    #             primary_btn = all_actions[0] # Lấy nút đầu tiên nếu không thấy nút Tạo mới

    #         # Công cụ đặc biệt (Excel, Ẩn hiện cột...)
    #         special_actions = [a.get('label') for a in all_actions if 'export' in a.get('action', '') or 'view' in a.get('action', '')]
            
    #         # Bảng dữ liệu
    #         table_desc = table.get('columns', [])
            
    #         # Trạng thái Form để AI hiểu
    #         form_info = f"Form đang hiển thị với {len(form_data)} trường nhập liệu." if is_dialog or has_form else None

    #         # --- 3. SOẠN THẢO PROMPT CHIẾN THUẬT (BIÊN KỊCH TOÀN CẢNH) ---
    #         prompt = f"""
    # ### 🎭 NHIỆM VỤ: BIÊN KỊCH PHIM HƯỚNG DẪN SỬ DỤNG HỆ THỐNG
    # **Mục tiêu:** {sub.get('sub_title', 'Hướng dẫn chức năng')}
    # **Trạng thái trang:** {"[DANH SÁCH TRỐNG - Hướng dẫn tạo mới]" if is_empty_state else "[CÓ DỮ LIỆU - Hướng dẫn quản lý]"}

    # ---
    # ### 📍 1. BỐI CẢNH & LỘ TRÌNH (CONTEXT & NAVIGATION)
    # - **URL hiện tại:** {nav.get('url', 'N/A')}
    # - **Lộ trình Menu (Breadcrumbs):** {" > ".join(breadcrumbs) if breadcrumbs else "N/A"}
    # - **Sidebar (Menu trái):** {sidebar_desc}
    # - **Trạng thái Form:** {form_info if form_info else "Form chưa mở - BẮT BUỘC phải nhấn nút khởi tạo trước."}

    # ### 🔍 2. QUAN SÁT GIAO DIỆN THỰC TẾ (UI ANALYSIS)
    # - **Nút hành động chính:** {primary_btn.get('label') if primary_btn else "Tạo mới"}
    # - **Bảng dữ liệu:** {'; '.join(table_desc) if table_desc else "Không phát hiện bảng dữ liệu."}
    # - **Công cụ bổ trợ:** {", ".join(special_actions) if special_actions else "Không có"}

    # ### 📝 3. YÊU CẦU KỊCH BẢN CHI TIẾT (STORYLINE LOGIC)
    # Hãy trả về một **JSON ARRAY phẳng** duy nhất. Tuyệt đối không bao bọc bởi key nào khác. 
    # Định dạng mỗi object: {{"step": 1, "vo": "Lời thoại", "action": "type/click", "target_label": "Tên nút/ô", "value": "Dữ liệu mẫu"}}

    # **QUY TẮC BIÊN KỊCH BẮT BUỘC (TUÂN THỦ THỨ TỰ 3 GIAI ĐOẠN):**

    # #### GIAI ĐOẠN A: ĐIỀU HƯỚNG TRUYỀN THỐNG
    # 1. **BẮT BUỘC:** Bước 1, 2, 3 phải là các thao tác click vào Menu Sidebar để dẫn người dùng đi từ Trang chủ vào đến trang mục tiêu.
    # - Dựa vào lộ trình: {sidebar_desc}
    # - VD: "Đầu tiên, tại menu bên trái, quý khách nhấn chọn mục {breadcrumbs[0] if len(breadcrumbs)>0 else ''}..."

    # #### GIAI ĐOẠN B: MỞ FORM NHẬP LIỆU
    # 2. Nếu trạng thái là Form chưa mở, bước tiếp theo BẮT BUỘC là click vào nút: `{primary_btn.get('label') if primary_btn else 'Tạo mới'}`.
    # - VD: "Tiếp theo, quý khách nhấn nút {primary_btn.get('label') if primary_btn else 'Tạo mới'} để bắt đầu thêm dữ liệu."

    # #### GIAI ĐOẠN C: CHI TIẾT NHẬP LIỆU
    # 3. **Lời thoại (VO):** Thân thiện, dùng "Chúng ta...", "Quý khách...". 
    # 4. **Hành động (Action):** - Với ô văn bản: dùng `type`, kèm `value` thực tế ngành vàng (VD: "Tiệm vàng Kim Long", "CH-Q1").
    # - Với danh sách chọn: dùng `click`, dặn "chọn giá trị phù hợp".
    # 5. **Kết thúc:** Luôn kết thúc bằng hành động `click` vào nút [Lưu] để hoàn tất.

    # **⚠️ CẢNH BÁO:** `target_label` phải khớp 100% với tên nút/ô đã liệt kê ở Mục 2. Chỉ trả về JSON.
    # """
    #         return {
    #             "prompt_letter": prompt,
    #             "clean_metadata": clean_meta 
    #         }

    #     except Exception as e:
    #         print(f"❌ Lỗi nghiêm trọng tại get_formatted_meta_for_ai: {e}")
    #         traceback.print_exc() 
    #         return None


    # --- HÀM BIÊN KỊCH: TRÁI TIM CỦA HỆ THỐNG ---
    def get_formatted_meta_for_ai(self, sub_id):
        """
        [PHIÊN BẢN STUDIO CHUYÊN NGHIỆP]
        Hợp nhất: Metadata kỹ thuật + Workflow tùy chỉnh + Lưu ý từ Đạo diễn Vũ.
        """
        try:
            # 1. Lấy dữ liệu Content từ DB (Bao gồm title, workflow, notes...)
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: return None
            sub = dict(row)

            # 2. Parse và làm sạch Metadata từ VisionMachine
            raw_meta = json.loads(sub.get('metadata', '{}'))
            clean_meta = self.clean_metadata_for_ai(raw_meta)
            
            # 3. Chuẩn bị các biến định danh kỹ thuật (Chống lỗi target_label)
            p_info = clean_meta['page_info']
            sidebar_path = p_info.get('sidebar_path', [])
            sidebar_desc = " > ".join(sidebar_path) if sidebar_path else "Trang chủ"
            
            input_labels = [i['label'] for i in clean_meta['form_to_fill']]
            all_actions = clean_meta['available_actions']
            action_labels = [a['label'] for a in all_actions]
            if 'Lưu' not in action_labels: action_labels.append('Lưu')

            # Nút mở form
            primary_btn = next((a for a in all_actions if any(kw in a['label'].lower() for kw in ['tạo', 'thêm', 'mới'])), None)
            p_btn_label = primary_btn['label'] if primary_btn else "Tạo mới"

            # Trạng thái UI
            is_empty = not clean_meta['table_structure']['has_data']
            is_dialog = p_info.get('is_dialog_open', False)

            # --- 4. SOẠN THẢO PROMPT "ĐẠO DIỄN VŨ" ---
            prompt = f"""
### 🎬 STUDIO PRODUCTION: {sub.get('sub_title')}
**Slogan thương hiệu:** {sub.get('slogan', 'Giải Pháp Vàng - Quản lý thông minh')}
**Mục tiêu Workflow:** {sub.get('workflow_custom', 'Hướng dẫn người dùng thao tác cơ bản')}

---
### 📍 1. BỐI CẢNH & LỘ TRÌNH KỸ THUẬT
- **Menu Sidebar:** {sidebar_desc}
- **Đường dẫn:** {" > ".join(p_info['breadcrumbs'])}
- **Trạng thái Form:** {"ĐÃ MỞ - Điền thông tin ngay" if is_dialog else f"CHƯA MỞ - Phải nhấn '{p_btn_label}'"}

### ✍️ 2. GHI CHÚ TỪ ĐẠO DIỄN VŨ (BẮT BUỘC TUÂN THỦ)
> {sub.get('director_notes', 'Diễn đạt tự nhiên, tập trung vào sự tiện lợi của phần mềm.')}

---
### 🔍 3. DANH SÁCH NHÃN (KHỚP 100% ĐỂ BOT KHÔNG SKIP)
- **Menu:** {", ".join([f"'{l}'" for l in sidebar_path])}
- **Input:** {", ".join([f"'{l}'" for l in input_labels])}
- **Button:** {", ".join([f"'{l}'" for l in action_labels])}

---
### 📝 4. YÊU CẦU KỊCH BẢN (JSON ONLY)
Trả về 1 JSON Array phẳng. KHÔNG GIẢI THÍCH.
Mỗi bước: {{"step": int, "vo": "Lời thoại", "action": "click/type", "target_label": "Nhãn khớp mục 3", "value": "Dữ liệu"}}

**QUY TẮC SỐNG CÒN:**
1. **Giai đoạn A (Dẫn nhập):** Phải click qua: {sidebar_desc}. Lời thoại (VO) phải lồng ghép slogan: "{sub.get('slogan')}".
2. **Giai đoạn B (Mở form):** Nếu chưa mở, click '{p_btn_label}'.
3. **Giai đoạn C (Nhập liệu):** Nhập các trường: {", ".join(input_labels)}. Dùng dữ liệu mẫu ngành vàng.
4. **Action:** Chỉ dùng "click" hoặc "type". KHÔNG dùng "Nhập", "Click".
5. **Target_label:** Copy y hệt từ mục 3. Sai 1 dấu cách là Bot sẽ chết.

**Ví dụ:**
[
  {{"step": 1, "vo": "Chào mừng quý khách đến với Giải Pháp Vàng, hãy chọn {sidebar_path[0] if sidebar_path else 'Menu'}", "action": "click", "target_label": "{sidebar_path[0] if sidebar_path else 'Menu'}", "value": ""}}
]
"""
            return {
                "prompt_letter": prompt, 
                "clean_metadata": clean_meta,
                "sub_data": sub # Trả về thêm để dùng ngoài StudioController nếu cần
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

    # def clean_metadata_for_ai(self, raw_data):
    #     """
    #     Gọt sạch tọa độ rác, lọc nút bấm ẩn, chỉ để lại dữ liệu nghiệp vụ.
    #     PHẢI CHẶN LỖI NONETYPE TẠI ĐÂY.
    #     """
    #     if not raw_data:
    #         return None

    #     # 1. Gom nút từ Layout (Toolbar)
    #     # Sử dụng .get() kèm default là {} để không bao giờ bị None
    #     layout_data = raw_data.get("layout", {})
    #     layout_actions = [
    #         {"label": a.get("label"), "type": "button"} 
    #         for a in layout_data.get("actions", [])
    #         if float(a.get("opacity", 1)) > 0 and a.get("is_visible") and a.get("label")
    #     ]

    #     # 2. Lọc Active Form - CHỖ GÂY LỖI ĐÃ ĐƯỢC FIX TẠI ĐÂY
    #     # Đảm bảo active_form luôn là một dict, kể cả khi raw_data không có key đó
    #     active_form = raw_data.get("active_form") or {} 
        
    #     # Bây giờ gọi .get() thoải mái vì active_form ít nhất là {}
    #     form_actions = [
    #         {"label": a.get("label"), "type": "button"}
    #         for a in active_form.get("actions", [])
    #         if a.get("label")
    #     ]

    #     # 3. Lọc Input Form
    #     form_inputs = [
    #         {
    #             "label": i.get("label"),
    #             "type": i.get("type"),
    #             "required": i.get("required", False)
    #         }
    #         for i in active_form.get("inputs", [])
    #         if i.get("label")
    #     ]
        
    #     # 4. Lọc Cấu trúc bảng
    #     tables = layout_data.get("tables", [])
    #     table_cols = tables[0].get("columns", []) if tables else []
    #     has_data = False
    #     if tables:
    #         has_data = tables[0].get("count", 0) > 0

    #     # 5. Hợp nhất Action
    #     all_available_actions = layout_actions + form_actions

    #     return {
    #         "page_info": {
    #             "url": raw_data.get("url"),
    #             "is_dialog_open": raw_data.get("state", {}).get("is_dialog_open", False),
    #             "breadcrumbs": raw_data.get("navigation", {}).get("breadcrumbs", [])
    #         },
    #         "available_actions": all_available_actions,
    #         "form_to_fill": form_inputs,
    #         "table_structure": {
    #             "columns": table_cols,
    #             "has_data": has_data
    #         }
    #     }


    # --- HÀM QUAN TRỌNG: LÀM SẠCH DỮ LIỆU ĐỂ "MỚM" CHO AI ---
    def clean_metadata_for_ai(self, raw_data):
        """
        Gọt sạch tọa độ, chỉ để lại nhãn (labels) để AI không bị loạn.
        """
        if not raw_data: return self._get_default_metadata()

        # 1. Bóc tách lộ trình (Cực kỳ quan trọng để AI không nhảy cóc)
        nav = raw_data.get("navigation", {})
        # Lấy danh sách menu sidebar đã quét được (ví dụ: ["Hệ thống", "Thông tin công ty", "Chi nhánh"])
        sidebar_items = nav.get("sidebar_items", []) or nav.get("hierarchy", [])
        breadcrumbs = nav.get("breadcrumbs", [])

        # 2. Bóc tách các nút bấm (Actions)
        layout = raw_data.get("layout", {})
        all_btns = layout.get("actions", [])
        
        # Nếu có form đang mở (Dialog), ưu tiên lấy nút trong Form
        active_form = raw_data.get("active_form") or {}
        if active_form:
            all_btns += active_form.get("actions", [])

        clean_actions = [
            {"label": a.get("label"), "is_primary": a.get("is_primary", False)} 
            for a in all_btns if a.get("label")
        ]

        # 3. Bóc tách ô nhập liệu (Inputs)
        inputs = active_form.get("inputs", []) if active_form else layout.get("inputs", [])
        clean_inputs = [
            {"label": i.get("label"), "type": i.get("type", "text"), "required": i.get("required", False)}
            for i in inputs if i.get("label")
        ]

        # 4. Kiểm tra dữ liệu bảng
        tables = layout.get("tables", [])
        table_cols = tables[0].get("columns", []) if tables else []
        has_data = tables[0].get("count", 0) > 0 if tables else False

        return {
            "page_info": {
                "url": raw_data.get("url"),
                "is_dialog_open": raw_data.get("state", {}).get("is_dialog_open", False) or bool(active_form),
                "breadcrumbs": breadcrumbs,
                "sidebar_path": sidebar_items
            },
            "available_actions": clean_actions,
            "form_to_fill": clean_inputs,
            "table_structure": {"columns": table_cols, "has_data": has_data}
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