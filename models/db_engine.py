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
        
        # 2. Bảng sub_contents - THỨ TỰ CHUẨN ĐỂ KHÔNG BAO GIỜ LỆCH
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

    def rollback(self):
        """Hàm quay xe khi gặp lỗi DB"""
        try:
            if self.conn:
                self.conn.rollback()
                print("⏪ Đã thực hiện Rollback dữ liệu do có lỗi.")
        except Exception as e:
            print(f"❌ Không thể Rollback: {e}")
            
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