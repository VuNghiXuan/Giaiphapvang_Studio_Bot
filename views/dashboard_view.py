import streamlit as st
import os
import json
from config import Config

def get_status_info(sub_path, manual_status=None):
    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    if manual_status in status_list: return manual_status
    raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
    output_dir = os.path.join(sub_path, "outputs")
    has_output = os.path.exists(output_dir) and any(f.endswith('.mp4') for f in os.listdir(output_dir))
    if has_output: return "Hoàn chỉnh"
    if os.path.exists(raw_file): return "Đã quay"
    return "Chưa quay"

def load_home_modules():
    path = r"D:\ThanhVu\AI_code\Giaiphapvang_Studio_Bot\recordings\giaiphapvang_home_selectors.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [item['text'] for item in data if item.get('text') and item.get('type') == 'link']
        except: return []
    return []

def render_dashboard(ctrl):
    # --- 1. ĐỒNG BỘ SESSION STATE ---
    if "selected_project_title" not in st.session_state: st.session_state.selected_project_title = "-- Chọn dự án --"
    if "current_module" not in st.session_state: st.session_state.current_module = "🏠 TẤT CẢ MODULE"

    with st.sidebar:
        if st.session_state.get('view') == "studio":
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"; st.rerun()
        st.markdown("### 🛠️ Hệ thống")
        if st.button("🔄 LÀM MỚI", use_container_width=True): st.rerun()

    st.title("🚀 TỔNG KHO HƯỚNG DẪN")
    
    all_projs_raw = ctrl.get_all_tutorials()
    projects = [dict(p) for p in all_projs_raw]
    project_titles = [p['title'] for p in projects]
    
    col_p, _ = st.columns([3, 1])
    p_idx = project_titles.index(st.session_state.selected_project_title) + 1 if st.session_state.selected_project_title in project_titles else 0
    selected_p_title = col_p.selectbox("📂 CHỌN DỰ ÁN:", ["-- Chọn dự án --"] + project_titles, index=p_idx)
    st.session_state.selected_project_title = selected_p_title

    if selected_p_title == "-- Chọn dự án --":
        st.info("💡 Chọn một dự án để bắt đầu làm việc.")
        return

    p = next(proj for proj in projects if proj['title'] == selected_p_title)
    is_giaiphapvang = "giaiphapvang" in p['title'].lower()

    # --- 2. XỬ LÝ PHÂN HỆ NGHIỆP VỤ ---
    if is_giaiphapvang:
        raw_modules = load_home_modules()
        all_options = ["🏠 TẤT CẢ MODULE"] + raw_modules
        
        # Đồng bộ Index cho Selectbox
        m_idx = all_options.index(st.session_state.current_module) if st.session_state.current_module in all_options else 0
        
        selected_mod = st.selectbox("📱 PHÂN HỆ (APP):", all_options, index=m_idx, key="main_module_select")
        
        # Cập nhật session khi thay đổi selectbox
        if selected_mod != st.session_state.current_module:
            st.session_state.current_module = selected_mod
            st.rerun()

        st.divider()

        if st.session_state.current_module == "🏠 TẤT CẢ MODULE":
            st.subheader("Trang chủ: Các phân hệ chức năng")
            cols = st.columns(3)
            for i, mod in enumerate(raw_modules):
                with cols[i % 3].container(border=True):
                    st.markdown(f"### 📦 {mod}")
                    if st.button("Mở danh mục", key=f"btn_nav_{i}", use_container_width=True):
                        st.session_state.current_module = mod # Cập nhật để lần rerun tới nó vào render_sub_list
                        st.rerun()
        else:
            # Vào đây khi current_module khác "TẤT CẢ"
            render_sub_list(ctrl, p, st.session_state.current_module)
    else:
        st.subheader(f"📁 Dự án: {p['title']}")
        render_sub_list(ctrl, p, None)

