import streamlit as st
import os
import json
from config import Config

def get_status_info(sub_path, manual_status=None):
    """Giữ nguyên logic cũ để lấy màu và label mặc định"""
    status_map = {
        "Chưa quay": ("🔴 Chưa quay", "#6c757d"),
        "Đã quay": ("🟡 Đã quay", "#d4af37"),
        "Hoàn chỉnh": ("🟢 Hoàn chỉnh", "#217346")
    }
    # Trả về info dựa trên status trong DB hoặc check file
    if manual_status in status_map: return status_map[manual_status]
    
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
    # --- SIDEBAR ---
    with st.sidebar:
        if st.session_state.get('view') == "studio":
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"; st.rerun()
        st.markdown("### 🛠️ Hệ thống")
        if st.button("🔄 LÀM MỚI", use_container_width=True): st.rerun()

    st.title("🚀 TỔNG KHO HƯỚNG DẪN")
    
    # --- 1. CHỌN DỰ ÁN ---
    all_projs_raw = ctrl.get_all_tutorials()
    projects = [dict(p) for p in all_projs_raw]
    project_titles = [p['title'] for p in projects]
    
    col_p, col_p_new = st.columns([3, 1])
    selected_p_title = col_p.selectbox("📂 CHỌN DỰ ÁN:", ["-- Chọn dự án --"] + project_titles)

    with col_p_new.popover("➕ Dự án mới", use_container_width=True):
        n = st.text_input("Tên dự án mới:")
        if st.button("Tạo ngay", use_container_width=True) and n:
            if n in project_titles: st.error("Tên đã tồn tại!")
            else:
                try:
                    ctrl.create_tutorial(n); st.success("Đã tạo!"); st.rerun()
                except Exception as e: st.error(f"Lỗi: {e}")

    if selected_p_title == "-- Chọn dự án --":
        st.info("💡 Chọn một dự án để bắt đầu làm việc.")
        return

    p = next(proj for proj in projects if proj['title'] == selected_p_title)
    is_giaiphapvang = "giaiphapvang" in p['title'].lower()

    # --- 2. LOGIC HIỂN THỊ ---
    if is_giaiphapvang:
        modules = load_home_modules()
        if "current_module" not in st.session_state:
            st.session_state.current_module = "🏠 TẤT CẢ MODULE"
            
        selected_mod = st.selectbox(
            "📱 PHÂN HỆ (APP):", 
            ["🏠 TẤT CẢ MODULE"] + modules,
            index=0 if st.session_state.current_module not in modules else modules.index(st.session_state.current_module) + 1
        )
        st.session_state.current_module = selected_mod
        st.divider()

        if selected_mod == "🏠 TẤT CẢ MODULE":
            st.subheader("Trang chủ: Các phân hệ chức năng")
            cols = st.columns(3)
            for i, mod in enumerate(modules):
                with cols[i % 3].container(border=True):
                    st.markdown(f"### 📦 {mod}")
                    if st.button("Mở danh mục", key=f"btn_nav_{i}", use_container_width=True):
                        st.session_state.current_module = mod; st.rerun()
        else:
            render_sub_list(ctrl, p, selected_mod)
    else:
        st.subheader(f"📁 Dự án: {p['title']}")
        render_sub_list(ctrl, p, None)

def render_sub_list(ctrl, p, module_name):
    sub_contents_raw = ctrl.get_sub_contents(p['id'])
    sub_contents = [dict(s) for s in sub_contents_raw]
    
    if module_name:
        display_subs = [s for s in sub_contents if s['sub_title'].startswith(f"{module_name}_")]
        prefix = f"{module_name}_"
    else:
        display_subs = sub_contents
        prefix = ""

    # Expander thêm bài mới giữ nguyên...
    with st.expander("➕ Thêm bài học mới"):
        c1, c2 = st.columns([3,1])
        new_name = c1.text_input("Tên bài học:", key=f"in_new_{p['id']}")
        if c2.button("Thêm", use_container_width=True) and new_name:
            ctrl.add_sub_content(p['id'], f"{prefix}{new_name}", p['folder_name']); st.rerun()

    if not display_subs:
        st.warning("Chưa có nội dung.")
    else:
        # Danh sách các option cho combo
        status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        
        for idx, s in enumerate(display_subs):
            sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
            
            # Lấy trạng thái hiện tại (string)
            current_status = get_status_info(sub_path, s.get('status'))
            
            # Màu sắc tương ứng để làm background cho selectbox
            bg_colors = {"Chưa quay": "#6c757d", "Đã quay": "#d4af37", "Hoàn chỉnh": "#217346"}
            current_color = bg_colors.get(current_status, "#6c757d")

            with st.container(border=True):
                c_name, c_status, c_man, c_auto, c_opt = st.columns([2.5, 1.2, 1.1, 1.1, 0.5])
                
                clean_name = s['sub_title'].replace(prefix, "")
                c_name.markdown(f"<div style='margin-top:8px'><b>{clean_name}</b></div>", unsafe_allow_html=True)
                
                # --- COMBO CHỌN TRẠNG THÁI ---
                with c_status:
                    # Dùng CSS để biến Selectbox thành nút có màu
                    st.markdown(f"""
                        <style>
                        div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
                            background-color: {current_color} !important;
                            color: white !important;
                            border-radius: 8px !important;
                        }}
                        div[data-testid="stSelectbox"] svg {{
                            fill: white !important;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
                    
                    new_status = st.selectbox(
                        "Status",
                        status_options,
                        index=status_options.index(current_status),
                        key=f"status_{s['id']}",
                        label_visibility="collapsed"
                    )
                    
                    # Nếu người dùng đổi trên Combo -> Cập nhật DB luôn
                    if new_status != s.get('status'):
                        ctrl.update_sub_content(s['id'], s['sub_title'], new_status)
                        st.rerun()

                # --- NÚT HÀNH ĐỘNG ---
                if c_man.button("🎥 Thủ công", key=f"m_{s['id']}", use_container_width=True):
                    st.session_state.active_project, st.session_state.active_sub = p, s
                    st.session_state.view, st.session_state.active_tab = "studio", "Quay thủ công"; st.rerun()

                if c_auto.button("🤖 Tự động", key=f"a_{s['id']}", use_container_width=True):
                    st.session_state.active_project, st.session_state.active_sub = p, s
                    st.session_state.view, st.session_state.active_tab = "studio", "Quay tự động 🤖"; st.rerun()
                
                with c_opt.popover("⚙️"):
                    # Phần quản lý (Di chuyển, Đổi tên, Xóa) giữ nguyên như code trước...
                    st.subheader("Cài đặt bài")
                    m1, m2 = st.columns(2)
                    if m1.button("🔼 Lên", key=f"up_{s['id']}", use_container_width=True, disabled=(idx == 0)):
                        ctrl.move_sub_content(s['id'], "up"); st.rerun()
                    if m2.button("🔽 Xuống", key=f"dn_{s['id']}", use_container_width=True, disabled=(idx == len(display_subs)-1)):
                        ctrl.move_sub_content(s['id'], "down"); st.rerun()
                    st.divider()
                    new_sub_t = st.text_input("Đổi tên bài:", value=clean_name, key=f"edit_{s['id']}")
                    if st.button("💾 LƯU TÊN", key=f"sav_{s['id']}", use_container_width=True):
                        ctrl.update_sub_content(s['id'], f"{prefix}{new_sub_t}", s.get('status')); st.rerun()
                    if st.button("🗑️ XÓA BÀI", key=f"del_{s['id']}", type="primary", use_container_width=True):
                        ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']); st.rerun()