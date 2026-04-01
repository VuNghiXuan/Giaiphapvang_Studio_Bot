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

    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None):
        """
        Thêm mới sub-content: 
        1. Chống trùng URL nghiệp vụ.
        2. Tự động định danh thư mục theo ID (Chống trùng folder vật lý).
        3. Chuẩn hóa Metadata từ Scanner.js 2026.
        """
        try:
            # 1. KIỂM TRA TRÙNG LẶP (Dựa trên URL và Tutorial ID)
            if url and url.strip() != "":
                existing = self.db.fetchone(
                    "SELECT id FROM sub_contents WHERE tutorial_id = ? AND url = ?", 
                    (t_id, url)
                )
                if existing:
                    print(f"ℹ️ URL nghiệp vụ đã tồn tại ID {existing['id']}: {url}")
                    return existing['id'] 

            # 2. TÍNH TOÁN VỊ TRÍ (Position)
            res = self.db.fetchone(
                "SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", 
                (t_id,)
            )
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0

            # 3. CHUẨN HÓA METADATA (Ép kiểu về JSON string an toàn)
            # Scanner mới trả về cấu trúc: {location, navigation, content, state}
            if isinstance(metadata, (dict, list)):
                meta_str = json.dumps(metadata, ensure_ascii=False)
            else:
                # Nếu metadata rỗng, tạo khung chuẩn để không lỗi khi parse sau này
                meta_str = json.dumps({
                    "location": {}, 
                    "navigation": {"sidebar_menu": [], "tabs": []}, 
                    "content": {"primary_actions": [], "form_fields": []},
                    "state": {}
                }, ensure_ascii=False)

            # 4. INSERT DỮ LIỆU TẠM THỜI (Để lấy ID thực tế)
            query = """
                INSERT INTO sub_contents (tutorial_id, sub_title, sub_folder, position, status, url, metadata)
                VALUES (:t_id, :title, '', :pos, 'Chưa quay', :url, :meta)
            """
            params = {
                "t_id": t_id, 
                "title": sub_title, 
                "pos": next_pos, 
                "url": str(url or ""), 
                "meta": meta_str
            }
            cursor = self.db.execute(query, params)
            new_id = cursor.lastrowid

            # 5. ĐỊNH DANH THƯ MỤC VẬT LÝ (Unique Folder Name)
            # Format: [ID]_[Tiêu đề không dấu] (Ví dụ: 42_Thanh_toan_hoa_don)
            safe_title = "".join([c if c.isalnum() else "_" for c in sub_title])
            unique_folder_name = f"{new_id}_{safe_title}"
            
            # Cập nhật ngược lại tên folder vào DB
            self.db.execute(
                "UPDATE sub_contents SET sub_folder = ? WHERE id = ?", 
                (unique_folder_name, new_id)
            )

            # 6. TẠO CẤU TRÚC THƯ MỤC LƯU TRỮ TRÊN Ổ ĐĨA
            # Đường dẫn: D:\ThanhVu\Storage\[Parent]\[Unique_Folder]
            full_sub_path = os.path.join(Config.BASE_STORAGE, parent_folder, unique_folder_name)
            
            os.makedirs(full_sub_path, exist_ok=True)
            for sub_f in ["raw", "outputs", "assets"]:
                # raw: chứa video quay từ Playwright
                # assets: chứa file lồng tiếng (TTS), phụ đề, screenshot
                # outputs: chứa video Final cho Tường Vân Apps
                os.makedirs(os.path.join(full_sub_path, sub_f), exist_ok=True)
            
            self.db.commit()
            print(f"✅ Đã thêm Sub-content ID {new_id}: {sub_title}")
            return new_id

        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            self.db.rollback()
            return False
        

    def update_sub_content(self, sub_id: int, **kwargs):
        """
        Cập nhật Sub-content thông minh:
        - Tự động nhận diện Metadata (Dict/List/String).
        - Chỉ cập nhật những trường được truyền vào (kwargs).
        - Chống lỗi Double JSON Stringify.
        """
        try:
            # 1. Kiểm tra sự tồn tại của record
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current: 
                print(f"⚠️ Không tìm thấy sub_id: {sub_id}")
                return False

            # 2. XỬ LÝ METADATA (Trái tim của hàm)
            # Chấp nhận cả 'metadata' hoặc 'new_metadata' cho linh hoạt
            new_meta = kwargs.get('metadata') or kwargs.get('new_metadata')
            final_meta = current['metadata']

            if new_meta is not None:
                if isinstance(new_meta, (dict, list)):
                    final_meta = json.dumps(new_meta, ensure_ascii=False)
                elif isinstance(new_meta, str):
                    try:
                        # Kiểm tra xem chuỗi có phải JSON hợp lệ không
                        json.loads(new_meta)
                        final_meta = new_meta
                    except ValueError:
                        # Nếu là chuỗi thường (như ghi chú), bọc nó vào JSON
                        final_meta = json.dumps(new_meta, ensure_ascii=False)

            # 3. CHUẨN BỊ PARAMS (Ưu tiên giá trị mới, không có thì dùng cũ)
            # Cách này giúp Vũ update lẻ tẻ từng trường mà không sợ mất data trường khác
            params = {
                "id": sub_id,
                "title": kwargs.get('title') or kwargs.get('new_title') or current['sub_title'],
                "status": kwargs.get('status') or kwargs.get('new_status') or current['status'],
                "url": str(kwargs.get('url') or kwargs.get('new_url') or current['url'] or ""),
                "meta": final_meta
            }

            # Tự động chuyển trạng thái nếu vừa cập nhật Metadata mới từ Scanner
            if new_meta and params['status'] == 'Chưa quay':
                params['status'] = 'Đã quét' # Hoặc 'Sẵn sàng' tùy Vũ đặt

            # 4. THỰC THI SQL
            query = """
                UPDATE sub_contents 
                SET sub_title = :title, 
                    status = :status, 
                    url = :url, 
                    metadata = :meta 
                WHERE id = :id
            """
            self.db.execute(query, params)
            self.db.commit()
            
            print(f"✅ Đã cập nhật Sub-content ID {sub_id}")
            return True

        except Exception as e:
            print(f"❌ Lỗi update_sub_content: {e}")
            self.db.rollback() # Luôn rollback nếu lỗi để an toàn DB
            return False

    def get_sub_contents(self, tutorial_id):
        """
        Lấy danh sách trang con và chuẩn hóa Metadata từ scanner.js 2026.
        Sắp xếp theo thứ tự nghiệp vụ (position) để AI hiểu luồng logic.
        """
        try:
            # 1. Truy vấn dữ liệu
            query = "SELECT * FROM sub_contents WHERE tutorial_id = ? ORDER BY position ASC"
            rows = self.db.fetchall(query, (tutorial_id,))
            results = []
            
            for row in rows:
                item = dict(row)
                item['url'] = str(item.get('url') or "")
                
                # 2. Parse JSON an toàn (Tránh crash nếu dữ liệu DB lỗi)
                meta_raw = item.get('metadata')
                meta = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    except:
                        meta = {}
                
                # 3. Trích xuất các phân vùng dữ liệu chính theo Schema mới
                content = meta.get('content', {})
                nav = meta.get('navigation', {})
                state = meta.get('state', {})
                
                # 4. TÓM TẮT NỘI DUNG (Summary for AI/UI)
                # Phần này giúp Vũ nhìn nhanh trên UI biết bài nào đã quét đủ dữ liệu
                item['summary'] = {
                    "num_fields": len(content.get('form_fields', [])),
                    # Tổng hợp tất cả các loại hành động có thể tương tác
                    "num_actions": (
                        len(content.get('primary_actions', [])) + 
                        len(content.get('row_operations', []))
                    ),
                    "num_tabs": len(nav.get('tabs', [])),
                    "table_columns": content.get('table_columns', []),
                    "is_dialog": state.get('is_dialog_open', False) or state.get('has_overlay', False)
                }

                # 5. CHUẨN HÓA METADATA GỐC (Đảm bảo không bao giờ bị null)
                # Nếu metadata rỗng, ta trả về khung chuẩn để các hàm khác không bị crash
                if not meta or not meta.get('content'):
                    item['metadata'] = {
                        "location": {},
                        "navigation": {"sidebar_menu": [], "tabs": []},
                        "content": {"primary_actions": [], "row_operations": [], "form_fields": []},
                        "state": {}
                    }
                else:
                    item['metadata'] = meta
                
                results.append(item)
                
            return results

        except Exception as e:
            print(f"❌ Lỗi get_sub_contents (Tutorial ID {tutorial_id}): {e}")
            return []

    def get_formatted_meta_for_ai(self, sub_id, mode="auto"):
        """
        Hàm đóng gói Full Prompt: Linh hoạt cho mọi Module và mọi loại Form.
        mode="add": Ép làm kịch bản thêm mới.
        mode="auto": Tự nhận diện dựa trên metadata.
        """
        try:
            sub = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not sub: return None
            
            meta = json.loads(sub['metadata']) if isinstance(sub['metadata'], str) else (sub['metadata'] or {})
            content = meta.get("content", {})
            
            # --- 1. LỌC FIELD THÔNG MINH ---
            form_fields = [
                f for f in content.get("form_fields", []) 
                if f.get('selector') != "#_r_p_" and "tìm kiếm" not in f.get('label', '').lower()
            ]

            path_parts = [p.strip() for p in sub['sub_title'].split('|')]
            execution_flow = [
                {"step": 1, "action": "navigate", "target": "https://giaiphapvang.net/", "desc": "Mở hệ thống Giải Pháp Vàng"}
            ]
            current_step = 2
            
            # --- 2. SIDEBAR (Linh hoạt mọi cấp độ) ---
            for part in path_parts:
                execution_flow.append({
                    "step": current_step,
                    "action": "click", 
                    "target": f".MuiListItemButton-root:has-text('{part}')",
                    "desc": f"Chọn {part}"
                })
                current_step += 1

            # --- 3. HÀNH ĐỘNG MỞ FORM (Chỉ click nếu tìm thấy nút phù hợp) ---
            primary_actions = content.get("primary_actions", [])
            # Tìm nút 'Tạo mới' hoặc 'Thêm'
            open_form_btn = next((b for b in primary_actions if any(kw in b.get('label', '') for kw in ["Tạo", "Thêm", "Mới", "Lập"])), None)
            
            if open_form_btn:
                execution_flow.append({
                    "step": current_step,
                    "action": "click",
                    "target": open_form_btn.get('selector'),
                    "desc": f"Bấm {open_form_btn['label']} để mở form nhập liệu"
                })
                current_step += 1

            # --- 4. ĐIỀN FORM (Chỉ thêm bước nếu có field) ---
            if form_fields:
                execution_flow.append({
                    "step": current_step, "action": "fill_form", 
                    "fields": form_fields, "desc": "Hoàn thiện các thông tin nghiệp vụ"
                })
                current_step += 1
            
            # --- 5. NÚT KẾT THÚC (Lưu/Xác nhận/In) ---
            submit_btn = next((b for b in primary_actions if any(kw in b.get('label', '') for kw in ["Lưu", "Hoàn tất", "Xác nhận", "In"])), None)
            execution_flow.append({
                "step": current_step, "action": "click", 
                "target": submit_btn.get('selector') if submit_btn else "button:has-text('Lưu')", 
                "desc": f"Bấm {submit_btn['label'] if submit_btn else 'Lưu'} để kết thúc"
            })

            # --- 6. ĐÓNG GÓI VỚI CHỈ THỊ NGỮ CẢNH ---
            blueprint = {"flow": execution_flow, "form_details": form_fields}
            
            # Tự động định nghĩa ngành hàng dựa trên tiêu đề (Vàng/Cầm đồ/Kế toán)
            title_l = sub['sub_title'].lower()
            context = "quản lý tiệm vàng"
            if "cầm đồ" in title_l: context = "nghiệp vụ cầm đồ"
            elif "thuế" in title_l or "kế toán" in title_l: context = "kế toán tài chính"

            full_letter = f"""Mày là Chuyên gia Đào tạo {context} tại Giải Pháp Vàng.
Hãy viết kịch bản video hướng dẫn: "{sub['sub_title']}".

--- 📦 DỮ LIỆU BLUEPRINT ---
{json.dumps(blueprint, ensure_ascii=False, indent=2)}

--- 🛠 CHỈ THỊ ---
1. NGÔN NGỮ: Dùng thuật ngữ {context} chuyên nghiệp.
2. THÔNG TIN MẪU: Tự bịa dữ liệu mẫu phù hợp ngành vàng (VD: Vàng 610, Trọng lượng 1.234 chỉ...).
3. KHÔNG TƯƠNG TÁC SEARCH: Bỏ qua '#_r_p_'.
4. FORMAT: Trả về duy nhất 1 MẢNG JSON PHẲNG.
"""
            return {"prompt_letter": full_letter}
        except Exception as e:
            return None
        
    def update_sub_content_metadata(self, sub_id, metadata):
        """Cập nhật metadata (nhận vào dict/list)"""
        return self.update_sub_content(sub_id, new_metadata=metadata)

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