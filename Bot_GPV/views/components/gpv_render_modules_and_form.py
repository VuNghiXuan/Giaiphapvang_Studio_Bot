import streamlit as st
import os
import json
import asyncio
import nest_asyncio
from pathlib import Path

# Import Engine mới đồng bộ
from Bot_GPV.core.gpv_module_navigator import ModuleNavigator
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
from Bot_GPV.views.components.gpv_render_forms_detail import RenderForm
from config import Config
from Bot_GPV.utils.async_helper import run_async

# Khởi tạo
nest_asyncio.apply()
ai_script = AIScripts()
# Khởi tạo Engine trung tâm
gpv_module_nav = ModuleNavigator()

def render_gpv_logic(ctrl, p, ai_script):
    """
    Hệ điều hành chính: Quản lý Module (Cấp 1)
    """
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    project_folder = p.get('folder_name', Config.APP_SLUG)

    # ĐIỀU HƯỚNG SANG CẤP 2 (DEEP SCAN)
    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        render_gpv_forms(ctrl, p, st.session_state.current_modul, ai_script)
        return 

    st.subheader("📦 Hệ thống Module nghiệp vụ")
    
    # --- KHU VỰC ĐỒNG BỘ CẤP 1 ---
    with st.expander("⚙️ CÀI ĐẶT & ĐỒNG BỘ HỆ THỐNG", expanded=False):
        if st.button("🔍 QUÉT DANH SÁCH MODULES (CẤP 1)", use_container_width=True):
            with st.spinner("🕵️ Đang hốt danh sách Modules gốc..."):
                home_modules = run_async(gpv_module_nav.run_task(
                    mode="HOME_SCAN", 
                    project_folder=project_folder
                ))
                
                if home_modules:
                    for mod in home_modules:
                        full_t = f"{mod['text']}|Home"
                        if not any(s['sub_title'] == full_t for s in db_subs):
                            ctrl.add_sub_content(
                                t_id=p['id'], 
                                sub_title=full_t, 
                                parent_folder=project_folder, 
                                url=mod['href'],
                                metadata={"type": "module_home", "source": "GPVEngine_V1"}
                            )
                    st.success(f"✅ Đã cập nhật {len(home_modules)} Modules!")
                    st.rerun()

    # --- RENDER CARD GRID ---
    # Lấy danh sách tên Module duy nhất từ các item có hậu tố |Home
    unique_moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if s['sub_title'].endswith("|Home")])))
    
    if not unique_moduls:
        st.info("Chưa có danh sách Module. Hãy bấm Quét Cấp 1.")
        return

    cols = st.columns(3)
    for i, mod in enumerate(unique_moduls):
        # Đếm số form con: Tìm các item bắt đầu bằng "TênModule|" nhưng không phải là chính nó
        child_forms = [s for s in db_subs if s['sub_title'].startswith(f"{mod}|") and not s['sub_title'].endswith("|Home")]
        status_icon = "🟢" if any(s.get('status') == "Đã nội soi" for s in child_forms) else "📁"

        with cols[i % 3].container(border=True):
            st.markdown(f"#### {status_icon} {mod}")
            st.caption(f"📄 {len(child_forms)} Form nghiệp vụ")
            if st.button(f"Mở Module", key=f"btn_nav_{mod}", use_container_width=True):
                st.session_state.current_modul = mod
                st.rerun()

