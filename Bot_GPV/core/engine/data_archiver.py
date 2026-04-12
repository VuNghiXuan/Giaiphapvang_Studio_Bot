import json
import os
from pathlib import Path

class DataArchiver:
    def __init__(self, config_class, controller_instance):
        self.config = config_class
        self.ctrl = controller_instance

    async def archive(self, results, mode, tutorial_id, project_folder, modul_name=None):
        """
        Lưu trữ dữ liệu thông minh: 
        Biến dữ liệu từ Miner thành cấu trúc thư mục và bản ghi DB chuẩn hóa.
        """
        print(f"📦 [Archiver] Đang bắt đầu lưu trữ với chế độ: {mode}")
        
        # FIX LỖI AttributeError: Kiểm tra nếu results bị truyền vào sai kiểu
        if not results:
            print("⚠️ [Archiver] Kết quả rỗng, bỏ qua lưu trữ.")
            return

        if mode == "DEEP_SCAN":
            # Chế độ nội soi: results là Dictionary { "Path | To | Menu": {data} }
            if not isinstance(results, dict):
                print(f"❌ [Archiver] Lỗi: Mode DEEP_SCAN yêu cầu dict nhưng nhận {type(results)}")
                return

            for path, data in results.items():
                # Kiểm tra dữ liệu data bên trong
                if not isinstance(data, dict):
                    print(f"⚠️ [Archiver] Bỏ qua path '{path}' vì data không phải dict.")
                    continue

                # 1. PHÂN TÍCH ĐƯỜNG DẪN
                parts = [p.strip() for p in path.split('|')]
                
                # Xác định Module chính
                actual_module = modul_name
                if not actual_module or actual_module == "Chung":
                    actual_module = parts[0] if parts else "Hệ thống"
                
                # 2. TÍNH TOÁN THƯ MỤC LƯU TRỮ (Slugify folder)
                # Ví dụ: thiet_lap/danh_muc/khach_hang
                calculated_sub_folder = "/".join([self.config.slugify(p) for p in parts])

                # 3. ĐỒNG BỘ VÀO DATABASE
                existing = self.ctrl.get_sub_by_title(path, tutorial_id)
                
                # LẤY METADATA AN TOÀN: Đảm bảo không lỗi .get()
                metadata_payload = data.get('metadata', {})
                target_url = data.get('url', '')

                try:
                    if existing:
                        sub_id = existing['id']
                        print(f"🔄 [Archiver] Cập nhật metadata cho: {path}")
                        self.ctrl.update_sub_content(
                            sub_id=sub_id,
                            metadata=metadata_payload,
                            status="Đã nội soi",
                            url=target_url,
                            module_name=actual_module,
                            sub_folder=calculated_sub_folder
                        )
                    else:
                        print(f"✨ [Archiver] Tạo mới bản ghi cho: {path}")
                        sub_id = self.ctrl.add_sub_content(
                            t_id=tutorial_id, 
                            sub_title=path, 
                            parent_folder=project_folder,
                            url=target_url, 
                            metadata=metadata_payload, 
                            status="Đã nội soi",
                            module_name=actual_module,
                            sub_folder=calculated_sub_folder
                        )
                    
                    # 4. LƯU FILE VẬT LÝ (Metadata JSON)
                    if sub_id and metadata_payload: 
                        self._save_physical_file(metadata_payload, project_folder, calculated_sub_folder)
                except Exception as e:
                    print(f"❌ [Archiver] Lỗi khi tương tác DB: {e}")

        elif mode == "HOME_SCAN":
            # Chế độ quét menu trang chủ
            modules = results if isinstance(results, list) else results.get('modules', [])
            for mod in modules:
                m_text = mod.get('text', 'Unknown')
                full_title = f"{m_text}|Home"
                
                existing = self.ctrl.get_sub_by_title(full_title, tutorial_id)
                
                if existing:
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
            print(f"✅ [Archiver] Đã lưu {len(modules)} module từ trang chủ.")

    def _save_physical_file(self, data, project_slug, sub_path):
        """
        Lưu Metadata thành file fields.json.
        Đường dẫn mới: storage/{project_slug}/{sub_path}/metadata/fields.json
        (Bỏ app_projects, gom tri thức vào sub-folder metadata cho sạch)
        """
        try:
            # 1. Lấy root storage từ Config (Ví dụ: D:/.../storage)
            # Nếu không có Config thì mặc định dùng Path("storage")
            base_storage = getattr(self.config, 'BASE_STORAGE', Path("storage"))
            
            # 2. Xây dựng đường dẫn: storage/ung_dung_vang/he_thong/settings/metadata/
            # Tôi khuyên ông nên cho fields.json vào folder 'metadata' 
            # để tách biệt với các folder 'raw' hay 'outputs' sau này.
            base_dir = base_storage / project_slug / sub_path / "metadata"
            base_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = base_dir / "fields.json"
            
            # 3. Ghi file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            print(f"💾 [File] Đã nạp tri thức vào: {file_path}")
            
        except Exception as e:
            print(f"❌ [File] Lỗi ghi file vật lý: {e}")