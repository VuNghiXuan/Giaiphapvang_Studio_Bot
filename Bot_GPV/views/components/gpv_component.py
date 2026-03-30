import streamlit as st
import os
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge
from ..utils_dashboad.ai_config_for_gpv_component import AIConfigHandler

class GPVComponent:    

    # =================================================================
    # PHẦN 1: RENDER DANH MỤC FORM
    # =================================================================

    @staticmethod
    def render_item_rows(ctrl, p, items, ai_script, project_name):
        st.markdown("""
            <style>
                /* Phóng to cửa sổ Popover khi nhấn vào nút 🤖 */
                div[data-testid="stPopoverBody"] {
                    width: 800px !important;
                    max-width: 90vw !important;
                }
                /* Làm các ô text area cao hơn cho dễ nhìn */
                textarea {
                    font-family: 'Consolas', 'Monaco', monospace !important;
                    font-size: 0.9rem !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda"}
        }
        status_options = list(STATUS_STYLES.keys())
        
        # Lấy tên folder an toàn từ object project p
        p_folder = p.get('project_folder') or p.get('folder_name') or project_name

        for idx, s in enumerate(items):
            sub_path = os.path.join(Config.BASE_STORAGE, p_folder, s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            
            parts = s['sub_title'].split('|')
            mod_name, form_name = parts[0], parts[-1]
            style = STATUS_STYLES.get(current_status, STATUS_STYLES["Chưa quay"])

            with st.container(border=True):
                st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div:has(input[key="st_{s['id']}"]) 
                    {{ border-left: 6px solid {style['color']} !important; background-color: {style['bg']}; }}</style>""", unsafe_allow_html=True)

                col_info, col_status, col_actions = st.columns([3, 1.2, 2.3])
                
               
                with col_info:
                    # 1. Tên Form kèm Link (Gom làm một cho gọn)
                    st.markdown(f"**{form_name}**", help=f"🔗 Link: {s.get('url', 'N/A')}")
                    
                    # 2. Hiển thị Badge trạng thái (Quay/Chưa quay) và Script đồng hàng
                    col_badge, col_script = st.columns([1, 1])
                    with col_badge:
                        render_status_badge(current_status)
                    with col_script:
                        # Check xem đã có kịch bản JSON lưu trong máy/DB chưa
                        if s.get('has_script'): 
                            st.markdown("<span style='color: #28a745; font-size: 0.75rem; font-weight: bold;'>📜 Đã có kịch bản</span>", unsafe_allow_html=True)
                    
                    # 3. Thông tin phụ
                    st.caption(f"📁 {s['sub_folder']} | 📦 {mod_name}")
                    
                    # 4. Tri thức hệ thống (Metadata) - Bot Biên Tập đã lọc
                    meta = s.get('metadata', {})
                    if isinstance(meta, dict) and meta.get('form_fields'):
                        # Lấy 5 label đầu tiên để Vũ biết bên trong có gì
                        fields = [f.get('label') for f in meta['form_fields'][:5] if isinstance(f, dict) and f.get('label')]
                        if fields:
                            st.markdown(f"<div style='font-size: 0.75rem; color: #666; font-style: italic;'>📝 {', '.join(fields)}...</div>", unsafe_allow_html=True)
                            

                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; font-weight: bold; margin-bottom:0;'>TRẠNG THÁI</p>", unsafe_allow_html=True)
                    GPVComponent.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    
                    # 🎥 Nút quay thủ công
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                        GPVComponent.navigate_to_studio(p, s, "Quay thủ công")
                    
                    # 🤖 Nút AI soạn kịch bản (Popover)
                    with c_auto.popover("🤖", help="AI soạn kịch bản"):
                        # FIX: Truyền ctrl vào đầu tiên để render_ai_config_panel có thể dùng lấy items dự án
                        GPVComponent.render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script)
                    
                    # ⚙️ Nút tùy chọn khác
                    with c_opt.popover("⚙️"):
                        GPVComponent.render_extra_options(ctrl, s, idx, len(items), p)

    

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        current_idx = options.index(current_status) if current_status in options else 0
        new_st = st.selectbox("ST", options, index=current_idx, key=f"st_{s['id']}", label_visibility="collapsed")
        if new_st != current_status:
            if ctrl.update_sub_content(s['id'], new_status=new_st):
                st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p):
        st.markdown("**Quản lý**")
        c1, c2 = st.columns(2)
        if c1.button("🔼", disabled=(idx==0), key=f"u_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "up")
            st.rerun()
        if c2.button("🔽", disabled=(idx==total-1), key=f"d_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "down")
            st.rerun()
        
        p_folder = p.get('project_folder') or p.get('folder_name') or ""
        if st.button("🗑️ XÓA", type="primary", use_container_width=True, key=f"del_{s['id']}"):
            if ctrl.delete_sub_content(s['id'], p_folder, s['sub_folder']):
                st.rerun()

    # =================================================================
    # PHẦN 2: PHẦN BIÊN TẬP VÀ XUẤT BẢN VIDEO 
    # =================================================================
    
    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """
        Giao diện Studio thu nhỏ: Nơi Đạo diễn Vũ duyệt kịch bản thô trước khi gửi AI.
        """
        if not isinstance(s, dict):
            st.error("Lỗi dữ liệu: Phân cảnh (s) không hợp lệ.")
            return

        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # --- BƯỚC 1: BOT BIÊN TẬP TRÍCH XUẤT TRI THỨC GỐC ---
        raw_ctx = ai_script.get_form_knowledge_from_db(s)
        
        if "⚠️" in raw_ctx:
            st.warning(raw_ctx)
        else:
            st.success("✅ Tri thức Metadata sẵn sàng.")

        # --- BƯỚC 2: THIẾT LẬP CẤU HÌNH (SẼ MANG QUA STUDIO) ---
        col1, col2 = st.columns(2)
        sel_model = col1.selectbox("Bộ não AI:", ["gemini-2.0-flash", "gemini-1.5-flash"], key=f"mdl_{s['id']}")
        
        voice_map = {"Hoài My (Nữ)": "vi-VN-HoaiMyNeural", "Nam Minh (Nam)": "vi-VN-NamMinhNeural"}
        sel_voice_label = col2.selectbox("Giọng đọc:", list(voice_map.keys()), key=f"voc_{s['id']}")
        
        with st.expander("📄 Tùy chỉnh tri thức bóc tách", expanded=False):
            user_edited_ctx = st.text_area("Context nghiệp vụ:", value=raw_ctx, height=150, key=f"raw_{s['id']}")

        # --- BƯỚC 3: THIẾT LẬP LIÊN THÔNG (WORKFLOW) ---
        all_options = [opt['id'] for opt in Config.AI_SCENARIOS] + ["WORKFLOW"]
        scenarios = st.multiselect(
            "Mục tiêu video:", 
            options=all_options,
            default=["ADD"],
            format_func=lambda x: "🔗 KẾT NỐI LIÊN THÔNG (WORKFLOW)" if x == "WORKFLOW" 
                                else next((o['label'] for o in Config.AI_SCENARIOS if o['id'] == x), x),
            key=f"sc_{s['id']}"
        )
        
        workflow_ctx = ""
        if "WORKFLOW" in scenarios:
            with st.container(border=True):
                st.markdown("🌐 **Thiết lập luồng liên kết Module/Form**")
                all_project_items = ctrl.get_sub_contents(p['id']) 
                other_forms = [item for item in all_project_items if item['id'] != s['id']]
                
                selected_next_forms = st.multiselect(
                    "Chọn Form tiếp theo để nối cảnh:",
                    options=other_forms,
                    format_func=lambda x: f"📦 {x['sub_title'].split('|')[0]} ➜ 📄 {x['sub_title'].split('|')[-1]}",
                    key=f"wf_target_{s['id']}"
                )
                
                if selected_next_forms:
                    for f in selected_next_forms:
                        f_ctx = ai_script.get_form_knowledge_from_db(f)
                        workflow_ctx += f"\n\n-- BƯỚC TIẾP THEO (LIÊN THÔNG): {f.get('sub_title')} --\n{f_ctx}"
                    st.info(f"💡 Đã tích hợp {len(selected_next_forms)} bước liên thông.")

        # --- BƯỚC 4: Ý ĐỒ ĐẠO DIỄN VÀ XEM TRƯỚC PROMPT ---
        notes = st.text_area("Lưu ý từ Đạo diễn Vũ:", key=f"nt_{s['id']}", placeholder="VD: Nhập mã xong phải chờ bảng giá nhảy...")
        slogan = st.text_input("Slogan kết thúc:", value=Config.DEFAULT_SLOGAN, key=f"slo_{s['id']}")

        # Đóng gói cấu hình tạm để tạo Prompt duyệt
        temp_config = {
            "scenarios": scenarios, 
            "notes": notes, 
            "slogan": slogan,
            "current_module": mod_name
        }
        
        # Tạo bản thảo Prompt cuối cùng để Vũ duyệt
        full_draft_prompt = ai_script.generate_ai_prompt(mod_name, form_name, temp_config, user_edited_ctx + workflow_ctx)

        with st.expander("🔍 XEM KỊCH BẢN THÔ (PROMPT) TRƯỚC KHI GỬI AI", expanded=False):
            # Vũ có thể sửa trực tiếp nội dung yêu cầu cuối cùng ở đây
            final_prompt_to_send = st.text_area("Yêu cầu gửi Biên tập AI:", value=full_draft_prompt, height=250, key=f"final_p_{s['id']}")

        st.divider()

        # --- BƯỚC 5: XUẤT BẢN & CHUYỂN VÙNG (STUDIO) ---
        if st.button("🚀 GỬI AI & SANG STUDIO", type="primary", use_container_width=True, key=f"run_{s['id']}"):
            with st.spinner(f"🎭 {ai_script.bot_actor} đang nhập vai để diễn ra JSON..."):
                # Gửi bản đã duyệt sang cho Gemini
                steps = ai_script.get_ai_script(final_prompt_to_send, sel_model)
                
                if steps:
                    # LƯU TRỮ CẤU HÌNH ĐỂ MANG SANG STUDIO
                    st.session_state.current_steps = steps
                    st.session_state.selected_voice = voice_map[sel_voice_label] # Mang giọng đọc qua
                    st.session_state.target_url = s.get('url', Config.TARGET_DOMAIN)
                    st.session_state.active_model = sel_model # Mang bộ não qua
                    
                    st.toast("✅ Đã xuất bản kịch bản thành công!", icon="🎬")
                    # Chuyển hướng sang Studio để xem AI lồng tiếng và diễn
                    GPVComponent.navigate_to_studio(p, s, "Quay tự động 🤖")
                else:
                    st.error("❌ Lỗi: AI không thể xuất bản JSON. Vui lòng kiểm tra lại nội dung kịch bản thô.")

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        st.session_state.update({"active_project": p, "active_sub": s, "view": "studio", "active_tab": tab_name})
        st.rerun()