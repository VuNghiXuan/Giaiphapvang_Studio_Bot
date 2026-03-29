import streamlit as st
import os
import json
import time
from playwright.sync_api import Page
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
from ..utils_dashboad.utils import get_status_info
# from ..components.dashboard_component import render_item_rows
from google import genai
from google.genai import types # Dùng để cấu hình kiểu dữ liệu trả về
from config import Config
from dotenv import load_dotenv

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
    """Trích xuất kiến thức tinh gọn cho AI - Đã đồng bộ đường dẫn với Scraper"""
    
    # Dùng trực tiếp từ Config để khớp với GiaiphapvangScraper
    json_path = Config.KNOWLEDGE_JSON_PATH
    
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(json_path):
        return f"⚠️ Lỗi: Không tìm thấy file dữ liệu tại: {json_path}. Vũ hãy chạy quét (Scrape) trước nhé!"

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        target_key = f"{module_name}|{form_name}"
        
        if target_key not in data:
            return f"⚠️ Dữ liệu cho '{form_name}' chưa có trong file JSON."

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
        return f"❌ Lỗi đọc file JSON: {str(e)}"
    

# ==========================================
# 3. LOGIC ĐIỀU KHIỂN BOT (AUTOMATION)MODULES
# ==========================================
"""
📂 Cấu trúc file logic của Vũ bây giờ sẽ như sau:
Hàm 1: get_form_knowledge (Lấy dữ liệu thô cho AI).

Hàm 2: highlight_element (Hiệu ứng visual).

Hàm 3: bot_execute_step (Động cơ thực thi mượt).

Hàm 4: run_full_script (Nhạc trưởng điều khiển toàn bộ).

"""
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


def bot_execute_step(page: Page, step_action, target_label, value=None, knowledge_full_data=None):
    """
    Thực hiện một bước trong kịch bản với hiệu ứng mượt mà để quay video.
    :param value: Giá trị cần nhập (nếu là fill)
    :param knowledge_full_data: Dữ liệu cấu trúc form từ file JSON
    """
    if not knowledge_full_data:
        knowledge_full_data = {}
        
    struct = knowledge_full_data.get('structure', {})
    
    # --- 1. XÁC ĐỊNH SELECTOR CHUẨN ---
    # Mặc định tìm theo text (cho các nút)
    selector = f"text='{target_label}'" 
    
    # Nếu là field nhập liệu, tìm theo ID/Name từ Knowledge Base
    field = next((f for f in struct.get('form_fields', []) if f['label'] == target_label), None)
    if field:
        if field.get('id'):
            selector = f"#{field.get('id')}"
        elif field.get('name'):
            selector = f"[name='{field.get('name')}']"

    try:
        # Đảm bảo phần tử xuất hiện và cuộn nó vào vùng nhìn thấy (Viewport)
        element = page.wait_for_selector(selector, state="visible", timeout=5000)
        element.scroll_into_view_if_needed()
        
        # Lấy tọa độ thực tế của phần tử để di chuột
        box = element.bounding_box()
        if not box:
            print(f"⚠️ Không lấy được tọa độ cho: {target_label}")
            return

        center_x = box['x'] + box['width'] / 2
        center_y = box['y'] + box['height'] / 2

        # --- 2. TRÌNH DIỄN (VISUAL) ---
        
        # Di chuyển chuột mượt đến mục tiêu (steps=25 giúp chuột lướt mượt, không giật)
        page.mouse.move(center_x, center_y, steps=25)
        
        # Highlight phần tử để người xem chú ý (gọi hàm highlight đã viết của Vũ)
        # Tôi thêm một chút nghỉ để hiệu ứng highlight kịp "ngấm" vào mắt người xem
        
        highlight_element(page, selector, duration_seconds=1.0)

        # --- 3. THỰC THI HÀNH ĐỘNG ---
        
        if step_action == "click":
            # Click trực tiếp tại tọa độ chuột đang đứng
            page.mouse.click(center_x, center_y)
            print(f"✅ Đã Click: {target_label}")
            
        elif step_action == "fill":
            # Click vào ô nhập trước khi gõ
            page.mouse.click(center_x, center_y)
            
            # Xóa nội dung cũ nếu có (Ctrl+A -> Backspace)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            
            # Gõ nội dung với độ trễ giữa các phím (giống người thật đang gõ)
            text_to_fill = str(value) if value else "Dữ liệu mẫu"
            page.keyboard.type(text_to_fill, delay=100) 
            print(f"✅ Đã Nhập '{text_to_fill}' vào: {target_label}")

        elif step_action == "wait":
            # Dùng cho các quãng nghỉ để Voice AI kịp đọc
            wait_time = float(value) if value else 1.0
            time.sleep(wait_time)

        # Nghỉ nhẹ sau mỗi bước để video không quá dồn dập
        time.sleep(0.5)

    except Exception as e:
        print(f"❌ Lỗi khi thực hiện bước [{step_action}] trên {target_label}: {str(e)}")

