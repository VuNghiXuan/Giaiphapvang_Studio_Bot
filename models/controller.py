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

    # --- HELPERS ---
    def _get_default_metadata(self):
        """Khung Metadata đồng bộ 100% với Script JS 'Vét Cạn'"""
        return {
            "navigation": {
                "url": "",
                "path": "",
                "hierarchy": [],
                "current_step": ""
            },
            "session": {
                "timestamp": "",
                "is_popup_open": False,
                "popup_type": "NONE"
            },
            "layout": {
                "sidebar": [],
                "main_content": {
                    "actions": [],
                    "row_operations": [],
                    "inputs": [],
                    "tables": [],
                    "scrollers": []
                },
                "active_form": None, # Chứa cấu trúc form nếu có 'nội soi'
                "export_formats": []
            }
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
        """Cập nhật và Hợp nhất thông tin thông minh"""
        try:
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: return False

            # Xử lý Metadata (Merge sâu)
            try:
                old_meta = json.loads(current['metadata']) if current['metadata'] else self._get_default_metadata()
            except:
                old_meta = self._get_default_metadata()

            new_meta = kwargs.get('metadata')
            if new_meta and isinstance(new_meta, dict):
                # Chỉ cập nhật những gì mới quét được, giữ lại những gì cũ đang có
                for key, value in new_meta.items():
                    if isinstance(value, dict) and key in old_meta:
                        old_meta[key].update(value)
                    else:
                        old_meta[key] = value
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current['metadata']

            status = kwargs.get('status') or current['status']
            if new_meta and status == 'Chưa quay': status = 'Đã quét'

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
            return True
        except Exception as e:
            print(f"❌ Lỗi update: {e}")
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
        BỨC THƯ GỬI AI (DIGITAL TWIN ACTOR) - TRÍ TUỆ NGÀNH VÀNG
        """
        try:
            sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not sub: return None
            
            meta = json.loads(sub['metadata'])
            nav = meta.get("navigation", {})
            layout = meta.get("layout", {})
            main = layout.get("main_content", {})
            form = layout.get("active_form", {})

            # --- XÂY DỰNG LỘ TRÌNH THÔNG MINH ---
            flow = []
            
            # 1. Khởi động (Lấy context từ Hierarchy)
            location = " > ".join(nav.get('hierarchy', ['Trang chủ']))
            flow.append({
                "stage": "OPENING",
                "desc": f"Giới thiệu bài học '{sub['sub_title']}' tại module {location}",
                "action": "identity_check"
            })

            # 2. Điều hướng Sidebar (Nếu chưa đúng trang)
            flow.append({
                "stage": "NAVIGATION",
                "action": "ensure_page",
                "target_url": nav.get('url'),
                "breadcrumb": nav.get('hierarchy')
            })

            # 3. Thao tác chính (Mở Form/Thêm mới)
            add_btn = next((a for a in main.get('actions', []) if "thêm" in a['label'].lower()), None)
            if add_btn:
                flow.append({
                    "stage": "INTERACTION",
                    "action": "click",
                    "label": add_btn['label'],
                    "selector": add_btn['selector']
                })

            # 4. Nhập liệu (Đây là lúc AI cần 'diễn' nghiệp vụ vàng)
            target_fields = form.get('inputs') if form else main.get('inputs', [])
            flow.append({
                "stage": "DATA_ENTRY",
                "fields": [f['label'] for f in target_fields],
                "logic_note": "Dùng kiến thức ngành vàng (Vàng 610, 18K, trọng lượng chi) để điền mẫu."
            })

            # --- ĐÓNG GÓI LÁ THƯ ---
            prompt = f"""Mày là Chuyên gia đào tạo AI của Giai Pháp Vàng.
Bài học: {sub['sub_title']}
URL: {nav.get('url')}

--- 📜 LỘ TRÌNH NGHIỆP VỤ (HÃY TUÂN THỦ) ---
{json.dumps(flow, ensure_ascii=False, indent=2)}

--- 🎭 CHỈ THỊ DIỄN XUẤT CHO DIGITAL TWIN ---
1. GIỌNG ĐIỆU: Chuyên nghiệp, rành mạch như một kế toán trưởng ngành vàng. 
2. NỘI DUNG: Khi nói về các ô nhập liệu, phải giải thích TẠI SAO (VD: 'Ô trọng lượng này quý khách nhập theo đơn vị Chi để hệ thống tự tính giá trị').
3. DỮ LIỆU MẪU: Tự tạo dữ liệu thực tế (Ví dụ: Nhập hàng 'Nhẫn nam 610', trọng lượng '2.550').
4. TRẢ VỀ: Duy nhất 1 mảng JSON chứa các bước: [{{ "step": 1, "speech": "...", "action": "...", "selector": "..." }}].

Bắt đầu viết kịch bản kĩ thuật:"""
            
            return {"prompt_letter": prompt}
        except Exception as e:
            print(f"❌ Lỗi tạo prompt: {e}")
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