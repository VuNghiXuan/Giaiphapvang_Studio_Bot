import streamlit as st
import json
import os
import asyncio
import time
from pathlib import Path
from config import Config
from core.ai_manager import AIManager
from .script_logic_helper import ScriptLogicHelper as Logic # Giả định tên alias của ông
from .script_ui_components import ScriptUIComponents as UI   # Giả định tên alias của ông
from ...ai_film_factory.auto_video_engine import AutoVideoEngine

class ScriptDialog:
    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script, project_slug=None):
        """
        Giao diện điều phối cấu hình kịch bản - Bản nâng cấp xâu chuỗi nghiệp vụ.
        project_slug: Ép dùng Config.APP_SLUG để đồng bộ folder.
        """
        # --- 🛠️ HACK CSS CHO DIALOG RỘNG & THOÁNG ---
        # --- 🛠️ HACK CSS SIÊU CẤP: PHÁ VỠ GIỚI HẠN LAYOUT CHA ---
        st.markdown("""
            <style>
                /* 1. Ép toàn bộ container chính của Streamlit ra FULL WIDTH */
                [data-testid="stAppViewBlockContainer"] {
                    max-width: 95% !important;
                    padding-left: 2rem !important;
                    padding-right: 2rem !important;
                }

                /* 2. Ép lớp overlay của Dialog phải bao phủ toàn màn hình */
                div[data-testid="stDialog"] {
                    display: flex !important;
                    justify-content: center !important;
                    width: 100vw !important;
                }

                /* 3. Cấu hình lại Dialog để bỏ qua giới hạn của container cha */
                div[data-testid="stDialog"] div[role="dialog"] {
                    width: 95vw !important;
                    max-width: 1800px !important;
                    left: 0 !important;
                    margin: auto !important;
                }

                /* 4. Tăng chiều cao vùng nội dung */
                div[data-testid="stDialog"] .st-emotion-cache-12m0612 {
                    max-height: 90vh !important;
                }

                /* 5. Làm đẹp cho Dialog "vàng bạc" của ông */
                div[role="dialog"] {
                    border-radius: 20px !important;
                    border: 3px solid #FFD700 !important;
                    box-shadow: 0px 0px 30px rgba(0,0,0,0.5) !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # Đảm bảo slug luôn chuẩn
        final_slug = project_slug or Config.APP_SLUG

        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # 1. Cấu hình AI & Workflow (Sử dụng các component UI dùng chung)
        sel_provider, sel_model, sel_voice_id = UI.render_ai_brain_config(s)
        scenarios, workflow_ctx = UI.render_workflow_selector(ctrl, p, s)

        # 2. Lấy dữ liệu Blueprint từ Database
        ai_res = ctrl.get_formatted_meta_for_ai(s['id'])
        if not ai_res: 
            return st.error("❌ Không thể lấy Blueprint từ Database. Vui lòng quét lại trang web.")
        
        if not isinstance(ai_res, dict):
            ai_res = {"prompt_letter": str(ai_res), "metadata_json": "{}"}

        metadata_raw = ai_res.get('metadata_json', '{}')
        base_prompt = ai_res.get('prompt_letter', "")

        # --- 🔗 KHU VỰC XÂU CHUỖI NGHIỆP VỤ (ĐẠO DIỄN VŨ) ---
        st.divider()
        st.markdown("### 🧬 Lộ trình diễn hoạt (Cross-module)")
        
        col_m1, col_m2 = st.columns([1, 2])
        target_goal = col_m1.selectbox(
            "🎯 Mục tiêu chính:", 
            ["Thêm mới", "Chỉnh sửa", "Xóa dữ liệu", "Quy trình liên hợp", "Báo cáo"],
            key=f"goal_{s['id']}"
        )

        all_modules = ctrl.get_all_modules() 
        selected_mods = col_m2.multiselect(
            "📦 Liên kết Module:",
            options=all_modules,
            help="Chọn các module sẽ xuất hiện trong video này.",
            key=f"mods_{s['id']}"
        )

        chained_desc = ""
        if selected_mods:
            st.info("📌 Chọn Form cụ thể để AI lập lộ trình điều hướng:")
            m_cols = st.columns(len(selected_mods))
            for idx, m in enumerate(selected_mods):
                forms_in_mod = ctrl.get_forms_by_module(m) 
                with m_cols[idx]:
                    selected_fs = st.multiselect(
                        f"📄 {m}:",
                        options=[f['sub_title'] for f in forms_in_mod],
                        key=f"forms_{m}_{s['id']}"
                    )
                    if selected_fs:
                        chained_desc += f"- Module {m}: Đi qua các Form [{', '.join(selected_fs)}]\n"

        # --- 🛠️ XỬ LÝ METADATA GỌN NHẸ ---
        try:
            meta_obj = json.loads(metadata_raw)
            layout = meta_obj.get('layout', {})
            active_form = layout.get('active_form', {})
            
            short_meta = {
                "navigation": meta_obj.get('navigation', {}).get('breadcrumbs', []),
                "form_inputs": [i.get('label') for i in active_form.get('inputs', []) if i.get('label')],
                "form_actions": [a.get('label') for a in active_form.get('actions', []) if a.get('label')]
            }
            intel_desc = json.dumps(short_meta, ensure_ascii=False, indent=2)
        except:
            intel_desc = "Metadata không khả dụng."

        # 3. Ghi chú & Slogan
        notes = st.text_area("✍️ Ghi chú đạo diễn (Lưu ý về logic diễn xuất):", 
                            placeholder="Ví dụ: Diễn giải từ việc nhập kho xong thì nhảy sang báo cáo tồn kho...",
                            key=f"nt_{s['id']}")
        
        # 4. Hợp nhất Prompt SIÊU CẤP
        full_prompt = (
            f"--- 🎭 CHỈ THỊ ĐẠO DIỄN ---\n"
            f"Mục tiêu: {target_goal}\n"
            f"Lộ trình liên kết nghiệp vụ:\n{chained_desc if chained_desc else 'Không có'}\n"
            f"Lưu ý: {notes if notes else 'N/A'}\n\n"
            f"{base_prompt}\n\n"
            f"--- 🤖 LABELS HỆ THỐNG ---\n{intel_desc}\n\n"
            f"--- 📍 BỐI CẢNH WORKFLOW ---\n{workflow_ctx}"
        )

        # 5. Review trước khi gửi
        with st.expander("📝 KIỂM TRA PROMPT GỬI AI", expanded=False):
            final_prompt = st.text_area("Nội dung gửi AI:", value=full_prompt, height=350, key=f"f_p_{s['id']}")

        st.divider()
        c1, c2 = st.columns(2)
        
        if c1.button("🎬 GỬI AI SOẠN KỊCH BẢN", width='stretch', key=f"btn_j_{s['id']}"):
            ScriptDialog._handle_json_generation(ai_script, final_slug, s, final_prompt, sel_model, sel_provider)

        json_key = f"last_json_{s['id']}"
        # Check cả session state và file vật lý
        has_script = json_key in st.session_state or Logic.check_script_exists(final_slug, s.get('sub_folder'))
        
        btn_label = "🚀 XUẤT VIDEO" if has_script else "⚠️ THIẾU KỊCH BẢN"
        if c2.button(btn_label, type="primary", width='stretch', key=f"btn_v_{s['id']}", disabled=not has_script):
            ScriptDialog._ai_auto_video_export(ctrl, final_slug, s, sel_voice_id)

        # 6. Preview & Biên tập
        ScriptDialog._render_result_preview(final_slug, s)

    @staticmethod
    def _render_result_preview(project_slug, s):
        """Hiển thị JSON và cho phép sửa trực tiếp"""
        json_key = f"last_json_{s['id']}"
        path_key = f"last_path_{s['id']}"

        # Nếu chưa có trong session, thử load từ đĩa
        if json_key not in st.session_state:
            sub_path = s.get('sub_folder') or f"Form_{s['id']}"
            file_path = Path(Config.BASE_STORAGE) / project_slug / sub_path / "metadata" / "latest_script.json"
            
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        st.session_state[json_key] = json.load(f)
                        st.session_state[path_key] = str(file_path)
                except: pass

        if json_key in st.session_state:
            st.divider()
            st.markdown("### 📝 Biên tập lộ trình diễn xuất (JSON)")
            
            current_json_str = json.dumps(st.session_state[json_key], indent=4, ensure_ascii=False)
            edited_json_str = st.text_area("Chỉnh sửa Action/Speech:", value=current_json_str, height=300, key=f"edit_json_{s['id']}")

            col_save, col_open, col_studio = st.columns([1, 1, 1.5])
            
            if col_save.button("💾 LƯU THAY ĐỔI", key=f"save_ed_{s['id']}"):
                try:
                    new_data = json.loads(edited_json_str)
                    target_file = st.session_state[path_key]
                    with open(target_file, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    st.session_state[json_key] = new_data
                    st.success("✅ Đã cập nhật!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi JSON: {e}")

            if col_open.button("📁 Mở Folder", key=f"open_f_{s['id']}"):
                os.startfile(os.path.dirname(st.session_state[path_key]))

            if col_studio.button("➡️ CHUYỂN QUA STUDIO", type="primary", key=f"nav_{s['id']}"):
                st.session_state.current_tab = "Quay tự động 🤖"
                st.session_state.selected_scene = s
                st.rerun()

    @staticmethod
    def _handle_json_generation(ai_script, project_slug, s, prompt, model, provider):
        with st.spinner("🎭 AI đang lập trình lộ trình diễn xuất..."):
            raw_res = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if not raw_res: return st.error("❌ AI không phản hồi.")

            try:
                steps = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                sub_path = s.get('sub_folder') or f"Form_{s['id']}"
                
                asset_dir = Path(Config.BASE_STORAGE) / project_slug / sub_path / "metadata"
                asset_dir.mkdir(parents=True, exist_ok=True)
                file_path = asset_dir / "latest_script.json"
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps, f, indent=4, ensure_ascii=False)
                
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                st.toast(f"✅ Đã lưu kịch bản!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"🚨 Lỗi lưu kịch bản: {e}")

    @staticmethod
    def _ai_auto_video_export(ctrl, project_slug, s, voice_id):
        json_key = f"last_json_{s['id']}"
        script_steps = st.session_state.get(json_key)
        
        if not script_steps: 
            return st.error("❌ Thiếu kịch bản.")

        try:
            engine = AutoVideoEngine(
                storage_path=Config.BASE_STORAGE,
                voice=voice_id
            )
            
            with st.spinner("🤖 Bot Playwright đang thực thi diễn xuất..."):
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Ép project_name là slug chuẩn (ung_dung_vang)
                final_video_path = loop.run_until_complete(engine.run_studio_bot(
                    target_url=s.get('url', "https://giaiphapvang.net"),
                    script_steps=script_steps,
                    project_name=project_slug,
                    full_path_str=s.get('sub_folder', 'Default')
                ))

                if final_video_path and os.path.exists(final_video_path):
                    st.balloons()
                    st.video(final_video_path)
                    ctrl.update_sub_content(sub_id=s['id'], status="Hoàn chỉnh")
                    st.success(f"✅ Video render thành công tại: {project_slug}")
                else:
                    st.error("❌ Engine không tạo được video.")
                    
        except Exception as e:
            st.error(f"🚨 Lỗi vận hành Bot: {e}")