def run_full_script(page: Page, script_steps, module_name, form_name):
    """
    Nhạc trưởng: Chạy toàn bộ kịch bản từ mảng JSON của AI.
    :param script_steps: Mảng các bước [{action, selector, value, description, ...}]
    :param module_name: Tên module (để bốc kiến thức)
    :param form_name: Tên form (để bốc kiến thức)
    """
    print(f"🎬 Bắt đầu quay video hướng dẫn cho: {form_name}")
    
    # 1. Lấy toàn bộ kiến thức của Form này để Bot có Selector chuẩn
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
    json_path = os.path.join(base_dir, "data", "knowledge_source.json")
    
    knowledge_full_data = {}
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
            knowledge_full_data = all_data.get(f"{module_name}|{form_name}", {})

    # 2. Duyệt qua từng bước trong kịch bản
    for i, step in enumerate(script_steps):
        action = step.get("action")      # click, fill, wait, speak
        label = step.get("label")        # Tên nhãn (ví dụ: "Tên chi nhánh")
        value = step.get("value")        # Dữ liệu nhập (nếu có)
        desc = step.get("description")   # Mô tả bước (để hiện sub)

        print(f"  [Bước {i+1}]: {desc}")

        # Nếu là hành động 'speak', ở đây Vũ sẽ gọi Voice AI (sẽ làm sau)
        # Hiện tại mình chỉ in ra hoặc log lại
        if action == "speak":
            print(f"🎙️ Voice AI nói: {value}")
            time.sleep(1.0) # Đợi một chút cho giống đang nói
            continue

        # Gọi hàm thực thi mượt mà mà mình đã tối ưu
        bot_execute_step(
            page=page,
            step_action=action,
            target_label=label,
            value=value,
            knowledge_full_data=knowledge_full_data
        )

    print(f"✅ Đã hoàn thành quay video cho {form_name}!")


def get_ai_script(prompt):
    """
    Gửi Prompt cho Gemini qua SDK mới và lấy kịch bản JSON sạch.
    """
    try:
        # 1. Khởi tạo Client (Lấy API Key từ môi trường)
        api_key = os.getenv("GOOGLE_API_KEY")
        model = os.getenv("GEMINI_MODEL")
        
        if not api_key:
            print("❌ Lỗi: Chưa cấu hình GEMINI_API_KEY trong file .env")
            return []
            
        client = genai.Client(api_key=api_key)
        
        # 2. Cấu hình Model và ép kiểu trả về là JSON
        # SDK mới dùng tham số 'config' thay vì 'generation_config' trực tiếp
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # 3. Xử lý kết quả trả về
        if not response.text:
            print("⚠️ AI không trả về nội dung.")
            return []
            
        script_data = json.loads(response.text)
        
        # Nếu AI trả về object có chứa key 'steps', mình bốc cái mảng đó ra
        if isinstance(script_data, dict) and "steps" in script_data:
            return script_data["steps"]
            
        return script_data if isinstance(script_data, list) else []

    except Exception as e:
        print(f"❌ Lỗi khi gọi SDK Gemini: {e}")
        return []
    


