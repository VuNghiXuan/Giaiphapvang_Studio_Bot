# import streamlit as st
# import asyncio
# import os
# import json
# import time
# from Bot_GPV.crawle.scrape_giaiphapvang import StructureExtractor
# from models.controller import StudioController # Thêm controller để ghi DB

# def sync_with_db(ctrl, p_id, p_folder):
#     knowledge_path = "knowledge_source.json"
#     if not os.path.exists(knowledge_path):
#         return 0
        
#     with open(knowledge_path, "r", encoding="utf-8") as f:
#         data = json.load(f)
    
#     existing_subs = {s['sub_title']: s['id'] for s in ctrl.get_sub_contents(p_id)}
#     new_count = 0
#     updated_count = 0
    
#     for page_name, info in data.items():
#         module = info.get('module', 'Nghiệp vụ')
#         full_title = f"{module}|{page_name}"
        
#         # Lấy toàn bộ cấu trúc để Bot học
#         structure_data = json.dumps(info.get('structure', {}), ensure_ascii=False)
        
#         if full_title not in existing_subs:
#             # Thêm mới kèm cấu trúc chi tiết
#             ctrl.add_sub_content(p_id, full_title, p_folder, metadata=structure_data)
#             new_count += 1
#         else:
#             # Nếu bài đã có, nhưng cấu trúc Web thay đổi (thêm input mới) -> Cập nhật lại cấu trúc
#             sub_id = existing_subs[full_title]
#             ctrl.update_sub_content_metadata(sub_id, structure_data)
#             updated_count += 1
            
#     return new_count, updated_count

# def render_settings(ctrl): # Nhận thêm tham số ctrl
#     st.header("⚙️ Cấu hình & Cập nhật Hệ thống")
#     st.info("Khi website Giải Pháp Vàng thay đổi (thêm Form, thêm tính năng), hãy chạy chức năng này để Bot cập nhật danh mục hướng dẫn.")

#     # Lấy dự án Giải Pháp Vàng để biết chỗ mà lưu vào DB
#     all_projs = ctrl.get_all_tutorials()
#     gpv_project = next((p for p in all_projs if "giaiphapvang" in p['title'].lower()), None)

#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.subheader("🔑 Thông tin quét (Scraper)")
#         target_url = st.text_input("URL Trang chủ:", value="https://giaiphapvang.net")
#         user_mail = st.text_input("Email đăng nhập:", value="admin@giaiphapvang.net")
#         user_pass = st.text_input("Mật khẩu:", type="password")

#     with col2:
#         st.subheader("🚀 Hành động")
#         st.write("Bot sẽ quét cấu trúc Web và **tự động cập nhật** vào danh sách bài hướng dẫn nếu có thay đổi.")
        
#         if st.button("🔍 CHẠY QUÉT & ĐỒNG BỘ DB", use_container_width=True, type="primary"):
#             if not user_mail or not user_pass:
#                 st.error("Vũ ơi, nhập tài khoản admin mới quét sâu vào các Form được!")
#             elif not gpv_project:
#                 st.error("Không tìm thấy dự án 'Giải Pháp Vàng' trong DB để đồng bộ!")
#             else:
#                 progress_bar = st.progress(0)
#                 status_text = st.empty()
                
#                 async def run_scraper():
#                     try:
#                         status_text.text("🤖 Đang khởi động trình duyệt Playwright...")
#                         # Truyền thẳng user/pass vào Scraper nếu class StructureExtractor có hỗ trợ
#                         extractor = StructureExtractor(output_file="knowledge_source.json")
#                         await extractor.run() 
#                         return True
#                     except Exception as e:
#                         st.error(f"Lỗi khi quét: {str(e)}")
#                         return False

#                 with st.spinner("Bot đang đi tuần tra... Vũ đừng tắt máy nhé!"):
#                     loop = asyncio.new_event_loop()
#                     asyncio.set_event_loop(loop)
#                     success = loop.run_until_complete(run_scraper())
#                     loop.close()
                    
#                 if success:
#                     status_text.text("💾 Đang đối soát và cập nhật Database...")
#                     added = sync_with_db(ctrl, gpv_project['id'], gpv_project['folder_name'])
                    
#                     st.success(f"✅ Đã cập nhật xong! Phát hiện và thêm mới **{added}** mục hướng dẫn.")
#                     progress_bar.progress(100)
#                     time.sleep(2)
#                     st.rerun()

#     st.divider()
    
#     # --- HIỂN THỊ DỮ LIỆU ĐÃ QUÉT ĐƯỢC ---
#     st.subheader("📊 Bản đồ cấu trúc hiện tại (Preview)")
#     if os.path.exists("knowledge_source.json"):
#         with open("knowledge_source.json", "r", encoding="utf-8") as f:
#             current_data = json.load(f)
        
#         st.write(f"📌 Tổng số trang đã vét: **{len(current_data)}**")
        
#         for page_name, info in current_data.items():
#             with st.expander(f"📄 {info.get('module', 'Nghiệp vụ')} > {page_name}"):
#                 c1, c2, c3 = st.columns(3)
                
#                 # Nút bấm
#                 btns = [b['text'] for b in info['structure'].get('buttons', []) if b['text']]
#                 c1.markdown(f"**🔘 Nút ({len(btns)})**")
#                 if btns: c1.json(btns)
                
#                 # Inputs
#                 inputs = [i['label'] for i in info['structure'].get('inputs', []) if i['label']]
#                 c2.markdown(f"**📝 Trường dữ liệu ({len(inputs)})**")
#                 if inputs: c2.json(inputs)
                
#                 # Link con
#                 links = [l['text'] for l in info['structure'].get('links', []) if l['text']]
#                 c3.markdown(f"**🔗 Menu con ({len(links)})**")
#                 if links: c3.json(links)
#     else:
#         st.warning("⚠️ Chưa có file dữ liệu. Nhấn quét để bắt đầu.")