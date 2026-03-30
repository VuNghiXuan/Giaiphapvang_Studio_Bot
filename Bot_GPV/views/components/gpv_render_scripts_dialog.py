import streamlit as st
import os
import json
from pathlib import Path
from config import Config
from ..utils_dashboad.video_engine import AutoVideoEngine
import asyncio

class ScriptDialog:
    """
    Class chuyên trách việc cấu hình kịch bản AI, xử lý tệp tin 
    và xuất bản video cho từng phân cảnh.
    """

    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """Giao diện chính trong Popover để phê duyệt kịch bản"""
        if not isinstance(s, dict):
            st.error("Lỗi dữ liệu: Phân cảnh không hợp lệ.")
            return

        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # --- BƯỚC 1: TRI THỨC GỐC ---
        raw_ctx = ai_script.get_form_knowledge_from_db(s)
        if "⚠️" in raw_ctx: 
            st.warning(raw_ctx)
        else: 
            st.success("✅ Tri thức Metadata sẵn sàng.")

        # --- BƯỚC 2: CẤU HÌNH BỘ NÃO AI ---
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
        sel_voice_id = voice_map[sel_voice_label]

        # --- BƯỚC 3: WORKFLOW & Ý ĐỒ ĐẠO DIỄN ---
        with st.expander("📄 Tùy chỉnh Workflow & Prompt", expanded=False):
            user_edited_ctx = st.text_area("Context nghiệp vụ:", value=raw_ctx, height=150, key=f"raw_{s['id']}")
            scenarios = st.multiselect("Mục tiêu:", options=["ADD", "EDIT", "DELETE", "WORKFLOW"], default=["ADD"], key=f"sc_{s['id']}")
            
            workflow_ctx = ""
            if "WORKFLOW" in scenarios:
                all_items = ctrl.get_sub_contents(p['id']) 
                selected_next = st.multiselect("Nối cảnh tiếp theo:", options=[i for i in all_items if i['id'] != s['id']], 
                                               format_func=lambda x: x['sub_title'], key=f"wf_{s['id']}")
                for f in selected_next:
                    workflow_ctx += f"\n\n-- TIẾP THEO: {f.get('sub_title')} --\n{ai_script.get_form_knowledge_from_db(f)}"

        notes = st.text_area("Lưu ý từ Đạo diễn Vũ:", key=f"nt_{s['id']}", placeholder="Dùng ngôn từ ngành kim hoàn...")
        
        # Tạo Prompt gửi AI
        temp_config = {
            "scenarios": scenarios, 
            "notes": notes, 
            "slogan": Config.DEFAULT_SLOGAN, 
            "current_module": mod_name
        }
        full_draft_prompt = ai_script.generate_ai_prompt(mod_name, form_name, temp_config, user_edited_ctx + workflow_ctx)

        with st.expander("🔍 KIỂM TRA BỨC THƯ GỬI AI", expanded=False):
            final_prompt = st.text_area("Nội dung chuẩn bị gửi đi:", value=full_draft_prompt, height=300, key=f"f_p_{s['id']}")

        st.divider()

        # --- BƯỚC 4: KHU VỰC NÚT BẤM ---
        b1, b2 = st.columns(2)
        
        if b1.button("🎬 GỬI AI SOẠN KỊCH BẢN JSON", use_container_width=True, key=f"btn_j_{s['id']}"):
            ScriptDialog._handle_json_generation(ctrl, p, s, ai_script, final_prompt, sel_model, sel_provider, sel_voice_id)

        if b2.button("🚀 XUẤT VIDEO HOÀN CHỈNH", type="primary", use_container_width=True, key=f"btn_v_{s['id']}"):
            ScriptDialog._ai_auto_video_export(ctrl, p, s, sel_model, sel_provider, sel_voice_id)

        # --- BƯỚC 5: HIỂN THỊ KẾT QUẢ VÀ MỞ FILE ---
        ScriptDialog._render_result_preview(p, s)

    @staticmethod
    def _render_result_preview(p, s):
        """Hiển thị, kiểm tra file tồn tại và cho phép sửa kịch bản"""
        json_key = f"last_json_{s['id']}"
        path_key = f"last_path_{s['id']}"

        # --- BƯỚC A: KIỂM TRA FILE VẬT LÝ NẾU SESSION TRỐNG ---
        if json_key not in st.session_state:
            _, sub_path = ScriptDialog._get_raw_video_path(p, s)
            file_path = sub_path / "assets" / "latest_script.json"
            
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        st.session_state[json_key] = data
                        st.session_state[path_key] = str(file_path)
                except Exception as e:
                    st.error(f"Lỗi đọc file cũ: {e}")

        # --- BƯỚC B: HIỂN THỊ GIAO DIỆN NẾU ĐÃ CÓ DỮ LIỆU ---
        if json_key in st.session_state:
            st.divider()
            st.markdown("### 📝 Biên tập kịch bản (JSON)")
            
            # Hiển thị đường dẫn file hiện tại
            st.caption(f"📂 File: `{st.session_state[path_key]}`")

            # Chuyển JSON sang String để sửa trong text_area
            current_json_str = json.dumps(st.session_state[json_key], indent=4, ensure_ascii=False)
            
            # Ô soạn thảo kịch bản
            edited_json_str = st.text_area(
                "Nội dung kịch bản (Có thể sửa trực tiếp):",
                value=current_json_str,
                height=300,
                key=f"edit_json_{s['id']}"
            )

            col_save, col_open, col_studio = st.columns([1, 1, 2])

            with col_save:
                # NÚT LƯU FILE: Sửa xong bấm nút này để ghi đè file cũ
                if st.button("💾 LƯU THAY ĐỔI", use_container_width=True, key=f"save_edit_{s['id']}"):
                    try:
                        new_data = json.loads(edited_json_str)
                        with open(st.session_state[path_key], "w", encoding="utf-8") as f:
                            json.dump(new_data, f, indent=4, ensure_ascii=False)
                        st.session_state[json_key] = new_data
                        st.success("✅ Đã lưu kịch bản mới!")
                    except Exception as e:
                        st.error(f"JSON sai định dạng: {e}")

            with col_open:
                if st.button("📁 Mở Folder", use_container_width=True, key=f"open_f_{s['id']}"):
                    os.startfile(os.path.dirname(st.session_state[path_key]))

            with col_studio:
                if st.button("➡️ SANG STUDIO QUAY LUÔN", type="primary", use_container_width=True, key=f"nav_{s['id']}"):
                    ScriptDialog.navigate_to_studio(p, s, "Quay tự động 🤖")

    @staticmethod
    def _get_raw_video_path(p, s):
        """Dò tìm file video gốc dựa trên cấu trúc thư mục"""
        storage_root = Path(Config.BASE_STORAGE)
        p_name = p.get('project_folder') or p.get('folder_name') or ""
        s_name = s.get('sub_folder', "")

        possible_paths = [
            storage_root / p_name / s_name,
            storage_root / Config.slugify_vietnamese(p_name) / Config.slugify_vietnamese(s_name)
        ]

        target_dir = possible_paths[0]
        for path in possible_paths:
            if path.exists():
                target_dir = path
                break

        if target_dir.exists():
            for item in os.listdir(target_dir):
                if "raw" in item.lower():
                    return target_dir / item, target_dir
                    
        return None, target_dir

    @staticmethod
    def _handle_json_generation(ctrl, p, s, ai_script, prompt, model, provider, voice_id):
        """Gọi AI soạn kịch bản và lưu vào file assets"""
        with st.spinner(f"🎭 AI ({provider}) đang soạn bài..."):
            steps = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if steps:
                _, sub_path = ScriptDialog._get_raw_video_path(p, s)
                asset_dir = sub_path / "assets"
                asset_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = asset_dir / "latest_script.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps, f, ensure_ascii=False, indent=4)
                
                # Cập nhật session state
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                st.session_state.update({"current_steps": steps, "selected_voice": voice_id})
                
                st.toast(f"✅ Đã lưu kịch bản!")
            else:
                st.error("❌ Lỗi: AI không phản hồi hoặc JSON sai định dạng.")

    
    @staticmethod
    def _ai_auto_video_export(ctrl, p, s, model, provider, voice_id):
        """
        THỰC THI BOT TỰ ĐỘNG:
        Quy trình khép kín: Load JSON -> Pre-check -> Login -> Playwright Action -> MoviePy Merge
        """
        
        
        # --- BƯỚC 1: TRUY XUẤT KỊCH BẢN ---
        json_key = f"last_json_{s['id']}"
        script_steps = st.session_state.get(json_key)
        
        # Nếu session trống (do vừa F5 trang), thử tìm file vật lý đã lưu trước đó
        _, sub_path = ScriptDialog._get_raw_video_path(p, s)
        asset_file = sub_path / "assets" / "latest_script.json"
        
        if not script_steps and asset_file.exists():
            try:
                with open(asset_file, "r", encoding="utf-8") as f:
                    script_steps = json.load(f)
                    st.session_state[json_key] = script_steps
            except Exception as e:
                st.error(f"❌ Không thể đọc file kịch bản cũ: {e}")
                return

        if not script_steps:
            st.error("❌ Chưa có kịch bản! Ông vui lòng nhấn 'GỬI AI SOẠN KỊCH BẢN' trước đã.")
            return

        # --- BƯỚC 2: KHỞI TẠO VÀ KIỂM TRA ĐIỀU KIỆN SẢN XUẤT ---
        try:
            # Khởi tạo Engine với giọng đọc từ UI (Hoài My/Nam Minh)
            engine = AutoVideoEngine(
                storage_path=Config.BASE_STORAGE,
                logo_path="assets/logo.png", # File logo của Đạo diễn Vũ
                voice=voice_id
            )
            
            # Kiểm tra xem có đủ Email/Pass và File kịch bản chuẩn chưa
            is_ready, missing_items = engine.check_ready_for_production(script_steps)
            if not is_ready:
                st.error(f"❌ Thiếu điều kiện sản xuất: {', '.join(missing_items)}")
                st.info("💡 Ông kiểm tra lại file .env hoặc kịch bản JSON nhé.")
                return
                
        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo Engine: {e}")
            return

        # --- BƯỚC 3: KÍCH HOẠT BOT DIỄN XUẤT ---
        with st.spinner("🤖 BOT ĐANG DIỄN... Vui lòng không chạm vào chuột/bàn phím!"):
            try:
                # Lấy các thông số định danh dự án
                # Ưu tiên lấy URL từ Metadata của phân cảnh
                target_url = s.get('url') or "https://giaiphapvang.vn" 
                project_name = p.get('project_folder') or p.get('folder_name') or "Project_Default"
                form_name = s.get('sub_folder') or f"Form_{s['id']}"

                # Chạy Async Bot trong môi trường Sync của Streamlit
                # Lưu ý: Dùng loop để tránh xung đột nếu có event loop đang chạy
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                final_video_path = loop.run_until_complete(engine.run_studio_bot(
                    target_url=target_url,
                    script_steps=script_steps,
                    project_name=project_name,
                    form_name=form_name
                ))

                # --- BƯỚC 4: HIỂN THỊ KẾT QUẢ ---
                if final_video_path and os.path.exists(final_video_path):
                    st.balloons()
                    st.success(f"🔥 XUẤT BẢN THÀNH CÔNG: {os.path.basename(final_video_path)}")
                    
                    # Hiển thị video để xem lại ngay lập tức
                    st.video(final_video_path)
                    
                    # Cập nhật trạng thái vào Database thông qua Controller
                    ctrl.update_sub_content(s['id'], new_status="Hoàn chỉnh")
                    
                    # Nút mở nhanh file để ông Vũ kiểm tra
                    if st.button("📂 Mở file video trên máy", key=f"open_v_{s['id']}"):
                        os.startfile(final_video_path)
                else:
                    st.error("❌ Bot chạy xong nhưng không tìm thấy file video đầu ra.")

            except Exception as e:
                st.error(f"❌ Lỗi trong quá trình Bot diễn xuất: {e}")
                st.exception(e) # Hiển thị chi tiết lỗi để debug nếu cần

    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        """Điều hướng tab trong session_state"""
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s
        st.rerun()