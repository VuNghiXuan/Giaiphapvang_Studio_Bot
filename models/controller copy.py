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
        """Thêm mới - Chống trùng và Chống lệch cột tuyệt đối"""
        sub_folder_name = "".join([c if c.isalnum() else "_" for c in sub_title])
        full_sub_path = os.path.join(Config.BASE_STORAGE, parent_folder, sub_folder_name)

        try:
            # 1. Chống trùng URL trong cùng project
            if url:
                existing = self.db.fetchone("SELECT id FROM sub_contents WHERE tutorial_id = ? AND url = ?", (t_id, url))
                if existing: return True 

            # 2. Tính Position
            res = self.db.fetchone("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0

            # 3. Insert với Named Parameters
            query = """
                INSERT INTO sub_contents (tutorial_id, sub_title, sub_folder, position, status, url, metadata)
                VALUES (:t_id, :title, :folder, :pos, 'Chưa quay', :url, :meta)
            """
            params = {
                "t_id": t_id, "title": sub_title, "folder": sub_folder_name,
                "pos": next_pos, "url": str(url or ""),
                "meta": json.dumps(metadata, ensure_ascii=False) if isinstance(metadata, (dict, list)) else (metadata or "")
            }
            self.db.execute(query, params)
            
            # 4. Tạo thư mục
            os.makedirs(full_sub_path, exist_ok=True)
            for f in ["raw", "outputs", "assets"]: os.makedirs(os.path.join(full_sub_path, f), exist_ok=True)
            
            self.db.commit()
            return True
        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            return False

    # def update_sub_content(self, sub_id, **kwargs):
    #     try:
    #         current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
    #         if not current: return False

    #         # Chỉ lấy giá trị mới nếu có truyền vào, không thì giữ nguyên bản gốc từ DB
    #         new_title = kwargs.get('new_title', current['sub_title'])
    #         new_status = kwargs.get('new_status', current['status'])
    #         new_url = kwargs.get('new_url', current['url'])
            
    #         # Xử lý metadata an toàn
    #         new_meta_raw = kwargs.get('new_metadata')
    #         if new_meta_raw is not None:
    #             new_meta = json.dumps(new_meta_raw, ensure_ascii=False) if isinstance(new_meta_raw, (dict, list)) else new_meta_raw
    #         else:
    #             new_meta = current['metadata']

    #         query = "UPDATE sub_contents SET sub_title=:title, status=:status, url=:url, metadata=:meta WHERE id=:id"
    #         params = {"title": new_title, "status": new_status, "url": new_url, "meta": new_meta, "id": sub_id}
            
    #         self.db.execute(query, params)
    #         self.db.commit()
    #         return True
    #     except Exception as e:
    #         print(f"❌ Lỗi update_sub_content: {e}")
    #         return False

    def update_sub_content(self, sub_id, **kwargs):
        """Update thông minh - Tuyệt đối không nhầm cột giữa Status và URL"""
        try:
            # 1. Lấy dữ liệu hiện tại để giữ lại nếu kwargs không truyền vào
            current = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not current:
                return False

            # 2. Chuẩn bị params (Dùng Named Parameters để mapping chính xác vào Query)
            # Chú ý: kwargs.get('new_url') phải vào :url, kwargs.get('new_status') phải vào :status
            params = {
                "id": sub_id,
                "title": kwargs.get('new_title', current['sub_title']),
                "status": kwargs.get('new_status', current['status']),
                "url": str(kwargs.get('new_url', current['url'] or "")),
                "meta": current['metadata']
            }
            
            # 3. Xử lý Metadata riêng nếu có truyền new_metadata
            new_meta = kwargs.get('new_metadata')
            if new_meta is not None:
                import json
                params["meta"] = json.dumps(new_meta, ensure_ascii=False) if isinstance(new_meta, (dict, list)) else new_meta

            # 4. Câu lệnh SQL dùng Named Placeholders (:name) cực kỳ an toàn
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
            return True
            
        except Exception as e:
            print(f"❌ Lỗi update_sub_content tại controller: {e}")
            return False

    def get_sub_contents(self, tutorial_id):
        try:
            query = "SELECT id, tutorial_id, sub_title, sub_folder, position, status, url, metadata FROM sub_contents WHERE tutorial_id = ? ORDER BY position ASC"
            rows = self.db.fetchall(query, (tutorial_id,))
            results = []
            for row in rows:
                item = dict(row)
                item['url'] = str(item.get('url') or "")
                # Parse JSON metadata an toàn
                meta = item.get('metadata')
                try:
                    item['metadata'] = json.loads(meta) if (meta and meta.startswith(('{', '['))) else {}
                except:
                    item['metadata'] = {}
                results.append(item)
            return results
        except Exception as e:
            print(f"❌ Lỗi get_sub_contents: {e}")
            return []

    def update_sub_content_metadata(self, sub_id, metadata):
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