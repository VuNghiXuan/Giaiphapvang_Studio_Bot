import streamlit as st
import os
import json
from pathlib import Path
from config import Config
from core.ai_manager import AIManager
from .gpv_render_scripts_dialog import ScriptDialog

class RenderForm:  
    ai_manager = AIManager()

    @staticmethod
    def get_status_info(sub_folder_path, manual_status=None):
        status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        if manual_status in status_list: 
            return manual_status
        if not sub_folder_path:
            return "Chưa quay"
        try:
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
    def render_item_rows(ctrl, p, items, ai_script, project_name):
        # Inject CSS để định dạng khung bo vàng giống ảnh mẫu
        st.markdown("""
            <style>
                /* Khung chứa nội dung con có viền vàng bo góc */
                div[data-testid="stVerticalBlock"] > div.stElementContainer > div.stVerticalBlockBorder {
                    border: 2px solid #FFD700 !important;
                    border-radius: 15px !important;
                    padding: 15px !important;
                    margin-bottom: 10px !important;
                }
                
                .group-header-text {
                    color: #202124;
                    font-weight: 800;
                    font-size: 1.2rem;
                    margin-bottom: 15px;
                }

                .folder-path-text {
                    color: #70757a;
                    font-size: 0.75rem;
                    font-family: 'Segoe UI', sans-serif;
                }

                .metadata-preview {
                    color: #555E6D;
                    font-size: 0.85rem;
                    margin-top: 8px;
                    border-left: 3px solid #FFD700;
                    padding-left: 10px;
                }
            </style>
        """, unsafe_allow_html=True)

        tree = {}
        for s in items:
            parts = [part.strip() for part in s['sub_title'].split('|')]
            cha = parts[0] if len(parts) > 0 else "Chưa phân loại"
            con = parts[1] if len(parts) > 1 else "Chính"
            if cha not in tree: tree[cha] = {}
            if con not in tree[cha]: tree[cha][con] = []
            tree[cha][con].append(s)

        for cha, danh_sach_con in tree.items():
            st.markdown(f'<div class="group-header-text">🏢 {cha}</div>', unsafe_allow_html=True)
            
            # Hướng dẫn nghiệp vụ
            RenderForm.render_guide_section(ctrl, cha, ai_script)

            for con, sub_items in danh_sach_con.items():
                if con != "Chính":
                    st.markdown(f"<p style='color:#217346; font-weight:600; font-size:0.9rem; margin-left: 10px;'>📂 {con}</p>", unsafe_allow_html=True)
                
                sorted_forms = sorted(sub_items, key=lambda x: (x.get('position', 0), x.get('id', 0)))

                for idx, s in enumerate(sorted_forms):
                    sub_path_str = s.get('sub_folder') or ""
                    current_status = RenderForm.get_status_info(sub_path_str, s.get('status'))
                    form_name = s['sub_title'].split('|')[-1].strip()
                    
                    # TẠO KHUNG BO VÀNG BẰNG CONTAINER
                    with st.container(border=True):
                        col_info, col_status, col_btn_1, col_btn_2, col_btn_3 = st.columns([4, 1.5, 0.4, 0.4, 0.4])
                        
                        with col_info:
                            st.markdown(f"<b style='font-size:1rem; color:#1A73E8;'>{form_name}</b>", unsafe_allow_html=True)
                            RenderForm.render_status_badge(current_status)
                            st.markdown(f"<div class='folder-path-text'>📁 {sub_path_str}</div>", unsafe_allow_html=True)
                            
                            try:
                                meta = s.get('metadata', {})
                                if isinstance(meta, str): meta = json.loads(meta)
                                inputs = meta.get('sub_form_details', {}).get('inputs') or meta.get('inputs', [])
                                if inputs:
                                    labels = [f.get('label') for f in inputs if isinstance(f, dict) and f.get('label')][:5]
                                    st.markdown(f"<div class='metadata-preview'>🔍 <i>{', '.join(labels)}</i></div>", unsafe_allow_html=True)
                            except: pass

                        with col_status:
                            RenderForm.render_status_selector(ctrl, s, current_status)

                        with col_btn_1:
                            if st.button("🎥", key=f"m_{s['id']}", help="Quay video"):
                                RenderForm.navigate_to_studio(p, s, "Quay thủ công")
                        
                        with col_btn_2:
                            with st.popover("🤖"):
                                ScriptDialog.render_ai_config_panel(ctrl, p, s, cha, form_name, ai_script)
                        
                        with col_btn_3:
                            with st.popover("⚙️"):
                                RenderForm.render_extra_options(ctrl, s, idx, len(sorted_forms), p)

    @staticmethod
    def render_guide_section(ctrl, menu_cha, ai_script):
        guide_key = f"guide_text_{menu_cha}"
        with st.expander(f"💡 Hướng dẫn nghiệp vụ: {menu_cha}", expanded=False):
            col_v, col_t = st.columns([1, 1.5])
            with col_v:
                st.image("https://img.youtube.com/vi/dQw4w9WgXcQ/0.jpg", width='stretch')
            with col_t:
                content = st.session_state.get(guide_key, "*Chưa có nội dung hướng dẫn*")
                st.info(content)
                if st.button(f"🪄 Soạn bài", key=f"ai_g_{menu_cha}"):
                    st.session_state[guide_key] = ai_script.ask_ai(f"Tóm tắt nghiệp vụ {menu_cha} cho tiệm vàng")
                    st.rerun()

    @staticmethod
    def render_status_selector(ctrl, s, current_status):
        options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
        try: current_idx = options.index(current_status)
        except: current_idx = 0
        new_st = st.selectbox("Status", options, index=current_idx, key=f"st_{s['id']}", label_visibility="collapsed")
        if new_st != current_status:
            if ctrl.update_sub_content(sub_id=s['id'], status=new_st): st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p):
        st.markdown("<b>Quản lý</b>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("🔼", disabled=(idx==0), key=f"u_{s['id']}"): 
            if ctrl.move_sub_content(s['id'], "up"): st.rerun()
        if c2.button("🔽", disabled=(idx==total-1), key=f"d_{s['id']}"): 
            if ctrl.move_sub_content(s['id'], "down"): st.rerun()
        st.divider()
        if st.button("🗑️ XÓA", type="primary", width='stretch', key=f"del_{s['id']}"):
            if ctrl.delete_sub_content(s['id'], p.get('folder_name'), s.get('sub_folder')): st.rerun()

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s
        st.rerun()