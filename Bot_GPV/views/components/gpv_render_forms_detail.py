import streamlit as st
import os
from pathlib import Path
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge
# from ..utils_dashboad.ai_config_for_gpv_component import AIConfigHandler
from core.ai_manager import AIManager
import json
from .gpv_render_scripts_dialog import ScriptDialog


class RenderForm:  
    ai_manager = AIManager()

    # =================================================================
    # PHẦN 1: RENDER DANH MỤC FORM
    # =================================================================

    @staticmethod
    def render_item_rows(ctrl, p, items, ai_script, project_name):
        st.markdown("""
            <style>
                div[data-testid="stPopoverBody"] { width: 800px !important; max-width: 90vw !important; }
                textarea { font-family: 'Consolas', monospace !important; font-size: 0.9rem !important; }
            </style>
        """, unsafe_allow_html=True)
        
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda"}
        }
        status_options = list(STATUS_STYLES.keys())
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
                    st.markdown(f"**{form_name}**", help=f"🔗 Link: {s.get('url', 'N/A')}")
                    col_badge, col_script = st.columns([1, 1])
                    with col_badge: render_status_badge(current_status)
                    with col_script:
                        if s.get('has_script'): 
                            st.markdown("<span style='color: #28a745; font-size: 0.75rem; font-weight: bold;'>📜 Đã có kịch bản</span>", unsafe_allow_html=True)
                    st.caption(f"📁 {s['sub_folder']} | 📦 {mod_name}")
                    
                    meta = s.get('metadata', {})
                    if isinstance(meta, dict) and meta.get('form_fields'):
                        fields = [f.get('label') for f in meta['form_fields'][:5] if isinstance(f, dict) and f.get('label')]
                        if fields: st.markdown(f"<div style='font-size: 0.75rem; color: #666; font-style: italic;'>📝 {', '.join(fields)}...</div>", unsafe_allow_html=True)

                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; font-weight: bold; margin-bottom:0;'>TRẠNG THÁI</p>", unsafe_allow_html=True)
                    RenderForm.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                        RenderForm.navigate_to_studio(p, s, "Quay thủ công")
                    
                    with c_auto.popover("🤖", help="AI soạn kịch bản"):
                        # KẾT NỐI CLASS SCRIPT DIALOG TẠI ĐÂY
                        ScriptDialog.render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script)
                    
                    with c_opt.popover("⚙️"):
                        RenderForm.render_extra_options(ctrl, s, idx, len(items), p)

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        current_idx = options.index(current_status) if current_status in options else 0
        new_st = st.selectbox("ST", options, index=current_idx, key=f"st_{s['id']}", label_visibility="collapsed")
        if new_st != current_status:
            if ctrl.update_sub_content(s['id'], new_status=new_st): st.rerun()

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
            if ctrl.delete_sub_content(s['id'], p_folder, s['sub_folder']): st.rerun()

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s
        st.rerun()