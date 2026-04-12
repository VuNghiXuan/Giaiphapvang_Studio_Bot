import streamlit as st
import nest_asyncio
import json
from datetime import datetime
from Bot_GPV.core.engine.orchestrator import ModuleOrchestrator 
from Bot_GPV.utils.async_helper import run_async
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
from config import Config

# Đảm bảo async chạy được trong Streamlit (Tránh lỗi ProactorEventLoop)
nest_asyncio.apply()

# Khởi tạo AI Script global
ai_script = AIScripts()

def get_orchestrator(ctrl): # Đảm bảo hàm này nhận ctrl
    if "orchestrator" not in st.session_state:
        # from Bot_GPV.core.engine.orchestrator import ModuleOrchestrator
        # from Bot_GPV.core.config import Config
        
        # QUAN TRỌNG: Phải truyền ctrl vào đây!
        st.session_state.orchestrator = ModuleOrchestrator(
            config_class=Config, 
            controller_instance=ctrl # <--- KIỂM TRA DÒNG NÀY
        )
    return st.session_state.orchestrator

def render_gpv_logic(ctrl, p, _ai_script_param):
    """
    GIAO DIỆN CẤP 1: Dashboard danh sách Modules (Thẻ Card)
    """
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    project_folder = Config.APP_SLUG
    orch = get_orchestrator(ctrl)

    # Điều hướng nếu đang ở trong một Module cụ thể
    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        render_gpv_forms(ctrl, p, st.session_state.current_modul, _ai_script_param)
        return 

    st.subheader("📦 Hệ thống Module nghiệp vụ")
    
    # --- KHU VỰC CÀI ĐẶT & ĐỒNG BỘ ---
    with st.expander("⚙️ CÀI ĐẶT & ĐỒNG BỘ HỆ THỐNG", expanded=False):
        col_btn, col_info = st.columns([1, 2])
        is_scanning = st.session_state.get("is_scanning", False)
        btn_label = "🕵️ Đang quét..." if is_scanning else "🔍 QUÉT DANH SÁCH MODULES (CẤP 1)"
        
        if col_btn.button(btn_label, width='stretch', disabled=is_scanning):
            st.session_state.is_scanning = True
            with st.spinner("🤖 Bot đang thâm nhập hệ thống giaiphapvang.net..."):
                try:
                    # Chạy Orchestrator để quét danh mục cấp 1 (Menu dọc)
                    run_async(orch.run(
                        mode="HOME_SCAN", 
                        project_folder=project_folder,
                        tutorial_id=p['id']
                    ))
                    st.toast("✅ Đã cập nhật danh sách Module!", icon="🚀")
                    st.session_state.scan_success = True
                except Exception as e:
                    st.error(f"💥 Lỗi thâm nhập: {e}")
                finally:
                    st.session_state.is_scanning = False
            
            if st.session_state.get("scan_success"):
                del st.session_state["scan_success"]
                st.rerun()
        
        col_info.caption(f"📍 Domain: {Config.TARGET_DOMAIN} | 📂 Storage: {Config.APP_SLUG}")

    # --- LẤY DỮ LIỆU TỪ DB ---
    # Sử dụng hàm get_all_modules mới trong StudioController
    unique_moduls = ctrl.get_all_modules()
    db_subs = ctrl.get_sub_contents(p['id']) # Lấy toàn bộ để đếm số lượng form
    
    if not unique_moduls:
        st.info("Chưa có dữ liệu Module. Hãy bấm 'Quét Cấp 1' để Bot tự động nhận diện danh mục.")
        return

    # --- RENDER CARD GRID (3 CỘT) ---
    cols = st.columns(3)
    for i, mod in enumerate(unique_moduls):
        # Lọc các form thuộc module này (để đếm và check trạng thái)
        child_forms = [
            s for s in db_subs 
            if (s.get('module_name') == mod or s['sub_title'].startswith(f"{mod}|")) 
            and "|Home" not in s['sub_title']
        ]
        
        # Check trạng thái: Nếu có ít nhất 1 form đã nội soi thành công
        is_done = any(s.get('status') == "Đã quét" for s in child_forms)
        status_icon = "🟢" if is_done else "📁"
        status_text = "Sẵn sàng" if is_done else "Chưa nội soi"

        with cols[i % 3].container(border=True):
            st.markdown(f"#### {status_icon} {mod}")
            st.caption(f"📄 {len(child_forms)} Form nghiệp vụ | `{status_text}`")
            
            if st.button(f"Mở Module", key=f"btn_nav_{mod}", width='stretch'):
                st.session_state.current_modul = mod
                st.rerun()

