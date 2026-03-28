import streamlit as st
import os
from config import Config
from ..utils_dashboad.utils import get_status_info
# from .utils_dashboad.gpv_handler import render_gpv_logic

def render_item_rows(ctrl, p, items):
    """Render từng dòng bài học/form"""
    status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    dots = {"Chưa quay": "🔴", "Đã quay": "🟡", "Hoàn chỉnh": "🟢"}
    
    for idx, s in enumerate(items):
        sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
        current_status = get_status_info(sub_path, s.get('status'))
        clean_name = s['sub_title'].split('|')[-1]

        with st.container(border=True):
            c_name, c_status, c_man, c_auto, c_opt = st.columns([2.5, 1.2, 0.8, 0.8, 0.5])
            c_name.markdown(f"**{clean_name}**")
            
            with c_status:
                new_st = st.selectbox("ST", status_options, label_visibility="collapsed",
                                      index=status_options.index(current_status) if current_status in status_options else 0,
                                      key=f"st_{s['id']}")
                if new_st != s.get('status'):
                    ctrl.update_sub_content(s['id'], s['sub_title'], new_st); st.rerun()

            if c_man.button("🎥", key=f"m_{s['id']}"):
                st.session_state.active_project, st.session_state.active_sub = p, s
                st.session_state.view, st.session_state.active_tab = "studio", "Quay thủ công"; st.rerun()

            if c_auto.button("🤖", key=f"a_{s['id']}"):
                st.session_state.active_project, st.session_state.active_sub = p, s
                st.session_state.view, st.session_state.active_tab = "studio", "Quay tự động 🤖"; st.rerun()
            
            with c_opt.popover("⚙️"):
                if st.button("🔼", key=f"up_{s['id']}", disabled=(idx==0)):
                    ctrl.move_sub_content(s['id'], "up"); st.rerun()
                if st.button("🔽", key=f"dn_{s['id']}", disabled=(idx==len(items)-1)):
                    ctrl.move_sub_content(s['id'], "down"); st.rerun()
                if st.button("🗑️ XÓA", key=f"del_{s['id']}", type="primary"):
                    ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder']); st.rerun()