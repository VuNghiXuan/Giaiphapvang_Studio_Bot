import streamlit as st
import json
import os
import time

def render_auto_recorder(sub_path):
    st.header("🤖 Robot Quay Phim Tự Động")
    
    if not os.path.exists("knowledge_source.json"):
        st.error("⚠️ Vũ ơi, chưa có file kiến thức web! Qua tab 'Cấu hình Web' quét trước nhé.")
        return

    with open("knowledge_source.json", "r", encoding="utf-8") as f:
        kb_data = json.load(f)

    # DANH SÁCH BÀI HƯỚNG DẪN (Lấy từ các App đã quét)
    st.subheader("🎯 Chọn kịch bản hướng dẫn")
    pages = list(kb_data.keys())
    
    # Combobox chọn trang/luồng
    selected_page = st.selectbox("Chọn trang nghiệp vụ (App) muốn hướng dẫn:", pages)

    if selected_page:
        info = kb_data[selected_page]
        
        # Hiển thị thông tin luồng
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"🌐 **URL:** {info['url']}")
            st.write(f"📝 Ô nhập liệu: {len(info['structure'].get('inputs', []))}")
            st.write(f"🔘 Nút bấm: {len(info['structure'].get('buttons', []))}")
            
        with col2:
            st.write("🎙️ **Kịch bản lồng tiếng:**")
            voice_text = st.text_area("AI sẽ nói gì:", value=f"Chào mừng bạn đến với hướng dẫn {selected_page}...")

        # NÚT BẮT ĐẦU QUAY TỰ ĐỘNG
        if st.button("🚀 BẮT ĐẦU XUẤT VIDEO TỰ ĐỘNG", use_container_width=True, type="primary"):
            st.warning("Bot đang khởi động trình duyệt... Vũ vui lòng không chạm vào máy!")
            # Sau này mình sẽ gọi hàm 'auto_playwright_executor' ở đây
            with st.status("Bot đang 'diễn' trên trình duyệt...", expanded=True) as status:
                st.write("Mở trình duyệt Playwright...")
                time.sleep(1)
                st.write(f"Đang tự động thao tác trên {selected_page}...")
                time.sleep(2)
                status.update(label="✅ Đã quay và lưu video thành công!", state="complete")