def generate_ai_prompt(module_name, form_name, ai_config, form_context):
        """
        Tạo 'Siêu Prompt' kết hợp Kiến thức thô + Cấu hình từ Dashboard.
        """
        scenarios = ", ".join(ai_config.get("scenarios", ["ADD"]))
        slogan = ai_config.get("slogan", "Giải Pháp Vàng - Đồng hành cùng tiệm vàng của bạn!")
        notes = ai_config.get("notes", "")

        prompt = f"""
    Bạn là chuyên gia soạn kịch bản Automation Video cho phần mềm quản lý tiệm vàng Giaiphapvang.net.
    Dựa trên cấu trúc trang Web dưới đây, hãy soạn kịch bản để Bot (Playwright) chạy chuột và Voice AI đọc lời bình.

    --- 🏗️ CẤU TRÚC TRANG (CONTEXT) ---
    {form_context}

    --- 🎯 YÊU CẦU NGHIỆP VỤ ---
    - Loại hướng dẫn: {scenarios}
    - Ghi chú đặc biệt từ Vũ: "{notes}"
    - Cách xưng hô: Thân thiện (dùng 'mình', 'các bạn').
    - Slogan kết video: {slogan}

    --- 📤 ĐỊNH DẠNG ĐẦU RA (JSON ONLY) ---
    Trả về một mảng 'steps' duy nhất. Mỗi phần tử là 1 bước:
    {{
    "action": "click" | "fill" | "wait" | "speak",
    "label": "Tên nhãn chính xác từ Context (ví dụ: 'Tên khách hàng')",
    "value": "Dữ liệu thực tế ngành vàng (nếu fill) | Lời bình (nếu speak) | Số giây (nếu wait)",
    "description": "Mô tả ngắn để hiện Subtitle"
    }}

    LƯU Ý: 
    1. Hành động 'speak' nên xuất hiện TRƯỚC khi thực hiện click/fill.
    2. Dữ liệu 'fill' phải thực tế (Ví dụ: Trọng lượng 1.234, Loại vàng 24K).
    3. 'label' phải khớp 100% với 'Ô nhập' hoặc 'Nút' trong Context.
    """
        return prompt

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


# ---------------------------Code từ file dasboard sang----------------
def render_item_rows(ctrl, p, items):
    """Hàm chính để render danh sách các Form"""
    status_options = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    
    for idx, s in enumerate(items):
        sub_path = os.path.join(Config.BASE_STORAGE, p['folder_name'], s['sub_folder'])
        current_status = get_status_info(sub_path, s.get('status'))
        
        # Tách tên Module và Form từ "Module|Form"
        parts = s['sub_title'].split('|')
        mod_name = parts[0]
        form_name = parts[-1]

        with st.container(border=True):
            col_info, col_status, col_actions = st.columns([3, 1.5, 2])
            
            # --- Cột Thông Tin ---
            col_info.markdown(f"**{form_name}**")
            col_info.caption(f"📁 {s['sub_folder']}")
            
            # --- Cột Trạng Thái ---
            with col_status:
                render_status_selector(ctrl, s, current_status, status_options)

            # --- Cột Thao Tác (Quay & Cấu hình) ---
            with col_actions:
                c_man, c_auto, c_opt = st.columns([1, 1, 1])
                
                # 1. Quay thủ công
                if c_man.button("🎥", key=f"m_{s['id']}", help="Quay thủ công"):
                    navigate_to_studio(p, s, "Quay thủ công")

                # 2. Quay tự động (Mở Popover để cấu hình AI trước khi quay)
                with c_auto.popover("🤖", help="Cấu hình quay tự động"):
                    render_ai_automation_config(p, s, mod_name, form_name)

                # 3. Menu phụ (Xóa/Di chuyển)
                with c_opt.popover("⚙️"):
                    render_extra_options(ctrl, s, idx, len(items), p)

# --- CÁC HÀM BỔ TRỢ ---

def render_status_selector(ctrl, s, current_status, options):
    """Hàm xử lý chọn trạng thái"""
    new_st = st.selectbox("ST", options, label_visibility="collapsed",
                          index=options.index(current_status) if current_status in options else 0,
                          key=f"st_{s['id']}")
    if new_st != s.get('status'):
        ctrl.update_sub_content(s['id'], s['sub_title'], new_st)
        st.rerun()

