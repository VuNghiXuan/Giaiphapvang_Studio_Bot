import streamlit as st
import asyncio
import os
import json
import time
from core.scrape_giaiphapvang import StructureExtractor

def render_settings():
    st.header("⚙️ Cấu hình & Cập nhật Hệ thống")
    st.info("Vì hệ thống đang phát triển, hãy chạy chức năng này khi giao diện web Giải Pháp Vàng có sự thay đổi.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔑 Thông tin quét (Scraper)")
        # Cho phép sửa URL nếu dev đổi domain
        target_url = st.text_input("URL Trang chủ:", value="https://giaiphapvang.net")
        user_mail = st.text_input("Email quét mẫu:", value=os.getenv("USER_EMAIL", ""))
        user_pass = st.text_input("Password quét mẫu:", type="password", value=os.getenv("USER_PASSWORD", ""))

    with col2:
        st.subheader("🚀 Hành động")
        st.write("Bot sẽ tự động đi qua các phân hệ (Kế toán, Mua bán...) để 'vét' sạch cấu trúc nút và trường dữ liệu.")
        
        if st.button("🔍 CHẠY QUÉT TOÀN BỘ CẤU TRÚC WEB", use_container_width=True, type="primary"):
            if not user_mail or not user_pass:
                st.error("Vũ ơi, nhập tài khoản mới quét được chứ!")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                async def run_scraper():
                    try:
                        status_text.text("🤖 Đang khởi động trình duyệt...")
                        # Truyền thẳng thông tin từ GUI vào Scraper
                        extractor = StructureExtractor(output_file="knowledge_source.json")
                        
                        # Chạy hàm quét chính
                        await extractor.run() 
                        return True
                    except Exception as e:
                        st.error(f"Lỗi khi quét: {str(e)}")
                        return False

                with st.spinner("Bot đang đi tuần tra các trang... Đừng tắt ứng dụng nhé!"):
                    # Xử lý chạy async trong thread an toàn cho Streamlit
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(run_scraper())
                    loop.close()
                    
                if success:
                    st.success("✅ Đã cập nhật file knowledge_source.json thành công!")
                    progress_bar.progress(100)
                    time.sleep(1)
                    st.rerun() # Tải lại trang để cập nhật bảng dữ liệu bên dưới
                    
    st.divider()
    
    # --- HIỂN THỊ DỮ LIỆU ĐÃ QUÉT ĐƯỢC ---
    st.subheader("📊 Bản đồ cấu trúc hiện tại")
    if os.path.exists("knowledge_source.json"):
        with open("knowledge_source.json", "r", encoding="utf-8") as f:
            current_data = json.load(f)
        
        # Thống kê nhanh
        st.write(f"📌 Đã quét được: **{len(current_data)}** trang nghiệp vụ.")
        
        for page_name, info in current_data.items():
            # Gom nhóm theo App để dễ nhìn (ví dụ: App_Kế Toán, App_Mua Bán)
            with st.expander(f"📄 {page_name}"):
                st.caption(f"🔗 Link: {info['url']}")
                
                c1, c2, c3 = st.columns(3)
                
                # Nút bấm
                btns = [b['text'] for b in info['structure'].get('buttons', []) if b['text']]
                c1.markdown(f"**🔘 Nút bấm ({len(btns)})**")
                if btns: c1.json(btns)
                else: c1.write("Không tìm thấy")
                
                # Inputs
                inputs = [i['label'] for i in info['structure'].get('inputs', []) if i['label']]
                c2.markdown(f"**📝 Trường dữ liệu ({len(inputs)})**")
                if inputs: c2.json(inputs)
                else: c2.write("Không tìm thấy")
                
                # Links/Menus
                links = [l['text'] for l in info['structure'].get('links', []) if l['text']]
                c3.markdown(f"**🔗 Menu con ({len(links)})**")
                if links: c3.json(links)
                else: c3.write("Không tìm thấy")
    else:
        st.warning("⚠️ Chưa có file dữ liệu cấu trúc. Hãy nhấn nút 'Chạy Quét' ở trên.")