import streamlit as st
import os
from pathlib import Path
from config import Config
from ..utils_dashboad.utils import get_status_info, render_status_badge
from ..utils_dashboad.ai_config_for_gpv_component import AIConfigHandler
from core.ai_manager import AIManager

class GPVComponent:  
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
                    GPVComponent.render_status_selector(ctrl, s, current_status, status_options)

                with col_actions:
                    st.write("") 
                    c_man, c_auto, c_opt = st.columns([1, 1, 1])
                    
                    # 🎥 Nút quay thủ công
                    if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                        GPVComponent.navigate_to_studio(p, s, "Quay thủ công")
                    
                    # 🤖 Nút AI soạn kịch bản (Popover)
                    with c_auto.popover("🤖", help="AI soạn kịch bản"):
                        # FIX: Truyền ctrl vào đầu tiên để render_ai_config_panel có thể dùng lấy items dự án
                        GPVComponent.render_ai_config_panel(ctrl, p, s, mod_name, form_name, ai_script)
                    
                    # ⚙️ Nút tùy chọn khác
                    with c_opt.popover("⚙️"):
                        GPVComponent.render_extra_options(ctrl, s, idx, len(items), p)

    

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
        """ Giao diện Studio: Phân tách logic và UI để dễ Debug """
        if not isinstance(s, dict):
            st.error("Lỗi dữ liệu: Phân cảnh (s) không hợp lệ.")
            return

        st.subheader(f"🎬 Phê duyệt kịch bản: {form_name}")
        
        # --- BƯỚC 1: TRI THỨC GỐC ---
        raw_ctx = ai_script.get_form_knowledge_from_db(s)
        if "⚠️" in raw_ctx: st.warning(raw_ctx)
        else: st.success("✅ Tri thức Metadata sẵn sàng.")

        # --- BƯỚC 2: CẤU HÌNH BỘ NÃO ---
        st.markdown("### 🧠 Cấu hình Bộ não AI")
        col1, col2, col3 = st.columns([1.5, 1.5, 1.2])
        
        providers = getattr(ai_script, 'available_providers', ["Gemini", "Groq", "Ollama"])
        env_provider = os.getenv("DEFAULT_PROVIDER", "Groq")
        
        default_p_idx = providers.index(env_provider) if env_provider in providers else 0
        sel_provider = col1.selectbox("Nhà cung cấp:", providers, index=default_p_idx, key=f"prov_{s['id']}")

        if sel_provider == "Gemini":
            models = [os.getenv("GEMINI_MODEL", "gemini-1.5-flash"), "gemini-2.0-flash"]
            sel_model = col2.selectbox("Bộ não AI:", models, key=f"mdl_{s['id']}")
        elif sel_provider == "Groq":
            models = [os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), "mixtral-8x7b-32768"]
            sel_model = col2.selectbox("Bộ não AI:", models, key=f"mdl_{s['id']}")
        else:
            sel_model = col2.text_input("Model Ollama:", value=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"), key=f"mdl_{s['id']}")

        voice_map = getattr(Config, 'VOICE_MAP', {"Hoài My (Nữ)": "vi-VN-HoaiMyNeural", "Nam Minh (Nam)": "vi-VN-NamMinhNeural"})
        sel_voice_label = col3.selectbox("Giọng đọc:", list(voice_map.keys()), key=f"voc_{s['id']}")
        sel_voice_id = voice_map[sel_voice_label]

        # --- BƯỚC 3: WORKFLOW & PROMPT ---
        with st.expander("📄 Tùy chỉnh tri thức & Workflow", expanded=False):
            user_edited_ctx = st.text_area("Context nghiệp vụ:", value=raw_ctx, height=150, key=f"raw_{s['id']}")
            
            scenarios_options = [opt['id'] for opt in Config.AI_SCENARIOS] + ["WORKFLOW"]
            scenarios = st.multiselect("Mục tiêu:", options=scenarios_options, default=["ADD"], key=f"sc_{s['id']}")
            
            workflow_ctx = ""
            if "WORKFLOW" in scenarios:
                all_items = ctrl.get_sub_contents(p['id']) 
                selected_next = st.multiselect("Nối cảnh tiếp theo:", options=[i for i in all_items if i['id'] != s['id']], 
                                               format_func=lambda x: x['sub_title'], key=f"wf_{s['id']}")
                for f in selected_next:
                    workflow_ctx += f"\n\n-- TIẾP THEO: {f.get('sub_title')} --\n{ai_script.get_form_knowledge_from_db(f)}"

        notes = st.text_area("Lưu ý từ Đạo diễn Vũ:", key=f"nt_{s['id']}", placeholder="Dùng từ ngữ chuyên ngành...")
        temp_config = {"scenarios": scenarios, "notes": notes, "slogan": Config.DEFAULT_SLOGAN, "current_module": mod_name}
        full_draft_prompt = ai_script.generate_ai_prompt(mod_name, form_name, temp_config, user_edited_ctx + workflow_ctx)

        with st.expander("🔍 KIỂM TRA PROMPT", expanded=False):
            final_prompt = st.text_area("Final Prompt:", value=full_draft_prompt, height=200, key=f"f_p_{s['id']}")

        st.divider()

        # --- BƯỚC 4: NÚT BẤM VÀ ĐIỀU HƯỚNG ---
        b1, b2 = st.columns(2)
        
        # Gọi hàm xử lý riêng cho gọn
        GPVComponent._render_action_buttons(b1, b2, ctrl, p, s, ai_script, final_prompt, sel_model, sel_provider, sel_voice_id)

    @staticmethod
    def _render_action_buttons(col_json, col_video, ctrl, p, s, ai_script, prompt, model, provider, voice_id):
        """ Hàm nội bộ xử lý logic nút bấm với Debug Print """
        
        if col_json.button("🎬 GỞI AI BIÊN SOẠN KỊCH BẢN JSON", use_container_width=True, key=f"btn_j_{s['id']}"):
            print("\n" + "="*50)
            print(f"🚀 [DEBUG] BẮT ĐẦU LẤY KỊCH BẢN JSON")
            print(f"📍 Phân cảnh: {s.get('sub_title')}")
            print(f"🤖 Provider: {provider} | Model: {model}")
            print(f"📝 Prompt Length: {len(prompt)} characters")
            
            with st.spinner(f"🎭 {provider} đang soạn bài..."):
                steps = ai_script.get_ai_script(prompt=prompt, model=model, provider=provider)
                
                if steps:
                    print(f"✅ [DEBUG] Lấy JSON thành công! Số lượng bước: {len(steps)}")
                    st.session_state.update({"current_steps": steps, "selected_voice": voice_id, "active_model": model, "active_provider": provider})
                    st.toast(f"✅ Đã nhận kịch bản từ {model}")
                    GPVComponent.navigate_to_studio(p, s, "Quay tự động 🤖")
                else:
                    print(f"❌ [DEBUG] Hàm get_ai_script trả về None hoặc Rỗng")
            print("="*50 + "\n")

        if col_video.button("🚀 XUẤT VIDEO", type="primary", use_container_width=True, key=f"btn_v_{s['id']}"):
            print("\n" + "="*50)
            print(f"🔥 [DEBUG] BẮT ĐẦU QUY TRÌNH XUẤT VIDEO HOÀN CHỈNH")
            
            # 1. Thiết lập đường dẫn
            storage_root = os.getenv("STORAGE_PATH", "storage")
            p_folder = p.get('folder_name') or p.get('project_folder') or "default"
            sub_path = Path(storage_root) / p_folder / s['sub_folder']
            
            # 2. BỘ LỌC TÌM KIẾM THÔNG MINH (TRỊ VỤ MẤT ĐUÔI FILE)
            video_raw = None
            if sub_path.exists():
                # Lấy tất cả các mục trong folder
                all_items = os.listdir(sub_path)
                for item in all_items:
                    # Kiểm tra xem tên có phải 'raw' (không phân biệt hoa thường/đuôi)
                    if item.lower().split('.')[0] == "raw":
                        potential_path = sub_path / item
                        if potential_path.is_file(): # CHỈ NHẬN FILE, KHÔNG NHẬN FOLDER
                            video_raw = potential_path
                            print(f"🎯 [DEBUG] Đã tìm thấy file gốc thực sự: {item}")
                            break

            video_out = sub_path / "final_tutorial.mp4"

            # 3. Kiểm tra và thực hiện Render
            if video_raw is None or not video_raw.exists():
                st.error(f"❌ Không tìm thấy file gốc 'raw' tại: {sub_path}")
                if sub_path.exists():
                    st.write("Folder hiện tại chỉ có:", os.listdir(sub_path))
                    st.warning("💡 Nếu 'raw' là folder, Vũ hãy bỏ file video ra ngoài folder đó nhé!")
            else:
                print(f"🔍 [DEBUG] Đường dẫn chốt: {video_raw.absolute()}")
                
                with st.spinner(f"🤖 {provider} đang xử lý hậu kỳ..."):
                    print(f"🎙️ [1/3] Whisper: Đang bóc băng âm thanh...")
                    # Luôn ép kiểu str() để đảm bảo thư viện ngoại vi không bị lỗi path
                    raw_segments = GPVComponent.ai_manager.transcribe_with_segments(str(video_raw))
                    
                    if raw_segments:
                        print(f"✅ Bóc được {len(raw_segments)} đoạn thoại.")
                        print(f"✍️ [2/3] {model}: Đang rewrite lời thoại...")
                        refined = GPVComponent.ai_manager.rewrite_segments(
                            raw_segments, 
                            s['sub_folder'], 
                            model=model, 
                            provider=provider
                        )
                        
                        print(f"🎬 [3/3] MoviePy: Đang render video cuối...")
                        success = GPVComponent.ai_manager.export_final_video(
                            str(video_raw), 
                            refined, 
                            str(video_out), 
                            voice_id
                        )
                        
                        if success:
                            print(f"🏆 [DEBUG] XUẤT VIDEO THÀNH CÔNG!")
                            st.success("🔥 Đã xuất bản video thành công!")
                            st.video(str(video_out))
                            ctrl.update_sub_content(s['id'], new_status="Hoàn chỉnh")
                        else:
                            print(f"❌ [DEBUG] Lỗi render MoviePy.")
                            st.error("❌ Lỗi Render. Kiểm tra lại thư viện hoặc dung lượng đĩa.")
                    else:
                        print(f"❌ [DEBUG] Whisper không tìm thấy âm thanh.")
                        st.error("❌ Whisper không bóc được âm thanh. File raw có tiếng không Vũ?")
            
            print("="*50 + "\n")