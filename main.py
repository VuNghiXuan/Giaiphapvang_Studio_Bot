import streamlit as st
import os
import time
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

# Import các cấu hình và Controller
from models.controller import StudioController
from config import Config
from core.ai_manager import AIManager

# Import các View cốt lõi
from views.dashboard_view import render_dashboard
from views.recorder_view import render_recorder
from views.editor_view import render_editor
from core.auto_knowledge_base import KnowledgeBase 

# --- 0. KHỞI TẠO HỆ THỐNG ---
load_dotenv()
ctrl = StudioController()

@st.cache_resource
def get_ai_manager():
    return AIManager()

ai_studio = get_ai_manager()

def main():
    st.set_page_config(
        page_title="Giaiphapvang Studio", 
        layout="wide", 
        page_icon="🎬"
    )

    # --- 1. CSS CUSTOM: GIAO DIỆN CHUYÊN NGHIỆP ---
    st.markdown("""
        <style>
        .stApp { background-color: #f8f9fa; }
        h1, h2, h3 { color: #217346 !important; }
        
        /* Nút bấm Xanh Excel */
        .stButton > button {
            border-radius: 6px;
            background-color: #217346;
            color: white;
            transition: 0.3s all;
        }
        .stButton > button:hover {
            background-color: #d4af37;
            border-color: #d4af37;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 2. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
    if "view" not in st.session_state: 
        st.session_state.view = "dashboard"
    if "active_project" not in st.session_state: 
        st.session_state.active_project = None 
    if "active_sub" not in st.session_state: 
        st.session_state.active_sub = None 
    
    # Quan trọng: active_tab phải khớp với tên trong list titles bên dưới
    if 'active_tab' not in st.session_state: 
        st.session_state.active_tab = "Quay thủ công"

    # ==========================================
    # VIEW 1: DASHBOARD (TỔNG KHO DẠNG CÂY)
    # ==========================================
    if st.session_state.view == "dashboard":
        render_dashboard(ctrl)

    # ==========================================
    # VIEW 2: STUDIO (KHÔNG GIAN LÀM VIỆC)
    # ==========================================
    elif st.session_state.view == "studio":
        p = st.session_state.active_project
        s = st.session_state.active_sub
        sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])

        # --- SIDEBAR: ĐIỀU KHIỂN ---
        with st.sidebar:
            st.success(f"📁 Dự án: **{p['title']}**")
            st.info(f"📹 Bài: **{s['sub_title']}**")
            
            if st.button("⬅️ THOÁT STUDIO", use_container_width=True, type="primary"):
                st.session_state.view = "dashboard"
                st.rerun()
            
            st.divider()
            st.markdown("### 🎙️ Giọng đọc AI")
            VOICE_OPTIONS = {
                "Hoài My (Sang trọng)": "vi-VN-HoaiMyNeural",
                "Nam Minh (Trầm ấm)": "vi-VN-NamMinhNeural"
            }
            sel_voice = st.selectbox("Chọn giọng:", list(VOICE_OPTIONS.keys()))
            st.session_state.selected_voice_id = VOICE_OPTIONS[sel_voice]

            st.markdown("### ⚙️ AI Brain")
            providers = ["Groq", "Gemini", "Ollama"]
            current_p = str(ai_studio.provider).capitalize()
            default_idx = providers.index(current_p) if current_p in providers else 1
            
            new_p = st.selectbox("Chọn não:", providers, index=default_idx)
            if new_p.lower() != str(ai_studio.provider).lower():
                ai_studio.provider = new_p.lower()
                st.rerun()

        # --- STUDIO TABS: CẬP NHẬT 4 BƯỚC ---
        # Tên Tab phải khớp 100% với tên mày set ở Dashboard
        titles = ["Quay thủ công", "Quay tự động 🤖", "Biên tập AI", "Kho thành phẩm"]
        icons = ["camera-video", "robot", "magic", "archive"]
        
        # Logic nhảy Tab: Tìm vị trí của Tab hiện tại trong danh sách titles
        try:
            curr_idx = titles.index(st.session_state.active_tab)
        except ValueError:
            curr_idx = 0

        selected = option_menu(
            menu_title=None,
            options=titles,
            icons=icons,
            orientation="horizontal",
            default_index=curr_idx,
            styles={
                "container": {"padding": "0px", "border-bottom": "2px solid #217346"},
                "nav-link-selected": {"background-color": "#217346"},
            }
        )
        # Cập nhật lại state khi người dùng click tay trên tab
        st.session_state.active_tab = selected

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ĐIỀU HƯỚNG NỘI DUNG TỪNG TAB ---
        # 2. Khởi tạo một đối tượng (instance) từ class đó
        kb = KnowledgeBase()
        
        if selected == titles[0]:
            # QUAY THỦ CÔNG (Code cũ của Vũ)
            render_recorder(sub_path)
            
        elif selected == titles[1]:
            # QUAY TỰ ĐỘNG (Tab Robot mới)
            try:
                from views.auto_recorder_view import render_auto_recorder
                render_auto_recorder(sub_path, kb)
            except ImportError:
                st.error("Chưa tìm thấy file views/auto_recorder_view.py!")
            
        elif selected == titles[2]:
            render_editor(ai_studio, sub_path)
            
        elif selected == titles[3]:
            st.subheader(f"📦 Thành phẩm: {s['sub_title']}")
            output_dir = os.path.join(sub_path, "outputs")
            if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
            
            files = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
            if not files:
                st.info("Chưa có video. Hãy sang tab Biên tập để xuất video!")
            else:
                cols = st.columns(2)
                for i, file in enumerate(files):
                    with cols[i % 2]:
                        st.video(os.path.join(output_dir, file))
                        st.caption(f"🎬 {file}")

if __name__ == "__main__":
    main()