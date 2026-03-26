import streamlit as st
import json
import os
import time
import sys
import asyncio
from playwright.sync_api import sync_playwright

# --- FIX LỖI NotImplementedError TRÊN WINDOWS ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Giả sử class KnowledgeBase này mày để trong file hoặc khai báo ở đây
class KnowledgeBase:
    def __init__(self):
        self.common_info = {
            "brand": "Phần mềm Giải Pháp Vàng (Giaiphapvang.net)",
            "bot_role": "Trợ lý ảo hướng dẫn sử dụng phần mềm chuyên nghiệp"
        }
        self.scenarios = {
            "login_system": {
                "title": "Hướng dẫn Đăng nhập và Truy cập Hệ thống",
                "selectors": {
                    "url": "https://giaiphapvang.net/auth/jwt/sign-in/",
                    "email": "input[name='email']",
                    "password": "input[name='password']",
                    "submit": "button[type='submit']",
                    "btn_he_thong": "internal:role=link[name='Hệ thống'i]",
                }
            },
            "danh_muc_chi_nhanh": {
                "title": "Quản lý Danh mục Chi nhánh",
                "selectors": {
                    "url": "https://giaiphapvang.net/dashboard/", # Link sau khi login
                    "menu": "internal:role=link[name='Danh mục'i]",
                    "sub_menu": "internal:role=link[name='Chi nhánh'i]",
                    "btn_add": "button:has-text('Thêm mới')",
                }
            }
        }

def run_auto_recorder_logic(scenario_data, save_path):
    """ Robot thực hiện hành động dựa trên kịch bản KnowledgeBase """
    selectors = scenario_data.get('selectors', {})
    url = selectors.get('url')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            record_video_dir=save_path,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        # 1. Đi đến trang web
        page.goto(url, wait_until="networkidle")
        time.sleep(1)

        # 2. Thực hiện hành động tự động dựa trên kịch bản
        try:
            if "email" in selectors and "password" in selectors:
                st.write("⌨️ Đang tự động điền thông tin đăng nhập...")
                page.fill(selectors['email'], "demo@giaiphapvang.net") # Vũ đổi mail thật nhé
                time.sleep(0.5)
                page.fill(selectors['password'], "123456") 
                time.sleep(0.5)
                page.click(selectors['submit'])
                page.wait_for_load_state("networkidle")
            
            if "menu" in selectors:
                st.write("🖱️ Đang bấm mở menu Danh mục...")
                page.click(selectors['menu'])
                time.sleep(1)
                
            if "sub_menu" in selectors:
                page.click(selectors['sub_menu'])
                time.sleep(1)

        except Exception as e:
            st.error(f"Robot kẹt ở bước nào đó: {e}")

        time.sleep(2) # Đợi tí để video ghi lại kết quả cuối
        context.close()
        video_path = page.video.path()
        browser.close()
        return video_path

def render_auto_recorder(sub_path):
    st.header("🤖 Robot Quay Phim (Theo Kịch Bản)")
    
    kb = KnowledgeBase()
    scenarios = kb.scenarios
    
    # Danh sách các bài hướng dẫn từ kịch bản
    scenario_keys = list(scenarios.keys())
    
    # Đồng bộ với Dashboard
    active_mod = st.session_state.get('active_module', "")
    default_idx = 0
    # Logic tìm kịch bản khớp với module đang chọn
    for i, key in enumerate(scenario_keys):
        if active_mod.lower() in key.lower():
            default_idx = i
            break

    selected_key = st.selectbox(
        "Chọn kịch bản hướng dẫn:", 
        scenario_keys, 
        index=default_idx,
        format_func=lambda x: scenarios[x]['title']
    )

    if selected_key:
        scene = scenarios[selected_key]
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🎬 **Kịch bản:** {scene['title']}")
            st.write(f"🔗 **URL khởi đầu:** {scene['selectors']['url']}")
            
        with col2:
            st.info("💡 **Robot sẽ làm:**")
            for action in scene['selectors'].keys():
                if action != 'url':
                    st.write(f"- Thực hiện: {action}")

        st.divider()

        if st.button("🎬 BẮT ĐẦU QUAY THEO KỊCH BẢN", use_container_width=True, type="primary"):
            raw_folder = os.path.join(sub_path, "raw")
            if not os.path.exists(raw_folder): os.makedirs(raw_folder)

            with st.status("🚀 Robot đang 'diễn' theo kịch bản...", expanded=True) as status:
                try:
                    temp_video_path = run_auto_recorder_logic(scene, raw_folder)
                    
                    final_path = os.path.join(raw_folder, f"{selected_key}.webm")
                    if os.path.exists(final_path): os.remove(final_path)
                    os.rename(temp_video_path, final_path)
                    
                    status.update(label="✅ Đã quay xong theo kịch bản!", state="complete")
                    st.success(f"Video lưu tại: {final_path}")
                except Exception as e:
                    st.error(f"Lỗi: {e}")
                    status.update(label="❌ Thất bại", state="error")