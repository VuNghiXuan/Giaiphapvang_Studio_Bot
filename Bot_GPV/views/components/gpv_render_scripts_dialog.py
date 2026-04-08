import streamlit as st
import json
import os
import asyncio
from .script_logic_helper import ScriptLogicHelper as Logic
from .script_ui_components import ScriptUIComponents as UI
from ...ai_film_factory.auto_video_engine import AutoVideoEngine
from config import Config
import time

class ScriptDialog:
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """Giao diện chính điều phối cấu hình kịch bản - Bản Gọn Nhẹ & An Toàn"""
        
        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # 1. Cấu hình AI & Workflow (Lấy các thông số từ UI selector)
        # Giả sử UI.render_ai_brain_config trả về: provider, model, voice_id
        sel_provider, sel_model, sel_voice_id = UI.render_ai_brain_config(s)
        scenarios, workflow_ctx = UI.render_workflow_selector(ctrl, p, s)

        # 2. Lấy dữ liệu Blueprint từ Database (Đã được controller định dạng cho AI)
        ai_res = ctrl.get_formatted_meta_for_ai(s['id'])
        if not ai_res: 
            return st.error("❌ Không thể lấy Blueprint từ Database. Vui lòng quét lại trang web.")
        
        # Đảm bảo ai_res là dict
        if not isinstance(ai_res, dict):
            ai_res = {"prompt_letter": str(ai_res), "metadata_json": "{}"}

        metadata_raw = ai_res.get('metadata_json', '{}')
        base_prompt = ai_res.get('prompt_letter', "")

        # --- 🛠️ XỬ LÝ RÚT GỌN NỘI DUNG GỬI AI (OMNI METADATA 2026) ---
        try:
            meta_obj = json.loads(metadata_raw)
            # Chỉ gửi những thông tin định danh cốt lõi để AI không bị loạn
            layout = meta_obj.get('layout', {})
            active_form = layout.get('active_form', {})
            main_content = layout.get('main_content', {})

            short_meta = {
                "navigation": meta_obj.get('navigation', {}).get('breadcrumbs', []),
                "available_actions": [a.get('label') for a in main_content.get('actions', []) if a.get('label')],
                "form_inputs": [i.get('label') for i in active_form.get('inputs', []) if i.get('label')],
                "form_actions": [a.get('label') for a in active_form.get('actions', []) if a.get('label')]
            }
            intel_desc = json.dumps(short_meta, ensure_ascii=False, indent=2)
        except Exception as e:
            intel_desc = f"Lỗi Parse Metadata: {str(e)}"

        # 3. Khu vực ghi chú của người dùng (Đạo diễn Vũ)
        notes = st.text_area("✍️ Lưu ý từ Đạo diễn Vũ:", 
                            placeholder="Ví dụ: Chỉ quay phần thêm mới chi nhánh, bỏ qua phần xóa...",
                            key=f"nt_{s['id']}")
        
        # 4. Hợp nhất Prompt
        full_prompt = (
            f"{base_prompt}\n\n"
            f"--- 🤖 TRI THỨC HỆ THỐNG (LABELS) ---\n{intel_desc}\n\n"
            f"--- 📍 BỐI CẢNH WORKFLOW ---\n{workflow_ctx}"
        )
        if notes:
            full_prompt += f"\n\n--- ✍️ GHI CHÚ BỔ SUNG ---\n{notes}"

        # 5. Review trước khi gửi
        with st.expander("📝 KIỂM TRA VĂN BẢN GỬI AI", expanded=False):
            final_prompt = st.text_area("Nội dung gửi AI:", value=full_prompt, height=350, key=f"f_p_{s['id']}")

        st.divider()
        c1, c2 = st.columns(2)
        
        # --- NÚT 1: SOẠN KỊCH BẢN ---
        if c1.button("🎬 GỬI AI SOẠN KỊCH BẢN", use_container_width=True, key=f"btn_j_{s['id']}"):
            ScriptDialog._handle_json_generation(ai_script, p, s, final_prompt, sel_model, sel_provider, sel_voice_id)

        # --- NÚT 2: XUẤT VIDEO (Thực thi Playwright) ---
        # Kiểm tra sự tồn tại của kịch bản trước khi cho phép chạy Bot
        json_key = f"last_json_{s['id']}"
        has_script = json_key in st.session_state or Logic.check_script_exists(p, s)
        
        btn_label = "🚀 XUẤT VIDEO HOÀN CHỈNH" if has_script else "⚠️ CHƯA CÓ KỊCH BẢN"
        if c2.button(btn_label, type="primary", use_container_width=True, key=f"btn_v_{s['id']}", disabled=not has_script):
            ScriptDialog._ai_auto_video_export(ctrl, p, s, sel_model, sel_provider, sel_voice_id)

        # 6. Preview & Biên tập kết quả
        ScriptDialog._render_result_preview(p, s)

    @staticmethod
    def _render_result_preview(p, s):
        """Hiển thị và cho phép sửa kịch bản JSON trực tiếp"""
        json_key = f"last_json_{s['id']}"
        path_key = f"last_path_{s['id']}"

        # Tự động load file cũ nếu session trống
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

        if json_key in st.session_state:
            st.divider()
            st.markdown("### 📝 Biên tập kịch bản (JSON)")
            
            # Hiển thị đường dẫn gọn gàng hơn
            display_path = os.path.relpath(st.session_state[path_key]) if os.path.exists(st.session_state[path_key]) else st.session_state[path_key]
            st.caption(f"📂 File: `{display_path}`")

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
                os.startfile(os.path.dirname(os.path.abspath(st.session_state[path_key])))

            if col_studio.button("➡️ STUDIO", type="primary", use_container_width=True, key=f"nav_{s['id']}"):
                st.session_state.current_tab = "Quay tự động 🤖"
                st.session_state.selected_scene = s
                st.rerun()

    @staticmethod
    def _handle_json_generation(ai_script, p, s, prompt, model, provider, voice_id):
        """Xử lý gọi AI và lưu file"""
        with st.spinner("🎭 AI đang soạn kịch bản diễn xuất..."):
            raw_res = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            
            if not raw_res:
                return st.error("❌ AI không phản hồi.")

            try:
                # Đảm bảo đầu ra là list các steps
                steps = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                steps = [step for step in steps if isinstance(step, dict) and step]
                
                if not steps:
                    return st.error("🚨 AI trả về kịch bản rỗng.")

                # Lưu file vật lý bằng Pathlib
                app_folder = p.get('folder_name', "Giai_Phap_Vang")
                sub_folder = s.get('sub_folder') or f"Form_{s['id']}"
                
                # Tạo folder assets nếu chưa có
                asset_dir = Config.get_path(app=app_folder, module=sub_folder, asset_type="metadata")
                asset_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = asset_dir / "latest_script.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps, f, indent=4, ensure_ascii=False)
                
                # Cập nhật Session
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                
                st.toast("✅ Kịch bản đã sẵn sàng!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"🚨 Lỗi xử lý kịch bản: {e}")


    @staticmethod
    def _ai_auto_video_export(ctrl, p, s, model, provider, voice_id):
        """THỰC THI BOT DIỄN VIÊN"""
        json_key = f"last_json_{s['id']}"
        script_steps = st.session_state.get(json_key)
        
        if not script_steps:
            return st.error("❌ Không tìm thấy dữ liệu kịch bản.")

        try:
            # Khởi tạo Engine - Ông Vũ nhớ truyền đúng đường dẫn logo tiệm vàng nhé
            engine = AutoVideoEngine(
                storage_path=Config.BASE_STORAGE,
                logo_path="assets/logo_htj.png", 
                voice=voice_id
            )
            
            with st.spinner("🤖 Bot đang mở trình duyệt và thực hiện các bước diễn..."):
                target_url = s.get('url') or "https://giaiphapvang.net"
                project_name = p.get('folder_name') or "Project_Default"
                form_name = s.get('sub_folder') or f"Form_{s['id']}"

                # Chạy luồng Bot Playwright
                final_video_path = asyncio.run(engine.run_studio_bot(
                    target_url=target_url,
                    script_steps=script_steps,
                    project_name=project_name,
                    form_name=form_name
                ))

                if final_video_path and os.path.exists(final_video_path):
                    st.balloons()
                    st.success(f"🔥 XUẤT BẢN THÀNH CÔNG!")
                    st.video(final_video_path)
                    
                    # Cập nhật trạng thái "Hoàn chỉnh" vào DB
                    ctrl.update_sub_content(sub_id=s['id'], status="Hoàn chỉnh")
                else:
                    st.error("❌ Bot chạy xong nhưng không tìm thấy file video đầu ra.")

        except Exception as e:
            st.error(f"🚨 Lỗi thực thi hệ thống: {e}")