import json
from config import Config
from models.controller import StudioController
import os

class DataArchiver:
    def __init__(self):
        self.ctrl = StudioController()

    async def archive(self, results, mode, tutorial_id, project_folder, modul_name=None):
        """
        Lưu trữ dữ liệu thông minh: Tự động nhận diện Module từ cấu trúc đường dẫn.
        """
        if mode == "DEEP_SCAN":
            for path, data in results.items():
                # 🔥 LOGIC TỰ ĐỘNG NHẬN DIỆN MODULE:
                # Nếu modul_name không có hoặc là "Chung", ta lấy phần tử đầu tiên của path
                # Ví dụ: "Hệ thống | Chung | Công ty" -> lấy "Hệ thống"
                actual_module = modul_name
                if not actual_module or actual_module == "Chung":
                    actual_module = path.split('|')[0].strip() if '|' in path else "Hệ thống"

                existing = self.ctrl.get_sub_by_title(path, tutorial_id)
                
                if existing:
                    sub_id = existing['id']
                    # Cập nhật thông tin cũ + Ghi nhận module_name chính xác
                    self.ctrl.update_sub_content(
                        sub_id=sub_id,
                        metadata=data.get('metadata'),
                        status="Đã nội soi",
                        url=data.get('url'),
                        module_name=actual_module # 👈 Đã tối ưu
                    )
                else:
                    # Nếu chưa có: Thêm mới hoàn toàn
                    sub_id = self.ctrl.add_sub_content(
                        t_id=tutorial_id, 
                        sub_title=path, 
                        parent_folder=project_folder,
                        url=data.get('url'), 
                        metadata=data.get('metadata'), 
                        status="Đã nội soi",
                        module_name=actual_module # 👈 Đã tối ưu
                    )
                
                # 2. Lưu file JSON
                if sub_id and data.get('metadata'): 
                    self._save_json(sub_id, data.get('metadata'), path)
        
        elif mode == "HOME_SCAN":
            modules = results if isinstance(results, list) else results.get('modules', [])
            for mod in modules:
                m_text = mod.get('text')
                full_title = f"{m_text}|Home"
                existing = self.ctrl.get_sub_by_title(full_title, tutorial_id)
                
                if existing:
                    # Cập nhật URL và ghi nhận module_name cho trang Home
                    self.ctrl.update_sub_content(
                        sub_id=existing['id'], 
                        url=mod.get('href'),
                        module_name=m_text 
                    )
                else:
                    self.ctrl.add_sub_content(
                        t_id=tutorial_id, 
                        sub_title=full_title,
                        parent_folder=project_folder, 
                        url=mod.get('href'), 
                        status="Chờ nội soi",
                        module_name=m_text
                    )
                    

    def _save_json(self, sub_id, metadata, full_path_title):
        try:
            # Ép kiểu dict ngay tại đây để tránh lỗi 'sqlite3.Row' đã gặp
            row_data = self.ctrl.db.fetchone("SELECT sub_folder FROM sub_contents WHERE id = ?", (sub_id,))
            row = dict(row_data) if row_data else {}
            
            if row.get('sub_folder'):
                logic_path = row['sub_folder']
            else:
                # Đồng bộ logic slugify với StudioController
                parts = [Config.slugify(p.strip()) for p in full_path_title.split('|')]
                if len(parts) > 1 and parts[1] == "chung": parts[1] = "settings"
                logic_path = "/".join(parts)

            # Đảm bảo dùng Pathlib xuyên suốt cho an toàn
            from pathlib import Path
            target_dir = Path(Config.BASE_STORAGE) / Config.APP_SLUG / logic_path / "metadata"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / "fields.json"
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            
            print(f"🎯 [Kịch bản]: Đã lưu đúng chỗ -> {file_path}")

        except Exception as e:
            print(f"❌ Lỗi định vị folder lưu JSON: {e}")

    def save_metadata(self, script_data, project_name, module_name, form_name):
        """
        Ép kịch bản phải chui vào đúng folder nghiệp vụ.
        """
        try:
            # 1. Dùng hàm chuẩn của Config để lấy path (như bên Engine)
            # Nó sẽ build ra: storage/ung_dung_vang/he_thong/settings/...
            base_folder = Config.get_asset_path(
                project_name=project_name, 
                module_name=module_name, 
                form_name=form_name, 
                asset_type="" # Để trống để lấy folder gốc của form đó
            )

            # 2. Thêm folder 'metadata' vào cuối
            target_dir = os.path.join(base_folder, "metadata")
            
            # 3. Tạo thư mục (nếu chưa có)
            os.makedirs(target_dir, exist_ok=True)

            # 4. Ghi file
            file_path = os.path.join(target_dir, "fields.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=4)
                
            print(f"🎯 Đã lưu kịch bản ĐÚNG CHỖ: {file_path}")
            
        except Exception as e:
            print(f"❌ Lỗi lưu kịch bản: {e}")