def render_ai_automation_config(p, s, mod_name, form_name):
    """Giao diện Cấu hình AI và kích hoạt quy trình soạn kịch bản"""
    st.markdown(f"### 🤖 Cấu hình AI: {form_name}")
    
    scenarios_list = Config.AI_SCENARIOS
    selected_ids = st.multiselect(
        "Loại hướng dẫn muốn tạo:",
        options=[opt['id'] for opt in scenarios_list],
        format_func=lambda x: next(o['label'] for o in scenarios_list if o['id'] == x),
        default=["ADD"],
        key=f"scen_{s['id']}"
    )
    
    slogan = st.text_input("Slogan kết video:", value=Config.DEFAULT_SLOGAN, key=f"slo_{s['id']}")
    notes = st.text_area("Ghi chú nhấn mạnh cho AI:", placeholder="Ví dụ: Lưu ý phí bù tuổi...", key=f"note_{s['id']}")
    
    # Nút bấm quan trọng nhất
    if st.button("🚀 BẮT ĐẦU SOẠN & QUAY", key=f"start_{s['id']}", type="primary", use_container_width=True):
        with st.spinner("🧠 AI đang phân tích Form và soạn kịch bản..."):
            # BƯỚC 1: Lấy kiến thức thô (Text) từ file JSON đã quét
            form_context = get_form_knowledge(mod_name, form_name)
            
            if "⚠️" in form_context: # Trường hợp chưa có dữ liệu quét
                st.error(form_context)
                return

            # BƯỚC 2: Gom cấu hình vào object
            ai_config = {
                "target_domain": Config.TARGET_DOMAIN,
                "scenarios": selected_ids,
                "slogan": slogan,
                "notes": notes,
                "mod_name": mod_name,
                "form_name": form_name
            }
            
            # BƯỚC 3: Tạo Prompt và gửi cho Gemini
            prompt = generate_ai_prompt(mod_name, form_name, ai_config, form_context)
            steps = get_ai_script(prompt)
            
            if steps:
                # BƯỚC 4: Lưu mọi thứ vào Session để Studio sử dụng
                st.session_state.ai_config = ai_config
                st.session_state.current_steps = steps # Kịch bản JSON
                
                st.toast("✅ Đã soạn xong kịch bản!", icon="🤖")
                navigate_to_studio(p, s, "Quay tự động 🤖")
            else:
                st.error("❌ AI không thể soạn kịch bản. Hãy kiểm tra API Key hoặc dữ liệu quét.")

def render_extra_options(ctrl, s, idx, total, p):
    """Hàm xử lý các nút Up, Down, Delete"""
    c1, c2 = st.columns(2)
    if c1.button("🔼", key=f"up_{s['id']}", disabled=(idx==0), use_container_width=True):
        ctrl.move_sub_content(s['id'], "up"); st.rerun()
    if c2.button("🔽", key=f"dn_{s['id']}", disabled=(idx==total-1), use_container_width=True):
        ctrl.move_sub_content(s['id'], "down"); st.rerun()
        
    st.divider()
    if st.button("🗑️ XÓA FORM", key=f"del_{s['id']}", type="primary", use_container_width=True):
        ctrl.delete_sub_content(s['id'], p['folder_name'], s['sub_folder'])
        st.rerun()

def navigate_to_studio(p, s, tab_name):
    """Chuyển hướng sang Studio"""
    st.session_state.active_project = p
    st.session_state.active_sub = s
    st.session_state.view = "studio"
    st.session_state.active_tab = tab_name
    st.rerun()

def validate_prompt_size(prompt):
    """Kiểm tra xem Prompt có quá dài không (Ước tính theo ký tự)"""
    # Bản Gemini Free Tier thường giới hạn khoảng 32k - 1M token, 
    # nhưng để an toàn và tránh 429, mình nên kiểm soát ở mức vừa phải.
    char_count = len(prompt)
    if char_count > 20000: # Ngưỡng cảnh báo
        return False, f"⚠️ Prompt quá dài ({char_count} ký tự). Hãy bớt ghi chú lại!"
    return True, char_count