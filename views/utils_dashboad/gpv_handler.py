import streamlit as st
import os
import json
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
from .ai_logic import AIHandler
from ..components.dashboard_component import GPVComponent
from config import Config

# Khởi tạo bộ não AI
ai_handler = AIHandler()

def render_gpv_logic(ctrl, p):
    """Điều hướng chính: Tối ưu chống Loop và Chồng lấn UI"""
    
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    # Lấy dữ liệu từ DB (Chuyển Row thành Dict để dễ xử lý)
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]

    # NHÁNH 1: GIAO DIỆN CHI TIẾT FORM (CẤP 2)
    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        render_gpv_forms(ctrl, p, st.session_state.current_modul)
        return # Chặn đứng để không render trang chủ bên dưới

    # NHÁNH 2: GIAO DIỆN CHỌN MODULE (TRANG CHỦ - CẤP 1)
    st.markdown("### 📦 Hệ thống Module")
    
    with st.expander("⚙️ ĐỒNG BỘ MODULE (CẤP 1)", expanded=False):
        if st.button("🔍 QUÉT MODULES MỚI", use_container_width=True, type="primary", key="btn_scan_c1"):
            with st.spinner("Đang quét danh sách Module..."):
                extractor = GiaiphapvangScraper()
                # Lấy danh sách module từ trang chủ phần mềm
                home_modules = extractor.get_home_modules()
                
                for mod in home_modules:
                    full_t = f"{mod['text']}|Home"
                    # Kiểm tra xem Module này đã có trong DB chưa
                    existing = next((s for s in db_subs if s['sub_title'] == full_t), None)
                    
                    if not existing:
                        # Thêm mới Module cha vào DB
                        ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                        # Lấy ID vừa tạo để cập nhật URL (status)
                        all_new = [dict(x) for x in ctrl.get_sub_contents(p['id'])]
                        target_id = all_new[-1]['id']
                        ctrl.update_sub_content(target_id, new_status=mod['href'])
                st.success("✅ Đã đồng bộ danh sách Module!")
                st.rerun()

    # Lọc danh sách các Module duy nhất từ DB
    moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
    
    if not moduls:
        st.info("💡 Vũ hãy bấm 'QUÉT MODULES MỚI' để bắt đầu.")
        return

    # Hiển thị Module dưới dạng Card
    cols = st.columns(3)
    for i, mod in enumerate(moduls):
        # Đếm số lượng Form con đã quét được (không tính bản ghi |Home)
        count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|") and not s['sub_title'].endswith("|Home")])
        
        with cols[i % 3].container(border=True):
            st.markdown(f"#### 📁 {mod}")
            st.caption(f"📄 {count} Forms đã quét")
            if st.button(f"Mở {mod}", key=f"btn_nav_{mod}_{i}", use_container_width=True):
                st.session_state.current_modul = mod
                st.rerun()

def render_gpv_forms(ctrl, p, modul_name):
    """Giao diện Cấp 2: Quét sâu từng Form, đồng bộ Metadata vào DB"""
    project_folder = p.get('folder_name', "Giai_Phap_Vang")
    
    c1, c2 = st.columns([3, 1.2])
    c1.subheader(f"📂 Module: {modul_name}")
    
    if c1.button("⬅️ Quay lại", key="back_to_main"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    if c2.button("🔍 CẬP NHẬT FORM (CẤP 2)", type="primary", use_container_width=True, key="btn_deep_scan"):
        with st.spinner(f"Đang mổ xẻ Module {modul_name}..."):
            # 1. Tìm URL của Module Home
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            
            if mod_home and mod_home.get('status'):
                extractor = GiaiphapvangScraper()
                # Chạy Playwright để vét sạch cấu trúc các Form bên trong
                deep_data = extractor.update_module_details(project_folder, modul_name, mod_home['status'])
                
                if deep_data:
                    for form_name, f_info in deep_data.items():
                        full_title = f"{modul_name}|{form_name}"
                        metadata_json = f_info.get('structure', {})
                        
                        # Kiểm tra xem Form con đã tồn tại trong DB chưa
                        existing_form = next((s for s in db_subs if s['sub_title'] == full_title), None)
                        
                        if existing_form:
                            # Nếu có rồi -> Cập nhật tri thức mới (Metadata)
                            ctrl.update_sub_content_metadata(existing_form['id'], metadata_json)
                            # Cập nhật thêm URL nếu cần
                            ctrl.update_sub_content(existing_form['id'], new_status=f_info.get('url'))
                        else:
                            # Nếu chưa -> Thêm mới bản ghi kèm Metadata
                            ctrl.add_sub_content(
                                t_id=p['id'],
                                sub_title=full_title,
                                parent_folder=project_folder,
                                metadata=metadata_json
                            )
                    st.success(f"✅ Đã 'vét cạn' tri thức cho {len(deep_data)} Forms!")
                    st.rerun()
                else:
                    st.error("❌ Không tìm thấy dữ liệu chi tiết.")

    # Hiển thị danh sách Form con
    current_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    
    display_data = []
    for sub in current_subs:
        form_name = sub['sub_title'].split('|')[-1]
        
        # Ưu tiên lấy Preview từ Metadata trong DB trước (vì Scraper mới đã lưu vào DB)
        metadata = sub.get('metadata')
        if metadata:
            if isinstance(metadata, str):
                try: metadata = json.loads(metadata)
                except: metadata = {}
            
            # Trích xuất nhanh thông tin để hiển thị Preview trên Dashboard
            fields = [f.get('label') for f in metadata.get('form_fields', []) if f.get('label')]
            sub['preview_fields'] = "📝 " + ", ".join(fields[:3]) + ("..." if len(fields) > 3 else "") if fields else "🔍 Danh sách"
            
            btns = metadata.get('actions', [])
            imp = [b for b in btns if any(w in b for w in ["Lưu", "Thêm", "Xuất", "In"])]
            sub['preview_actions'] = "⚡ " + ", ".join(imp[:3] if imp else btns[:3])
        else:
            sub['preview_fields'] = "Chưa có tri thức"
            sub['preview_actions'] = ""

        display_data.append(sub)
    
    # Gọi Component để vẽ giao diện (Mỗi dòng là 1 Form)
    if display_data:
        # Khởi tạo component hiển thị
        gp_component = GPVComponent() 
        gp_component.render_item_rows(ctrl, p, display_data, ai_handler, project_folder)
    else:
        st.info("Module này chưa có Form. Vũ hãy nhấn 'CẬP NHẬT FORM (CẤP 2)' ở trên nhé!")