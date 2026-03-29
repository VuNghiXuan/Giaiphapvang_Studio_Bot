import sqlite3
import os
import json
from config import Config

class DBEngine:
    def __init__(self):
        # Kết nối tới DB, cho phép sử dụng trên nhiều thread
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # 1. Bảng Dự án lớn (Tutorials)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                folder_name TEXT UNIQUE,
                position INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Bảng Bài học con (sub_contents)
        # Sắp xếp lại thứ tự cột cho chuẩn logic: Status đứng trước, URL/Metadata đứng sau
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sub_contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tutorial_id INTEGER,
                sub_title TEXT,
                sub_folder TEXT,
                position INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Chưa quay',
                url TEXT,
                metadata TEXT,
                FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE
            )
        ''')
        
        # --- LOGIC BẢO TRÌ SCHEMA (ALTER TABLE) ---
        # Kiểm tra xem các cột mới có tồn tại không, nếu không thì tự thêm
        cursor.execute("PRAGMA table_info(sub_contents)")
        columns = [column[1] for column in cursor.fetchall()]
        
        schema_updates = {
            'status': "ALTER TABLE sub_contents ADD COLUMN status TEXT DEFAULT 'Chưa quay'",
            'url': "ALTER TABLE sub_contents ADD COLUMN url TEXT",
            'metadata': "ALTER TABLE sub_contents ADD COLUMN metadata TEXT"
        }

        for col_name, sql_alter in schema_updates.items():
            if col_name not in columns:
                try:
                    cursor.execute(sql_alter)
                    print(f"✅ Đã bổ sung cột '{col_name}' vào DB")
                except Exception as e:
                    print(f"⚠️ Lỗi khi nâng cấp schema (cột {col_name}): {e}")
            
        self.conn.commit()

    def execute(self, query, params=()):
        """Thực thi câu lệnh SQL (Dùng cho INSERT, UPDATE, DELETE)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print(f"❌ Lỗi SQL: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            raise e

    def commit(self):
        """Lưu thay đổi vào Database"""
        self.conn.commit()

    def close(self):
        """Đóng kết nối"""
        self.conn.close()

    def fetchone(self, query, params=()):
        """Lấy 1 dòng kết quả"""
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        """Lấy tất cả dòng kết quả"""
        cursor = self.execute(query, params)
        return cursor.fetchall()