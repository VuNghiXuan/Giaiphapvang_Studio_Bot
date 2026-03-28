import streamlit as st
import os
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
# from .dashboard_ui_components import render_item_rows # Import hàm vẽ dòng từ file linh kiện
from ..components.dashboard_component import render_item_rows
import json

def render_gpv_logic(ctrl, p):
    """Logic phân cấp Module cho Giải Pháp Vàng"""
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    
    if st.session_state.current_modul == "🏠 TẤT CẢ MODULS":
        # --- Cấp 1: Danh sách Module ---
        with st.expander("⚙️ ĐỒNG BỘ MODULE (CẤP 1)", expanded=True):
            if st.button("🔍 QUÉT MODULES MỚI", use_container_width=True, type="primary"):
                with st.spinner("Đang quét CMS Giải Pháp Vàng..."):
                    extractor = GiaiphapvangScraper()
                    for mod in extractor.get_home_modules():
                        full_t = f"{mod['text']}|Home"
                        # Chỉ add nếu chưa có trong DB
                        if not any(s['sub_title'] == full_t for s in db_subs):
                            ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                            # Lấy ID vừa tạo để update URL vào cột status (hardcode logic của Vũ)
                            last = [dict(s) for s in ctrl.get_sub_contents(p['id'])][-1]
                            ctrl.update_sub_content(last['id'], full_t, mod['href'])
                    st.rerun()

        moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
        if not moduls: 
            st.info("💡 Vũ ơi, bấm nút quét ở trên để lấy danh sách Module nhé!")
            return
            
        cols = st.columns(3)
        for i, mod in enumerate(moduls):
            count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|")]) - 1
            with cols[i % 3].container(border=True):
                st.markdown(f"### 📦 {mod}")
                st.caption(f"📄 {max(0, count)} Forms con")
                if st.button(f"Mở {mod}", key=f"btn_{mod}", use_container_width=True):
                    st.session_state.current_modul = mod
                    st.rerun()
    else:
        # --- Cấp 2: Danh sách Form con ---
        render_gpv_forms(ctrl, p, st.session_state.current_modul)

def render_gpv_forms(ctrl, p, modul_name):
    """Chi tiết các Form con bên trong một Module"""
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"📂 Module: {modul_name}")
    if c1.button("⬅️ Quay lại"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    if c2.button("🔍 CẬP NHẬT FORM (CẤP 2)", type="primary", use_container_width=True):
        with st.spinner(f"Đang quét Form của {modul_name}..."):
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            if mod_home:
                extractor = GiaiphapvangScraper()
                # Quét chi tiết từ link Home của module
                results = extractor.update_module_details(modul_name, mod_home['status'])
                for f_name in results.keys():
                    full_t = f"{modul_name}|{f_name}"
                    if not any(s['sub_title'] == full_t for s in db_subs):
                        ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                st.rerun()

    # Chỉ hiển thị các dòng thuộc module hiện tại và bỏ dòng |Home đi
    display_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    render_item_rows(ctrl, p, display_subs)


    # ------------Hàm cho AI lấy thông tin file Json biên kịch bản -------------------
    def get_form_knowledge(module_name, form_name):
        """
        Hàm này chỉ làm đúng 1 việc: Đọc JSON -> Lọc đúng Form -> Trả về cho AI
        """
        json_path = "data/knowledge_source.json"
        
        if not os.path.exists(json_path):
            return "⚠️ Chưa có dữ liệu kiến thức, Vũ hãy chạy Quét (Scrape) trước nhé!"

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Key định danh: "Tên Module|Tên Form"
            target_key = f"{module_name}|{form_name}"
            
            if target_key in data:
                info = data[target_key]
                struct = info.get('structure', {})
                
                # Chuẩn bị nội dung 'sạch' nhất để AI không bị lú
                knowledge_text = f"""
                DỮ LIỆU NGHIỆP VỤ CHO FORM: {form_name}
                - Module: {module_name}
                - Các cột hiển thị trên bảng: {', '.join(struct.get('columns', []))}
                - Các nút chức năng có sẵn: {', '.join(struct.get('actions', []))}
                - Các trường nhập liệu (Form Fields): {json.dumps(struct.get('form_fields', []), ensure_ascii=False)}
                """
                return knowledge_text
        except Exception as e:
            return f"❌ Lỗi đọc file: {str(e)}"
        
        return f"🔍 Không tìm thấy kiến thức cho {form_name} trong module {module_name}"