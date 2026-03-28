import streamlit as st
import os
from config import Config
from ..utils_dashboad.utils import get_status_info

def render_item_rows(ctrl, p, items):
    """Hàm chính để render danh sách các Form"""
    status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    
    for idx, s in enumerate(items):
        sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
        current_status = get_status_info(sub_path, s.get('status'))
        
        # Tách tên Module và Form từ "Module|Form"
        parts = s['sub_title'].split('|')
        mod_name = parts[0]
        form_name = parts[-1]

        with st.container(border=True):
            col_info, col_status, col_actions = st.columns([3, 1.5, 2])
            
            # --- Cột Thông Tin ---
            col_info.markdown(f"**{form_name}**")
            col_info.caption(f"📁 {s['sub_folder']}")
            
            # --- Cột Trạng Thái ---
            with col_status:
                render_status_selector(ctrl, s, current_status, status_options)

            # --- Cột Thao Tác (Quay & Cấu hình) ---
            with col_actions:
                c_man, c_auto, c_opt = st.columns([1, 1, 1])
                
                # Quay thủ công
                if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                    navigate_to_studio(p, s, "Quay thủ công")

                # Quay tự động (Mở Popover để cấu hình AI trước khi quay)
                with c_auto.popover("🤖", help="Cấu hình quay tự động"):
                    render_ai_automation_config(p, s, mod_name, form_name)

                # Menu phụ (Xóa/Di chuyển)
                with c_opt.popover("⚙️"):
                    render_extra_options(ctrl, s, idx, len(items), p)

# --- CÁC HÀM BỔ TRỢ ĐỂ DỄ ĐỌC ---

def render_status_selector(ctrl, s, current_status, options):
    """Hàm xử lý chọn trạng thái"""
    new_st = st.selectbox("ST", options, label_visibility="collapsed",
                          index=options.index(current_status) if current_status in options else 0,
                          key=f"st_{s['id']}")
    if new_st != s.get('status'):
        ctrl.update_sub_content(s['id'], s['sub_title'], new_st)
        st.rerun()

def render_ai_automation_config(p, s, mod_name, form_name):
    """Giao diện Cấu hình AI lấy dữ liệu từ Config"""
    st.markdown(f"### 🤖 Cấu hình AI: {form_name}")
    
    # 1. Lấy danh sách nghiệp vụ từ Config
    # GUI tự động sinh ra danh sách dựa trên mảng AI_SCENARIOS trong Config
    scenarios_list = Config.AI_SCENARIOS
    
    selected_ids = st.multiselect(
        "Loại hướng dẫn muốn tạo:",
        options=[opt['id'] for opt in scenarios_list],
        format_func=lambda x: next(o['label'] for o in scenarios_list if o['id'] == x),
        default=["ADD"],
        key=f"scen_{s['id']}"
    )
    
    # 2. Lấy Slogan mặc định từ Config
    slogan = st.text_input(
        "Slogan kết video:", 
        value=Config.DEFAULT_SLOGAN, 
        key=f"slo_{s['id']}"
    )
    
    notes = st.text_area(
        "Ghi chú nhấn mạnh cho AI:", 
        placeholder="Ví dụ: Lưu ý khách hàng về phí bù tuổi...", 
        key=f"note_{s['id']}"
    )
    
    # 3. Nút xác nhận
    if st.button("🚀 BẮT ĐẦU SOẠN & QUAY", key=f"start_{s['id']}", type="primary", use_container_width=True):
        # Lưu vào session để qua Studio Bot tự biết đường mà chạy
        st.session_state.ai_config = {
            "target_domain": Config.TARGET_DOMAIN, # Bot sẽ dùng cái này để goto(url)
            "scenarios": selected_ids,
            "slogan": slogan,
            "notes": notes,
            "mod_name": mod_name,
            "form_name": form_name
        }
        navigate_to_studio(p, s, "Quay tự động 🤖")

def render_extra_options(ctrl, s, idx, total, p):
    """Hàm xử lý các nút Up, Down, Delete"""
    c1, c2 = st.columns(2)
    if c1.button("🔼", key=f"up_{s['id']}", disabled=(idx==0), use_container_width=True):
        ctrl.move_sub_content(s['id'], "up"); st.rerun()
    if c2.button("🔽", key=f"dn_{s['id']}", disabled=(idx==total-1), use_container_width=True):
        ctrl.move_sub_content(s['id'], "down"); st.rerun()
        
    st.divider()
    if st.button("🗑️ XÓA FORM", key=f"del_{s['id']}", type="primary", use_container_width=True):
        ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder'])
        st.rerun()

def navigate_to_studio(p, s, tab_name):
    """Chuyển hướng sang Studio"""
    st.session_state.active_project = p
    st.session_state.active_sub = s
    st.session_state.view = "studio"
    st.session_state.active_tab = tab_name
    st.rerun()