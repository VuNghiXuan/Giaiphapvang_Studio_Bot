import streamlit as st
import json
import os
import asyncio
from .script_logic_helper import ScriptLogicHelper as Logic
from .script_ui_components import ScriptUIComponents as UI
from ...ai_film_factory.auto_video_engine import AutoVideoEngine
from config import Config

class ScriptDialog:
    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """Giao diện chính điều phối cấu hình kịch bản"""
        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # 1. Cấu hình AI & Workflow (Dùng UI Component đã tách)
        sel_provider, sel_model, sel_voice_id = UI.render_ai_brain_config(s)
        scenarios, workflow_ctx = UI.render_workflow_selector(ctrl, p, s)

        # 2. Lấy Prompt từ Controller (Dữ liệu đã được format nghiệp vụ tiệm vàng)
        ai_res = ctrl.get_formatted_meta_for_ai(s['id'])
        if not ai_res: 
            return st.error("❌ Không thể lấy Blueprint từ Database.")
        
        base_prompt = ai_res['prompt_letter']
        notes = st.text_area("✍️ Lưu ý từ Đạo diễn Vũ:", key=f"nt_{s['id']}", placeholder="Ví dụ: Nhấn mạnh phần bù tuổi vàng...")
        
        # Hợp nhất bức thư gửi AI
        full_prompt = f"{base_prompt}\n{workflow_ctx}"
        if notes:
            full_prompt += f"\n\n--- ✍️ GHI CHÚ BỔ SUNG ---\n{notes}"

        # 3. Khu vực kiểm duyệt nội dung trước khi gửi
        with st.expander("🔍 KIỂM TRA NỘI DUNG GỬI AI", expanded=False):
            final_prompt = st.text_area("Nội dung chuẩn bị gửi đi:", value=full_prompt, height=350, key=f"f_p_{s['id']}")

        st.divider()
        c1, c2 = st.columns(2)
        
        # 4. Nút bấm thực thi
        if c1.button("🎬 GỬI AI SOẠN KỊCH BẢN", use_container_width=True, key=f"btn_j_{s['id']}"):
            ScriptDialog._handle_json_generation(ai_script, p, s, final_prompt, sel_model, sel_provider, sel_voice_id)

        if c2.button("🚀 XUẤT VIDEO HOÀN CHỈNH", type="primary", use_container_width=True, key=f"btn_v_{s['id']}"):
            ScriptDialog._ai_auto_video_export(ctrl, p, s, sel_model, sel_provider, sel_voice_id)

        # 5. HIỂN THỊ KẾT QUẢ VÀ BIÊN TẬP (Hàm Vũ đang bị thiếu đây!)
        ScriptDialog._render_result_preview(p, s)

    @staticmethod
    def _render_result_preview(p, s):
        """Hiển thị, kiểm tra file tồn tại và cho phép sửa kịch bản JSON trực tiếp"""
        json_key = f"last_json_{s['id']}"
        path_key = f"last_path_{s['id']}"

        # Tự động load file cũ nếu session state trống (khi F5)
        if json_key not in st.session_state:
            _, sub_path = Logic.get_raw_video_path(p, s)
            file_path = sub_path / "assets" / "latest_script.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        st.session_state[json_key] = data
                        st.session_state[path_key] = str(file_path)
                except: pass

        # Nếu đã có dữ liệu kịch bản thì hiện ô biên tập
        if json_key in st.session_state:
            st.divider()
            st.markdown("### 📝 Biên tập kịch bản (JSON)")
            st.caption(f"📂 File: `{st.session_state[path_key]}`")

            current_json_str = json.dumps(st.session_state[json_key], indent=4, ensure_ascii=False)
            edited_json_str = st.text_area("Chỉnh sửa bước diễn:", value=current_json_str, height=250, key=f"edit_json_{s['id']}")

            col_save, col_open, col_studio = st.columns([1, 1, 1.5])
            
            if col_save.button("💾 LƯU LẠI", use_container_width=True, key=f"save_ed_{s['id']}"):
                try:
                    new_data = json.loads(edited_json_str)
                    with open(st.session_state[path_key], "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    st.session_state[json_key] = new_data
                    st.success("✅ Đã cập nhật kịch bản!")
                except Exception as e:
                    st.error(f"JSON lỗi: {e}")

            if col_open.button("📁 Folder", use_container_width=True, key=f"open_f_{s['id']}"):
                os.startfile(os.path.dirname(st.session_state[path_key]))

            if col_studio.button("➡️ STUDIO", type="primary", use_container_width=True, key=f"nav_{s['id']}"):
                st.session_state.current_tab = "Quay tự động 🤖"
                st.session_state.selected_scene = s
                st.rerun()

    @staticmethod
    def _handle_json_generation(ai_script, p, s, prompt, model, provider, voice_id):
        """Xử lý gọi AI và lưu file"""
        with st.spinner("🎭 AI đang soạn bài..."):
            steps = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if steps:
                _, sub_path = Logic.get_raw_video_path(p, s)
                file_path = Logic.save_script_to_file(sub_path, steps)
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                st.toast("✅ Đã có kịch bản mới!")
            else:
                st.error("❌ AI không phản hồi đúng định dạng JSON.")

    @staticmethod
    def _ai_auto_video_export(ctrl, p, s, model, provider, voice_id):
        """
        THỰC THI BOT TỰ ĐỘNG:
        Quy trình khép kín: Load JSON -> Pre-check -> Login -> Playwright Action -> MoviePy Merge
        """
        # --- BƯỚC 1: TRUY XUẤT KỊCH BẢN ---
        json_key = f"last_json_{s['id']}"
        script_steps = st.session_state.get(json_key)
        
        # Dùng Logic helper để lấy đường dẫn (đảm bảo đồng bộ với hàm tách file)
        _, sub_path = Logic.get_raw_video_path(p, s)
        asset_file = sub_path / "assets" / "latest_script.json"
        
        # Nếu session trống (do vừa F5 trang), thử tìm file vật lý đã lưu trước đó
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
            # Khởi tạo Engine với giọng đọc từ UI
            engine = AutoVideoEngine(
                storage_path=Config.BASE_STORAGE,
                logo_path="assets/logo.png", 
                voice=voice_id
            )
            
            # Kiểm tra xem có đủ Email/Pass và File kịch bản chuẩn chưa
            is_ready, missing_items = engine.check_ready_for_production(script_steps)
            if not is_ready:
                st.error(f"❌ Thiếu điều kiện sản xuất: {', '.join(missing_items)}")
                st.info("💡 Vũ kiểm tra lại file .env hoặc kịch bản JSON nhé.")
                return
                
        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo Engine: {e}")
            return

        # --- BƯỚC 3: KÍCH HOẠT BOT DIỄN XUẤT ---
        with st.spinner("🤖 BOT ĐANG DIỄN... Vui lòng không chạm vào chuột/bàn phím!"):
            try:
                # Lấy các thông số định danh dự án từ Blueprint/Metadata
                target_url = s.get('url') or "https://giaiphapvang.net" 
                project_name = p.get('project_folder') or p.get('folder_name') or "Project_Default"
                form_name = s.get('sub_folder') or f"Form_{s['id']}"

                # Xử lý luồng Asyncio trong Streamlit
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Chạy Bot để quay màn hình và khớp voice
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
                    
                    # Hiện video lên UI để xem luôn cho nóng
                    st.video(final_video_path)
                    
                    # Cập nhật trạng thái vào DB (Vũ dùng Controller để đồng bộ nhé)
                    ctrl.update_sub_content(s['id'], new_status="Hoàn chỉnh")
                    
                    # Nút mở file nhanh
                    if st.button("📂 Mở folder chứa video", key=f"open_v_res_{s['id']}"):
                        os.startfile(os.path.dirname(final_video_path))
                else:
                    st.error("❌ Bot chạy xong nhưng không tìm thấy video đầu ra. Kiểm tra log MoviePy!")

            except Exception as e:
                st.error(f"❌ Lỗi trong quá trình Bot diễn xuất: {e}")
                st.exception(e)