def render_gpv_forms(ctrl, p, modul_name, _ai_script_param):
    """
    GIAO DIỆN CẤP 2: Quét chi tiết và quản lý kịch bản cho từng Form
    """
    project_folder = Config.APP_SLUG
    orch = get_orchestrator(ctrl)
    
    # Thanh Header điều hướng
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        if st.button("⬅️ Quay lại Dashboard", key="back_to_main"): 
            st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
            st.rerun()
        st.subheader(f"📂 Module: {modul_name}")

    # Nút Deep Scan (Nội soi toàn bộ)
    is_deep_scanning = st.session_state.get("is_deep_scanning", False)
    deep_btn_label = "🤖 Đang nội soi..." if is_deep_scanning else "🔍 NỘI SOI TOÀN BỘ FORM"

    if header_col2.button(deep_btn_label, type="primary", width='stretch', disabled=is_deep_scanning):
        st.session_state.is_deep_scanning = True
        with st.spinner(f"🕵️ Bot đang bóc tách từng Form trong module {modul_name}..."):
            # Tìm trang Home của Module để lấy URL gốc
            db_subs = ctrl.get_sub_contents(p['id'])
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            
            if mod_home and mod_home.get('url'):
                try:
                    run_async(orch.run(
                        mode="DEEP_SCAN",
                        module_url=mod_home['url'], 
                        project_folder=project_folder,
                        modul_name=modul_name,
                        tutorial_id=p['id']
                    ))
                    st.session_state.deep_scan_done = True
                except Exception as e:
                    st.error(f"Lỗi khi nội soi: {e}")
            else:
                st.error("Không tìm thấy URL gốc để bắt đầu nội soi!")
        
        st.session_state.is_deep_scanning = False
        if st.session_state.get("deep_scan_done"):
            del st.session_state["deep_scan_done"]
            st.rerun()

    st.divider()

    # --- HIỂN THỊ DANH SÁCH FORM CHI TIẾT ---
    all_items = ctrl.get_sub_contents(p['id'])
    
    # Logic lọc chuẩn xác: Theo module_name hoặc prefix sub_title
    current_subs = []
    for s in all_items:
        # Bỏ qua trang Home của module, chỉ lấy các trang chức năng (Sửa, Thêm, Danh sách...)
        if s.get('module_name') == modul_name and "|Home" not in s['sub_title']:
            current_subs.append(s)

    if not current_subs:
        st.warning(f"⚠️ Chưa có Form con nào thuộc '{modul_name}'. Hãy bấm 'NỘI SOI' để Bot quét tự động.")
    else:
        # Import Component hiển thị dòng (Row)
        try:
            from Bot_GPV.views.components.gpv_render_forms_detail import RenderForm
            
            # Sắp xếp theo vị trí hoặc tên
            sorted_subs = sorted(current_subs, key=lambda x: (x.get('position', 0), x['sub_title']))
            
            # Hiển thị tiêu đề bảng dữ liệu
            h1, h2, h3, h4 = st.columns([2.5, 1, 1, 1.5])
            h1.caption("TÊN FORM / CHỨC NĂNG")
            h2.caption("TRẠNG THÁI")
            h3.caption("TRI THỨC")
            h4.caption("THAO TÁC")

            # Gọi Render chi tiết cho từng dòng
            RenderForm.render_item_rows(
                ctrl=ctrl, 
                p=p, 
                items=sorted_subs, 
                _ai_script_param=_ai_script_param, 
                project_folder=project_folder
            )
        except ImportError:
            st.error("❌ Không tìm thấy component 'gpv_render_forms_detail'. Vui lòng kiểm tra lại cấu trúc folder views.")