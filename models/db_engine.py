import sqlite3
import os
import json
from config import Config

class DBEngine:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row # Cho phép truy cập theo tên cột row['title']
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        # 1. Bảng Tutorials
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                folder_name TEXT UNIQUE,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Bảng sub_contents (Knowledge Base)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tutorial_id INTEGER,
                module_name TEXT,
                sub_title TEXT,
                sub_folder TEXT,
                position INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Chưa quay',
                url TEXT,
                metadata TEXT,
                table_schema TEXT,
                sample_data TEXT,
                has_hidden_actions INTEGER DEFAULT 0, 
                action_type TEXT,
                UNIQUE(tutorial_id, sub_title),
                FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()

    # --- HÀM TRUY VẤN CORE ---

    def get_sub_content_by_id(self, sub_id):
        """Lấy 1 bản ghi và trả về dạng dict để an toàn khi xử lý"""
        sql = "SELECT * FROM sub_contents WHERE id = ?"
        row = self.fetchone(sql, (sub_id,))
        return dict(row) if row else None

    def get_neighbor_item(self, t_id, current_pos, direction):
        """Tìm item hàng xóm để đổi chỗ (Up/Down)"""
        if direction == "up":
            sql = "SELECT id, position FROM sub_contents WHERE tutorial_id = ? AND position < ? ORDER BY position DESC LIMIT 1"
        else:
            sql = "SELECT id, position FROM sub_contents WHERE tutorial_id = ? AND position > ? ORDER BY position ASC LIMIT 1"
        
        return self.fetchone(sql, (t_id, current_pos))

    def update_position(self, sub_id, new_pos):
        """Cập nhật vị trí hiển thị"""
        sql = "UPDATE sub_contents SET position = ? WHERE id = ?"
        self.execute(sql, (new_pos, sub_id))

    def save_mining_result(self, tutorial_id, mining_data):
        """Lưu kết quả từ TableMiner JS vào DB"""
        query = '''
            INSERT INTO sub_contents (
                tutorial_id, module_name, sub_title, url, 
                metadata, table_schema, sample_data, has_hidden_actions
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tutorial_id, sub_title) DO UPDATE SET
                metadata = excluded.metadata,
                table_schema = excluded.table_schema,
                sample_data = excluded.sample_data,
                has_hidden_actions = excluded.has_hidden_actions,
                status = 'Đã quét'
        '''
        
        metadata_json = json.dumps(mining_data.get('actions_detected', []), ensure_ascii=False)
        schema_json = json.dumps(mining_data.get('headers', []), ensure_ascii=False)
        sample_json = json.dumps(mining_data.get('sample_data', []), ensure_ascii=False)
        
        # Check hidden actions thông minh từ list actions
        actions = mining_data.get('actions_detected', [])
        has_hidden = 1 if any(a.get('sub_actions') for a in actions if isinstance(a, dict)) else 0

        params = (
            tutorial_id,
            mining_data.get('module_name', ''),
            mining_data.get('sub_title', ''),
            mining_data.get('url', ''),
            metadata_json,
            schema_json,
            sample_json,
            has_hidden
        )
        
        self.execute(query, params)
        self.commit()

    # --- UTILS HỖ TRỢ ---

    def execute(self, query, params=()):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print(f"❌ Lỗi SQL: {e} | Query: {query}")
            raise e

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def fetchone(self, query, params=()):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        cursor = self.execute(query, params)
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()