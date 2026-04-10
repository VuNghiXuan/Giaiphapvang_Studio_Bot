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
    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """Giao diện điều phối cấu hình kịch bản - Bản nâng cấp xâu chuỗi nghiệp vụ"""
        
        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # 1. Cấu hình AI & Workflow
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

        # Giả sử ctrl có hàm lấy danh sách tất cả modules hiện có
        all_modules = ctrl.get_all_modules() 
        selected_mods = col_m2.multiselect(
            "📦 Liên kết Module:",
            options=all_modules,
            help="Chọn các module sẽ xuất hiện trong video này.",
            key=f"mods_{s['id']}"
        )

        # Chọn Form cụ thể cho từng Module đã chọn
        chained_desc = ""
        if selected_mods:
            st.info("📌 Chọn Form cụ thể để AI lập lộ trình điều hướng:")
            m_cols = st.columns(len(selected_mods))
            for idx, m in enumerate(selected_mods):
                # Giả sử ctrl có hàm lấy forms theo tên module
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
            ScriptDialog._handle_json_generation(ai_script, p, s, final_prompt, sel_model, sel_provider, sel_voice_id)

        json_key = f"last_json_{s['id']}"
        has_script = json_key in st.session_state or Logic.check_script_exists(p, s)
        
        btn_label = "🚀 XUẤT VIDEO" if has_script else "⚠️ THIẾU KỊCH BẢN"
        if c2.button(btn_label, type="primary", width='stretch', key=f"btn_v_{s['id']}", disabled=not has_script):
            ScriptDialog._ai_auto_video_export(ctrl, p, s, sel_model, sel_provider, sel_voice_id)

        # 6. Preview & Biên tập
        ScriptDialog._render_result_preview(p, s)

    @staticmethod
    def _render_result_preview(p, s):
        """Hàm load kịch bản lên để sửa và lưu trực tiếp"""
        from pathlib import Path
        json_key = f"last_json_{s['id']}"
        path_key = f"last_path_{s['id']}"

        # 1. Định vị file script theo cấu trúc mới (metadata/latest_script.json)
        if json_key not in st.session_state:
            app_folder = p.get('folder_name', "Giai_Phap_Vang")
            sub_logical_path = s.get('sub_folder', f"Form_{s['id']}")
            
            # Khớp chính xác với folder lúc lưu
            base_storage = Path(Config.BASE_STORAGE)
            file_path = base_storage / app_folder / sub_logical_path / "metadata" / "latest_script.json"
            
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        st.session_state[json_key] = json.load(f)
                        st.session_state[path_key] = str(file_path)
                except Exception as e:
                    st.error(f"Lỗi đọc file kịch bản: {e}")

        # 2. Giao diện biên tập
        if json_key in st.session_state:
            st.divider()
            st.markdown("### 📝 Biên tập lộ trình diễn xuất (JSON)")
            
            # Hiển thị nội dung JSON hiện tại
            current_json_str = json.dumps(st.session_state[json_key], indent=4, ensure_ascii=False)
            edited_json_str = st.text_area(
                "Chỉnh sửa các bước (Action/Target/Speech):", 
                value=current_json_str, 
                height=300, 
                key=f"edit_json_{s['id']}"
            )

            col_save, col_open, col_studio = st.columns([1, 1, 1.5])
            
            # --- NÚT LƯU BIÊN TẬP ---
            if col_save.button("💾 LƯU THAY ĐỔI", width='stretch', key=f"save_ed_{s['id']}"):
                try:
                    new_data = json.loads(edited_json_str)
                    target_file = st.session_state[path_key]
                    
                    # Ghi đè lại file JSON
                    with open(target_file, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    
                    st.session_state[json_key] = new_data
                    st.success("✅ Đã cập nhật kịch bản!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi cú pháp JSON: {e}")

            # --- NÚT MỞ THƯ MỤC ---
            if col_open.button("📁 Mở Folder", width='stretch', key=f"open_f_{s['id']}"):
                folder_path = os.path.dirname(os.path.abspath(st.session_state[path_key]))
                os.startfile(folder_path)

            # --- NÚT QUA STUDIO ---
            if col_studio.button("➡️ CHUYỂN QUA STUDIO", type="primary", width='stretch', key=f"nav_{s['id']}"):
                st.session_state.current_tab = "Quay tự động 🤖"
                st.session_state.selected_scene = s
                st.rerun()

    @staticmethod
    def _handle_json_generation(ai_script, p, s, prompt, model, provider, voice_id):
        with st.spinner("🎭 AI đang lập trình lộ trình diễn xuất..."):
            # 1. Gọi AI lấy kịch bản
            raw_res = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if not raw_res: 
                return st.error("❌ AI không phản hồi.")

            try:
                # 2. Xử lý dữ liệu JSON từ AI
                steps = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                
                # 3. Định vị Folder lưu trữ (Cấu trúc phân cấp chuẩn của Vũ)
                # p['folder_name'] thường là 'ung_dung_vang'
                app_folder = p.get('folder_name', "Giai_Phap_Vang")
                
                # s['sub_folder'] là chuỗi từ DB: 'he_thong/settings/thong_tin_cong_ty/chi_nhanh'
                sub_logical_path = s.get('sub_folder') or f"Form_{s['id']}"
                
                # Tạo Path tuyệt đối: D:\ThanhVu\...\storage\ung_dung_vang\he_thong\...\metadata
                # Sử dụng / của Pathlib để tự động xử lý dấu gạch chéo trên Windows
                from pathlib import Path
                base_storage = Path(Config.BASE_STORAGE)
                asset_dir = base_storage / app_folder / sub_logical_path / "metadata"
                
                # 4. Thực thi tạo folder và ghi file
                asset_dir.mkdir(parents=True, exist_ok=True)
                file_path = asset_dir / "latest_script.json"
                
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps, f, indent=4, ensure_ascii=False)
                
                # 5. Cập nhật trạng thái giao diện
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                
                st.toast(f"✅ Đã lưu kịch bản vào: {sub_logical_path}")
                time.sleep(1) # Đợi 1 chút để user kịp thấy toast
                st.rerun()
                
            except Exception as e:
                st.error(f"🚨 Lỗi thực thi lưu kịch bản: {e}")
                import traceback
                st.code(traceback.format_exc()) # Show lỗi chi tiết để debug nếu cần

    @staticmethod
    def _ai_auto_video_export(ctrl, p, s, model, provider, voice_id):
        """
        THỰC THI XUẤT VIDEO TỰ ĐỘNG - GPV STUDIO
        Đảm bảo video chui đúng vào folder: Project/Module/Form/videos
        """
        json_key = f"last_json_{s['id']}"
        script_steps = st.session_state.get(json_key)
        
        if not script_steps: 
            return st.error("❌ Thiếu kịch bản. Hãy nhấn 'GỬI AI SOẠN KỊCH BẢN' trước.")

        try:
            # 1. Khởi tạo Engine với cấu hình riêng cho Hiệp Thành Jewelry
            engine = AutoVideoEngine(
                storage_path=Config.BASE_STORAGE,
                logo_path="assets/logo_htj.png", # Logo thương hiệu vàng
                voice=voice_id
            )
            
            with st.spinner("🤖 Bot Playwright đang thực thi lộ trình diễn xuất..."):
                # 2. Xử lý phân tách đường dẫn nghiệp vụ
                # s['sub_folder'] ví dụ: "he_thong/settings/thong_tin_cong_ty/chi_nhanh"
                full_sub_path = s.get('sub_folder', '')
                path_parts = full_sub_path.split('/')
                
                # Module là phần ở giữa (ví dụ: "he_thong/settings/thong_tin_cong_ty")
                # Form là phần cuối cùng (ví dụ: "chi_nhanh")
                m_name = "/".join(path_parts[:-1]) if len(path_parts) > 1 else "Chung"
                f_name = path_parts[-1] if path_parts else f"Form_{s['id']}"

                # 3. Chạy tiến trình Async trong môi trường Sync của Streamlit
                final_video_path = asyncio.run(engine.run_studio_bot(
                    target_url=s.get('url', "https://giaiphapvang.net"),
                    script_steps=script_steps,
                    project_name=p.get('folder_name'), # Ví dụ: "ung_dung_vang"
                    module_name=m_name,
                    form_name=f_name
                ))

                # 4. Kiểm tra và hiển thị kết quả
                if final_video_path and os.path.exists(final_video_path):
                    st.balloons()
                    st.success(f"✅ Video đã được render thành công!")
                    
                    # Hiển thị video trực tiếp trên giao diện
                    st.video(final_video_path)
                    
                    # Cập nhật trạng thái vào Database của Vũ
                    ctrl.update_sub_content(sub_id=s['id'], status="Hoàn chỉnh")
                    
                    # Nút mở thư mục chứa video cho tiện
                    if st.button("📁 Mở thư mục chứa video"):
                        os.startfile(os.path.dirname(os.path.abspath(final_video_path)))
                else:
                    st.error("❌ Engine không tạo được video. Kiểm tra lại logic StudioMachine.")
                    
        except Exception as e:
            st.error(f"🚨 Lỗi vận hành Bot: {e}")
            import traceback
            st.code(traceback.format_exc())