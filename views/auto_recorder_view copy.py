import streamlit as st
import os
import asyncio
import sys
from dotenv import load_dotenv

# Import các module cốt lõi của Vũ
from core.browser_agent import BrowserAgent
from core.ai_manager import AIManager

import nest_asyncio
nest_asyncio.apply() # Chống lỗi loop cho Streamlit trên Windows

# Load biến môi trường
load_dotenv()

def render_auto_recorder(sub_path, kb_instance):
    st.header("🎬 Giaiphapvang Studio Bot")
    st.caption("Robot tự động thực hiện thao tác và AI biên soạn video lồng tiếng.")

    if 'agent' not in st.session_state:
        st.session_state.agent = BrowserAgent()
    if 'ai_manager' not in st.session_state:
        st.session_state.ai_manager = AIManager()

    agent = st.session_state.agent
    ai_studio = st.session_state.ai_manager
    
    scenarios = kb_instance.scenarios
    scenario_keys = list(scenarios.keys())

    selected_key = st.selectbox(
        "🎯 Chọn quy trình hướng dẫn:",
        scenario_keys,
        format_func=lambda x: scenarios[x].get('title', x)
    )

    if selected_key:
        scene = scenarios[selected_key]
        # Lấy danh sách các bước thao tác (Selectors)
        steps_list = scene.get('selectors', []) 
        
        # --- HIỂN THỊ THÔNG TIN (Đã dọn dẹp trùng lặp) ---
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🎥 **Kịch bản:** {scene.get('title', 'Không tiêu đề')}")
            url_root = scene.get('url', 'Chưa xác định')
            st.write(f"🌐 **Trang gốc:** {url_root}")
            
        with col2:
            st.info("🤖 **Lộ trình Robot:**")
            st.write(f"🔢 Số bước thao tác: **{len(steps_list)} bước**")
            st.caption("Mở trình duyệt -> Tự động thao tác -> AI lồng tiếng")

        st.divider()
        video_area = st.empty()

        if st.button("🚀 BẮT ĐẦU SẢN XUẤT (AUTO STUDIO)", use_container_width=True, type="primary"):
            email_login = os.getenv("USER_EMAIL")
            pass_login = os.getenv("USER_PASSWORD")

            if not email_login or not pass_login:
                st.error("⚠️ Vũ ơi, file .env thiếu thông tin đăng nhập!")
                return

            # --- LOGIC KHỚP LỆNH THÔNG MINH ---
            # Chuyển đổi các bước từ KB sang định dạng Agent hiểu được
            final_script = []
            
            # Bước 1: Luôn luôn là đi tới trang gốc
            final_script.append({"action": "goto", "selector": url_root, "description": "Truy cập Giải Pháp Vàng"})

            # Bước 2: Duyệt qua các selectors trong KB để map dữ liệu
            for step in steps_list:
                target = step.get('target', '')
                action = step.get('action', 'click')
                name = step.get('name', 'Thao tác')

                # Logic lấy value thông minh
                val = None
                if action == "fill":
                    if "email" in target.lower(): val = email_login
                    elif "password" in target.lower() or "pass" in target.lower(): val = pass_login
                
                # FIX LỖI float(None): 
                # Nếu là bước 'wait', hãy đảm bảo 'value' là một con số (giây) hoặc chuỗi rỗng, đừng để None
                if action == "wait":
                    val = str(step.get('timeout', 5000)) # Mặc định chờ 5s nếu không ghi gì

                final_script.append({
                    "action": action,
                    "selector": target,
                    "value": val,  # Bây giờ val đã là string hoặc number, không còn None
                    "description": name
                })

            async def start_process():
                with st.status("🛠️ Studio đang xử lý...", expanded=True) as status:
                    st.write("🎬 Robot đang thực hiện thao tác...")
                    # Truyền final_script đã được xử lý vào Agent
                    video_raw, action_logs = await agent.run_scenario(selected_key, final_script)
                    
                    if not video_raw:
                        st.error("Lỗi: Không quay được video.")
                        return

                    st.write("🤖 AI đang biên soạn lời thoại chuyên nghiệp...")
                    refined_segments = ai_studio.rewrite_segments(action_logs, selected_key)
                    
                    st.write("🎙️ Đang lồng tiếng Hoài My và render...")
                    output_final = os.path.join(sub_path, f"{selected_key}_STUDIO.mp4")
                    
                    success = ai_studio.export_final_video(
                        video_path=video_raw,
                        script_segments=refined_segments,
                        output_path=output_final
                    )

                    if success:
                        status.update(label="✅ ĐÃ XONG! Video cực nuột Vũ ơi.", state="complete")
                        st.balloons()
                        video_area.video(output_final)
                    else:
                        st.error("Render video thất bại.")

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_process())
            except Exception as e:
                # Nếu loop cũ đang chạy thì dùng chính nó
                asyncio.run(start_process())