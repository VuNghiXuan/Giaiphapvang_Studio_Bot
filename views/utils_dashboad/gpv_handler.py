import streamlit as st
import os
import json
import time
from playwright.sync_api import Page
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
from ..components.dashboard_component import render_item_rows

# ==========================================
# 1. LOGIC GIAO DIỆN (STREAMLIT UI)
# ==========================================

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
                        if not any(s['sub_title'] == full_t for s in db_subs):
                            ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
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
                results = extractor.update_module_details(modul_name, mod_home['status'])
                for f_name in results.keys():
                    full_t = f"{modul_name}|{f_name}"
                    if not any(s['sub_title'] == full_t for s in db_subs):
                        ctrl.add_sub_content(p['id'], full_t, p['folder_name'])
                st.rerun()

    display_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    render_item_rows(ctrl, p, display_subs)


# ==========================================
# 2. LOGIC TRUY XUẤT KIẾN THỨC (KNOWLEDGE)
# ==========================================

def get_form_knowledge(module_name, form_name):
    """Trích xuất kiến thức tinh gọn cho AI"""
    # Lấy đường dẫn động từ root dự án
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    json_path = os.path.join(base_dir, "data", "knowledge_source.json")
    
    if not os.path.exists(json_path):
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        target_key = f"{module_name}|{form_name}"
        if target_key not in data:
            return f"⚠️ Dữ liệu cho '{form_name}' chưa được quét."

        struct = data[target_key].get('structure', {})
        fields = [f.get('label') for f in struct.get('form_fields', []) if f.get('label')]
        
        return f"""
### THÔNG TIN NGHIỆP VỤ: {form_name}
- **Module:** {module_name}
- **Bảng:** {', '.join(struct.get('columns', []))}
- **Nút:** {', '.join(struct.get('actions', []))}
- **Ô nhập:** {', '.join(fields)}
"""
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"


# ==========================================
# 3. LOGIC ĐIỀU KHIỂN BOT (AUTOMATION)
# ==========================================

def highlight_element(page: Page, selector: str, duration_seconds: float = 1.5):
    """Highlight phần tử trên web trước khi thao tác"""
    try:
        page.wait_for_selector(selector, state="visible", timeout=5000)
        
        # JS tạo hiệu ứng phồng nhẹ và viền đỏ
        js_code = f"""
            (sel) => {{
                const el = document.querySelector(sel);
                if (el) {{
                    el.dataset.oldStyle = el.style.cssText;
                    el.style.cssText = "border: 3px solid red !important; background: rgba(255,255,0,0.2) !important; transition: 0.3s; transform: scale(1.05); z-index: 9999;";
                }}
            }}
        """
        page.evaluate(js_code, selector)
        time.sleep(duration_seconds)
        
        # Xóa highlight
        page.evaluate("(sel) => { const el = document.querySelector(sel); if(el) el.style.cssText = el.dataset.oldStyle; }", selector)
    except:
        pass

def bot_execute_step(page: Page, step_action, target_label, knowledge_full_data):
    """Thực hiện một bước trong kịch bản"""
    struct = knowledge_full_data.get('structure', {})
    
    # 1. Tìm selector
    selector = f"text='{target_label}'" # Mặc định tìm theo text nút
    
    # Nếu là field nhập liệu, tìm theo ID/Name
    field = next((f for f in struct.get('form_fields', []) if f['label'] == target_label), None)
    if field:
        selector = f"#{field.get('id')}" if field.get('id') else f"[name='{field.get('name')}']"

    # 2. Highlight và Chạy
    highlight_element(page, selector)
    
    if step_action == "click":
        page.click(selector)
    elif step_action == "fill":
        page.fill(selector, "Dữ liệu mẫu") # Chỗ này Vũ có thể lấy từ file mock_data

def suggest_video_scenarios(module_name, form_name):
    """Gợi ý các loại video có thể sản xuất dựa trên nút bấm tìm thấy"""
    knowledge = get_form_knowledge(module_name, form_name)
    if not knowledge: return []
    
    scenarios = []
    # Logic: Nếu thấy chữ 'Thêm' hoặc 'Lưu' -> Gợi ý kịch bản Thêm mới
    if any(keyword in knowledge for keyword in ['Thêm', 'Lưu', 'Tạo']):
        scenarios.append({"id": "ADD", "label": "Hướng dẫn Thêm mới", "icon": "➕"})
    
    if any(keyword in knowledge for keyword in ['Xóa', 'Hủy', 'Bỏ']):
        scenarios.append({"id": "DEL", "label": "Hướng dẫn Xóa/Hủy", "icon": "🗑️"})
        
    if any(keyword in knowledge for keyword in ['Sửa', 'Cập nhật']):
        scenarios.append({"id": "EDIT", "label": "Hướng dẫn Chỉnh sửa", "icon": "📝"})
        
    return scenarios