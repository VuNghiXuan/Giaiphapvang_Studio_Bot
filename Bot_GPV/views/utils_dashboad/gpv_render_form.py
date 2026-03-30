import streamlit as st
import os
import json
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
# from Bot_GPV.views.components.gpv_component import GPVComponent
from Bot_GPV.views.components.gpv_component import GPVComponent
from config import Config

# Khởi tạo bộ não AI
ai_script = AIScripts()

def render_gpv_logic(ctrl, p, ai_script):
    """Điều hướng chính: Tối ưu chống Loop và Chồng lấn UI"""
    
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    # Lấy dữ liệu từ DB (Chuyển Row thành Dict để dễ xử lý)
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]

    # NHÁNH 1: GIAO DIỆN CHI TIẾT FORM (CẤP 2)
    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        # Đảm bảo truyền đủ ai_script vào hàm cấp 2
        render_gpv_forms(ctrl, p, st.session_state.current_modul, ai_script)
        return # Chặn đứng để không render trang chủ bên dưới

    # NHÁNH 2: GIAO DIỆN CHỌN MODULE (TRANG CHỦ - CẤP 1)
    st.markdown("### 📦 Hệ thống Module")
    
    with st.expander("⚙️ ĐỒNG BỘ MODULE (CẤP 1)", expanded=False):
        if st.button("🔍 QUÉT MODULES MỚI", use_container_width=True, type="primary", key="btn_scan_c1"):
            with st.spinner("Đang quét danh sách Module..."):
                extractor = GiaiphapvangScraper()
                # Lấy danh sách module từ trang chủ phần mềm
                home_modules = extractor.get_home_modules()
                
                count_new = 0
                for mod in home_modules:
                    full_t = f"{mod['text']}|Home"
                    # Kiểm tra xem Module này đã có trong DB chưa
                    existing = next((s for s in db_subs if s['sub_title'] == full_t), None)
                    
                    if not existing:
                        # 1. Thêm mới Module cha vào DB với đầy đủ tham số
                        ctrl.add_sub_content(
                            t_id=p['id'], 
                            sub_title=full_t, 
                            parent_folder=p['folder_name'],
                            url=mod['href'], # Lưu trực tiếp URL vào cột URL luôn
                            metadata={}
                        )
                        count_new += 1
                        
                        # Không cần gọi update_sub_content nữa vì đã truyền URL ngay lúc tạo.
                        # Nếu Vũ vẫn muốn update riêng thì dùng: new_url=mod['href']
                                                                        
                st.success(f"✅ Đã đồng bộ! Thêm mới {count_new} Module.")
                st.rerun()

    # Lọc danh sách các Module duy nhất từ DB để hiển thị Card
    moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
    
    if not moduls:
        st.info("💡 Vũ hãy bấm 'QUÉT MODULES MỚI' để bắt đầu.")
        return

    # Hiển thị Module dưới dạng Card
    cols = st.columns(3)
    for i, mod in enumerate(moduls):
        # Đếm số lượng Form con (không tính bản ghi |Home)
        count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|") and not s['sub_title'].endswith("|Home")])
        
        with cols[i % 3].container(border=True):
            st.markdown(f"#### 📁 {mod}")
            st.caption(f"📄 {count} Forms đã quét")
            if st.button(f"Mở {mod}", key=f"btn_nav_{mod}_{i}", use_container_width=True):
                st.session_state.current_modul = mod
                st.rerun()


