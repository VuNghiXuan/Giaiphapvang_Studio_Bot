import streamlit as st
import os
import json
import time
from pathlib import Path
from config import Config
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
# Giả định ScriptDialog đã được import đúng đường dẫn
from .gpv_render_scripts_dialog import ScriptDialog


@st.dialog("Cấu hình kịch bản AI", width="large") # Ép width="large" ở đây
def show_ai_config(ctrl, p, s, cha_name, display_name, ai_script, project_slug):
    # Gọi cái panel của ông vào đây
    ScriptDialog.render_ai_config_panel(
        ctrl, p, s, cha_name, display_name, ai_script, project_slug=project_slug 
    )
    

class RenderForm:  

    @staticmethod
    def get_status_info(sub_folder_path, manual_status=None):
        """ Hàm 1: Kiểm tra trạng thái thực tế của video trong storage """
        status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        if manual_status in status_list: 
            return manual_status
        if not sub_folder_path:
            return "Chưa quay"
        try:
            # Kiểm tra sự tồn tại của file vật lý
            base_path = Config.BASE_STORAGE / Config.APP_SLUG / sub_folder_path
            raw_dir = base_path / "raw"
            output_dir = base_path / "outputs"
            
            if output_dir.exists() and any(f.suffix == '.mp4' for f in output_dir.glob("*")):
                return "Hoàn chỉnh"
            if raw_dir.exists() and any(f.suffix in ['.mp4', '.webm'] for f in raw_dir.glob("*")):
                return "Đã quay"
        except Exception: pass
        return "Chưa quay"

    @staticmethod
    def render_status_badge(status):
        """ Hàm 2: Vẽ Badge trạng thái bằng HTML/CSS """
        status_map = {
            "Chưa quay": {"bg": "#F8F9FA", "color": "#6C757D", "border": "#DEE2E6"},
            "Đã quay": {"bg": "#007BFF", "color": "#FFFFFF", "border": "#0056B3"},
            "Hoàn chỉnh": {"bg": "#217346", "color": "#FFFFFF", "border": "#1e663e"}
        }
        cfg = status_map.get(status, status_map["Chưa quay"])
        st.markdown(f"""
            <div style="background-color: {cfg['bg']}; color: {cfg['color']}; 
            padding: 2px 10px; border-radius: 12px; font-size: 0.65rem; 
            font-weight: 700; display: inline-block; border: 1px solid {cfg['border']};
            text-transform: uppercase; margin-bottom: 5px;">
                {status}
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_item_rows(ctrl, p, items, _ai_script_param, project_folder):
        """ 
        Hàm 3 (TRỌNG TÂM): Render danh sách Form nghiệp vụ.
        Đã sửa tên tham số thành _ai_script_param để khớp với Dashboard.
        """
        project_slug = project_folder or Config.APP_SLUG

        # Inject CSS tùy chỉnh cho Card
        st.markdown("""
            <style>
                div[data-testid="stVerticalBlock"] > div.stElementContainer > div.stVerticalBlockBorder {
                    margin-bottom: 20px !important; 
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                    border-left: 5px solid #FFD700 !important;
                }
                .group-header-text { color: #202124; font-weight: 800; font-size: 1.2rem; margin-top: 20px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
                .folder-path-text { color: #70757a; font-size: 0.75rem; }
                .metadata-preview { color: #555E6D; font-size: 0.85rem; margin-top: 8px; border-left: 3px solid #FFD700; padding-left: 10px; font-style: italic; }
            </style>
        """, unsafe_allow_html=True)

        # Phân cấp dữ liệu theo Module Cha | Con
        tree = {}
        for s in items:
            parts = [part.strip() for part in s['sub_title'].split('|')]
            cha = parts[0] if len(parts) > 0 else "Chưa phân loại"
            con = parts[1] if len(parts) > 1 else "Chính"
            if cha not in tree: tree[cha] = {}
            if con not in tree[cha]: tree[cha][con] = []
            tree[cha][con].append(s)

        # Duyệt cây thư mục
        for cha_name, danh_sach_con in tree.items():
            st.markdown(f'<div class="group-header-text">🏢 {cha_name}</div>', unsafe_allow_html=True)
            
            # Render vùng hướng dẫn AI
            RenderForm.render_guide_section(ctrl, cha_name, _ai_script_param)

            for con_name, sub_items in danh_sach_con.items():
                if con_name != "Chính":
                    st.markdown(f"<p style='color:#217346; font-weight:600; font-size:0.9rem; margin-left: 10px;'>📂 {con_name}</p>", unsafe_allow_html=True)
                
                sorted_forms = sorted(sub_items, key=lambda x: (x.get('position', 0), x.get('id', 0)))

                for idx, s in enumerate(sorted_forms):
                    sub_path_str = s.get('sub_folder') or ""
                    current_status = RenderForm.get_status_info(sub_path_str, s.get('status'))
                    display_name = s['sub_title'].split('|')[-1].strip()
                    
                    with st.container(border=True):
                        col_info, col_status, col_btn_1, col_btn_2, col_btn_3 = st.columns([4, 1.5, 0.4, 0.4, 0.4])
                        
                        with col_info:
                            st.markdown(f"<b style='font-size:1rem; color:#1A73E8;'>{display_name}</b>", unsafe_allow_html=True)
                            RenderForm.render_status_badge(current_status)
                            st.markdown(f"<div class='folder-path-text'>📁 {project_slug}/{sub_path_str}</div>", unsafe_allow_html=True)
                            
                            # Preview nội dung Metadata (nếu có)
                            try:
                                meta = s.get('metadata')
                                if isinstance(meta, str): meta = json.loads(meta)
                                if meta:
                                    inputs = meta.get('sub_form_details', {}).get('inputs') or meta.get('inputs', [])
                                    labels = [f.get('label') for f in inputs if isinstance(f, dict) and f.get('label')][:5]
                                    if labels:
                                        st.markdown(f"<div class='metadata-preview'>🔍 Trường dữ liệu: {', '.join(labels)}</div>", unsafe_allow_html=True)
                            except: pass

                        with col_status:
                            RenderForm.render_status_selector(ctrl, s, current_status)

                        with col_btn_1:
                            if st.button("🎥", key=f"btn_man_{s['id']}", help="Quay video thủ công"):
                                RenderForm.navigate_to_studio(p, s, "Quay thủ công")
                        
                        # with col_btn_2:
                        #     with st.popover("🤖", help="Cấu hình kịch bản AI"):
                        #         ScriptDialog.render_ai_config_panel(
                        #             ctrl, p, s, cha_name, display_name, _ai_script_param,
                        #             project_slug=project_slug 
                        #         )

                        with col_btn_2:
                            # Thay popover bằng một nút bấm bình thường cho sạch bài
                            if st.button("🤖", key=f"btn_ai_{s['id']}", help="Cấu hình kịch bản AI"):
                                # Gọi hàm render dialog (hàm này phải có @st.dialog)
                                show_ai_config(ctrl, p, s, cha_name, display_name, _ai_script_param, project_slug)
                                
                        
                        with col_btn_3:
                            with st.popover("⚙️", help="Quản lý"):
                                RenderForm.render_extra_options(ctrl, s, idx, len(sorted_forms), p, project_slug=project_slug)

    @staticmethod
    def render_guide_section(ctrl, menu_cha, ai_script):
        """ Hàm 4: Vùng gợi ý nghiệp vụ từ AI """
        safe_id = "".join(filter(str.isalnum, menu_cha))
        guide_key = f"guide_data_{safe_id}"
        
        with st.expander(f"💡 Hướng dẫn nghiệp vụ: {menu_cha}", expanded=False):
            col_v, col_t = st.columns([1, 1.5])
            with col_v:
                # Video placeholder hoặc video hướng dẫn thực tế
                st.image("https://img.youtube.com/vi/dQw4w9WgXcQ/0.jpg", width='stretch')
            
            with col_t:
                content = st.session_state.get(guide_key, "*Chưa có nội dung hướng dẫn. Hãy bấm Soạn bài để AI phân tích.*")
                st.info(content)
                
                if st.button(f"🪄 Soạn bài: {menu_cha}", key=f"btn_guide_ai_{safe_id}"):
                    with st.spinner("AI đang phân tích nghiệp vụ Giải Pháp Vàng..."):
                        res = ai_script.ask_ai(f"Tóm tắt nghiệp vụ {menu_cha} cho tiệm vàng ngắn gọn, chuyên nghiệp.")
                        if res:
                            st.session_state[guide_key] = res
                            st.rerun()

    @staticmethod
    def render_status_selector(ctrl, s, current_status):
        """ Hàm 5: Dropdown thay đổi trạng thái """
        options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        try: current_idx = options.index(current_status)
        except: current_idx = 0
        
        new_st = st.selectbox(
            "Trạng thái", options, index=current_idx, 
            key=f"sel_st_{s['id']}", label_visibility="collapsed"
        )
        if new_st != current_status:
            if ctrl.update_sub_content(sub_id=s['id'], status=new_st): 
                st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p, project_slug=None):
        """ Hàm 6: Các nút chức năng phụ (Xóa, Di chuyển) """
        final_slug = project_slug or Config.APP_SLUG
        
        st.markdown("<b>Thứ tự hiển thị</b>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("🔼", disabled=(idx==0), key=f"up_{s['id']}"): 
            if ctrl.move_sub_content(s['id'], "up"): st.rerun()
        if c2.button("🔽", disabled=(idx==total-1), key=f"down_{s['id']}"): 
            if ctrl.move_sub_content(s['id'], "down"): st.rerun()
        
        st.divider()
        if st.button("🗑️ XÓA FORM", type="primary", width='stretch', key=f"delete_{s['id']}"):
            if ctrl.delete_sub_content(s['id'], final_slug, s.get('sub_folder')): 
                st.rerun()

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        """ Hàm 7: Chuyển hướng sang Studio để quay phim """
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s
        st.rerun()