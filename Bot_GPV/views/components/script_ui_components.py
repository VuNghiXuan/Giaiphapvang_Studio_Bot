import streamlit as st

class ScriptUIComponents:
    @staticmethod
    def render_ai_brain_config(s):
        """Render bộ chọn Model và Giọng đọc"""
        st.markdown("### 🧠 Cấu hình Bộ não AI")
        col1, col2, col3 = st.columns([1.5, 1.5, 1.2])
        
        providers = ["Groq", "Gemini", "Ollama"]
        sel_provider = col1.selectbox("Nhà cung cấp:", providers, key=f"prov_{s['id']}")

        if sel_provider == "Gemini":
            models = ["gemini-1.5-flash", "gemini-2.0-flash"]
            sel_model = col2.selectbox("Bộ não AI:", models, key=f"mdl_{s['id']}")
        elif sel_provider == "Groq":
            models = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
            sel_model = col2.selectbox("Bộ não AI:", models, key=f"mdl_{s['id']}")
        else:
            sel_model = col2.text_input("Model Ollama:", value="qwen2.5:3b", key=f"mdl_{s['id']}")

        voice_map = {"Hoài My (Nữ)": "vi-VN-HoaiMyNeural", "Nam Minh (Nam)": "vi-VN-NamMinhNeural"}
        sel_voice_label = col3.selectbox("Giọng đọc:", list(voice_map.keys()), key=f"voc_{s['id']}")
        
        return sel_provider, sel_model, voice_map[sel_voice_label]

    @staticmethod
    def render_workflow_selector(ctrl, p, s):
        """Giao diện chọn nối cảnh tiếp theo"""
        with st.expander("📄 Tùy chỉnh Workflow & Mục tiêu", expanded=False):
            scenarios = st.multiselect("Mục tiêu:", options=["ADD", "EDIT", "DELETE", "WORKFLOW"], default=["ADD"], key=f"sc_{s['id']}")
            workflow_ctx = ""
            if "WORKFLOW" in scenarios:
                all_items = ctrl.get_sub_contents(p['id']) 
                selected_next = st.multiselect("Nối cảnh tiếp theo:", options=[i for i in all_items if i['id'] != s['id']], 
                                               format_func=lambda x: x['sub_title'], key=f"wf_{s['id']}")
                for f in selected_next:
                    f_meta = ctrl.get_formatted_meta_for_ai(f['id'])
                    workflow_ctx += f"\n\n-- TIẾP THEO: {f.get('sub_title')} --\n{f_meta.get('prompt_letter', '')}"
            return scenarios, workflow_ctx