def render_sub_list(ctrl, p, module_name):
    # Nút quay lại nhanh cho tiện
    if module_name:
        if st.button("⬅️ Quay lại danh sách Module"):
            st.session_state.current_module = "🏠 TẤT CẢ MODULE"; st.rerun()

    sub_contents_raw = ctrl.get_sub_contents(p['id'])
    sub_contents = [dict(s) for s in sub_contents_raw]
    prefix = f"{module_name}_" if module_name else ""
    display_subs = [s for s in sub_contents if s['sub_title'].startswith(prefix)] if module_name else sub_contents

    with st.expander("➕ Thêm bài học mới"):
        c1, c2 = st.columns([3,1])
        new_name = c1.text_input("Tên bài học:", key=f"in_new_{p['id']}")
        if c2.button("Thêm", use_container_width=True) and new_name:
            ctrl.add_sub_content(p['id'], f"{prefix}{new_name}", p['folder_name']); st.rerun()

    if not display_subs:
        st.warning(f"Chưa có nội dung cho module {module_name}.")
    else:
        status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        bg_colors = {"Chưa quay": "#6c757d", "Đã quay": "#d4af37", "Hoàn chỉnh": "#217346"}
        dots = {"Chưa quay": "🔴", "Đã quay": "🟡", "Hoàn chỉnh": "🟢"}
        
        for idx, s in enumerate(display_subs):
            sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            current_color = bg_colors.get(current_status, "#6c757d")

            with st.container(border=True):
                c_name, c_status, c_man, c_auto, c_opt = st.columns([2.3, 1.4, 1.1, 1.1, 0.5])
                
                clean_name = s['sub_title'].replace(prefix, "")
                # margin-top: 10px để cân bằng với Selectbox
                c_name.markdown(f"<div style='margin-top:10px; font-weight:bold; font-size:15px'>{clean_name}</div>", unsafe_allow_html=True)
                
                with c_status:
                    # Fix lệch dòng triệt để bằng cách kéo Widget lên 8px
                    st.markdown(f"""
                        <style>
                        div[data-testid="stSelectbox"]:has(div[key="status_{s['id']}"]) {{
                            margin-top: -8px !important;
                        }}
                        div[key="status_{s['id']}"] div[data-baseweb="select"] {{
                            background-color: {current_color} !important;
                            color: white !important;
                            height: 38px !important;
                            border-radius: 8px !important;
                            border: none !important;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
                    
                    new_status = st.selectbox(
                        "Status", status_options,
                        index=status_options.index(current_status),
                        key=f"status_{s['id']}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"{dots.get(x, '⚪')} {x}"
                    )
                    
                    if new_status != s.get('status'):
                        ctrl.update_sub_content(s['id'], s['sub_title'], new_status); st.rerun()

                # Nút bấm hành động - Truyền module_name vào session để Auto-Record bắt được
                if c_man.button("🎥 Thủ công", key=f"m_{s['id']}", use_container_width=True):
                    st.session_state.active_project, st.session_state.active_sub = p, s
                    st.session_state.active_module = module_name
                    st.session_state.view, st.session_state.active_tab = "studio", "Quay thủ công"; st.rerun()

                if c_auto.button("🤖 Tự động", key=f"a_{s['id']}", use_container_width=True):
                    st.session_state.active_project, st.session_state.active_sub = p, s
                    st.session_state.active_module = module_name
                    st.session_state.view, st.session_state.active_tab = "studio", "Quay tự động 🤖"; st.rerun()
                
                with c_opt.popover("⚙️"):
                    m1, m2 = st.columns(2)
                    if m1.button("🔼 Lên", key=f"up_{s['id']}", use_container_width=True, disabled=(idx == 0)):
                        ctrl.move_sub_content(s['id'], "up"); st.rerun()
                    if m2.button("🔽 Xuống", key=f"dn_{s['id']}", use_container_width=True, disabled=(idx == len(display_subs)-1)):
                        ctrl.move_sub_content(s['id'], "down"); st.rerun()
                    st.divider()
                    new_sub_t = st.text_input("Đổi tên bài:", value=clean_name, key=f"edit_{s['id']}")
                    if st.button("💾 LƯU", key=f"sav_{s['id']}", use_container_width=True):
                        ctrl.update_sub_content(s['id'], f"{prefix}{new_sub_t}", s.get('status')); st.rerun()
                    if st.button("🗑️ XÓA", key=f"del_{s['id']}", type="primary", use_container_width=True):
                        ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']); st.rerun()