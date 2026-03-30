import streamlit as st

class AIConfigHandler:
    @staticmethod
    def get_initial_context(s, mod_name, form_name, ai_handler, p_folder):
        """Logic bóc tách metadata ban đầu (giữ nguyên logic bóc tách của Vũ)"""
        meta = s.get('metadata')
        if isinstance(meta, dict) and meta.get('form_fields'):
            fields = meta.get('form_fields', [])
            actions_raw = meta.get('actions', [])
            ctx = f"DỮ LIỆU THỰC TẾ TỪ HỆ THỐNG (FORM: {form_name}):\n- Link: {s.get('url', 'N/A')}\n"
            ctx += "- Các trường dữ liệu tìm thấy:\n"
            for f in fields:
                if isinstance(f, dict):
                    req = "(Bắt buộc)" if f.get('required') else ""
                    ctx += f"  + {f.get('label', 'Không tên')} ({f.get('type', 'text')}) {req}\n"
            
            cleaned_actions = [a.get('label', a.get('selector', 'Nút')) if isinstance(a, dict) else str(a) for a in actions_raw]
            if cleaned_actions:
                ctx += f"- Thao tác khả dụng: {', '.join(cleaned_actions)}\n"
            return ctx, True
        return ai_handler.get_form_knowledge(p_folder, mod_name, form_name), False

    @staticmethod
    def render_workflow_logic(s, items, ai_handler):
        """Xử lý UI chọn form liên thông và trả về context bổ sung"""
        workflow_ctx = ""
        with st.container(border=True):
            st.markdown("🌐 **Thiết lập luồng liên kết Module/Form**")
            other_forms = [item for item in items if item['id'] != s['id']]
            selected_next_forms = st.multiselect(
                "Chọn các Form đích để kết nối:",
                options=other_forms,
                format_func=lambda x: f"[{x['sub_title'].split('|')[0]}] -> {x['sub_title'].split('|')[-1]}",
                key=f"wf_target_{s['id']}"
            )
            if selected_next_forms:
                for f in selected_next_forms:
                    f_ctx = ai_handler.get_form_knowledge_from_db(f)
                    workflow_ctx += f"\n\n-- BƯỚC TIẾP THEO: {f['sub_title']} --\n{f_ctx}"
                st.success(f"✅ Đã gộp tri thức của {len(selected_next_forms)} Form.")
        return workflow_ctx