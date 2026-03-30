import os
import re

class ProjectInspector:
    def __init__(self, project_path):
        self.project_path = project_path
        # 1. Pattern tìm SQL INSERT/UPDATE
        self.sql_write_pattern = re.compile(r'\.(execute|executemany)\s*\(\s*["\'](INSERT|UPDATE).*?["\']', re.IGNORECASE | re.DOTALL)
        
        # 2. Pattern tìm hàm cập nhật (update_sub_content)
        self.update_func_pattern = re.compile(r'update_sub_content\((.*?)\)', re.IGNORECASE)
        
        # 3. Pattern tìm logic gán biến (A = B) liên quan đến status/url
        self.assignment_pattern = re.compile(r'(status|url|metadata)\s*=\s*(.*)', re.IGNORECASE)

    def inspect(self):
        print(f"🔍 Đang quét hệ thống (Đã loại bỏ Comment & Definition) tại: {self.project_path}")
        print("="*80)
        
        for root, dirs, files in os.walk(self.project_path):
            ignore_dirs = ['env', 'venv', '.git', '__pycache__', 'node_modules', 'inspector.py']
            if any(x in root for x in ignore_dirs): continue
                
            for file in files:
                if file.endswith('.py') and not any(x in file.lower() for x in ['copy', 'backup']):
                    self.check_file(os.path.join(root, file))

    def check_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except: return
            
        file_printed = False
        
        for i, line in enumerate(lines):
            line_strip = line.strip()
            # --- BỘ LỌC THÔNG MINH: Bỏ qua dòng comment hoặc dòng trống ---
            if not line_strip or line_strip.startswith('#'):
                continue

            issues = []
            line_lower = line_strip.lower()
            
            # --- KIỂM TRA 1: SQL TRUYỀN DẤU '?' ---
            if self.sql_write_pattern.search(line):
                if '?' in line and ':' not in line:
                    issues.append("⚠️ SQL dùng dấu '?' - Dễ lệch cột. Nên chuyển sang ':name'.")
                if 'status' in line_lower and 'url' in line_lower:
                    if line_lower.find('status') > line_lower.find('url'):
                        issues.append("💡 Cẩn thận: Thứ tự 'url' và 'status' trong SQL có thể bị đảo.")

            # --- KIỂM TRA 2: HÀM UPDATE (Chỉ kiểm tra LỜI GỌI HÀM, bỏ qua DEF) ---
            update_match = self.update_func_pattern.search(line)
            if update_match:
                # Nếu dòng này chứa 'def ', tức là đang khai báo hàm -> KHÔNG BÁO LỖI
                if 'def ' in line_lower:
                    pass 
                else:
                    content = update_match.group(1)
                    # Nếu gọi hàm mà không có dấu '=' (truyền theo vị trí) và có nhiều hơn 2 tham số
                    if '=' not in content and len(content.split(',')) > 1:
                        issues.append("⚠️ Gọi hàm update bằng vị trí. Hãy dùng 'new_url=...' để an toàn!")

            # --- KIỂM TRA 3: LOGIC GÁN BIẾN NGHI VẤN ---
            assign_match = self.assignment_pattern.search(line_strip)
            if assign_match:
                target, value = assign_match.groups()
                # Nếu gán cái gì đó có chữ 'url' hoặc 'http' vào biến 'status'
                if 'status' in target.lower() and ('http' in value or 'url' in value.lower()):
                    issues.append(f"🚨 CẢNH BÁO: Đang gán URL vào biến '{target}'!")

            # In kết quả
            if issues:
                if not file_printed:
                    print(f"\n📄 FILE: {os.path.relpath(file_path, self.project_path)}")
                    file_printed = True
                for issue in issues:
                    print(f"   [Dòng {i+1}]: {issue}")
                    print(f"      👉 Code: {line_strip}")

if __name__ == "__main__":
    current_root = os.path.dirname(os.path.abspath(__file__))
    inspector = ProjectInspector(current_root)
    inspector.inspect()
    print("\n✅ Rà soát hoàn tất. Nếu không có thông báo gì, code của Vũ đã chuẩn đét!")