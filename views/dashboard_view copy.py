import streamlit as st
import os
import json
from config import Config

def get_status_info(sub_path, manual_status=None):
    """Kiểm tra trạng thái bài học dựa trên DB hoặc file vật lý"""
    status_map = {
        "Chưa quay": ("🔴 Chưa quay", "#6c757d"),
        "Đã quay": ("🟡 Đã quay", "#d4af37"),
        "Hoàn chỉnh": ("🟢 Hoàn chỉnh", "#217346")
    }
    if manual_status in status_map:
        return status_map[manual_status]

    raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
    output_dir = os.path.join(sub_path, "outputs")
    has_output = os.path.exists(output_dir) and any(f.endswith('.mp4') for f in os.listdir(output_dir))
    has_raw = os.path.exists(raw_file)

    if has_output: return status_map["Hoàn chỉnh"]
    if has_raw: return status_map["Đã quay"]
    return status_map["Chưa quay"]

def render_dashboard(ctrl):
    # --- SIDEBAR: GIỮ NGUYÊN CỦA VŨ ---
    with st.sidebar:
        if st.session_state.get('view') == "studio":
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"
                st.session_state.active_project = None
                st.session_state.active_sub = None
                st.rerun()
            st.divider()

        st.markdown("### 🛠️ Hệ thống")
        if st.button("🔄 LÀM MỚI DANH MỤC", use_container_width=True):
            st.rerun()

    # --- NỘI DUNG CHÍNH ---
    st.title("🚀 TỔNG KHO HƯỚNG DẪN")
    
    # 1. COMBOBOX CHỌN DỰ ÁN (MỚI THÊM)
    projects = ctrl.get_all_tutorials()
    project_titles = ["➕ TẠO DỰ ÁN MỚI"] + [p['title'] for p in projects]
    
    selected_proj_name = st.selectbox("📂 CHỌN DỰ ÁN ĐỂ LÀM VIỆC:", project_titles, index=0)

    # A. TRƯỜNG HỢP: TẠO DỰ ÁN MỚI
    if selected_proj_name == "➕ TẠO DỰ ÁN MỚI":
        with st.container(border=True):
            st.subheader("Tạo dự án quản lý thủ công")
            c1, c2 = st.columns([3, 1])
            n = c1.text_input("Tên dự án:", placeholder="Nhập tên dự án...", key="new_proj_name")
            if c2.button("Tạo ngay", use_container_width=True, type="primary"):
                if n: 
                    ctrl.create_tutorial(n)
                    st.rerun()

    # B. TRƯỜNG HỢP: CHỌN DỰ ÁN "giaiphapvang" (TỰ ĐỘNG MAP TỪ JSON)
    elif "giaiphapvang" in selected_proj_name.lower():
        st.info(f"⚡ Đang hiển thị danh mục tự động cho dự án: {selected_proj_name}")
        json_path = "knowledge_source.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                auto_data = json.load(f)
            
            for page_name, info in auto_data.items():
                with st.container(border=True):
                    c_name, c_btn = st.columns([4, 1])
                    c_name.markdown(f"**🖥️ {page_name}** \n<small>{info['url']}</small>", unsafe_allow_html=True)
                    if c_btn.button("🤖 QUAY AUTO", key=f"auto_gpv_{page_name}", use_container_width=True):
                        st.session_state.active_project = {"title": selected_proj_name, "folder_name": "giaiphapvang"}
                        st.session_state.active_sub = {"sub_title": page_name, "sub_folder": page_name.replace(" ", "_"), "page_info": info}
                        st.session_state.view = "studio"
                        st.session_state.active_tab = "Quay tự động 🤖"
                        st.rerun()
        else:
            st.warning("Không tìm thấy file knowledge_source.json để đổ dữ liệu tự động.")

    # C. TRƯỜNG HỢP: DỰ ÁN BÌNH THƯỜNG (GIAO DIỆN CŨ CỦA VŨ)
    else:
        # Lấy object dự án hiện tại
        p = next(proj for proj in projects if proj['title'] == selected_proj_name)
        p_idx = projects.index(p)
        total_projects = len(projects)

        with st.container(border=True):
            col_p_title, col_p_opt = st.columns([4.2, 0.8])
            col_p_title.markdown(f"### 📁 {p['title']}")
            
            with col_p_opt.popover("⚙️", use_container_width=True):
                st.subheader("Quản lý Dự án")
                m_p1, m_p2 = st.columns(2)
                if m_p1.button("🔼 Lên", key=f"up_p_{p['id']}", disabled=(p_idx == 0)):
                    ctrl.move_tutorial(p['id'], "up"); st.rerun()
                if m_p2.button("🔽 Xuống", key=f"down_p_{p['id']}", disabled=(p_idx == total_projects - 1)):
                    ctrl.move_tutorial(p['id'], "down"); st.rerun()

                st.divider()
                new_p_title = st.text_input("Đổi tên dự án:", value=p['title'], key=f"edit_p_t_{p['id']}")
                if st.button("💾 LƯU TÊN MỚI", key=f"btn_p_upd_{p['id']}", use_container_width=True):
                    ctrl.update_tutorial_title(p['id'], new_p_title); st.rerun()

                st.divider()
                sub_n = st.text_input("Tên hướng dẫn mới:", key=f"add_in_{p['id']}")
                if st.button("➕ Thêm hướng dẫn", key=f"btn_add_{p['id']}", use_container_width=True):
                    if sub_n: 
                        ctrl.add_sub_content(p['id'], sub_n, p['folder_name']); st.rerun()

                st.divider()
                if st.button("🗑️ XÓA DỰ ÁN", key=f"del_p_{p['id']}", type="primary", use_container_width=True):
                    ctrl.delete_tutorial(p['id'], p['folder_name']); st.rerun()

            # --- HIỂN THỊ CÁC BÀI HỌC (VIEW CŨ CỦA VŨ) ---
            sub_contents = ctrl.get_sub_contents(p['id'])
            total_subs = len(sub_contents)
            
            for idx, s_row in enumerate(sub_contents):
                s = dict(s_row) 
                sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
                label, color = get_status_info(sub_path, s.get('status'))
                
                st.markdown("---")
                # Vũ muốn tích hợp cả 2 nút nên tao chia thêm cột
                c_icon, c_name, c_status, c_man, c_auto, c_opt = st.columns([0.2, 2.5, 0.9, 1.1, 1.1, 0.5])
                
                c_icon.markdown("<div style='margin-top:5px'>└─ 📹</div>", unsafe_allow_html=True)
                c_name.markdown(f"<div style='margin-top:5px'><b>{s['sub_title']}</b></div>", unsafe_allow_html=True)
                c_status.markdown(f"""<div style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; text-align: center; width: 95px; margin-top:8px;">{label}</div>""", unsafe_allow_html=True)
                
                # Nút Thủ công (Vào Studio tab thủ công)
                if c_man.button("🎥 THỦ CÔNG", key=f"man_{s['id']}", use_container_width=True):
                    st.session_state.active_project = p
                    st.session_state.active_sub = s
                    st.session_state.view = "studio"
                    st.session_state.active_tab = "Quay thủ công"
                    st.rerun()

                # Nút Tự động (Vào Studio tab robot)
                if c_auto.button("🤖 TỰ ĐỘNG", key=f"auto_{s['id']}", use_container_width=True):
                    st.session_state.active_project = p
                    st.session_state.active_sub = s
                    st.session_state.view = "studio"
                    st.session_state.active_tab = "Quay tự động 🤖"
                    st.rerun()
                
                with c_opt.popover("⚙️", use_container_width=True):
                    st.subheader("Cài đặt bài")
                    m1, m2 = st.columns(2)
                    if m1.button("🔼", key=f"up_{s['id']}", disabled=(idx == 0)):
                        ctrl.move_sub_content(s['id'], "up"); st.rerun()
                    if m2.button("🔽", key=f"down_{s['id']}", disabled=(idx == total_subs - 1)):
                        ctrl.move_sub_content(s['id'], "down"); st.rerun()
                    
                    st.divider()
                    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
                    new_st = st.selectbox("Trạng thái:", status_list, index=status_list.index(s.get('status', "Chưa quay")), key=f"sel_st_{s['id']}")
                    new_sub_name = st.text_input("Tên bài:", value=s['sub_title'], key=f"txt_{s['id']}")
                    
                    if st.button("💾 LƯU", key=f"upd_{s['id']}", use_container_width=True):
                        ctrl.update_sub_content(s['id'], new_sub_name, new_st); st.rerun()
                    
                    if st.button("🗑️ XÓA BÀI", key=f"del_s_{s['id']}", type="primary", use_container_width=True):
                        ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']); st.rerun()