import streamlit as st
import os
from config import Config
# Import logic điều hướng từ gpv_handler
# from .utils_dashboad.gpv_render_form import render_gpv_logic, render_gpv_forms, ai_script
from Bot_GPV.views.components.gpv_render_modules_and_form import ai_script, render_gpv_logic, render_gpv_forms
# Import class giao diện từ components
# from .components.gpv_component import GPVComponent
from Bot_GPV.views.components.gpv_render_forms_detail import RenderForm

# --- 1. HÀM RENDER CHO DỰ ÁN THƯỜNG ---
def render_normal_logic(ctrl, p, ai_script): # Vũ nhớ check xem đã nhận ai_script ở đầu hàm chưa nhé
    """Giao diện danh sách phẳng cho các dự án không phải GPV"""
    with st.container(border=True):
        st.subheader("📝 Quản lý bài học")
        col_in, col_btn = st.columns([3, 1])
        
        # Key độc nhất dựa trên ID dự án để tránh xung đột widget
        sub_n = col_in.text_input("Tên bài học mới:", placeholder="Nhập tên bài học...", key=f"input_add_{p['id']}")
        
        if col_btn.button("➕ THÊM BÀI", use_container_width=True, type="primary"):
            if sub_n: 
                # SỬA LỖI TẠI ĐÂY: Truyền tên tham số rõ ràng để không bao giờ bị lệch cột
                ctrl.add_sub_content(
                    t_id=p['id'], 
                    sub_title=sub_n, 
                    parent_folder=p['folder_name'],
                    url="",         # Ép kiểu rỗng để tránh nhảy cột Status
                    metadata={}      # Khởi tạo meta rỗng cho bài mới
                )
                st.success(f"Đã thêm: {sub_n}")
                st.rerun()
            else:
                st.error("Vũ ơi, nhập tên bài đã chứ!")

    st.divider()
    
    # Lấy danh sách bài học từ DB
    display_subs = ctrl.get_sub_contents(p['id'])
    
    if not display_subs:
        st.info("Dự án này chưa có bài học nào. Hãy thêm ở trên 👆")
    else:
        # GỌI TỪ CLASS COMPONENT: Vẽ từng dòng video (🎥, 🤖, ⚙️)
        # Đảm bảo ai_script đã được truyền vào hàm render_normal_logic
        RenderForm.render_item_rows(ctrl, p, display_subs, ai_script)

# --- 2. HÀM CHÍNH ĐIỀU HƯỚNG DASHBOARD ---
def render_dashboard(ctrl):
    # Khởi tạo session state nếu chưa có
    if "selected_project_title" not in st.session_state: 
        st.session_state.selected_project_title = "-- Chọn dự án --"
    if "current_modul" not in st.session_state: 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("### 🚀 Studio Control")
        if st.button("🔄 LÀM MỚI", use_container_width=True): 
            st.rerun()
        st.divider()
        st.caption(f"📍 Storage: {Config.BASE_STORAGE}")

    st.title("🚀 QUẢN LÝ VIDEO NGHIỆP VỤ")

    # --- 1. CHUẨN BỊ DANH SÁCH DỰ ÁN ---
    db_projects = [dict(p) for p in ctrl.get_all_tutorials()]
    db_titles = [p['title'] for p in db_projects]
    
    GPV_NAME = "Giải Pháp Vàng"
    NEW_PROJ_PLACEHOLDER = "➕ Khởi tạo dự án mới..."
    
    # Xây dựng danh sách options cho selectbox
    display_options = ["-- Chọn dự án --"] + db_titles
    
    # Thêm option "mồi" cho Giải Pháp Vàng nếu trong DB chưa có
    if GPV_NAME not in db_titles:
        display_options.append(GPV_NAME)
    
    # Luôn thêm option tạo dự án mới
    display_options.append(NEW_PROJ_PLACEHOLDER)

    # --- FIX LỖI RESET ID CHỌN DỰ ÁN ---
    try:
        current_index = display_options.index(st.session_state.selected_project_title)
    except (ValueError, KeyError):
        current_index = 0

    selected_p_title = st.selectbox(
        "📂 CHỌN DỰ ÁN:", 
        options=display_options, 
        index=current_index
    )

    st.session_state.selected_project_title = selected_p_title

    if selected_p_title == "-- Chọn dự án --":
        st.info("💡 Vũ ơi, chọn dự án có sẵn hoặc tạo mới để bắt đầu nhé!")
        return

    # --- 2. XỬ LÝ LOGIC THEO LỰA CHỌN ---

    if selected_p_title == NEW_PROJ_PLACEHOLDER:
        with st.container(border=True):
            st.subheader("🆕 Thiết lập dự án mới")
            new_name = st.text_input("Nhập tên dự án Vũ muốn đặt:", placeholder="Ví dụ: Dự án Xây Dựng, Video TikTok...")
            
            if st.button("💾 LƯU VÀO DATABASE", type="primary", use_container_width=True):
                if new_name:
                    if new_name in db_titles:
                        st.error("Tên này có rồi Vũ ơi, đặt tên khác đi!")
                    else:
                        if ctrl.create_tutorial(new_name):
                            st.success(f"✅ Đã lưu dự án '{new_name}' thành công!")
                            st.session_state.selected_project_title = new_name
                            st.rerun()
                else:
                    st.warning("Vũ chưa nhập tên dự án kìa!")
        return

    p = next((proj for proj in db_projects if proj['title'] == selected_p_title), None)

    if selected_p_title == GPV_NAME and p is None:
        st.warning(f"⚠️ Dự án '{GPV_NAME}' chưa được khởi tạo trong Database.")
        if st.button(f"🚀 KÍCH HOẠT DỰ ÁN {GPV_NAME.upper()}", type="primary", use_container_width=True):
            if ctrl.create_tutorial(GPV_NAME):
                st.success("Khởi tạo Giải Pháp Vàng thành công!")
                st.session_state.selected_project_title = GPV_NAME
                st.rerun()
        return


    if p:
        # Kiểm tra nếu là dự án Giải Pháp Vàng
        is_gpv = any(kw in p['title'].lower() for kw in ["giải pháp vàng", "giaiphapvang", "gpv"])
        
        if is_gpv:
            # Đảm bảo truyền ai_script vào để đồng bộ logic AI bên trong GPV
            render_gpv_logic(ctrl, p, ai_script) 
        else:
            # Dự án thường cũng cần ai_script cho các tính năng bổ trợ trong GPVComponent
            render_normal_logic(ctrl, p, ai_script)
    else:
        st.error("Dữ liệu dự án có vấn đề. Hãy bấm 'Làm mới' ở Sidebar.")
            
    