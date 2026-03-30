import streamlit as st
import os
import json
from config import Config
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper

# --- IMPORT CÁC HÀM TỪ FILE NGOÀI (NẾU ÔNG ĐÃ TÁCH FILE) ---
# Nếu ông để file cùng thư mục, dùng lệnh này:
# from .utils_dashboard.gpv_handler import render_gpv_logic, render_gpv_forms 
# from utils import get_status_info
from .utils_dashboad.gpv_render_form import render_gpv_logic, render_gpv_forms 

# --- TRƯỜNG HỢP ÔNG MUỐN GOM TẤT CẢ VÀO 1 FILE DASHBOARD.PY ---

def get_status_info(sub_path, manual_status=None):
    """Kiểm tra trạng thái video dựa trên file thực tế"""
    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    if manual_status in status_list: return manual_status
    raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
    output_dir = os.path.join(sub_path, "outputs")
    has_output = os.path.exists(output_dir) and any(f.endswith('.mp4') for f in os.listdir(output_dir))
    if has_output: return "Hoàn chỉnh"
    if os.path.exists(raw_file): return "Đã quay"
    return "Chưa quay"

def render_dashboard(ctrl):
    if "selected_project_title" not in st.session_state: 
        st.session_state.selected_project_title = "-- Chọn dự án --"
    if "current_modul" not in st.session_state: 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    with st.sidebar:
        st.markdown("### 🚀 Studio Control")
        if st.button("🔄 LÀM MỚI", use_container_width=True): st.rerun()
        if st.session_state.get('view') == "studio":
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"; st.rerun()
        st.divider()
        st.caption(f"📍 Storage: {Config.BASE_STORAGE}")

    st.title("🚀 QUẢN LÝ VIDEO NGHIỆP VỤ")

    # --- 1. LẤY DỮ LIỆU DỰ ÁN ---
    all_projs_raw = ctrl.get_all_tutorials()
    projects = [dict(p) for p in all_projs_raw]
    project_titles = [p['title'] for p in projects]
    
    # MẸO: Tự động tạo dự án GPV nếu chưa có để nó hiện ra
    if not any(kw in str(project_titles).lower() for kw in ["giải pháp vàng", "gpv"]):
        with st.warning("Chưa có dự án Giải Pháp Vàng!"):
            if st.button("Tạo dự án GPV mẫu"):
                ctrl.create_tutorial("Phần mềm Giải Pháp Vàng")
                st.rerun()

    col_p, col_add = st.columns([3, 1])
    try:
        p_idx = project_titles.index(st.session_state.selected_project_title) + 1
    except:
        p_idx = 0

    selected_p_title = col_p.selectbox("📂 CHỌN DỰ ÁN:", ["-- Chọn dự án --"] + project_titles, index=p_idx)

    # Nút thêm dự án mới
    with col_add.popover("➕ Dự án mới"):
        new_p_name = st.text_input("Tên dự án mới:")
        if st.button("TẠO NGAY", use_container_width=True):
            if new_p_name and ctrl.create_tutorial(new_p_name): st.rerun()

    if selected_p_title == "-- Chọn dự án --":
        st.session_state.selected_project_title = "-- Chọn dự án --"
        st.info("💡 Vũ ơi, chọn một dự án để bắt đầu nhé!")
        return

    st.session_state.selected_project_title = selected_p_title
    p = next(proj for proj in projects if proj['title'] == selected_p_title)
    
    # Kiểm tra xem đây có phải dự án GPV không
    is_gpv = any(kw in p['title'].lower() for kw in ["giải pháp vàng", "giaiphapvang", "gpv"])

    # --- 2. HEADER DỰ ÁN (Sửa/Xóa/Di chuyển) ---
    with st.container(border=True):
        c_tit, c_move, c_edit = st.columns([3, 1, 1])
        c_tit.subheader(f"📁 {p['title']}")
        with c_move.popover("↕️ Di chuyển"):
            curr_idx = project_titles.index(p['title'])
            m1, m2 = st.columns(2)
            if m1.button("🔼 Lên", disabled=(curr_idx == 0)): ctrl.move_tutorial(p['id'], "up"); st.rerun()
            if m2.button("🔽 Xuống", disabled=(curr_idx == len(projects)-1)): ctrl.move_tutorial(p['id'], "down"); st.rerun()
        with c_edit.popover("⚙️ Cài đặt"):
            new_title = st.text_input("Đổi tên:", value=p['title'])
            if st.button("LƯU TÊN"): ctrl.update_tutorial_title(p['id'], new_title); st.rerun()
            if st.button("🗑️ XÓA DỰ ÁN", type="primary"): ctrl.delete_tutorial(p['id'], p['folder_name']); st.rerun()

    # --- 3. PHÂN LUỒNG LOGIC ---
    if is_gpv:
        render_gpv_logic(ctrl, p)
    else:
        render_normal_logic(ctrl, p)

