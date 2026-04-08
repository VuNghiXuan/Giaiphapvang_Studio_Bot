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
    def render_item_rows(ctrl, p, items, ai_script, project_name):
        # 1. Inject CSS để tùy chỉnh giao diện (Popover rộng hơn cho dễ soạn kịch bản)
        st.markdown("""
            <style>
                div[data-testid="stPopoverBody"] { width: 850px !important; max-width: 95vw !important; }
                .form-card { border-left: 6px solid #ccc; transition: 0.3s; }
                .form-card:hover { transform: translateX(5px); }
            </style>
        """, unsafe_allow_html=True)
        
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa", "icon": "⚪"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff", "icon": "🔵"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda", "icon": "🟢"}
        }
        
        status_options = list(STATUS_STYLES.keys())
        p_folder = p.get('folder_name') or project_name

        for idx, s in enumerate(items):
            # 2. Xử lý trạng thái dựa trên Logic thực tế + DB
            # Sử dụng Config.get_path để lấy đường dẫn chuẩn Pathlib
            sub_folder = s.get('sub_folder') or f"Form_{s['id']}"
            current_status = get_status_info(p_folder, sub_folder, s.get('status'))
            
            # Tách tên Module và Form
            parts = s['sub_title'].split('|')
            mod_name = parts[0] if len(parts) > 1 else "General"
            form_name = parts[-1]
            
            style = STATUS_STYLES.get(current_status, STATUS_STYLES["Chưa quay"])

            # 3. Vẽ Card cho từng Form
            with st.container(border=True):
                # Border-left màu theo trạng thái
                st.markdown(f"""
                    <style>
                        div[data-testid="stVerticalBlock"] > div:has(input[key="st_{s['id']}"]) {{
                            border-left: 6px solid {style['color']} !important;
                            background-color: {style['bg']};
                        }}
                    </style>
                """, unsafe_allow_html=True)

                col_info, col_status, col_actions = st.columns([3.5, 1.2, 2.5])
                
                with col_info:
                    st.markdown(f"**{form_name}**", help=f"🔗 Link: {s.get('url', 'N/A')}")
                    
                    c_badge, c_script = st.columns([1, 1])
                    with c_badge: 
                        render_status_badge(current_status)
                    with c_script:
                        # Kiểm tra xem file JSON kịch bản có tồn tại thực tế không
                        metadata_path = Config.get_path(app=p_folder, module=sub_folder, asset_type="metadata")
                        has_script_file = (metadata_path / "latest_script.json").exists()
                        if has_script_file: 
                            st.markdown("<span style='color: #28a745; font-size: 0.75rem; font-weight: bold;'>📜 Đã có kịch bản</span>", unsafe_allow_html=True)
                    
                    st.caption(f"📁 {sub_folder} | 📦 {mod_name}")
                    
                    # Hiển thị Preview các trường (fields) từ Metadata Omni 2026
                    meta = s.get('metadata', {})
                    if isinstance(meta, str):
                        try: meta = json.loads(meta)
                        except: meta = {}
                    
                    # Bóc tách fields từ cấu trúc layout/active_form
                    fields = []
                    layout = meta.get('layout', {})
                    active_form = layout.get('active_form', {})
                    inputs = active_form.get('inputs') if active_form else layout.get('main_content', {}).get('inputs', [])
                    
                    if inputs:
                        fields = [f.get('label') for f in inputs[:5] if isinstance(f, dict) and f.get('label')]
                        if fields: 
                            st.markdown(f"<div style='font-size: 0.75rem; color: #666; font-style: italic;'>📝 {', '.join(fields)}...</div>", unsafe_allow_html=True)

                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; font-weight: bold; margin-bottom:0;'>TRẠNG THÁI</p>", unsafe_allow_html=True)
                    RenderForm.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Vào Studio quay/biên tập"):
                        RenderForm.navigate_to_studio(p, s, "Quay thủ công")
                    
                    # Nút AI soạn kịch bản - Popover rộng
                    with c_auto.popover("🤖", help="AI soạn kịch bản tự động"):
                        ScriptDialog.render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script)
                    
                    # Các tùy chọn phụ
                    with c_opt.popover("⚙️"):
                        RenderForm.render_extra_options(ctrl, s, idx, len(items), p)

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        try:
            current_idx = options.index(current_status)
        except:
            current_idx = 0
            
        new_st = st.selectbox("ST", options, index=current_idx, key=f"st_{s['id']}", label_visibility="collapsed")
        if new_st != current_status:
            # Cập nhật trạng thái vào Database
            if ctrl.update_sub_content(sub_id=s['id'], status=new_st):
                st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p):
        st.markdown("**Sắp xếp & Xóa**")
        c1, c2 = st.columns(2)
        if c1.button("🔼", disabled=(idx==0), key=f"u_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "up")
            st.rerun()
        if c2.button("🔽", disabled=(idx==total-1), key=f"d_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "down")
            st.rerun()
        
        st.divider()
        p_folder = p.get('folder_name', "")
        if st.button("🗑️ XÓA FORM", type="primary", use_container_width=True, key=f"del_{s['id']}"):
            if ctrl.delete_sub_content(s['id'], p_folder, s.get('sub_folder')): 
                st.rerun()

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s
        st.rerun()

# ------------------- CÁC HÀM BỔ TRỢ CHUẨN PATHLIB -------------------

def get_status_info(app_folder, sub_folder, manual_status=None):
    """
    Kiểm tra trạng thái dựa trên thực tế folder storage.
    """
    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    if manual_status in status_list: 
        return manual_status
        
    # Lấy đường dẫn bằng Config chuẩn
    raw_dir = Config.get_path(app=app_folder, module=sub_folder, asset_type="raw")
    output_dir = Config.get_path(app=app_folder, module=sub_folder, asset_type="outputs")
    
    # Check Hoàn chỉnh: Có file mp4 trong outputs
    if output_dir.exists() and any(f.suffix == '.mp4' for f in output_dir.glob("*")):
        return "Hoàn chỉnh"
    
    # Check Đã quay: Có bất kỳ file video nào trong raw (.webm, .mp4)
    if raw_dir.exists() and any(f.suffix in ['.mp4', '.webm'] for f in raw_dir.glob("*")):
        return "Đã quay"
        
    return "Chưa quay"

def render_status_badge(status):
    colors = {
        "Chưa quay": "#808080",
        "Đã quay": "#007bff",
        "Hoàn chỉnh": "#28a745"
    }
    color = colors.get(status, "#808080")
    st.markdown(f"""
        <span style="background-color: {color}; color: white; padding: 2px 10px; 
        border-radius: 12px; font-size: 0.7rem; font-weight: bold; white-space: nowrap;">
            {status.upper()}
        </span>
    """, unsafe_allow_html=True)