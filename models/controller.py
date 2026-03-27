import os
import shutil
import traceback
import json
from config import Config
from .db_engine import DBEngine

class StudioController:
    def __init__(self):
        # Kết nối DB và đảm bảo bảng đã có cột metadata
        self.db = DBEngine()

    # --- QUẢN LÝ DỰ ÁN LỚN (TUTORIALS) ---

    def create_tutorial(self, title):
        """Tạo dự án mới kèm thư mục vật lý"""
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
        """Lấy danh sách dự án sắp xếp theo position"""
        try:
            return self.db.execute("SELECT * FROM tutorials ORDER BY position ASC").fetchall()
        except Exception as e:
            print(f"❌ Lỗi get_all_tutorials: {e}")
            return []

    def delete_tutorial(self, t_id, folder_name):
        """Xóa sạch dự án: DB + Thư mục vật lý"""
        try:
            self.db.execute("DELETE FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            self.db.execute("DELETE FROM tutorials WHERE id = ?", (t_id,))
            self.db.commit()
            
            full_path = os.path.join(Config.BASE_STORAGE, folder_name)
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_tutorial: {e}")
            return False

    def move_tutorial(self, t_id, direction):
        """Hoán đổi vị trí giữa các dự án lớn"""
        try:
            curr = self.db.execute("SELECT id, position FROM tutorials WHERE id = ?", (t_id,)).fetchone()
            if not curr: return False
            curr_pos = curr['position']
            
            if direction == "up":
                target = self.db.execute("SELECT id, position FROM tutorials WHERE position < ? ORDER BY position DESC LIMIT 1", (curr_pos,)).fetchone()
            else:
                target = self.db.execute("SELECT id, position FROM tutorials WHERE position > ? ORDER BY position ASC LIMIT 1", (curr_pos,)).fetchone()

            if target:
                self.db.execute("UPDATE tutorials SET position = ? WHERE id = ?", (target['position'], t_id))
                self.db.execute("UPDATE tutorials SET position = ? WHERE id = ?", (curr_pos, target['id']))
                self.db.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ Lỗi move_tutorial: {e}")
            return False

    # --- QUẢN LÝ BÀI HỌC CON (SUB_CONTENTS) ---

    def add_sub_content(self, t_id, sub_title, parent_folder, metadata=None):
        """
        Thêm bài học mới kèm metadata (JSON structure từ Scraper).
        metadata: Có thể là Dictionary hoặc String JSON.
        """
        sub_folder_name = "".join([c if c.isalnum() else "_" for c in sub_title])
        full_sub_path = os.path.join(Config.BASE_STORAGE, parent_folder, sub_folder_name)
        
        # Đảm bảo metadata lưu vào DB là String JSON
        if isinstance(metadata, (dict, list)):
            metadata_str = json.dumps(metadata, ensure_ascii=False)
        else:
            metadata_str = metadata

        try:
            res = self.db.execute("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,)).fetchone()
            next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0

            self.db.execute(
                "INSERT INTO sub_contents (tutorial_id, sub_title, sub_folder, position, status, metadata) VALUES (?, ?, ?, ?, ?, ?)", 
                (t_id, sub_title, sub_folder_name, next_pos, "Chưa quay", metadata_str)
            )
            
            # Tạo cấu trúc thư mục làm việc
            os.makedirs(full_sub_path, exist_ok=True)
            os.makedirs(os.path.join(full_sub_path, "raw"), exist_ok=True)
            os.makedirs(os.path.join(full_sub_path, "outputs"), exist_ok=True)
            
            self.db.commit()
            return True
        except Exception as e:
            print(f"❌ Lỗi add_sub_content: {e}")
            traceback.print_exc()
            return False

    def get_sub_contents(self, tutorial_id):
        """Lấy danh sách bài học, tự động parse metadata từ String sang Dict"""
        try:
            rows = self.db.execute(
                "SELECT * FROM sub_contents WHERE tutorial_id = ? ORDER BY position ASC", 
                (tutorial_id,)
            ).fetchall()
            
            results = []
            for row in rows:
                item = dict(row)
                # Parse metadata để AI có thể đọc trực tiếp như một Dictionary
                if item.get('metadata'):
                    try:
                        item['metadata'] = json.loads(item['metadata'])
                    except:
                        pass 
                results.append(item)
            return results
        except Exception as e:
            print(f"❌ Lỗi get_sub_contents: {e}")
            return []

    def update_sub_content_metadata(self, sub_id, metadata):
        """Cập nhật lại tri thức khi Scraper chạy lại"""
        try:
            if isinstance(metadata, (dict, list)):
                metadata = json.dumps(metadata, ensure_ascii=False)
            
            self.db.execute("UPDATE sub_contents SET metadata = ? WHERE id = ?", (metadata, sub_id))
            self.db.commit()
            return True
        except Exception as e:
            print(f"❌ Lỗi update_sub_content_metadata: {e}")
            return False

    def move_sub_content(self, sub_id, direction):
        """Hoán đổi thứ tự bài học"""
        try:
            curr = self.db.execute("SELECT id, tutorial_id, position FROM sub_contents WHERE id = ?", (sub_id,)).fetchone()
            if not curr: return False
            curr = dict(curr)
            curr_pos = curr['position']
            t_id = curr['tutorial_id']

            if direction == "up":
                target = self.db.execute(
                    "SELECT id, position FROM sub_contents WHERE tutorial_id = ? AND position < ? ORDER BY position DESC LIMIT 1",
                    (t_id, curr_pos)
                ).fetchone()
            else:
                target = self.db.execute(
                    "SELECT id, position FROM sub_contents WHERE tutorial_id = ? AND position > ? ORDER BY position ASC LIMIT 1",
                    (t_id, curr_pos)
                ).fetchone()

            if target:
                target = dict(target)
                self.db.execute("UPDATE sub_contents SET position = ? WHERE id = ?", (target['position'], sub_id))
                self.db.execute("UPDATE sub_contents SET position = ? WHERE id = ?", (curr_pos, target['id']))
                self.db.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ Lỗi move_sub_content: {e}")
            return False

    def delete_sub_content(self, sub_id, folder_name, sub_folder):
        """Xóa bài học và dọn dẹp file vật lý"""
        try:
            self.db.execute("DELETE FROM sub_contents WHERE id = ?", (sub_id,))
            self.db.commit()
            
            full_path = os.path.join(Config.BASE_STORAGE, folder_name, sub_folder)
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_sub_content: {e}")
            return False