import streamlit as st
import os
import json
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge

class GPVComponent:
    @staticmethod
    def render_item_rows(ctrl, p, items, ai_handler, project_name):
        """
        Hàm chính để render danh sách các Form với màu sắc và dữ liệu Preview
        """
        # 1. Định nghĩa bảng màu trạng thái chuyên nghiệp
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa", "border": "#dee2e6"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff", "border": "#b3d7ff"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda", "border": "#c3e6cb"}
        }
        status_options = list(STATUS_STYLES.keys())
        
        for idx, s in enumerate(items):
            # Lấy thông trạng thái thực tế dựa trên folder vật lý
            sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            
            # Tách tên Module và Form từ sub_title (VD: "Danh mục|Khách hàng")
            parts = s['sub_title'].split('|')
            mod_name = parts[0]
            form_name = parts[-1]

            style = STATUS_STYLES.get(current_status, STATUS_STYLES["Chưa quay"])

            # 2. Render Container với hiệu ứng vạch màu bên trái (Visual Cue)
            with st.container(border=True):
                st.markdown(f"""
                    <style>
                        div[data-testid="stVerticalBlock"] > div:has(input[key="st_{s['id']}"]) {{
                            border-left: 6px solid {style['color']} !important;
                            background-color: {style['bg']};
                        }}
                    </style>
                """, unsafe_allow_html=True)

                col_info, col_status, col_actions = st.columns([3, 1.2, 2.3])
                
                with col_info:
                    # Tiêu đề Form & Badge trạng thái
                    st.markdown(f"**{form_name}**", help=f"Đường dẫn: {s.get('status', 'N/A')}")
                    render_status_badge(current_status) 
                    st.caption(f"📁 {s['sub_folder']} | 📦 {mod_name}") 
                    
                    # --- HIỂN THỊ TRÍ THỨC HỆ THỐNG (VÉT ĐƯỢC) ---
                    # Ưu tiên lấy từ metadata (DB) nếu render_gpv_logic đã bóc sẵn
                    p_fields = s.get('preview_fields', "Chưa có dữ liệu")
                    p_actions = s.get('preview_actions', "")
                    
                    if "Chưa có dữ liệu" not in p_fields:
                        st.markdown(f"""
                            <div style='font-size: 0.75rem; color: #444; background: white; 
                                        padding: 6px; border-radius: 4px; border: 1px solid #ddd;'>
                                📝 <b>Các trường:</b> {p_fields}
                            </div>
                        """, unsafe_allow_html=True)
                    
                    if p_actions:
                        st.markdown(f"""
                            <div style='font-size: 0.75rem; color: #004d40; font-weight: 500; margin-top: 4px;'>
                                ⚡ <b>Thao tác:</b> {p_actions}
                            </div>
                        """, unsafe_allow_html=True)
                
                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; color: {style['color']}; font-weight: bold; margin-bottom: 0;'>QUẢN LÝ TRẠNG THÁI</p>", unsafe_allow_html=True)
                    GPVComponent.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") # Spacer để căn giữa nút bấm
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    
                    # Nút vào Studio quay tay
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay Studio thủ công", use_container_width=True):
                        GPVComponent.navigate_to_studio(p, s, "Quay thủ công")

                    # Nút AI Popover - Trung tâm điều khiển kịch bản
                    with c_auto.popover("🤖", help="AI soạn kịch bản tự động", use_container_width=True):
                        GPVComponent.render_ai_config_panel(p, s, project_name, mod_name, form_name, ai_handler)

                    # Nút Cài đặt phụ (Xóa, Di chuyển)
                    with c_opt.popover("⚙️", use_container_width=True):
                        GPVComponent.render_extra_options(ctrl, s, idx, len(items), p)

    @staticmethod
    def render_ai_config_panel(p, s, project_name, mod_name, form_name, ai_handler):
        """Bảng cấu hình AI: Sử dụng tri thức từ DB/JSON để soạn kịch bản"""
        st.subheader(f"🤖 AI Studio: {form_name}")
        
        # 1. Lấy ngữ cảnh từ tri thức đã vét (Hàm get_form_knowledge của Vũ)
        form_context = ai_handler.get_form_knowledge(p['folder_name'], mod_name, form_name)
        
        if "⚠️" in form_context:
            st.warning("Form này chưa quét Cấp 2. AI sẽ hoạt động dựa trên phán đoán (độ chính xác thấp).")
        else:
            st.success("✅ Tri thức hệ thống đã sẵn sàng.")

        col_brain, col_voice = st.columns(2)
        selected_model = col_brain.selectbox("Bộ não AI:", ["gemini-2.0-flash", "gemini-1.5-pro"], key=f"mdl_{s['id']}")
        selected_voice = col_voice.selectbox("Giọng đọc:", ["Ban Mai (Nữ)", "Minh Quang (Nam)"], key=f"voc_{s['id']}")
        
        # Cho phép Vũ xem/sửa dữ liệu mà AI sẽ đọc
        with st.expander("📄 Xem tri thức AI sẽ đọc", expanded=False):
            form_context = st.text_area("Context gửi AI:", value=form_context, height=250, key=f"raw_{s['id']}")

        # Cấu hình nghiệp vụ cho kịch bản
        scenarios = st.multiselect(
            "Mục tiêu video:", 
            [opt['id'] for opt in Config.AI_SCENARIOS], 
            default=["ADD"], 
            format_func=lambda x: next(o['label'] for o in Config.AI_SCENARIOS if o['id'] == x), 
            key=f"sc_{s['id']}"
        )
        
        notes = st.text_area("Vũ muốn AI lưu ý gì thêm?", placeholder="VD: Nhấn mạnh vào cách nhập tiền công...", height=80, key=f"nt_{s['id']}")
        slogan = st.text_input("Slogan thương hiệu:", value=Config.DEFAULT_SLOGAN, key=f"slo_{s['id']}")

        if st.button("🚀 BẮT ĐẦU SOẠN KỊCH BẢN", type="primary", use_container_width=True, key=f"run_{s['id']}"):
            with st.spinner("AI đang 'nuốt' dữ liệu và viết kịch bản..."):
                ai_config = {
                    "scenarios": scenarios, 
                    "notes": notes, 
                    "slogan": slogan
                }
                # 2. Tạo Prompt và gọi API Gemini
                prompt = ai_handler.generate_ai_prompt(mod_name, form_name, ai_config, form_context)
                steps = ai_handler.get_ai_script(prompt, selected_model)
                
                if steps:
                    st.session_state.current_steps = steps
                    st.session_state.selected_voice = selected_voice
                    # Chuyển sang View Studio để xem AI diễn xuất
                    GPVComponent.navigate_to_studio(p, s, "Quay tự động 🤖")
                else:
                    st.error("AI không trả về kịch bản. Kiểm tra lại API Key hoặc Context.")

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        """Hàm cập nhật trạng thái nghiệp vụ nhanh"""
        new_st = st.selectbox(
            "ST_Select", options, 
            index=options.index(current_status) if current_status in options else 0, 
            key=f"st_{s['id']}", 
            label_visibility="collapsed"
        )
        # Chỉ cập nhật nếu user thay đổi thực sự
        if new_st != s.get('status'): 
            ctrl.update_sub_content(s['id'], new_status=new_st)
            st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p):
        """Các tùy chọn quản lý bổ sung"""
        st.markdown("**Sắp xếp & Quản lý**")
        c1, c2 = st.columns(2)
        if c1.button("🔼 Lên", disabled=(idx==0), key=f"u_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "up")
            st.rerun()
        if c2.button("🔽 Xuống", disabled=(idx==total-1), key=f"d_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "down")
            st.rerun()
        
        st.divider()
        if st.button("🗑️ XÓA VĨNH VIỄN", type="primary", use_container_width=True, key=f"del_{s['id']}"):
            # Xóa cả trong DB và thư mục vật lý
            if ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']):
                st.toast(f"Đã xóa {s['sub_title']}")
                st.rerun()

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        """Hàm điều hướng tập trung sang trang Studio"""
        st.session_state.active_project = p
        st.session_state.active_sub = s
        st.session_state.view = "studio"
        st.session_state.active_tab = tab_name
        st.rerun()