# --- CÁC HÀM LOGIC (NẾU KHÔNG IMPORT THÌ PHẢI KHAI BÁO Ở ĐÂY) ---

def render_gpv_logic(ctrl, p):
    """Logic riêng cho Giải Pháp Vàng"""
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    
    if st.session_state.current_modul == "🏠 TẤT CẢ MODULS":
        with st.expander("⚙️ ĐỒNG BỘ MODULE (CẤP 1)", expanded=True):
            if st.button("🔍 QUÉT MODULES MỚI", use_container_width=True, type="primary"):
                with st.spinner("Đang quét CMS..."):
                    extractor = GiaiphapvangScraper()
                    for mod in extractor.get_home_modules():
                        full_t = f"{mod['text']}|Home"
                        if not any(s['sub_title'] == full_t for s in db_subs):
                            ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                            last = [dict(s) for s in ctrl.get_sub_contents(p['id'])][-1]
                            ctrl.update_sub_content(last['id'], full_t, mod['href'])
                    st.rerun()

        moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
        if not moduls: st.info("Chưa có module nào. Hãy bấm Quét ở trên.")
        
        cols = st.columns(3)
        for i, mod in enumerate(moduls):
            count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|")]) - 1
            with cols[i % 3].container(border=True):
                st.markdown(f"### 📦 {mod}")
                st.write(f"📄 {max(0, count)} Forms")
                if st.button(f"Mở {mod}", key=f"btn_{mod}", use_container_width=True):
                    st.session_state.current_modul = mod; st.rerun()
    else:
        render_gpv_forms(ctrl, p, st.session_state.current_modul)

def render_gpv_forms(ctrl, p, modul_name):
    """Chi tiết các Form trong Module GPV"""
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"📂 Module: {modul_name}")
    if c1.button("⬅️ Quay lại danh sách Module"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"; st.rerun()
    
    if c2.button("🔍 CẬP NHẬT FORM (CẤP 2)", type="primary", use_container_width=True):
        with st.spinner("Đang quét chi tiết..."):
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            if mod_home:
                extractor = GiaiphapvangScraper()
                results = extractor.get_module_details(modul_name, mod_home['status'])
                for f_name in results.keys():
                    full_t = f"{modul_name}|{f_name}"
                    if not any(s['sub_title'] == full_t for s in db_subs):
                        ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                st.rerun()

    display_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    render_item_rows(ctrl, p, display_subs)

def render_normal_logic(ctrl, p):
    """Giao diện phẳng cho dự án thường"""
    with st.container(border=True):
        sub_n = st.text_input("Tên bài học mới:")
        if st.button("➕ Thêm bài"):
            if sub_n: ctrl.add_sub_content(p['id'], sub_n, p['folder_name']); st.rerun()
    
    display_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    render_item_rows(ctrl, p, display_subs)

def render_item_rows(ctrl, p, items):
    """Render từng dòng bài học/form"""
    status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    dots = {"Chưa quay": "🔴", "Đã quay": "🟡", "Hoàn chỉnh": "🟢"}
    
    for idx, s in enumerate(items):
        sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
        current_status = get_status_info(sub_path, s.get('status'))
        clean_name = s['sub_title'].split('|')[-1]

        with st.container(border=True):
            c_name, c_status, c_man, c_auto, c_opt = st.columns([2.5, 1.2, 0.8, 0.8, 0.5])
            c_name.markdown(f"**{clean_name}**")
            
            with c_status:
                new_st = st.selectbox("ST", status_options, label_visibility="collapsed",
                                      index=status_options.index(current_status) if current_status in status_options else 0,
                                      key=f"st_{s['id']}")
                if new_st != s.get('status'):
                    ctrl.update_sub_content(s['id'], s['sub_title'], new_st); st.rerun()

            if c_man.button("🎥", key=f"m_{s['id']}"):
                st.session_state.active_project, st.session_state.active_sub = p, s
                st.session_state.view, st.session_state.active_tab = "studio", "Quay thủ công"; st.rerun()

            if c_auto.button("🤖", key=f"a_{s['id']}"):
                st.session_state.active_project, st.session_state.active_sub = p, s
                st.session_state.view, st.session_state.active_tab = "studio", "Quay tự động 🤖"; st.rerun()
            
            with c_opt.popover("⚙️"):
                if st.button("🔼", key=f"up_{s['id']}", disabled=(idx==0)):
                    ctrl.move_sub_content(s['id'], "up"); st.rerun()
                if st.button("🔽", key=f"dn_{s['id']}", disabled=(idx==len(items)-1)):
                    ctrl.move_sub_content(s['id'], "down"); st.rerun()
                if st.button("🗑️ XÓA", key=f"del_{s['id']}", type="primary"):
                    ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']); st.rerun()