def render_gpv_forms(ctrl, p, modul_name, ai_script):
    """Giao diện Cấp 2: Quét sâu từng Form, đồng bộ Metadata vào DB"""
    project_folder = p.get('folder_name', "Giai_Phap_Vang")
    
    c1, c2 = st.columns([3, 1.2])
    c1.subheader(f"📂 Module: {modul_name}")
    
    if c1.button("⬅️ Quay lại", key="back_to_main"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    if c2.button("🔍 CẬP NHẬT FORM (CẤP 2)", type="primary", use_container_width=True, key="btn_deep_scan"):
        with st.spinner(f"Đang mổ xẻ Module {modul_name}..."):
            # 1. Lấy dữ liệu mới nhất từ DB
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            
            # 2. Tìm URL của Module Home (Lấy từ cột 'url' thay vì 'status' cho chuẩn)
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            
            # Ưu tiên lấy link từ cột 'url', nếu cũ quá thì ngó tạm cột 'status'
            target_url = mod_home.get('url') if mod_home and mod_home.get('url') else mod_home.get('status') if mod_home else None
            
            if target_url:
                extractor = GiaiphapvangScraper()
                # Chạy Playwright để vét sạch cấu trúc
                deep_data = extractor.update_module_details(project_folder, modul_name, target_url)
                
                if deep_data:
                    for form_name, f_info in deep_data.items():
                        full_title = f"{modul_name}|{form_name}"
                        metadata_json = f_info.get('structure', {})
                        form_url = f_info.get('url', "")
                        
                        existing_form = next((s for s in db_subs if s['sub_title'] == full_title), None)
                        
                        if existing_form:
                            # CẬP NHẬT: Dùng Named Arguments để chống nhảy cột
                            ctrl.update_sub_content(
                                sub_id=existing_form['id'], 
                                new_url=form_url,
                                new_metadata=metadata_json,
                                new_status="Chưa quay" # Reset status nếu cần
                            )
                        else:
                            # THÊM MỚI: Truyền đủ 5 tham số chính chủ
                            ctrl.add_sub_content(
                                t_id=p['id'],
                                sub_title=full_title,
                                parent_folder=project_folder,
                                url=form_url,
                                metadata=metadata_json
                            )
                    st.success(f"✅ Đã 'vét cạn' tri thức cho {len(deep_data)} Forms!")
                    st.rerun()
                else:
                    st.error("❌ Không tìm thấy dữ liệu chi tiết từ Scraper.")
            else:
                st.error("❌ Không tìm thấy URL của Module gốc để quét sâu.")

    # --- PHẦN HIỂN THỊ DANH SÁCH FORM ---
    current_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    
    display_data = []
    for sub in current_subs:
        # Xử lý Metadata an toàn
        meta = sub.get('metadata')
        if isinstance(meta, str) and meta.strip():
            try: meta = json.loads(meta)
            except: meta = {}
        elif not isinstance(meta, dict):
            meta = {}

        # 1. Trích xuất Fields (Labels)
        fields = [f.get('label') for f in meta.get('form_fields', []) if f.get('label')]
        sub['preview_fields'] = "📝 " + ", ".join(fields[:3]) + ("..." if len(fields) > 3 else "") if fields else "🔍 Chưa có field"
        
        # 2. Trích xuất Actions (Buttons) - Fix lỗi lặp item['label']
        btns = meta.get('actions', [])
        # Lọc các nút quan trọng
        important_keywords = ["Lưu", "Thêm", "Xuất", "In", "Tính"]
        imp = [b for b in btns if any(kw in (b.get('label', '') if isinstance(b, dict) else str(b)) for kw in important_keywords)]
        
        source_list = imp[:3] if imp else btns[:3]
        labels = []
        for item in source_list:
            if isinstance(item, dict): labels.append(str(item.get('label', '')))
            else: labels.append(str(item))
            
        sub['preview_actions'] = "⚡ " + ", ".join(filter(None, labels)) if labels else ""
        display_data.append(sub)
    
    # GỌI COMPONENT HIỂN THỊ
    if display_data:
        gp_component = GPVComponent() 
        # Đảm bảo truyền đủ project_folder để AI/Hệ thống biết đường dẫn lưu file
        gp_component.render_item_rows(ctrl, p, display_data, ai_script, project_folder)
    else:
        st.info("Module này chưa có Form. Vũ hãy nhấn 'CẬP NHẬT FORM (CẤP 2)' ở trên nhé!")