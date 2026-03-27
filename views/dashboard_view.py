import streamlit as st
import os
import json
import asyncio
from config import Config
from core.scrape_giaiphapvang import StructureExtractor

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="GPV AI Studio", layout="wide")

def get_status_info(sub_path, manual_status=None):
    """Kiểm tra trạng thái thực tế của Form dựa trên file vật lý"""
    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    if manual_status in status_list: return manual_status
    
    raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
    output_dir = os.path.join(sub_path, "outputs")
    
    has_output = os.path.exists(output_dir) and any(f.endswith('.mp4') for f in os.listdir(output_dir))
    
    if has_output: return "Hoàn chỉnh"
    if os.path.exists(raw_file): return "Đã quay"
    return "Chưa quay"

def load_knowledge_data():
    """Tải cấu trúc từ file JSON (kết quả Scraper)"""
    path = os.path.abspath(os.path.join(os.getcwd(), "knowledge_source.json"))
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e: 
            print(f"❌ JSON ERROR: {e}")
            return {}
    return {}

def render_dashboard(ctrl):
    # --- 1. KHỞI TẠO SESSION STATE ---
    if "selected_project_title" not in st.session_state: 
        st.session_state.selected_project_title = "-- Chọn dự án --"
    if "current_modul" not in st.session_state: 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    with st.sidebar:
        st.markdown("### 🚀 Studio Control")
        if st.button("🔄 LÀM MỚI", use_container_width=True): 
            st.rerun()
            
        if st.session_state.get('view') == "studio":
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"
                st.rerun()
        
        st.divider()
        st.caption(f"📍 Storage: {Config.BASE_STORAGE}")

    st.title("🚀 QUẢN LÝ VIDEO NGHIỆP VỤ")

    # --- 2. QUẢN LÝ DỰ ÁN (PROJECTS) ---
    all_projs_raw = ctrl.get_all_tutorials()
    if not all_projs_raw:
        ctrl.create_tutorial("Phần mềm Giải Pháp Vàng")
        st.rerun()

    projects = [dict(p) for p in all_projs_raw]
    project_titles = [p['title'] for p in projects]
    
    col_p, col_add = st.columns([3, 1])
    
    try:
        p_idx = project_titles.index(st.session_state.selected_project_title) + 1
    except:
        p_idx = 0

    selected_p_title = col_p.selectbox("📂 CHỌN DỰ ÁN:", ["-- Chọn dự án --"] + project_titles, index=p_idx)

    with col_add.popover("➕ Dự án mới"):
        new_p_name = st.text_input("Tên dự án mới:")
        if st.button("TẠO NGAY", use_container_width=True):
            if new_p_name and ctrl.create_tutorial(new_p_name):
                st.rerun()

    if selected_p_title == "-- Chọn dự án --":
        st.session_state.selected_project_title = "-- Chọn dự án --"
        st.info("💡 Vũ ơi, chọn một dự án để bắt đầu quản lý các Moduls nhé!")
        return

    st.session_state.selected_project_title = selected_p_title
    p = next(proj for proj in projects if proj['title'] == selected_p_title)
    is_gpv = any(kw in p['title'].lower() for kw in ["giải pháp vàng", "giaiphapvang", "gpv"])

    # --- 3. ĐỒNG BỘ CẤU TRÚC (CHO GPV) ---
    if is_gpv:
        with st.expander("⚙️ ĐỒNG BỘ MODULS & FORMS TỪ GIAIPHAPVANG.NET", expanded=True):
            st.info("Bot sẽ quét các Form con nằm trong các Modul từ trang Dashboard.")
            if st.button("🔍 BẮT ĐẦU QUÉT & CẬP NHẬT", type="primary", use_container_width=True):
                with st.spinner("🤖 Bot đang bóc tách cấu trúc..."):
                    try:
                        extractor = StructureExtractor(output_file="knowledge_source.json")
                        asyncio.run(extractor.run())
                        
                        data = load_knowledge_data()
                        current_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
                        added_count = 0
                        
                        for form_name, info in data.items():
                            modul = info.get('module', 'Nghiệp vụ')
                            full_title = f"{modul}|{form_name}"
                            if not any(s['sub_title'] == full_title for s in current_subs):
                                ctrl.add_sub_content(p['id'], full_title, p['folder_name'])
                                added_count += 1
                        
                        st.success(f"✅ Xong! Đã thêm mới {added_count} Forms vào các Moduls.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Scraper: {e}")

    # --- 4. HIỂN THỊ DANH SÁCH MODULS ---
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
    if not moduls: moduls = ["Chưa phân loại"]

    all_options = ["🏠 TẤT CẢ MODULS"] + moduls
    m_idx = all_options.index(st.session_state.current_modul) if st.session_state.current_modul in all_options else 0
    selected_mod = st.selectbox("📱 CHỌN MODUL NGHIỆP VỤ:", all_options, index=m_idx)
    
    if selected_mod != st.session_state.current_modul:
        st.session_state.current_modul = selected_mod
        st.rerun()

    st.divider()

    if st.session_state.current_modul == "🏠 TẤT CẢ MODULS":
        st.subheader("📦 Danh sách Moduls (Nghiệp vụ)")
        cols = st.columns(3)
        for i, mod in enumerate(moduls):
            count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|")])
            with cols[i % 3].container(border=True):
                st.markdown(f"### 📦 {mod}")
                st.write(f"📄 {count} Forms con")
                if st.button(f"Mở {mod}", key=f"btn_mod_{i}", use_container_width=True):
                    st.session_state.current_modul = mod
                    st.rerun()
    else:
        render_forms_list(ctrl, p, st.session_state.current_modul)

