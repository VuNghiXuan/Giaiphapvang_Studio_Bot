import streamlit as st
import os
import json
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge

class GPVComponent:
    @staticmethod
    @staticmethod
    def render_item_rows(ctrl, p, items, ai_handler, project_name):
        """
        Hàm chính để render danh sách các Form với màu sắc và dữ liệu Preview
        """
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa", "border": "#dee2e6"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff", "border": "#b3d7ff"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda", "border": "#c3e6cb"}
        }
        status_options = list(STATUS_STYLES.keys())
        
        for idx, s in enumerate(items):
            sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            
            parts = s['sub_title'].split('|')
            mod_name = parts[0]
            form_name = parts[-1]
            style = STATUS_STYLES.get(current_status, STATUS_STYLES["Chưa quay"])

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
                    form_url = s.get('url', 'N/A')
                    st.markdown(f"**{form_name}**", help=f"🔗 Link: {form_url}")
                    render_status_badge(current_status) 
                    st.caption(f"📁 {s['sub_folder']} | 📦 {mod_name}")
                    
                    # --- XỬ LÝ TRÍ THỨC TỪ METADATA ---
                    meta = s.get('metadata')
                    fields_list = []
                    actions_list = []

                    if isinstance(meta, dict):
                        # Bóc tách Fields
                        fields_raw = meta.get('form_fields', [])
                        fields_list = [f.get('label') for f in fields_raw if isinstance(f, dict) and f.get('label')]
                        
                        # Bóc tách Actions (Xử lý cả String và Dict)
                        actions_raw = meta.get('actions', [])
                        for a in actions_raw:
                            if isinstance(a, dict):
                                actions_list.append(a.get('label', 'Nút không tên'))
                            else:
                                actions_list.append(str(a))

                    # Hiển thị Fields Preview
                    if fields_list:
                        p_fields = ", ".join(fields_list[:5]) + ("..." if len(fields_list) > 5 else "")
                        st.markdown(f"""
                            <div style='font-size: 0.75rem; color: #444; background: white; 
                                         padding: 6px; border-radius: 4px; border: 1px solid #ddd;'>
                                📝 <b>Các trường:</b> {p_fields}
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("💡 Form này chưa có dữ liệu quét chi tiết.")

                    # Hiển thị Actions Preview (Dùng join an toàn)
                    if actions_list:
                        p_actions = ", ".join(actions_list)
                        st.markdown(f"""
                            <div style='font-size: 0.75rem; color: #004d40; font-weight: 500; margin-top: 4px;'>
                                ⚡ <b>Thao tác:</b> {p_actions}
                            </div>
                        """, unsafe_allow_html=True)
                
                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; color: {style['color']}; font-weight: bold; margin-bottom: 0;'>QUẢN LÝ TRẠNG THÁI</p>", unsafe_allow_html=True)
                    GPVComponent.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay Studio thủ công", use_container_width=True):
                        GPVComponent.navigate_to_studio(p, s, "Quay thủ công")
                    with c_auto.popover("🤖", help="AI soạn kịch bản tự động", use_container_width=True):
                        GPVComponent.render_ai_config_panel(p, s, project_name, mod_name, form_name, ai_handler)
                    with c_opt.popover("⚙️", use_container_width=True):
                        GPVComponent.render_extra_options(ctrl, s, idx, len(items), p)

    
    @staticmethod
    def render_ai_config_panel(p, s, project_name, mod_name, form_name, ai_handler):
        """Bảng cấu hình AI: Sử dụng tri thức từ DB để soạn kịch bản"""
        st.subheader(f"🤖 AI Studio: {form_name}")
        
        # --- 1. XỬ LÝ TRI THỨC (CONTEXT) TỪ DB METADATA ---
        meta = s.get('metadata')
        has_deep_data = False
        raw_context = ""

        if isinstance(meta, dict) and meta.get('form_fields'):
            has_deep_data = True
            fields = meta.get('form_fields', [])
            actions_raw = meta.get('actions', [])
            
            raw_context = f"DỮ LIỆU THỰC TẾ TỪ HỆ THỐNG (FORM: {form_name}):\n"
            raw_context += f"- Link: {s.get('url', 'N/A')}\n"
            raw_context += "- Các trường dữ liệu tìm thấy:\n"
            
            for f in fields:
                if isinstance(f, dict):
                    req = "(Bắt buộc)" if f.get('required') else ""
                    label = f.get('label', 'Không tên')
                    f_type = f.get('type', 'text')
                    sel = f.get('selector', '')
                    raw_context += f"  + {label} (Loại: {f_type}, Selector: {sel}) {req}\n"
            
            # --- FIX LỖI JOIN TẠI ĐÂY ---
            cleaned_actions = []
            for a in actions_raw:
                if isinstance(a, dict):
                    # Nếu là dict, lấy label hoặc selector làm định danh
                    cleaned_actions.append(a.get('label', a.get('selector', 'Nút')))
                else:
                    cleaned_actions.append(str(a))
            
            if cleaned_actions:
                raw_context += f"- Thao tác khả dụng: {', '.join(cleaned_actions)}\n"
        else:
            raw_context = ai_handler.get_form_knowledge(p['folder_name'], mod_name, form_name)
        
        if not has_deep_data and "⚠️" in raw_context:
            st.warning("⚠️ Form này chưa quét Cấp 2. AI sẽ hoạt động dựa trên phán đoán chung.")
        else:
            st.success("✅ Tri thức hệ thống (Metadata DB) đã sẵn sàng.")

        # --- 2. CẤU HÌNH BỘ NÃO & GIỌNG ĐỌC ---
        col_brain, col_voice = st.columns(2)
        selected_model = col_brain.selectbox(
            "Bộ não AI:", 
            ["gemini-2.0-flash", "gemini-1.5-pro"], 
            key=f"mdl_{s['id']}"
        )
        
        voice_options = {
            "Hoài My (Nữ - Neural)": "vi-VN-HoaiMyNeural",
            "Nam Minh (Nam - Neural)": "vi-VN-NamMinhNeural"
        }
        
        selected_voice_label = col_voice.selectbox(
            "Giọng đọc (Edge-TTS):", 
            options=list(voice_options.keys()), 
            key=f"voc_{s['id']}"
        )
        selected_voice_code = voice_options[selected_voice_label]
        
        with st.expander("📄 Xem/Sửa tri thức AI sẽ đọc", expanded=False):
            final_context = st.text_area(
                "Nội dung Context:", 
                value=raw_context, 
                height=250, 
                key=f"raw_{s['id']}"
            )

        # --- 3. CẤU HÌNH NGHIỆP VỤ ---
        scenarios = st.multiselect(
            "Mục tiêu video:", 
            [opt['id'] for opt in Config.AI_SCENARIOS], 
            default=["ADD"], 
            format_func=lambda x: next(o['label'] for o in Config.AI_SCENARIOS if o['id'] == x), 
            key=f"sc_{s['id']}"
        )
        
        notes = st.text_area(
            "Vũ muốn AI lưu ý gì thêm?", 
            placeholder="VD: Nhấn mạnh vào cách nhập mã số thuế...", 
            height=80, 
            key=f"nt_{s['id']}"
        )
        
        slogan = st.text_input(
            "Slogan thương hiệu:", 
            value=Config.DEFAULT_SLOGAN, 
            key=f"slo_{s['id']}"
        )

        # --- 4. NÚT CHẠY AI ---
        if st.button("🚀 BẮT ĐẦU SOẠN KỊCH BẢN", type="primary", use_container_width=True, key=f"run_{s['id']}"):
            if not final_context.strip():
                st.error("Lỗi: Context trống, AI không thể lập kịch bản.")
                return

            with st.spinner("AI đang 'nuốt' dữ liệu và viết kịch bản..."):
                ai_config = {
                    "scenarios": scenarios, 
                    "notes": notes, 
                    "slogan": slogan,
                    "voice": selected_voice_code 
                }
                
                prompt = ai_handler.generate_ai_prompt(mod_name, form_name, ai_config, final_context)
                steps = ai_handler.get_ai_script(prompt, selected_model)
                
                if steps:
                    st.session_state.current_steps = steps
                    st.session_state.selected_voice = selected_voice_code 
                    st.session_state.target_url = s.get('url', Config.TARGET_DOMAIN)
                    GPVComponent.navigate_to_studio(p, s, "Quay tự động 🤖")
                else:
                    st.error("AI không trả về kịch bản. Kiểm tra lại API Key hoặc nội dung Context.")

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        """Cập nhật trạng thái 'Chưa quay/Đã quay' vào DB"""
        # Tìm index của status hiện tại trong list options
        try:
            current_idx = options.index(current_status)
        except ValueError:
            current_idx = 0

        new_st = st.selectbox(
            "ST_Select", options, 
            index=current_idx, 
            key=f"st_{s['id']}", 
            label_visibility="collapsed"
        )

        # CHỖ CẦN SỬA: Chỉ update status, giữ nguyên các cột khác
        if new_st != current_status: 
            if ctrl.update_sub_content(s['id'], new_status=new_st):
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