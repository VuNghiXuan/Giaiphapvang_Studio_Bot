import os
import shutil
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

    # --- QUẢN LÝ BÀI HỌC CON (SUB_CONTENTS) ---

    def _get_default_metadata(self):
        """Hàm helper để tạo khung Metadata chuẩn, tránh lỗi thiếu key"""
        return {
            "location": {
                "url": "", "title": "", "breadcrumbs": [], 
                "active_module": "", "active_tab": ""
            },
            "navigation": {
                "sidebar_menu": [], 
                "tabs": []
            },
            "content": {
                "primary_actions": [], 
                "row_operations": [], 
                "form_fields": [], 
                "table_columns": []
            },
            "state": {
                "is_loading": False,
                "is_dialog_open": False,
                "scroll_status": {
                    "sidebar_can_scroll": False,
                    "table_horizontal_scroll": False
                }
            }
        }
    

    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None):
        try:
            # Check trùng URL
            if url and url.strip() != "":
                existing = self.db.fetchone(
                    "SELECT id FROM sub_contents WHERE tutorial_id = ? AND url = ?", 
                    (t_id, url)
                )
                if existing: return existing['id'] 

            res = self.db.fetchone(
                "SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", 
                (t_id,)
            )
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0

            # Khởi tạo metadata chuẩn nếu chưa có
            final_metadata = self._get_default_metadata()
            if isinstance(metadata, dict):
                # Hợp nhất metadata truyền vào với khung chuẩn
                for key in final_metadata:
                    if key in metadata:
                        final_metadata[key] = metadata[key]
            
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

            # Tạo folder
            safe_title = "".join([c if c.isalnum() else "_" for c in sub_title])
            unique_folder_name = f"{new_id}_{safe_title}"
            self.db.execute("UPDATE sub_contents SET sub_folder = ? WHERE id = ?", (unique_folder_name, new_id))

            full_sub_path = os.path.join(Config.BASE_STORAGE, parent_folder, unique_folder_name)
            os.makedirs(full_sub_path, exist_ok=True)
            for sub_f in ["raw", "outputs", "assets"]:
                os.makedirs(os.path.join(full_sub_path, sub_f), exist_ok=True)
            
            self.db.commit()
            return new_id
        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            self.db.rollback()
            return False

    def update_sub_content(self, sub_id: int, **kwargs):
        """Cập nhật thông tin và HỢP NHẤT metadata cũ với mới"""
        try:
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: return False

            # Lấy metadata cũ từ DB
            try:
                old_meta = json.loads(current['metadata']) if current['metadata'] else self._get_default_metadata()
            except:
                old_meta = self._get_default_metadata()

            # Lấy metadata mới từ kwargs
            new_meta = kwargs.get('metadata') or kwargs.get('new_metadata')
            
            if new_meta is not None:
                if isinstance(new_meta, dict):
                    # CHỈNH SỬA QUAN TRỌNG: Hợp nhất (Merge) thay vì ghi đè hoàn toàn
                    for key in old_meta:
                        if key in new_meta:
                            old_meta[key] = new_meta[key]
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current['metadata']

            status = kwargs.get('status') or kwargs.get('new_status') or current['status']
            # Tự động chuyển trạng thái nếu đã có metadata quét về
            if new_meta and status == 'Chưa quay':
                status = 'Đã quét'

            params = {
                "id": sub_id,
                "title": kwargs.get('title') or kwargs.get('new_title') or current['sub_title'],
                "status": status,
                "url": str(kwargs.get('url') or kwargs.get('new_url') or current['url'] or ""),
                "meta": final_meta_str
            }

            query = """
                UPDATE sub_contents 
                SET sub_title = :title, status = :status, url = :url, metadata = :meta 
                WHERE id = :id
            """
            self.db.execute(query, params)
            self.db.commit()
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

    def get_formatted_meta_for_ai(self, sub_id):
        """
        BỨC THƯ GỬI AI (DIGITAL TWIN ACTOR)
        Xây dựng lộ trình: Login -> Home -> Module -> Sidebar (Scroll) -> Tab -> Form -> Multi-Save
        """
        try:
            sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not sub: return None
            
            meta = json.loads(sub['metadata']) if isinstance(sub['metadata'], str) else (sub['metadata'] or {})
            content = meta.get("content", {})
            nav = meta.get("navigation", {})
            state = meta.get("state", {})
            scroll = state.get("scroll_status", {})

            # --- 1. KHỞI TẠO LỘ TRÌNH (USER JOURNEY) ---
            execution_flow = []
            
            # Bước 1: Trạng thái bắt đầu
            execution_flow.append({
                "step": 1, 
                "action": "check_context", 
                "target": "Dashboard_Home", 
                "desc": f"Đang ở trang chủ {Config.APP_NAME}. Giới thiệu bài học: {sub['sub_title']}"
            })

            # Bước 2: Truy cập Module chính
            # Tự suy luận Module từ tiêu đề (Vũ có thể map table này rộng hơn)
            module_map = {"chi nhánh": "Hệ thống", "vàng": "Nghiệp vụ", "kho": "Kho hàng", "thu chi": "Kế toán"}
            module_name = next((v for k, v in module_map.items() if k in sub['sub_title'].lower()), "Hệ thống")
            
            execution_flow.append({
                "step": 2, 
                "action": "module_access", 
                "target": f"nav:has-text('{module_name}')",
                "desc": f"Click chọn Module {module_name} trên thanh điều hướng chính"
            })

            # Bước 3: Tương tác Sidebar (Có tính đến Scroll)
            current_step = 3
            sidebar_items = nav.get('sidebar_menu', [])
            target_menu = next((item for item in sidebar_items if item.get('label') in sub['sub_title'] or item.get('is_active')), None)
            
            if target_menu:
                execution_flow.append({
                    "step": current_step, 
                    "action": "click_sidebar", 
                    "target": target_menu.get('selector'),
                    "desc": f"Tìm và chọn menu: {target_menu['label']}",
                    "need_scroll": scroll.get('sidebar_can_scroll', False) # Quan trọng để AI diễn tả việc tìm kiếm
                })
                current_step += 1

            # Bước 4: Xử lý Tab (Nếu có phân cấp như Thông tin công ty -> Chi nhánh)
            tabs = nav.get('tabs', [])
            if tabs:
                active_tab = next((t for t in tabs if t.get('is_active')), tabs[0])
                execution_flow.append({
                    "step": current_step, 
                    "action": "switch_tab",
                    "target": active_tab.get('selector'),
                    "desc": f"Chuyển sang thẻ nội dung: {active_tab['label']}"
                })
                current_step += 1

            # Bước 5: Thao tác mở Form (Tạo mới)
            btns = content.get("primary_actions", [])
            open_btn = next((b for b in btns if any(k in b['label'] for k in ["Thêm", "Tạo", "Mới", "Lập"])), None)
            execution_flow.append({
                "step": current_step, 
                "action": "open_form",
                "target": open_btn['selector'] if open_btn else "button:has-text('Tạo mới')",
                "desc": f"Click nút {open_btn['label'] if open_btn else 'Tạo mới'} để mở cửa sổ nhập liệu"
            })
            current_step += 1

            # Bước 6: Nhập liệu chi tiết (AI tự bịa data thực tế ngành vàng ở đây)
            fields = [f for f in content.get("form_fields", []) if f.get('selector') != '#_r_p_']
            execution_flow.append({
                "step": current_step, 
                "action": "fill_form",
                "fields": fields if fields else "AUTO_FILL_BY_CONTEXT", 
                "desc": "Nhập liệu chi tiết các thông số (Vàng, Tuổi, Trọng lượng, Chi nhánh...)",
                "is_dialog": state.get('is_dialog_open', True)
            })
            current_step += 1

            # Bước 7: Xử lý đa nút bấm (Lưu / Lưu & Thêm / Hủy)
            submit_actions = []
            for b in btns:
                label = b['label'].lower()
                if any(k in label for k in ["lưu", "xác nhận", "thêm tiếp", "hủy", "đóng"]):
                    submit_actions.append({"label": b['label'], "selector": b['selector']})

            execution_flow.append({
                "step": current_step, 
                "action": "finalize",
                "available_buttons": submit_actions,
                "desc": "Hoàn tất nghiệp vụ. Chọn Lưu để đóng form hoặc Lưu & Thêm để nhập tiếp."
            })

            # --- 2. ĐÓNG GÓI PROMPT JSON ---
            full_letter = f"""Mày là AI Actor của thương hiệu {Config.APP_NAME}. 
Slogan: "{Config.DEFAULT_SLOGAN}"

Nhiệm vụ: Viết kịch bản video hướng dẫn nghiệp vụ chuyên nghiệp cho bài: "{sub['sub_title']}".

--- 📦 BLUEPRINT HÀNH TRÌNH (TUÂN THỦ TRÌNH TỰ NÀY) ---
{json.dumps(execution_flow, ensure_ascii=False, indent=2)}

--- 🛠 CHỈ THỊ DIỄN XUẤT ---
1. LỜI THOẠI (Speech): 
   - Phải tự nhiên, dẫn dắt từ trang Home: "Chào mừng quý khách, hôm nay tôi sẽ hướng dẫn..."
   - Khi chọn Sidebar: "Tại danh mục bên trái, quý khách cuộn chuột tìm mục..."
   - Khi nhập liệu: Bịa dữ liệu thực tế (Ví dụ: Nhập Chi nhánh Quận 5, Mã CN-Q5, Vàng mặc định 610...).
2. ĐỊNH DẠNG: Trả về duy nhất 1 mảng **json** phẳng. Mỗi phần tử gồm: (Step, Action, Target, Speech, UI_Note).
3. TRÁNH LỖI: Luôn bao gồm chữ **json** trong kết quả để đảm bảo định dạng máy đọc được.

Bắt đầu viết kịch bản **json** ngay:
"""
            return {"prompt_letter": full_letter}

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