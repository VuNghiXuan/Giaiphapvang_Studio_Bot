import streamlit as st
import nest_asyncio
from Bot_GPV.core.engine.orchestrator import ModuleOrchestrator 
from Bot_GPV.utils.async_helper import run_async
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
from config import Config

# Đảm bảo async chạy được trong Streamlit
nest_asyncio.apply()

# Khởi tạo AI Script global để fix lỗi ImportError
ai_script = AIScripts()

def get_orchestrator():
    """ Khởi tạo Orchestrator an toàn trong session_state """
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = ModuleOrchestrator()
    return st.session_state.orchestrator

def render_gpv_logic(ctrl, p, _ai_script_param):
    """
    Giao diện Cấp 1: Dashboard danh sách Modules
    """
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    # FIX: Đảm bảo project_folder luôn chuẩn theo Config
    project_folder = p.get('folder_name') if p.get('folder_name') else Config.APP_SLUG
    orch = get_orchestrator()

    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        render_gpv_forms(ctrl, p, st.session_state.current_modul, _ai_script_param)
        return 

    st.subheader("📦 Hệ thống Module nghiệp vụ")
    
    # --- KHU VỰC ĐỒNG BỘ CẤP 1 ---
    with st.expander("⚙️ CÀI ĐẶT & ĐỒNG BỘ HỆ THỐNG", expanded=False):
        is_scanning = st.session_state.get("is_scanning", False)
        btn_label = "🕵️ Đang quét... Vui lòng đợi" if is_scanning else "🔍 QUÉT DANH SÁCH MODULES (CẤP 1)"
        
        if st.button(btn_label, width='stretch', disabled=is_scanning):
            st.session_state.is_scanning = True
            with st.spinner("🤖 Bot đang thâm nhập hệ thống..."):
                try:
                    run_async(orch.run(
                        mode="HOME_SCAN", 
                        project_folder=project_folder,
                        tutorial_id=p['id']
                    ))
                    st.session_state.scan_success = True
                except Exception as e:
                    st.error(f"💥 Lỗi: {e}")
                finally:
                    st.session_state.is_scanning = False
            
            if st.session_state.get("scan_success"):
                del st.session_state["scan_success"]
                st.rerun()

    # --- RENDER CARD GRID ---
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    
    # FIX: Lọc danh sách Module sạch hơn, bỏ qua các module kỹ thuật
    forbidden_display = ['Chung', 'Home', 'Default', 'Settings']
    # unique_moduls = sorted(list(set([
    #     s['sub_title'].split('|')[0].strip() 
    #     for s in db_subs if "|Home" in s['sub_title']
    #     and s['sub_title'].split('|')[0].strip() not in forbidden_display
    # ])))

    unique_moduls = ctrl.get_all_modules()
    
    if not unique_moduls:
        st.info("Chưa có dữ liệu Module. Hãy bấm 'Quét Cấp 1' để bắt đầu.")
        return

    cols = st.columns(3)
    # --- TRONG render_gpv_logic ---
    for i, mod in enumerate(unique_moduls):
        # Lấy các form con - Ưu tiên lọc theo cột module_name nếu có
        child_forms = [
            s for s in db_subs 
            if (s.get('module_name') == mod or s['sub_title'].startswith(f"{mod}|")) 
            and "|Home" not in s['sub_title']
        ]
        
        # FIX: Check trạng thái nội soi chính xác
        is_done = any(s.get('status') == "Đã nội soi" for s in child_forms)
        status_icon = "🟢" if is_done else "📁"

        with cols[i % 3].container(border=True):
            st.markdown(f"#### {status_icon} {mod}")
            st.caption(f"📄 {len(child_forms)} Form nghiệp vụ")
            if st.button(f"Mở Module", key=f"btn_nav_{mod}", width='stretch'):
                st.session_state.current_modul = mod
                st.rerun()

def render_gpv_forms(ctrl, p, modul_name, _ai_script_param):
    """
    Giao diện Cấp 2: Quét chi tiết từng Form
    """
    project_folder = p.get('folder_name', Config.APP_SLUG)
    orch = get_orchestrator()
    
    c1, c2 = st.columns([3, 1.2])
    c1.subheader(f"📂 Module: {modul_name}")
    
    if c1.button("⬅️ Quay lại", key="back_to_main"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    # Khóa nút tương tự cho Deep Scan
    is_deep_scanning = st.session_state.get("is_deep_scanning", False)
    deep_btn_label = "🤖 Đang nội soi..." if is_deep_scanning else "🔍 NỘI SOI TOÀN BỘ FORM"

    if c2.button(deep_btn_label, type="primary", width='stretch', disabled=is_deep_scanning):
        st.session_state.is_deep_scanning = True
        with st.spinner(f"🕵️ Bot đang bóc tách module {modul_name}..."):
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            
            if mod_home and mod_home.get('url'):
                run_async(orch.run(
                    mode="DEEP_SCAN",
                    module_url=mod_home['url'], 
                    project_folder=project_folder,
                    modul_name=modul_name,
                    tutorial_id=p['id']
                ))
                st.session_state.deep_scan_done = True
            else:
                st.error("Không tìm thấy URL gốc!")
        
        st.session_state.is_deep_scanning = False
        if st.session_state.get("deep_scan_done"):
            del st.session_state["deep_scan_done"]
            st.rerun()

    # --- HIỂN THỊ DANH SÁCH ---
    all_items = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    
    # Sửa lại logic lọc: Lấy phần đầu của sub_title so sánh cho chắc ăn
    current_subs = []
    for s in all_items:
        title_parts = [part.strip() for part in s['sub_title'].split('|')]
        # Nếu phần đầu khớp với modul_name và không phải là trang Home
        if title_parts[0] == modul_name and "Home" not in title_parts:
            current_subs.append(s)

    if not current_subs:
        st.warning(f"⚠️ Đã tìm thấy Module nhưng chưa có Form con nào thuộc '{modul_name}'. Hãy bấm 'Nội soi'!")
        # Debug thử xem DB có gì
        if st.checkbox("Debug: Xem dữ liệu thô"):
            st.write(all_items[:3]) 
    else:
        from Bot_GPV.views.components.gpv_render_forms_detail import RenderForm
        # Gọi Static Method đúng cách (không khởi tạo class)
        # Sắp xếp theo sub_title để hiển thị đúng thứ tự
        sorted_subs = sorted(current_subs, key=lambda x: x['sub_title'])
        RenderForm.render_item_rows(ctrl, p, sorted_subs, _ai_script_param, project_folder)