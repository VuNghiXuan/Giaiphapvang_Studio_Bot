import streamlit as st
import os
from pathlib import Path
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge
from ..utils_dashboad.ai_config_for_gpv_component import AIConfigHandler
from core.ai_manager import AIManager
import json

class RenderForm:  
    ai_manager = AIManager() # Khởi tạo thực thể quản lý AI
    # =================================================================
    # PHẦN 1: RENDER DANH MỤC FORM
    # =================================================================

    @staticmethod
    def render_item_rows(ctrl, p, items, ai_script, project_name):
        st.markdown("""
            <style>
                /* Phóng to cửa sổ Popover khi nhấn vào nút 🤖 */
                div[data-testid="stPopoverBody"] {
                    width: 800px !important;
                    max-width: 90vw !important;
                }
                /* Làm các ô text area cao hơn cho dễ nhìn */
                textarea {
                    font-family: 'Consolas', 'Monaco', monospace !important;
                    font-size: 0.9rem !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        STATUS_STYLES = {
            "Chưa quay": {"color": "#808080", "bg": "#f8f9fa"},
            "Đã quay": {"color": "#007bff", "bg": "#e7f3ff"},
            "Hoàn chỉnh": {"color": "#28a745", "bg": "#d4edda"}
        }
        status_options = list(STATUS_STYLES.keys())
        
        # Lấy tên folder an toàn từ object project p
        p_folder = p.get('project_folder') or p.get('folder_name') or project_name

        for idx, s in enumerate(items):
            sub_path = os.path.join(Config.BASE_STORAGE, p_folder, s['sub_folder'])
            current_status = get_status_info(sub_path, s.get('status'))
            
            parts = s['sub_title'].split('|')
            mod_name, form_name = parts[0], parts[-1]
            style = STATUS_STYLES.get(current_status, STATUS_STYLES["Chưa quay"])

            with st.container(border=True):
                st.markdown(f"""<style>div[data-testid="stVerticalBlock"] > div:has(input[key="st_{s['id']}"]) 
                    {{ border-left: 6px solid {style['color']} !important; background-color: {style['bg']}; }}</style>""", unsafe_allow_html=True)

                col_info, col_status, col_actions = st.columns([3, 1.2, 2.3])
                
               
                with col_info:
                    # 1. Tên Form kèm Link (Gom làm một cho gọn)
                    st.markdown(f"**{form_name}**", help=f"🔗 Link: {s.get('url', 'N/A')}")
                    
                    # 2. Hiển thị Badge trạng thái (Quay/Chưa quay) và Script đồng hàng
                    col_badge, col_script = st.columns([1, 1])
                    with col_badge:
                        render_status_badge(current_status)
                    with col_script:
                        # Check xem đã có kịch bản JSON lưu trong máy/DB chưa
                        if s.get('has_script'): 
                            st.markdown("<span style='color: #28a745; font-size: 0.75rem; font-weight: bold;'>📜 Đã có kịch bản</span>", unsafe_allow_html=True)
                    
                    # 3. Thông tin phụ
                    st.caption(f"📁 {s['sub_folder']} | 📦 {mod_name}")
                    
                    # 4. Tri thức hệ thống (Metadata) - Bot Biên Tập đã lọc
                    meta = s.get('metadata', {})
                    if isinstance(meta, dict) and meta.get('form_fields'):
                        # Lấy 5 label đầu tiên để Vũ biết bên trong có gì
                        fields = [f.get('label') for f in meta['form_fields'][:5] if isinstance(f, dict) and f.get('label')]
                        if fields:
                            st.markdown(f"<div style='font-size: 0.75rem; color: #666; font-style: italic;'>📝 {', '.join(fields)}...</div>", unsafe_allow_html=True)
                            

                with col_status:
                    st.markdown(f"<p style='font-size: 0.7rem; font-weight: bold; margin-bottom:0;'>TRẠNG THÁI</p>", unsafe_allow_html=True)
                    RenderForm.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    
                    # 🎥 Nút quay thủ công
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                        RenderForm.navigate_to_studio(p, s, "Quay thủ công")
                    
                    # 🤖 Nút AI soạn kịch bản (Popover)
                    with c_auto.popover("🤖", help="AI soạn kịch bản"):
                        # FIX: Truyền ctrl vào đầu tiên để render_ai_config_panel có thể dùng lấy items dự án
                        RenderForm.render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script)
                    
                    # ⚙️ Nút tùy chọn khác
                    with c_opt.popover("⚙️"):
                        RenderForm.render_extra_options(ctrl, s, idx, len(items), p)

    

    @staticmethod
    def render_status_selector(ctrl, s, current_status, options):
        current_idx = options.index(current_status) if current_status in options else 0
        new_st = st.selectbox("ST", options, index=current_idx, key=f"st_{s['id']}", label_visibility="collapsed")
        if new_st != current_status:
            if ctrl.update_sub_content(s['id'], new_status=new_st):
                st.rerun()

    @staticmethod
    def render_extra_options(ctrl, s, idx, total, p):
        st.markdown("**Quản lý**")
        c1, c2 = st.columns(2)
        if c1.button("🔼", disabled=(idx==0), key=f"u_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "up")
            st.rerun()
        if c2.button("🔽", disabled=(idx==total-1), key=f"d_{s['id']}", use_container_width=True): 
            ctrl.move_sub_content(s['id'], "down")
            st.rerun()
        
        p_folder = p.get('project_folder') or p.get('folder_name') or ""
        if st.button("🗑️ XÓA", type="primary", use_container_width=True, key=f"del_{s['id']}"):
            if ctrl.delete_sub_content(s['id'], p_folder, s['sub_folder']):
                st.rerun()

    # =================================================================
    # PHẦN 2: PHẦN BIÊN TẬP VÀ XUẤT BẢN VIDEO 
    # =================================================================
    
    @staticmethod
    def render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script):
        """ Giao diện chính của Studio: Sạch sẽ và dễ bảo trì """
        if not isinstance(s, dict):
            st.error("Lỗi dữ liệu: Phân cảnh không hợp lệ.")
            return

        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # --- BƯỚC 1: TRI THỨC GỐC ---
        raw_ctx = ai_script.get_form_knowledge_from_db(s)
        if "⚠️" in raw_ctx: st.warning(raw_ctx)
        else: st.success("✅ Tri thức Metadata sẵn sàng.")

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
        temp_config = {"scenarios": scenarios, "notes": notes, "slogan": "Ứng dụng vàng, giải pháp toàn diện cho ngành kim hoàn", "current_module": mod_name}
        full_draft_prompt = ai_script.generate_ai_prompt(mod_name, form_name, temp_config, user_edited_ctx + workflow_ctx)

        with st.expander("🔍 KIỂM TRA BỨC THƯ GỬI AI", expanded=False):
            final_prompt = st.text_area("Nội dung chuẩn bị gửi đi:", value=full_draft_prompt, height=300, key=f"f_p_{s['id']}")

        st.divider()

        # --- BƯỚC 4: KHU VỰC NÚT BẤM (ĐÃ TÁCH BIỆT LOGIC) ---
        b1, b2 = st.columns(2)
        
        # Nút 1: Gửi AI lấy kịch bản JSON
        if b1.button("🎬 GỞI AI SOẠN KỊCH BẢN JSON", use_container_width=True, key=f"btn_j_{s['id']}"):
            RenderForm._handle_json_generation(ctrl, p, s, ai_script, final_prompt, sel_model, sel_provider, sel_voice_id)

        # Nút 2: Xuất Video hoàn chỉnh
        if b2.button("🚀 XUẤT VIDEO HOÀN CHỈNH", type="primary", use_container_width=True, key=f"btn_v_{s['id']}"):
            RenderForm._handle_video_export(ctrl, p, s, sel_model, sel_provider, sel_voice_id)

    # --- HÀM HỖ TRỢ 1: DÒ TÌM FILE VIDEO GỐC ---
    @staticmethod
    def _get_raw_video_path(p, s):
        storage_root = Path(Config.BASE_STORAGE)
        
        # Lấy các biến tên
        p_name = p.get('project_folder') or p.get('folder_name') or ""
        s_name = s.get('sub_folder', "")

        # Danh sách các khả năng đường dẫn có thể tồn tại (Có dấu và Không dấu)
        possible_paths = [
            storage_root / p_name / s_name,
            storage_root / Config.slugify_vietnamese(p_name) / Config.slugify_vietnamese(s_name)
        ]

        target_dir = possible_paths[0] # Mặc định
        for path in possible_paths:
            if path.exists():
                target_dir = path
                break

        # Bây giờ mới tìm file 'raw' trong target_dir đã xác định
        if target_dir.exists():
            for item in os.listdir(target_dir):
                if "raw" in item.lower():
                    return target_dir / item, target_dir
                    
        return None, target_dir
    
    # --- HÀM HỖ TRỢ 2: XỬ LÝ GỌI AI & LƯU ASSETS ---
    @staticmethod
    def _handle_json_generation(ctrl, p, s, ai_script, prompt, model, provider, voice_id):
        print(f"\n🚀 [DEBUG] GỬI AI: {provider} | {model}")
        with st.spinner(f"🎭 {provider} đang soạn bài..."):
            steps = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if steps:
                # Lưu vào assets để lưu trữ lâu dài
                _, sub_path = RenderForm._get_raw_video_path(p, s)
                asset_dir = sub_path / "assets"
                asset_dir.mkdir(parents=True, exist_ok=True)
                with open(asset_dir / "latest_script.json", "w", encoding="utf-8") as f:
                    json.dump(steps, f, ensure_ascii=False, indent=4)
                
                st.session_state.update({"current_steps": steps, "selected_voice": voice_id})
                st.toast("✅ Đã lưu kịch bản vào folder assets!")
                RenderForm.navigate_to_studio(p, s, "Quay tự động 🤖")
            else:
                st.error("❌ Lỗi: AI không phản hồi hoặc JSON sai định dạng.")

    # --- HÀM HỖ TRỢ 3: QUY TRÌNH HẬU KỲ VIDEO ---
    @staticmethod
    def _handle_video_export(ctrl, p, s, model, provider, voice_id):
        video_raw, sub_path = RenderForm._get_raw_video_path(p, s)
        video_out = sub_path / "final_tutorial.mp4"

        if not video_raw:
            st.error(f"❌ Không thấy file 'raw' tại: {sub_path}")
            return

        print(f"\n🔥 [DEBUG] BẮT ĐẦU XUẤT VIDEO: {video_raw.name}")
        with st.spinner(f"🤖 {provider} đang render hậu kỳ..."):
            # Bước 1: Whisper (Chuyển sang string path)
            raw_segments = RenderForm.ai_manager.transcribe_with_segments(str(video_raw))
            
            if raw_segments:
                # Bước 2: AI Rewrite
                refined = RenderForm.ai_manager.rewrite_segments(raw_segments, s['sub_folder'], model=model, provider=provider)
                
                # Bước 3: Render MoviePy
                success = RenderForm.ai_manager.export_final_video(str(video_raw), refined, str(video_out), voice_id)
                
                if success:
                    st.success("🔥 Đã xuất bản video!")
                    st.video(str(video_out))
                    ctrl.update_sub_content(s['id'], new_status="Hoàn chỉnh")
            else:
                st.error("❌ Whisper không tìm thấy đoạn thoại nào trong video gốc.")
    
    # --- HÀM HỖ TRỢ 4: ĐIỀU HƯỚNG SANG TRANG STUDIO ---
    @staticmethod
    def navigate_to_studio(p, s, tab_name):
        # Không cần import streamlit ở đây nữa vì đầu file đã có 'import streamlit as st'
        st.session_state.current_tab = tab_name 
        st.session_state.selected_scene = s # Lưu phân cảnh đang chọn để Studio biết đường mà mở
        st.rerun()
    
    # --- HÀM HỖ TRỢ 5: MỞ KỊCH BẢN ĐÃ LƯU TỪ AI ---
    @staticmethod
    def _handle_json_generation(ctrl, p, s, ai_script, prompt, model, provider, voice_id):
        print(f"\n🚀 [DEBUG] GỬI AI: {provider} | {model}")
        with st.spinner(f"🎭 {provider} đang soạn bài..."):
            steps = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
            if steps:
                # 1. Lấy đường dẫn chuẩn (Ưu tiên tìm folder có sẵn)
                _, sub_path = RenderForm._get_raw_video_path(p, s)
                asset_dir = sub_path / "assets"
                asset_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = asset_dir / "latest_script.json"
                
                # 2. Ghi file
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(steps, f, ensure_ascii=False, indent=4)
                
                # 3. Cập nhật session để giao diện hiển thị ngay
                st.session_state[f"last_json_{s['id']}"] = steps
                st.session_state[f"last_path_{s['id']}"] = str(file_path)
                
                st.toast(f"✅ Đã lưu vào: {file_path.name}")
                # Không rerun ngay để người dùng kịp nhìn thấy kịch bản vừa hiện ra
            else:
                st.error("❌ Lỗi: AI không phản hồi hoặc JSON sai định dạng.")