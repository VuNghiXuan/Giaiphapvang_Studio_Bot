import streamlit as st
import os
import time
import sys
import asyncio
from dotenv import load_dotenv # Thêm để load tài khoản
from playwright.sync_api import sync_playwright

# Load biến môi trường từ .env (Vũ đảm bảo file .env nằm ở thư mục gốc nhé)
load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def run_auto_recorder_by_scenario(scenario, save_path):
    selectors = scenario.get('selectors', {})
    url = selectors.get('url')
    
    # Lấy tài khoản từ .env giống file scrape của mày
    email_env = os.getenv("USER_EMAIL")
    pass_env = os.getenv("USER_PASSWORD")

    with sync_playwright() as p:
        # headless=False để Vũ xem Robot diễn
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            record_video_dir=save_path,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        try:
            st.write(f"🌐 Đang truy cập: {url}")
            # FIX TIMEOUT: Dùng 'domcontentloaded' thay vì 'networkidle' cho bớt khắt khe
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Nghỉ tay 2 giây cho trang ổn định (giống kiểu chờ của con người)
            time.sleep(2)

            # 2. Tự động thực hiện các bước dựa trên kịch bản
            if "email" in selectors and email_env:
                st.write("⌨️ Đang tự động điền Email từ hệ thống...")
                page.wait_for_selector(selectors['email'], timeout=10000)
                page.fill(selectors['email'], email_env)
                time.sleep(0.5)
                
            if "password" in selectors and pass_env:
                st.write("⌨️ Đang điền Password bảo mật...")
                page.fill(selectors['password'], pass_env)
                time.sleep(0.5)
                
            if "submit" in selectors:
                st.write("🖱️ Đang bấm Đăng nhập...")
                page.click(selectors['submit'])
                # Sau khi bấm submit, đợi trang chuyển hướng xong
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3) # Đợi Dashboard hiện ra rõ ràng để quay phim
            
            # Thực hiện các bước click menu tiếp theo nếu có trong kịch bản
            for key in ["menu", "sub_menu", "btn_add"]:
                if key in selectors:
                    st.write(f"🤖 Robot đang tìm và bấm: {key}...")
                    page.wait_for_selector(selectors[key], timeout=5000)
                    page.click(selectors[key])
                    time.sleep(1.5)

            # Diễn thêm một chút: cuộn trang cho video sinh động
            page.mouse.wheel(0, 500)
            time.sleep(2)

        except Exception as e:
            st.warning(f"⚠️ Robot gặp chút vấn đề khi thao tác: {str(e)}")

        context.close()
        video_path = page.video.path()
        browser.close()
        return video_path

def render_auto_recorder(sub_path, kb_instance):
    st.header("🤖 Robot Quay Phim (Theo Kịch Bản)")
    
    # Kiểm tra biến môi trường trước khi bắt đầu
    if not os.getenv("USER_EMAIL") or not os.getenv("USER_PASSWORD"):
        st.warning("⚠️ Vũ ơi, chưa thấy USER_EMAIL/PASSWORD trong file .env. Robot sẽ không tự đăng nhập được đâu!")

    scenarios = kb_instance.scenarios
    scenario_keys = list(scenarios.keys())

    selected_key = st.selectbox(
        "🎯 Chọn kịch bản để Robot thực thi:",
        scenario_keys,
        format_func=lambda x: scenarios[x].get('title', x)
    )

    if selected_key:
        current_scene = scenarios[selected_key]
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🎬 **Kịch bản:** {current_scene.get('title')}")
            st.info(f"🔗 URL: {current_scene['selectors'].get('url')}")
        
        with col2:
            st.write("🎙️ **Lời thoại AI thuyết minh:**")
            script_text = st.text_area("Nội dung thuyết minh:", 
                                     value=f"Chào mừng các bạn, hôm nay Robot sẽ hướng dẫn bài: {current_scene.get('title')}.", 
                                     height=100)

        st.divider()

        if st.button("🎬 KÍCH HOẠT ROBOT DIỄN THẬT", use_container_width=True, type="primary"):
            raw_folder = os.path.join(sub_path, "raw")
            if not os.path.exists(raw_folder):
                os.makedirs(raw_folder)

            with st.status("🚀 Robot đang làm việc...", expanded=True) as status:
                try:
                    st.write("📽️ Khởi động máy quay...")
                    temp_video = run_auto_recorder_by_scenario(current_scene, raw_folder)
                    
                    final_name = f"raw_{selected_key}.webm"
                    final_path = os.path.join(raw_folder, final_name)
                    
                    if os.path.exists(final_path): os.remove(final_path)
                    os.rename(temp_video, final_path)
                    
                    status.update(label="✅ Đã quay xong video kịch bản!", state="complete")
                    st.success(f"📺 Lưu tại: {final_path}")
                except Exception as e:
                    st.error(f"Lỗi: {str(e)}")
                    status.update(label="❌ Thất bại", state="error")