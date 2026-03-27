import sqlite3
from config import Config

class DBEngine:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # 1. Bảng Dự án lớn
        cursor.execute('''CREATE TABLE IF NOT EXISTS tutorials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            folder_name TEXT UNIQUE,
            position INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 2. Bảng Bài học con (Thêm cột metadata để lưu cấu trúc Form)
        cursor.execute('''CREATE TABLE IF NOT EXISTS sub_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tutorial_id INTEGER,
            sub_title TEXT,
            sub_folder TEXT,
            position INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Chưa quay',
            metadata TEXT, 
            FOREIGN KEY(tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE
        )''')
        
        # Kiểm tra xem cột metadata đã tồn tại chưa (phòng trường hợp DB cũ đã có)
        try:
            cursor.execute("SELECT metadata FROM sub_contents LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE sub_contents ADD COLUMN metadata TEXT")
            
        self.conn.commit()

    def execute(self, query, params=()):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print(f"❌ Lỗi SQL: {e}")
            raise e

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()