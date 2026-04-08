import os
import re
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
    
    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None, status="Chưa quay"):
        """
        Thêm nghiệp vụ con (Form) vào Database và tạo cấu trúc thư mục vật lý.
        Khớp 100% với các tham số truyền từ Scraper.
        """
        try:
            # 1. Tính toán vị trí hiển thị (Position)
            res = self.db.fetchone("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0
            
            # 2. Xử lý Metadata (Gộp với mặc định)
            final_metadata = self._get_default_metadata()
            if isinstance(metadata, dict): 
                final_metadata.update(metadata)
            
            # 3. INSERT VÀO DATABASE
            # Lưu ý: 'status' giờ đã được nhận diện như một tham số của hàm
            cursor = self.db.execute(
                "INSERT INTO sub_contents (tutorial_id, sub_title, sub_folder, position, status, url, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    t_id, 
                    sub_title, 
                    '', # sub_folder sẽ update ở bước sau
                    next_pos, 
                    status, # Sử dụng giá trị truyền từ hàm (ví dụ: 'scanned' hoặc 'Đã quét')
                    str(url or ""), 
                    json.dumps(final_metadata, ensure_ascii=False)
                )
            )
            new_id = cursor.lastrowid

            # 4. ĐỒNG BỘ ĐƯỜNG DẪN THƯ MỤC: {ID}_{slug_title}
            # Dùng slugify để tên folder không có dấu/khoảng trắng, tránh lỗi OS
            safe_sub_title = Config.slugify(sub_title)
            unique_folder_name = f"{new_id}_{safe_sub_title}"
            
            self.db.execute("UPDATE sub_contents SET sub_folder = ? WHERE id = ?", (unique_folder_name, new_id))
            
            # 5. TẠO CẤU TRÚC FOLDER VẬT LÝ "VÉT CẠN"
            # Đường dẫn thực tế: storage / {parent_folder} / {unique_folder_name} / ...
            for asset in ["raw", "outputs", "assets", "metadata"]:
                Config.get_path(app=parent_folder, module=unique_folder_name, asset_type=asset)
            
            self.db.commit()
            print(f"✅ [StudioController]: Đã thêm Form '{sub_title}' với ID {new_id}")
            return new_id

        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            self.db.rollback()
            return False

    # --- CẬP NHẬT TRÍ THỨC (Đây là chỗ quan trọng để đồng bộ ảnh) ---
    def update_sub_content(self, sub_id: int, **kwargs):
        """
        Cập nhật tri thức mới cho Form. 
        Đồng bộ hóa metadata từ VisionMachine vào Database.
        """
        try:
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: return False

            # 1. MAPPING THAM SỐ (Chống lọt lưới dữ liệu)
            new_url = kwargs.get('new_url') or kwargs.get('url')
            new_metadata = kwargs.get('new_metadata') or kwargs.get('metadata')
            new_status = kwargs.get('new_status') or kwargs.get('status')
            new_title = kwargs.get('new_title') or kwargs.get('title')

            # 2. XỬ LÝ METADATA (Merge thông minh)
            old_meta = json.loads(current['metadata']) if current['metadata'] else self._get_default_metadata()
            
            if new_metadata and isinstance(new_metadata, dict):
                # Đồng bộ Screenshot và môi trường từ VisionMachine
                if "environment" in new_metadata:
                    if "environment" not in old_meta: old_meta["environment"] = {}
                    old_meta["environment"].update(new_metadata["environment"])
                
                # Cập nhật các khối tri thức then chốt
                for key in ["session", "navigation", "main_content", "active_form"]:
                    if key in new_metadata: 
                        old_meta[key] = new_metadata[key]

                old_meta['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current['metadata']

            # 3. QUẢN LÝ TRẠNG THÁI (Status)
            status = new_status or current['status']
            # Tự động kích hoạt trạng thái "Đã quét" khi có tri thức
            if new_metadata and status == 'Chưa quay': 
                status = 'Đã quét'

            # 4. THỰC THI (SQL chuẩn chỉnh)
            self.db.execute("""
                UPDATE sub_contents 
                SET sub_title = :title, status = :status, url = :url, metadata = :meta 
                WHERE id = :id
            """, {
                "id": sub_id, 
                "title": new_title or current['sub_title'],
                "status": status, 
                "url": str(new_url or current['url'] or ""),
                "meta": final_meta_str
            })
            
            self.db.commit()
            print(f"✅ [StudioDB]: ID {sub_id} đã nạp tri thức mới thành công.")
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
        Rút gọn tri thức tối đa để AI viết kịch bản không bị "ngáo" tọa độ.
        """
        try:
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: return None
            sub = dict(row)

            raw_meta = json.loads(sub.get('metadata', '{}'))
            
            # Lọc lấy Label sạch (Bỏ qua tọa độ pixel rác)
            short_intel = {
                "breadcrumbs": raw_meta.get('navigation', {}).get('breadcrumbs', []),
                "main_buttons": [a['label'] for a in raw_meta.get('main_content', {}).get('actions', []) if a.get('label')],
                "form_inputs": [i['label'] for i in raw_meta.get('active_form', {}).get('inputs', []) if i.get('label')],
                "form_buttons": [a['label'] for a in raw_meta.get('active_form', {}).get('actions', []) if a.get('label')]
            }

            # Tạo Prompt kịch bản khung
            prompt = f"""
### 🎬 KỊCH BẢN: {sub.get('sub_title')}
**Mục tiêu:** Diễn hoạt nghiệp vụ vào đến màn hình '{short_intel['breadcrumbs'][-1] if short_intel['breadcrumbs'] else 'Nghiệp vụ'}'.

---
### 📍 LỘ TRÌNH DI CHUYỂN
Trang Chủ -> Click '{sub.get('module_name', 'Hệ thống')}' -> {' > '.join(short_intel['breadcrumbs'])}

---
### 🔍 CÁC ĐIỂM TƯƠNG TÁC (NHÃN CHUẨN)
- **Nhập liệu:** {', '.join(short_intel['form_inputs']) or 'Không có'}
- **Nút bấm:** {', '.join(short_intel['main_buttons'] + short_intel['form_buttons']) or 'Không có'}

---
### 📝 YÊU CẦU:
Viết kịch bản JSON gồm 3 giai đoạn: DI CHUYỂN -> TƯƠNG TÁC FORM -> KẾT THÚC.
            """
            return {
                "prompt_letter": prompt.strip(),
                "sub_id": sub_id,
                "raw_metadata": sub.get('metadata') # Vẫn gửi bản gốc phòng khi AI cần tọa độ chính xác
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
        folder_name: Tên folder dự án
        sub_folder: Tên folder sub-content (ví dụ: 10_them_moi_khach_hang)
        """
        try:
            self.db.execute("DELETE FROM sub_contents WHERE id = ?", (sub_id,))
            self.db.commit()
            
            # Xóa folder bằng Pathlib
            full_path = Config.get_path(app=folder_name, module=sub_folder)
            if full_path.exists():
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_sub_content: {e}")
            return False

    def update_sub_content_metadata(self, sub_id, metadata):
        return self.update_sub_content(sub_id, metadata=metadata)