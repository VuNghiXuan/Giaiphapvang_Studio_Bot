import streamlit as st
from config import Config
import json

class AIConfigHandler:
    def get_initial_context(s, mod_name, form_name, ai_handler, p_folder):
        """
        Logic bóc tách metadata ban đầu từ Database - Bản Upgrade by Thanh Vu.
        Hỗ trợ tự động nhận diện và nạp tri thức cho AI Studio.
        """
        # Lấy metadata từ object sub_item (s)
        meta = s.get('metadata')
        
        # 1. KIỂM TRA & PARSE DỮ LIỆU
        # Nếu metadata lưu trong DB là chuỗi JSON, ta cần parse thành dict
        if isinstance(meta, str) and meta.strip():
            try:
                meta = json.loads(meta)
            except Exception as e:
                print(f"⚠️ Lỗi parse JSON Metadata: {e}")
                meta = {}
        
        # Đảm bảo meta là một dictionary sau khi xử lý
        if not isinstance(meta, dict):
            meta = {}

        # 2. KIỂM TRA SỰ TỒN TẠI CỦA TRI THỨC SÂU (Fields)
        if meta.get('form_fields'):
            fields = meta.get('form_fields', [])
            actions_raw = meta.get('actions', [])
            
            # Khởi tạo context với cấu trúc phân cấp rõ ràng để Gemini dễ đọc
            ctx = f"--- DỮ LIỆU THỰC TẾ TỪ HỆ THỐNG (FORM: {form_name}) ---\n"
            ctx += f"- Module: {mod_name}\n"
            ctx += f"- URL truy cập: {s.get('url', 'N/A')}\n"
            ctx += "- Danh sách ô nhập liệu (Fields):\n"
            
            # --- Bóc tách Fields (Tối đa 25 fields để tránh tràn Token) ---
            for f in fields[:25]:
                if isinstance(f, dict) and f.get('label'):
                    label = f.get('label')
                    f_type = f.get('type', 'text')
                    req = "[Bắt buộc]" if f.get('required') else ""
                    ctx += f"   + {label} (Loại: {f_type}) {req}\n"
            
            # --- Bóc tách Actions + Lọc rác (Blacklist) ---
            # Loại bỏ các nút điều hướng giao diện không mang giá trị nghiệp vụ
            BLACK_LIST = ["close", "đóng", "hủy", "cancel", "x", "thoát", "settings", "cài đặt"]
            cleaned_actions = []
            
            for a in actions_raw:
                label = ""
                if isinstance(a, dict):
                    # Ưu tiên lấy Label, nếu không có lấy Text hoặc Selector
                    label = a.get('label') or a.get('text') or a.get('selector', '')
                else:
                    label = str(a)
                
                if label and label.lower() not in BLACK_LIST:
                    cleaned_actions.append(label)

            if cleaned_actions:
                # Chỉ lấy 10 nút quan trọng nhất
                ctx += f"- Nút bấm khả dụng: {', '.join(cleaned_actions[:10])}\n"
            
            return ctx, True
        
        # 3. TRƯỜNG HỢP DỰ PHÒNG (FALLBACK)
        # Nếu Form chưa được "Quét Cấp 2", gọi Handler để lấy thông tin cơ bản
        # Truyền object 's' vào để Handler có thể tự bóc tách thêm nếu cần
        fallback_ctx = ai_handler.get_form_knowledge(s, p_folder, mod_name, form_name)
        return fallback_ctx, False
    
    @staticmethod
    def render_workflow_logic(s, items, ai_handler):
        """Giao diện chọn liên thông và trả về context bổ sung"""
        workflow_ctx = ""
        with st.container(border=True):
            st.markdown("🌐 **Thiết lập luồng liên kết Module/Form**")
            other_forms = [item for item in items if item['id'] != s['id']]
            
            selected_next_forms = st.multiselect(
                "Chọn các Form đích để kết nối nghiệp vụ:",
                options=other_forms,
                format_func=lambda x: f"[{x['sub_title'].split('|')[0]}] -> {x['sub_title'].split('|')[-1]}",
                key=f"wf_target_{s['id']}"
            )

            if selected_next_forms:
                for f in selected_next_forms:
                    f_ctx = ai_handler.get_form_knowledge_from_db(f)
                    workflow_ctx += f"\n\n-- BƯỚC TIẾP THEO: {f['sub_title']} --\n{f_ctx}"
                st.success(f"✅ Đã tích hợp {len(selected_next_forms)} Form.")
        return workflow_ctx