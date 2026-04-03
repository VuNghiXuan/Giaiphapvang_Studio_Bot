import os
import shutil
from datetime import datetime
import json
from config import Config
from .db_engine import DBEngine

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
    #     BỨC THƯ CHI TIẾT GỬI AI - Chuyển đổi Metadata UI thành kịch bản sản xuất video tự động.
    #     """
    #     try:
    #         sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
    #         if not sub or not sub['metadata']: return None
            
    #         meta = json.loads(sub['metadata'])
    #         nav = meta.get("navigation", {})
    #         layout = meta.get("layout", {})
    #         main = layout.get("main_content", {})
    #         active_form = layout.get("active_form", {})

    #         # --- PHÂN TÍCH CHUYÊN SÂU LỚP GIAO DIỆN ---
            
    #         # 1. Sidebar & Điều hướng
    #         sidebar_info = layout.get("sidebar", {})
    #         sidebar_desc = "Cố định bên trái"
    #         if sidebar_info.get("has_scroll"):
    #             sidebar_desc += ", có thanh cuộn dọc để xem thêm menu."

    #         # 2. Bảng dữ liệu (Table) & Nút ẩn
    #         tables = main.get("tables", [])
    #         table_desc = []
    #         for t in tables:
    #             cols = ", ".join(t.get("columns", []))
    #             scroll = "Hỗ trợ cuộn ngang" if t.get("scroll_info", {}).get("can_scroll_h") else "Hiển thị đầy đủ"
    #             table_desc.append(f"Bảng dữ liệu [{cols}]. Đặc điểm: {scroll}.")

    #         # 3. Nút chức năng đặc biệt (Xuất file, Ẩn hiện cột)
    #         special_actions = [a.get('label') for a in main.get('actions', []) 
    #                         if any(x in a.get('label', '').lower() for x in ['xuất', 'cột', 'lọc', 'mật độ'])]

    #         # 4. Chi tiết Form nhập liệu (Nếu có active_form)
    #         form_desc = {}
    #         if active_form:
    #             form_desc = {
    #                 "fields": [f"{i.get('label')} (Loại: {i.get('type')}, Bắt buộc: {i.get('required')})" 
    #                         for i in active_form.get('inputs', [])],
    #                 "buttons": [f"{b.get('label')} (Màu: {b.get('bg_color')}, Chính: {b.get('is_primary')})" 
    #                             for b in active_form.get('actions', [])],
    #                 "error_logic": "Nếu nhập thiếu trường bắt buộc, hệ thống sẽ báo đỏ tại trường đó."
    #             }

    #         # --- SOẠN THẢO BỨC THƯ (PROMPT) ---
    #         prompt = f"""
    # Nhiệm vụ: Viết kịch bản quay phim & lời thoại hướng dẫn sử dụng phần mềm Giai Pháp Vàng.
    # Mục tiêu: {sub['sub_title']} (ID: {meta.get('form_id')})

    # 1. BỐI CẢNH HỆ THỐNG:
    # - Đường dẫn URL: {nav.get('url')}
    # - Cấu trúc Menu: {" > ".join(nav.get('hierarchy', []))}
    # - Sidebar: {sidebar_desc}

    # 2. CHI TIẾT GIAO DIỆN DANH SÁCH (MAIN UI):
    # - Các bảng hiện có: {'; '.join(table_desc)}
    # - Nút thao tác trên bảng: {", ".join([a.get('label') for a in main.get('row_operations', [])])}
    # - Công cụ bổ trợ: {", ".join(special_actions)} (Hướng dẫn người dùng cách ẩn/hiện cột hoặc xuất Excel tại đây).

    # 3. CHI TIẾT FORM NGHIỆP VỤ (ACTIVE FORM - LỚP SÂU):
    # {"- Danh sách trường nhập liệu: " + ", ".join(form_desc.get('fields', [])) if form_desc else "- Không có Form nhập liệu riêng."}
    # {"- Các nút xác nhận: " + ", ".join(form_desc.get('buttons', [])) if form_desc else ""}
    # - Lưu ý về Combobox: Nếu là trường chọn, hướng dẫn nhấn để xổ danh sách liên kết từ bảng dữ liệu khác.

    # 4. KỊCH BẢN YÊU CẦU:
    # Hãy soạn kịch bản theo định dạng:
    # - Lời thoại (Voice-over): Thân thiện, chuyên nghiệp. Ví dụ: "Tại giao diện danh sách, quý khách nhấn vào nút Tạo mới có màu xanh để mở Form..."
    # - Hành động (Action): Mô tả vị trí click dựa trên tọa độ Rect hoặc nhãn nút. 
    # - Xử lý lỗi: Mô tả cách nhận biết khi nhấn Lưu mà bị báo lỗi (Trường nào hiện đỏ).

    # Dữ liệu JSON thô để tham khảo tọa độ: {json.dumps(meta, ensure_ascii=False)}
    # """

    #         return {"prompt_letter": prompt}
    #     except Exception as e:
    #         print(f"❌ Lỗi get_formatted_meta_for_ai: {e}")
    #         return None

    def get_formatted_meta_for_ai(self, sub_id):
        """
        BỨC THƯ CHI TIẾT GỬI AI v2.0 - Biến Metadata thành Kịch bản điện ảnh.
        """
        try:
            sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not sub or not sub['metadata']: return None
            
            meta = json.loads(sub['metadata'])
            nav = meta.get("navigation", {})
            layout = meta.get("layout", {})
            main = layout.get("main_content", {})
            active_form = layout.get("active_form", {})

            # --- 1. PHÂN TÍCH THỊ GIÁC (VISUAL ANALYSIS) ---
            sidebar_info = nav.get("sidebar", {})
            sidebar_desc = "Cố định bên trái"
            if sidebar_info.get("has_scroll"):
                sidebar_desc += " (Menu dài, cần cuộn chuột để thấy hết các mục)"

            # Phân tích Bảng & Trạng thái rỗng
            tables = main.get("tables", [])
            table_desc = []
            is_empty_state = True
            for t in tables:
                cols = t.get("columns", [])
                if cols: is_empty_state = False
                scroll = "Bảng rộng, cần hướng dẫn kéo thanh cuộn ngang" if t.get("needs_h_scroll") else "Hiển thị gọn trong màn hình"
                table_desc.append(f"Bảng có {len(cols)} cột [{', '.join(cols[:5])}...]. Đặc điểm: {scroll}.")

            # Phân tích nút quan trọng (Primary Actions)
            all_actions = main.get("actions", [])
            primary_btn = next((a for a in all_actions if a.get('is_primary')), None)
            special_actions = [a.get('label') for a in all_actions if any(x in a.get('label', '').lower() for x in ['xuất', 'cột', 'lọc', 'mật độ'])]

            # --- 2. PHÂN TÍCH FORM CHI TIẾT ---
            form_info = ""
            if active_form:
                fields = active_form.get('inputs', [])
                btns = active_form.get('actions', [])
                form_info = f"""
        - Tên Form/Dialog: {active_form.get('context_name', 'Form nhập liệu')}
        - Danh sách {len(fields)} trường: {', '.join([f"{i.get('label')} ({'Bắt buộc' if i.get('required') else 'Tùy chọn'})" for i in fields])}
        - Nút xác nhận: {', '.join([f"{b.get('label')} (Màu: {b.get('rect', {}).get('bg_color')})" for b in btns])}
        - Logic Validation: Nếu bỏ trống trường bắt buộc, hệ thống sẽ báo lỗi chữ đỏ tại label của trường đó.
                """

            # --- 3. SOẠN THẢO BỨC THƯ (PROMPT BIÊN KỊCH) ---
            prompt = f"""
    # NHIỆM VỤ: VIẾT KỊCH BẢN QUAY PHIM & LỜI THOẠI HƯỚNG DẪN SỬ DỤNG
    Mục tiêu: {sub['sub_title']}
    Trạng thái trang: {"[TRANG TRỐNG - Hướng dẫn tạo mới dữ liệu]" if is_empty_state else "[CÓ DỮ LIỆU - Hướng dẫn quản lý/tra cứu]"}

    ## 1. BỐI CẢNH (CONTEXT)
    - URL: {nav.get('url')}
    - Lộ trình: {" > ".join(nav.get('breadcrumbs', []))}
    - Sidebar: {sidebar_desc}

    ## 2. QUAN SÁT GIAO DIỆN (MAIN UI)
    - Bảng dữ liệu: {'; '.join(table_desc) if table_desc else "Không phát hiện bảng."}
    - Nút hành động chính: {primary_btn.get('label') if primary_btn else "Không có nút nổi bật."}
    - Thao tác trên từng dòng: {", ".join([a.get('label') for a in main.get('row_operations', [])])}
    - Công cụ: {", ".join(special_actions)} (Hướng dẫn người dùng Xuất Excel hoặc Ẩn/Hiện cột nếu cần).

    ## 3. CHI TIẾT NỘI SOI FORM (DEEP SCAN)
    {form_info if form_info else "- Không có Form đang mở hoặc không có Form ẩn."}

    ## 4. YÊU CẦU KỊCH BẢN (STORYLINE)
    Hãy soạn kịch bản chi tiết bao gồm:
    1. Lời thoại (Voice-over): Chuyên nghiệp, chậm rãi. (Ví dụ: "Chào mừng quý khách... Hãy nhìn vào nút {primary_btn.get('label') if primary_btn else 'Tạo mới'}...")
    2. Hành động (Action): Mô tả chính xác vị trí chuột (Dựa vào nhãn hoặc tọa độ trong JSON).
    3. Chỉ dẫn vật lý: Mô tả màu sắc nút (Hex color) để người xem dễ nhận diện.
    4. Xử lý tình huống: Nếu là Combobox, dặn người dùng "nhấn để chọn danh sách". Nếu nhấn Lưu lỗi, dặn "kiểm tra các ô báo đỏ".

    Dữ liệu JSON thô để tham khảo tọa độ chính xác: {json.dumps(meta, ensure_ascii=False)}
            """
            return {"prompt_letter": prompt}
            
        except Exception as e:
            print(f"❌ Lỗi get_formatted_meta_for_ai: {e}")
            return None
        
        
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