def render_gpv_forms(ctrl, p, modul_name, ai_script):
    """
    Giao diện Cấp 2: Quét sâu (Nội soi) bằng GPVEngine
    Fix: Hiển thị chính xác theo nhãn Module|Nhóm|Form
    """
    project_folder = p.get('folder_name', Config.APP_SLUG)
    
    # Header điều hướng
    c1, c2 = st.columns([3, 1.2])
    c1.subheader(f"📂 Module: {modul_name}")
    
    if c1.button("⬅️ Quay lại", key="back_to_main"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    # --- LOGIC NỘI SOI (DEEP SCAN) ---
    if c2.button("🔍 NỘI SOI TOÀN BỘ FORM", type="primary", use_container_width=True):
        with st.spinner(f"🤖 GPVEngine đang thâm nhập {modul_name}..."):
            # Lấy danh sách sub hiện tại để so khớp
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            
            if mod_home and mod_home.get('url'):
                # Chạy task quét sâu với tham số modul_name để dán nhãn đồng nhất
                deep_data = run_async(gpv_module_nav.run_task(
                    mode="DEEP_SCAN", 
                    module_url=mod_home['url'], 
                    project_folder=project_folder,
                    modul_name=modul_name
                ))
                
                if deep_data:
                    count_updated = 0
                    
                    # 1. Tách scan_time ra trước để không bị coi là 1 Module/Form
                    scan_time = deep_data.pop("scan_time", None) 
                    
                    for full_path, f_info in deep_data.items():
                        # 2. Ép kiểu f_info từ JSON string sang Dict (nếu cần)
                        if isinstance(f_info, str):
                            try:
                                f_info = json.loads(f_info)
                            except:
                                continue # Nếu lỗi parse thì bỏ qua item này luôn
                        
                        # 3. CHỈ XỬ LÝ NẾU LÀ METADATA THẬT (có chứa url hoặc inputs/buttons)
                        # Tránh trường hợp các key rác lọt vào
                        if not isinstance(f_info, dict) or (not f_info.get('url') and 'inputs' not in f_info):
                            continue

                        current_url = f_info.get('url', "")
                        
                        # 4. Kiểm tra xem form đã tồn tại chưa
                        existing = next((s for s in db_subs if s['sub_title'] == full_path), None)
                        
                        if existing:
                            ctrl.update_sub_content(
                                sub_id=existing['id'], 
                                new_url=current_url, 
                                new_metadata=f_info, 
                                new_status="Đã nội soi"
                            )
                        else:
                            ctrl.add_sub_content(
                                t_id=p['id'], 
                                sub_title=full_path, 
                                parent_folder=project_folder, 
                                url=current_url, 
                                metadata=f_info, 
                                status="Đã nội soi"
                            )
                        count_updated += 1
                    
                    # Lưu log scan_time vào đâu đó hoặc in ra thông báo
                    if scan_time:
                        print(f"⏱️ Thời gian nội soi: {scan_time}")

                   
                    
                    # st.success(f"✅ Đã đồng bộ {count_updated} Forms!")
                    if count_updated > 0:
                        st.success(f"✅ Đã đồng bộ {count_updated} Forms!")
                        st.rerun() # Buộc Streamlit đọc lại DB để lấy ID 19 mới tinh
                else:
                    st.error("⚠️ Không tìm thấy Sidebar. Kiểm tra lại quyền truy cập!")

    # --- HIỂN THỊ DANH SÁCH FORM (BỘ LỌC CHUẨN) ---
    all_items = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
    current_subs = []

    # 1. Tìm cái record "Tổng kho tri thức" (ID 18 trong cái JSON của ông)
    # Đây là nơi chứa toàn bộ danh sách Form con bị nhồi vào Metadata
    knowledge_bag = next((s for s in all_items if s['sub_title'] == "module_info"), None)

    if knowledge_bag:
        # Lấy metadata ra (đã được xử lý JSON nếu là string)
        meta = knowledge_bag.get('metadata', {})
        if isinstance(meta, str):
            try: meta = json.loads(meta)
            except: meta = {}

        # 2. Duyệt qua metadata để nhặt ra các Form thuộc Module này
        for idx, (key, value) in enumerate(meta.items()): # Thêm idx ở đây
            if isinstance(value, dict) and key.startswith(f"{modul_name}|"):
                # Tạo một object giả lập giống cấu trúc DB
                current_subs.append({
                    # Tạo ID giả bằng cách cộng ID gốc với số thứ tự để không trùng
                    "id": f"{knowledge_bag['id']}_{idx}", 
                    "sub_title": key,
                    "sub_folder": "manual_scan",
                    "url": value.get('url', ''),
                    "status": "Đã nội soi",
                    "metadata": value,
                    "summary": {"fields": 0, "actions": 0}
                })

    # 3. Dự phòng: Nếu sau này ông sửa Engine để lưu mỗi Form 1 dòng riêng trong DB
    db_direct_subs = [
        s for s in all_items 
        if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")
    ]
    for ds in db_direct_subs:
        if not any(cs['sub_title'] == ds['sub_title'] for cs in current_subs):
            current_subs.append(ds)

    # --- RENDER RA GIAO DIỆN ---
    if not current_subs:
        st.info(f"Module '{modul_name}' chưa có dữ liệu nội soi.")
        if st.checkbox("🔍 Kiểm tra dữ liệu thô trong Database"):
            st.json(all_items)
    else:
        # Sắp xếp lại cho đẹp theo bảng chữ cái
        current_subs = sorted(current_subs, key=lambda x: x['sub_title'])
        
        st.write(f"📊 Tìm thấy **{len(current_subs)}** Form nghiệp vụ")
        
        render_engine = RenderForm()
        render_engine.render_item_rows(ctrl, p, current_subs, ai_script, project_folder)