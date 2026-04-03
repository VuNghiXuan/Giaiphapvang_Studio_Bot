import streamlit as st
import os
import json
from Bot_GPV.crawle.scrape_giaiphapvang import GiaiphapvangScraper
from Bot_GPV.core.gpv_ai_logic_knowledge import AIScripts
# from Bot_GPV.views.components.gpv_component import GPVComponent
from Bot_GPV.views.components.gpv_render_forms_detail import RenderForm
from config import Config

import asyncio
import nest_asyncio
nest_asyncio.apply()

# Khởi tạo bộ não AI
ai_script = AIScripts()

def render_gpv_logic(ctrl, p, ai_script):
    """Điều hướng chính: Tối ưu chống Loop và Chồng lấn UI"""
    
    if "current_modul" not in st.session_state:
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"

    # Lấy dữ liệu từ DB (Chuyển Row thành Dict để dễ xử lý)
    db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]

    # NHÁNH 1: GIAO DIỆN CHI TIẾT FORM (CẤP 2)
    if st.session_state.current_modul != "🏠 TẤT CẢ MODULS":
        # Đảm bảo truyền đủ ai_script vào hàm cấp 2
        render_gpv_forms(ctrl, p, st.session_state.current_modul, ai_script)
        return # Chặn đứng để không render trang chủ bên dưới

    # NHÁNH 2: GIAO DIỆN CHỌN MODULE (TRANG CHỦ - CẤP 1)
    st.markdown("### 📦 Hệ thống Module")
    
    with st.expander("⚙️ ĐỒNG BỘ MODULE (CẤP 1)", expanded=False):
        if st.button("🔍 QUÉT MODULES MỚI", use_container_width=True, type="primary", key="btn_scan_c1"):
            with st.spinner("Đang quét danh sách Module..."):
                extractor = GiaiphapvangScraper()
                # Lấy danh sách module từ trang chủ phần mềm
                home_modules = extractor.get_home_modules()
                
                count_new = 0
                for mod in home_modules:
                    full_t = f"{mod['text']}|Home"
                    # Kiểm tra xem Module này đã có trong DB chưa
                    existing = next((s for s in db_subs if s['sub_title'] == full_t), None)
                    
                    if not existing:
                        # 1. Thêm mới Module cha vào DB với đầy đủ tham số
                        ctrl.add_sub_content(
                            t_id=p['id'], 
                            sub_title=full_t, 
                            parent_folder=p['folder_name'],
                            url=mod['href'], # Lưu trực tiếp URL vào cột URL luôn
                            metadata={}
                        )
                        count_new += 1
                        
                        # Không cần gọi update_sub_content nữa vì đã truyền URL ngay lúc tạo.
                        # Nếu Vũ vẫn muốn update riêng thì dùng: new_url=mod['href']
                                                                        
                st.success(f"✅ Đã đồng bộ! Thêm mới {count_new} Module.")
                st.rerun()

    # Lọc danh sách các Module duy nhất từ DB để hiển thị Card
    moduls = sorted(list(set([s['sub_title'].split('|')[0] for s in db_subs if '|' in s['sub_title']])))
    
    if not moduls:
        st.info("💡 Vũ hãy bấm 'QUÉT MODULES MỚI' để bắt đầu.")
        return

    # Hiển thị Module dưới dạng Card
    cols = st.columns(3)
    for i, mod in enumerate(moduls):
        # Đếm số lượng Form con (không tính bản ghi |Home)
        count = len([s for s in db_subs if s['sub_title'].startswith(f"{mod}|") and not s['sub_title'].endswith("|Home")])
        
        with cols[i % 3].container(border=True):
            st.markdown(f"#### 📁 {mod}")
            st.caption(f"📄 {count} Forms đã quét")
            if st.button(f"Mở {mod}", key=f"btn_nav_{mod}_{i}", use_container_width=True):
                st.session_state.current_modul = mod
                st.rerun()


