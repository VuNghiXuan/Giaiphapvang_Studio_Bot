import json
import os
from models.controller import StudioController
from config import Config

def test_database_integrity():
    print("🔍 ĐANG KIỂM TRA HỆ THỐNG CƠ SỞ DỮ LIỆU (VERSION 2)...\n")
    ctrl = StudioController()
    
    # 1. Tạo dự án Test
    project_name = "Test_Project_AI"
    ctrl.create_tutorial(project_name)
    
    # Lấy ID của dự án vừa tạo
    all_projects = ctrl.get_all_tutorials()
    project = next((t for t in all_projects if t['title'] == project_name), None)
    
    if not project:
        print("❌ Lỗi: Không tạo được dự án test.")
        return
    
    t_id = project['id']
    folder_name = project['folder_name']
    print(f"✅ Dự án '{project_name}' đã sẵn sàng (ID: {t_id})")

    # 2. Giả lập Metadata tri thức (Giống hệt dữ liệu Scraper quét được)
    sample_metadata = {
        "form_fields": [
            {"label": "Mã chi nhánh", "type": "text", "selector": "[name='code']", "required": True},
            {"label": "Tên chi nhánh", "type": "text", "selector": "[name='name']", "required": True},
            {"label": "Email", "type": "text", "selector": "[name='email']"}
        ],
        "actions": [
            {"label": "Lưu", "selector": "button.btn-primary"},
            {"label": "Hủy", "selector": "button.btn-cancel"}
        ],
        "last_scan": "2026-03-29"
    }
    
    sample_url = "https://giaiphapvang.com/chi-nhanh/add"

    # 3. Test hàm THÊM MỚI (add_sub_content)
    print("\n--- TEST THÊM FORM MỚI ---")
    res_add = ctrl.add_sub_content(
        t_id=t_id, 
        sub_title="Danh mục|Chi nhánh", 
        parent_folder=folder_name, 
        metadata=sample_metadata, 
        url=sample_url
    )
    
    if res_add:
        print("✅ Thêm Form 'Chi nhánh' thành công.")
    else:
        print("❌ Thêm Form thất bại.")

    # 4. Test hàm TRUY VẤN (get_sub_contents) - QUAN TRỌNG NHẤT
    print("\n--- TEST TRUY VẤN TRI THỨC ---")
    items = ctrl.get_sub_contents(t_id)
    
    if items:
        target = items[0]
        print(f"📍 Kết quả DB trả về cho Form: {target['sub_title']}")
        print(f"🔗 URL lưu trong DB: {target.get('url')}")
        print(f"🤖 Metadata (Type: {type(target.get('metadata'))}):")
        
        # Kiểm tra xem có parse được metadata không
        meta = target.get('metadata')
        if isinstance(meta, dict):
            print(f"   - Số lượng trường quét được: {len(meta.get('form_fields', []))}")
            print(f"   - Thao tác: {', '.join([a.get('label') for a in meta.get('actions', [])])}")
            
            if target.get('url') == sample_url:
                print("\n⭐ KẾT LUẬN: DB LƯU TRỮ URL VÀ METADATA CHUẨN XÁC!")
            else:
                print("\n⚠️ CẢNH BÁO: URL bị sai lệch hoặc None.")
        else:
            print("❌ Lỗi: Metadata không được tự động parse sang Dictionary.")
    else:
        print("❌ Không tìm thấy dữ liệu con nào trong DB.")

    # 5. Dọn dẹp (Tùy chọn) - Nếu muốn xóa luôn sau khi test thì bỏ comment 2 dòng dưới
    # ctrl.delete_tutorial(t_id, folder_name)
    # print("\n🧹 Đã dọn dẹp dữ liệu test.")

if __name__ == "__main__":
    test_database_integrity()