def render_forms_list(ctrl, p, modul_name):
    """Hiển thị các Forms con trong một Modul"""
    st.subheader(f"📂 Modul: {modul_name}")
    if st.button("⬅️ Quay lại danh sách Moduls"):
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()

    sub_contents = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    display_subs = [s for s in sub_contents if s['sub_title'].startswith(f"{modul_name}|")]

    with st.expander("➕ Thêm Form mới thủ công"):
        c1, c2 = st.columns([3,1])
        new_name = c1.text_input("Tên Form con:")
        if c2.button("Xác nhận", use_container_width=True) and new_name:
            full_name = f"{modul_name}|{new_name}"
            if ctrl.add_sub_content(p['id'], full_name, p['folder_name']):
                st.rerun()

    if not display_subs:
        st.info("Modul này chưa có Form nào.")
    else:
        status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        dots = {"Chưa quay": "🔴", "Đã quay": "🟡", "Hoàn chỉnh": "🟢"}
        
        for s in display_subs:
            sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            form_name = s['sub_title'].split('|')[-1] # Lấy tên form con

            with st.container(border=True):
                c_name, c_status, c_man, c_auto, c_opt = st.columns([2.5, 1.2, 1, 1, 0.5])
                c_name.markdown(f"**{form_name}**")
                
                with c_status:
                    new_status = st.selectbox(
                        "Trạng thái", status_options,
                        index=status_options.index(current_status) if current_status in status_options else 0,
                        key=f"st_{s['id']}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"{dots.get(x, '⚪')} {x}"
                    )
                    if new_status != s.get('status'):
                        ctrl.update_sub_content(s['id'], s['sub_title'], new_status)
                        st.rerun()

                if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                    st.session_state.active_project = p
                    st.session_state.active_sub = s
                    st.session_state.view = "studio"
                    st.session_state.active_tab = "Quay thủ công"
                    st.rerun()

                if c_auto.button("🤖", key=f"a_{s['id']}", help="Quay tự động"):
                    st.session_state.active_project = p
                    st.session_state.active_sub = s
                    st.session_state.view = "studio"
                    st.session_state.active_tab = "Quay tự động 🤖"
                    st.rerun()
                
                with c_opt.popover("⚙️"):
                    if st.button("🗑️ XÓA FORM", key=f"del_{s['id']}", type="primary", use_container_width=True):
                        if ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']):
                            st.rerun()