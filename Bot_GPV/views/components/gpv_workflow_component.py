import streamlit as st
import json

class WorkflowBuilder:
    @staticmethod
    def render_workflow_panel(ctrl, ai_handler):
        st.header("🎬 Studio Liên Thông: Kết nối nghiệp vụ")
        
        # 1. Chọn các Form tham gia vào chuỗi kịch bản
        st.subheader("🔗 Bước 1: Chọn chuỗi Form nghiệp vụ")
        all_projects = ctrl.get_all_projects() # Giả sử hàm này tồn tại
        
        # Cho phép chọn nhiều Form từ DB
        selected_forms = st.multiselect(
            "Chọn các Form theo thứ tự xuất hiện trong Video:",
            options=ctrl.get_all_sub_contents_flat(), # Lấy list phẳng của tất cả form
            format_func=lambda x: f"{x['sub_title']} ({x['sub_folder']})",
            key="workflow_select"
        )

        if selected_forms:
            st.divider()
            st.subheader("📝 Bước 2: Cấu hình kịch bản tổng")
            
            with st.expander("🔍 Kiểm tra Tri thức tổng hợp (Multi-Metadata)", expanded=True):
                combined_context = ""
                for i, form in enumerate(selected_forms):
                    # Gọi Bot Biên Tập của ai_handler để lấy context từng form
                    form_ctx = ai_handler.get_form_knowledge_from_db(form)
                    combined_context += f"\n=== GIAI ĐOẠN {i+1}: {form['sub_title']} ===\n"
                    combined_context += form_ctx + "\n"
                
                st.text_area("Context gửi cho AI:", value=combined_context, height=300)

            # 2. Ghi chú luồng nối (Ví dụ: Từ form A bấm nút nào để qua form B)
            user_flow_notes = st.text_area(
                "Mô tả luồng kết nối:", 
                placeholder="Ví dụ: Từ Danh mục chi nhánh, nhấn Thêm mới để vào Form nhập liệu, sau khi lưu thì quay lại danh sách..."
            )

            # 3. Nút bấm sản xuất kịch bản liên thông
            if st.button("🚀 SOẠN KỊCH BẢN LIÊN THÔNG", type="primary"):
                # Gửi combined_context + user_flow_notes cho AI
                # AI lúc này sẽ thấy toàn bộ bức tranh của 2-3 màn hình
                st.info("Đang điều phối kịch bản đa màn hình...")
                # Logic gọi AI tương tự nhưng Prompt sẽ yêu cầu "Workflow Script"