def render_gpv_forms(ctrl, p, modul_name, ai_script):
    """
    Giao diện Cấp 2: Quét sâu từng Form, đồng bộ Metadata vào DB.
    Đã tối ưu truy xuất theo cấu trúc Omni Metadata 2026.
    """
    project_folder = p.get('folder_name', "Giai_Phap_Vang")
    
    c1, c2 = st.columns([3, 1.2])
    c1.subheader(f"📂 Module: {modul_name}")
    
    if c1.button("⬅️ Quay lại", key="back_to_main"): 
        st.session_state.current_modul = "🏠 TẤT CẢ MODULS"
        st.rerun()
    
    if c2.button("🔍 CẬP NHẬT FORM (CẤP 2)", type="primary", use_container_width=True, key="btn_deep_scan"):
        with st.spinner(f"Đang mổ xẻ Module {modul_name}..."):
            # 1. Lấy dữ liệu mới nhất từ DB để so khớp
            db_subs = [dict(s) for s in ctrl.get_sub_contents(p['id'])]
            
            # 2. Tìm URL của Module Home (điểm bắt đầu để quét sâu)
            mod_home = next((s for s in db_subs if s['sub_title'] == f"{modul_name}|Home"), None)
            target_url = mod_home.get('url') if mod_home else None
            
            # if target_url:
            #     extractor = GiaiphapvangScraper()
            #     try:
            #         # Gọi Scraper quét sâu các liên kết bên trong module
            #         deep_data = extractor.update_module_details(project_folder, modul_name, target_url)
            #     except Exception as e:
            #         st.error(f"❌ Lỗi khi quét Playwright: {e}")
            #         deep_data = None
                
            #     # 1. KIỂM TRA VÀ GIẢI MÃ COROUTINE (THÊM ĐOẠN NÀY)
            #     if asyncio.iscoroutine(deep_data):
            #         try:
            #             # Kiểm tra xem có vòng lặp nào đang chạy không
            #             loop = asyncio.get_event_loop()
            #             if loop.is_running():
            #                 # Nếu đang ở trong loop (như Streamlit), ta ép nó chạy đến khi xong
            #                 nest_asyncio.apply() # Cần 'pip install nest_asyncio' nếu chưa có
            #                 deep_data = loop.run_until_complete(deep_data)
            #             else:
            #                 deep_data = asyncio.run(deep_data)
            #         except Exception as e:
            #             # Cách dự phòng cuối cùng nếu các cách trên lỗi
            #             st.warning(f"⚠️ Đang thử giải pháp dự phòng cho Async...")
            #             # deep_data = asyncio.get_event_loop().run_until_complete(deep_data)
            #             deep_data = asyncio.run(deep_data)

            if target_url:
                extractor = GiaiphapvangScraper()
                try:
                    # Gọi hàm - lúc này deep_data_result có thể là Coroutine
                    deep_data_result = extractor.update_module_details(project_folder, modul_name, target_url)
                    
                    # GIẢI MÃ COROUTINE
                    if asyncio.iscoroutine(deep_data_result):
                        try:
                            loop = asyncio.get_event_loop()
                            # Vì đã có nest_asyncio.apply() ở đầu file, dòng này sẽ chạy mượt
                            deep_data = loop.run_until_complete(deep_data_result)
                        except RuntimeError:
                            # Nếu thread này chưa có loop nào, tạo mới
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            deep_data = loop.run_until_complete(deep_data_result)
                    else:
                        deep_data = deep_data_result

                except Exception as e:
                    st.error(f"❌ Lỗi khi quét Playwright: {e}")
                    deep_data = None
                
                if deep_data:
                    for form_name, f_info in deep_data.items():
                        full_title = f"{modul_name}|{form_name}"
                        metadata_json = f_info.get('structure', {}) # Đây là metadata 'vét cạn'
                        form_url = f_info.get('url', "")
                        
                        existing_form = next((s for s in db_subs if s['sub_title'] == full_title), None)
                        
                        if existing_form:
                            # CẬP NHẬT (Sửa lại đúng tên tham số trong StudioController)
                            ctrl.update_sub_content(
                                sub_id=existing_form['id'], 
                                url=form_url, 
                                metadata=metadata_json, 
                                status="Đã quét"
                            )
                        else:
                            # THÊM MỚI nếu chưa có trong DB
                            ctrl.add_sub_content(
                                t_id=p['id'],
                                sub_title=full_title,
                                parent_folder=project_folder,
                                url=form_url,
                                metadata=metadata_json
                            )
                    st.success(f"✅ Đã 'vét cạn' tri thức cho {len(deep_data)} Forms!")
                    st.rerun()
                else:
                    st.error("❌ Không tìm thấy dữ liệu chi tiết từ Scraper.")
            else:
                st.error("❌ Không tìm thấy URL của Module gốc để quét sâu.")

    # --- PHẦN HIỂN THỊ DANH SÁCH FORM ---
    current_subs = [dict(s) for s in ctrl.get_sub_contents(p['id']) 
                    if s['sub_title'].startswith(f"{modul_name}|") and not s['sub_title'].endswith("|Home")]
    
    display_data = []
    for sub in current_subs:
        # Giải mã Metadata an toàn
        meta = sub.get('metadata')
        if isinstance(meta, str) and meta.strip():
            try: meta = json.loads(meta)
            except: meta = {}
        elif not isinstance(meta, dict):
            meta = {}

        # 1. TRUY XUẤT THEO CẤU TRÚC OMNI: layout -> main_content
        layout = meta.get('layout', {})
        main = layout.get('main_content', {})
        active_form = layout.get('active_form', {}) # Ưu tiên nếu đã 'nội soi' form

        # Gom Fields (Ưu tiên fields trong form nếu đang mở, nếu không lấy main)
        target_inputs = active_form.get('inputs') if active_form else main.get('inputs', [])
        fields = [f.get('label') or f.get('placeholder') or f.get('name') 
                  for f in target_inputs if isinstance(f, dict)]
        
        sub['all_fields'] = fields 
        sub['preview_fields'] = "📝 " + ", ".join(fields[:5]) + ("..." if len(fields) > 5 else "") if fields else "🔍 Trống"
        
        # 2. GOM ACTIONS (Nút bấm chính + Nút trong dòng)
        all_btns = []
        raw_btns = main.get('actions', []) + main.get('row_operations', [])
        if active_form:
            raw_btns += active_form.get('actions', [])

        for item in raw_btns:
            if isinstance(item, dict):
                label = item.get('label', '')
            else:
                label = str(item)
                
            if label and label not in all_btns:
                all_btns.append(label)

        sub['all_actions'] = all_btns 
        
        # Sắp xếp ưu tiên các nút quan trọng ngành vàng lên đầu Preview
        priority_keywords = ["Lưu", "Thêm", "Tính", "In", "Duyệt", "Quét"]
        sorted_btns = sorted(all_btns, key=lambda x: any(kw in x for kw in priority_keywords), reverse=True)

        sub['preview_actions'] = "⚡ " + ", ".join(sorted_btns[:6]) + ("..." if len(sorted_btns) > 6 else "") if sorted_btns else "🚫 Không nút"
        
        display_data.append(sub)

    # GỌI COMPONENT RENDER TỪNG DÒNG (Card UI)
    if display_data:
        gp_component = RenderForm() 
        gp_component.render_item_rows(ctrl, p, display_data, ai_script, project_folder)
    else:
        st.info("💡 Module này chưa có Form. Vũ hãy nhấn 'CẬP NHẬT FORM (CẤP 2)' ở trên để quét tri thức.")