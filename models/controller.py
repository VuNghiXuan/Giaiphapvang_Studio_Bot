import os
import re
import shutil
from datetime import datetime
import json
from config import Config
from .db_engine import DBEngine
import traceback
import streamlit as st
from difflib import get_close_matches

class StudioController:
    def __init__(self):
        self.db = DBEngine()

    # --- QUẢN LÝ DỰ ÁN LỚN (TUTORIALS) ---
    def create_tutorial(self, title):
        # Sử dụng slugify từ Config để đồng nhất cách đặt tên folder
        folder_name = Config.slugify(title) 
        
        try:
            # 1. Kiểm tra DB
            existing = self.db.fetchone("SELECT id FROM tutorials WHERE folder_name = ?", (folder_name,))
            if not existing:
                res = self.db.execute("SELECT MAX(position) as max_pos FROM tutorials").fetchone()
                next_pos = (res['max_pos'] + 1) if res and res['max_pos'] is not None else 0
                
                self.db.execute(
                    "INSERT INTO tutorials (title, folder_name, position) VALUES (?, ?, ?)", 
                    (title, folder_name, next_pos)
                )
                self.db.commit()

            # 2. Tạo folder vật lý thông qua Config (Tự động mkdir -p)
            Config.get_path(app=folder_name)
            
            return True
        except Exception as e:
            print(f"❌ Lỗi create_tutorial: {e}")
            return False
        
    def get_all_tutorials(self):
        try:
            return self.db.execute("SELECT * FROM tutorials ORDER BY position ASC").fetchall()
        except Exception as e:
            print(f"❌ Lỗi get_all_tutorials: {e}")
            return []

    def delete_tutorial(self, t_id, folder_name):
        try:
            # 1. Xóa DB trước
            self.db.execute("DELETE FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            self.db.execute("DELETE FROM tutorials WHERE id = ?", (t_id,))
            self.db.commit()
            
            # 2. Xóa folder vật lý (Cực kỳ thận trọng)
            full_path = Config.get_path(app=folder_name)
            if full_path.exists() and full_path.is_dir():
                try:
                    shutil.rmtree(full_path)
                except OSError as e:
                    print(f"⚠️ Không thể xóa folder vật lý (có thể file đang mở): {e}")
                    # Có thể đổi tên folder thành .deleted_bak để xử lý sau
                    full_path.rename(full_path.with_suffix('.deleted'))
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_tutorial: {e}")
            return False
    
    def _get_default_metadata(self):
        return {
            "page_info": {"url": "", "is_dialog_open": False, "sidebar_path": []},
            "available_actions": [], 
            "form_to_fill": [],
            "table_structure": {"has_data": False}, 
            "scanned_at": ""
        }
    
    

    def add_sub_content(self, t_id, sub_title, parent_folder, url=None, metadata=None, status="Chưa quay", module_name="Chung", sub_folder=None):
        """
        Phiên bản Nâng cấp: Tự động xây dựng folder + Ghi nhận Module chính xác.
        Xử lý thông minh tham số 'sub_folder' từ Archiver truyền sang.
        """
        try:
            # 1. KIỂM TRA TRÙNG LẶP
            check_sql = "SELECT id FROM sub_contents WHERE tutorial_id = ? AND sub_title = ?"
            if self.db.fetchone(check_sql, (t_id, sub_title)):
                print(f"⚠️ [StudioDB]: Form '{sub_title}' đã tồn tại. Bỏ qua.")
                return False

            # 2. TÍNH TOÁN VỊ TRÍ (POSITION)
            res = self.db.fetchone("SELECT MAX(position) as max_pos FROM sub_contents WHERE tutorial_id = ?", (t_id,))
            max_pos = 0
            if res:
                res_dict = dict(res)
                max_pos = res_dict.get('max_pos') if res_dict.get('max_pos') is not None else 0
            next_pos = max_pos + 1
            
            # 3. XỬ LÝ METADATA MẶC ĐỊNH
            final_metadata = self._get_default_metadata() if hasattr(self, '_get_default_metadata') else {}
            if isinstance(metadata, dict): 
                final_metadata.update(metadata)
            
            # 4. XỬ LÝ ĐƯỜNG DẪN LOGIC (logic_path)
            # Nếu Archiver có truyền sub_folder thì dùng luôn, không thì tự tính
            if sub_folder:
                logic_path = sub_folder
            else:
                parts = [Config.slugify(p.strip()) for p in sub_title.split('|')]
                if len(parts) > 1 and parts[1] == "chung": 
                    parts[1] = "settings"
                logic_path = "/".join(parts)
            
            # 5. INSERT VÀO DATABASE
            sql_insert = """
                INSERT INTO sub_contents 
                (tutorial_id, module_name, sub_title, sub_folder, position, status, url, metadata) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                t_id, 
                module_name, 
                sub_title, 
                logic_path, 
                next_pos, 
                status, 
                str(url or ""), 
                json.dumps(final_metadata, ensure_ascii=False)
            )
            
            cursor = self.db.execute(sql_insert, params)
            new_id = cursor.lastrowid

            # 6. TẠO CẤU TRÚC THƯ MỤC VẬT LÝ
            app_slug = parent_folder if parent_folder else getattr(Config, 'APP_SLUG', 'default_app')
            base_module_path = Config.BASE_STORAGE / app_slug / logic_path
            
            # 4 tầng thư mục tiêu chuẩn: raw (quay màn hình), outputs (video thành phẩm), metadata (tri thức AI)
            assets_structure = ["raw", "outputs", "assets", "metadata"]
            
            for folder_type in assets_structure:
                target_path = base_module_path / folder_type
                target_path.mkdir(parents=True, exist_ok=True)
            
            # 7. BACKUP METADATA RA FILE VẬT LÝ
            meta_backup_path = base_module_path / "metadata" / "fields.json"
            with open(meta_backup_path, "w", encoding="utf-8") as f:
                json.dump(final_metadata, f, ensure_ascii=False, indent=4)
            
            self.db.commit()
            print(f"✅ [StudioDB]: Đã tạo Form '{sub_title}' thành công (ID: {new_id})")
            return new_id

        except Exception as e:
            self.db.rollback()
            print(f"❌ [StudioDB] Lỗi add_sub_content: {str(e)}")
            traceback.print_exc()
            return False


    def update_sub_content(self, sub_id: int, **kwargs):
        """
        Cập nhật tri thức mới cho Form. 
        Đồng bộ hóa metadata từ VisionMachine và Module danh mục.
        Bản sửa lỗi: Nhận thêm sub_folder để khớp với Archiver.
        """
        try:
            # 0. Truy vấn và ép kiểu sang dict
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: 
                return False
                
            current = dict(row)

            # 1. MAPPING THAM SỐ (Bổ sung sub_folder)
            new_url = kwargs.get('new_url') or kwargs.get('url')
            new_metadata = kwargs.get('new_metadata') or kwargs.get('metadata')
            new_status = kwargs.get('new_status') or kwargs.get('status')
            new_title = kwargs.get('new_title') or kwargs.get('title')
            new_module = kwargs.get('module_name') or kwargs.get('new_module')
            # THÊM DÒNG NÀY ĐỂ FIX LỖI ARCHIVER
            new_folder = kwargs.get('sub_folder') or kwargs.get('new_folder')

            # 2. XỬ LÝ METADATA (Merge thông minh)
            try:
                old_meta = json.loads(current.get('metadata', '{}')) if current.get('metadata') else self._get_default_metadata()
            except Exception:
                old_meta = self._get_default_metadata()
            
            if new_metadata and isinstance(new_metadata, dict):
                keys_to_update = [
                    "page_info", "available_actions", "form_to_fill", 
                    "table_structure", "actions_detected", "session", 
                    "navigation", "main_content", "active_form"
                ]
                
                for key in keys_to_update:
                    if key in new_metadata:
                        old_meta[key] = new_metadata[key]
                
                if "environment" in new_metadata:
                    if "environment" not in old_meta: 
                        old_meta["environment"] = {}
                    if isinstance(new_metadata["environment"], dict):
                        old_meta["environment"].update(new_metadata["environment"])
                    else:
                        old_meta["environment"] = new_metadata["environment"]

                old_meta['scanned_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                final_meta_str = json.dumps(old_meta, ensure_ascii=False)
            else:
                final_meta_str = current.get('metadata')

            # 3. QUẢN LÝ TRẠNG THÁI
            status = new_status or current.get('status', 'Chờ nội soi')
            if new_metadata and status == 'Chờ nội soi': 
                status = 'Đã quét'

            # 4. THỰC THI SQL (Bổ sung sub_folder vào câu lệnh UPDATE)
            sql = """
                UPDATE sub_contents 
                SET sub_title = :title, 
                    status = :status, 
                    url = :url, 
                    metadata = :meta,
                    module_name = :mod_name,
                    sub_folder = :folder
                WHERE id = :id
            """
            params = {
                "id": sub_id, 
                "title": new_title or current.get('sub_title'),
                "status": status, 
                "url": str(new_url or current.get('url') or ""),
                "meta": final_meta_str,
                "mod_name": new_module or current.get('module_name'),
                "folder": new_folder or current.get('sub_folder') # Cập nhật folder nếu có
            }
            
            self.db.execute(sql, params)
            self.db.commit()
            
            # 5. ĐỒNG BỘ FILE VẬT LÝ (Optional nhưng nên có)
            # Nếu ông muốn mỗi lần update DB là file fields.json cũng mới luôn
            if new_metadata:
                try:
                    app_slug = Config.APP_SLUG
                    logic_path = params['folder'] or ""
                    if logic_path:
                        meta_file = Config.BASE_STORAGE / app_slug / logic_path / "metadata" / "fields.json"
                        meta_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(meta_file, "w", encoding="utf-8") as f:
                            json.dump(old_meta, f, ensure_ascii=False, indent=4)
                except: pass

            print(f"✅ [StudioDB]: ID {sub_id} đã nạp tri thức (Module: {params['mod_name']})")
            return True

        except Exception as e:
            print(f"❌ Lỗi update_sub_content tại ID {sub_id}: {e}")
            traceback.print_exc()
            self.db.rollback()
            return False
        
    def get_sub_contents(self, tutorial_id):
        try:
            rows = self.db.fetchall("SELECT * FROM sub_contents WHERE tutorial_id = ? ORDER BY position ASC", (tutorial_id,))
            results = []
            for row in rows:
                item = dict(row)
                try: meta = json.loads(item['metadata']) if item['metadata'] else {}
                except: meta = {}

                content = meta.get('content', {})
                state = meta.get('state', {})
                scroll = state.get('scroll_status', {})

                item['summary'] = {
                    "fields": len(content.get('form_fields', [])),
                    "actions": len(content.get('primary_actions', [])) + len(content.get('row_operations', [])),
                    "has_scroll": scroll.get('sidebar_can_scroll') or scroll.get('table_horizontal_scroll'),
                    "is_dialog": state.get('is_dialog_open', False)
                }
                item['metadata'] = meta
                results.append(item)
            return results
        except Exception as e:
            print(f"❌ Lỗi get_sub_contents: {e}")
            return []


    def generate_workflow_context(self, ui_context, target_goal="Thêm mới", full_path=""):
        """
        Hàm 'Đạo diễn': Tự động tạo kịch bản từ lúc đăng nhập đến khi hoàn thành form.
        full_path ví dụ: "Hệ thống | Chung | Thông tin công ty | Chi nhánh"
        """
        btns = ui_context.get('nut_bam_truc_tiep', [])
        inputs = ui_context.get('danh_sach_o_nhap_lieu', [])
        
        workflow = []
        curr = 1

        # --- PHẦN 1: ĐIỀU HƯỚNG ĐA TẦNG (Giải quyết lỗi diễn hỏng Cảnh 1) ---
        if full_path and "|" in full_path:
            # Tách chuỗi thành list: ['Hệ thống', 'Chung', 'Thông tin công ty', 'Chi nhánh']
            path_parts = [p.strip() for p in full_path.split("|")]
            
            for part in path_parts:
                workflow.append({
                    "step": curr,
                    "type": "click",
                    "label": part,
                    "vo": f"Truy cập vào mục {part}"
                })
                curr += 1
        else:
            # Fallback nếu không có path chi tiết
            workflow.append({
                "step": curr, 
                "type": "move", 
                "label": "Mở module hệ thống", 
                "vo": "Truy cập vào hệ thống"
            })
            curr += 1

        # --- PHẦN 2: THỰC THI NGHIỆP VỤ THEO MỤC TIÊU ---
        goal_lower = target_goal.lower()

        # Nhóm 1: THÊM MỚI
        if any(x in goal_lower for x in ["thêm", "tạo"]):
            open_btn = next((b for b in btns if any(x in b for x in ["Tạo", "Mới", "Thêm"])), "Tạo mới")
            save_btn = next((b for b in btns if b != open_btn and any(x in b for x in ["Cập nhật", "Lưu", "Thêm", "Xác nhận"])), "Lưu lại")
            
            workflow.append({"step": curr, "type": "click", "label": open_btn, "vo": f"Nhấn {open_btn}"}); curr += 1
            for inp in inputs:
                workflow.append({"step": curr, "type": "type", "label": inp, "value": f"Mẫu {inp}", "vo": f"Nhập {inp}"}); curr += 1
            workflow.append({"step": curr, "type": "click", "label": save_btn, "vo": "Hoàn tất lưu dữ liệu"})

        # Nhóm 2: CHỈNH SỬA
        elif any(x in goal_lower for x in ["sửa", "chỉnh", "cập nhật"]):
            edit_btn = next((b for b in btns if any(x in b for x in ["Sửa", "Cập nhật"])), "Sửa")
            workflow.append({"step": curr, "type": "click", "label": "Chọn dữ liệu", "vo": "Chọn dòng cần chỉnh sửa"}); curr += 1
            workflow.append({"step": curr, "type": "click", "label": edit_btn, "vo": "Nhấn nút chỉnh sửa"}); curr += 1
            if inputs:
                workflow.append({"step": curr, "type": "type", "label": inputs[0], "value": "Thông tin cập nhật", "vo": f"Thay đổi {inputs[0]}"}); curr += 1
            workflow.append({"step": curr, "type": "click", "label": "Lưu", "vo": "Cập nhật thông tin"})

        # Nhóm 3: XÓA
        elif "xóa" in goal_lower:
            workflow.append({"step": curr, "type": "click", "label": "Chọn dòng cần xóa", "vo": "Chọn dữ liệu muốn xóa"}); curr += 1
            workflow.append({"step": curr, "type": "click", "label": "Xóa", "vo": "Thực hiện lệnh xóa"}); curr += 1
            workflow.append({"step": curr, "type": "click", "label": "Xác nhận", "vo": "Đồng ý xóa dữ liệu"})

        # Nhóm 4: CÁC MỤC KHÁC (Báo cáo, Tin tức, Hệ thống...)
        else:
            view_btn = next((b for b in btns if any(x in b for x in ["Xem", "Xuất", "Lọc"])), "Xem chi tiết")
            workflow.append({"step": curr, "type": "click", "label": view_btn, "vo": f"Mở xem {target_goal}"})

        # --- PHẦN 3: KẾT THÚC ---
        curr += 1
        workflow.append({"step": curr, "type": "finish", "label": "Giải Pháp Toàn Diện Cho Ngành Kim Hoàn", "vo": "Quy trình đã hoàn thành"})
        
        return workflow

    def get_formatted_meta_for_ai(self, sub_id, director_notes="", target_goal="Thêm mới", is_expanded=False):
        try:
            row = self.db.fetchone("SELECT * FROM sub_contents WHERE id = ?", (sub_id,))
            if not row: return None
            sub = dict(row)
            
            # 1. Làm sạch & Lấy dữ liệu Metadata
            clean = self.clean_metadata_for_ai(json.loads(sub.get('metadata', '{}')))
            all_btns = [a['label'] for a in clean['available_actions'] if not a['is_trigger_menu']]
            form_inputs = [i['label'] for i in clean['form_to_fill']]
            full_path_str = sub.get('sub_title', '') 

            # 2. LOGIC CHỐNG LOÃNG (Nâng cấp: Ưu tiên nút "Lưu" hơn "Thêm")
            if not is_expanded:
                # Ưu tiên "lưu" lên đầu để AI thấy nó trước
                keywords = ["lưu", "tạo mới", "thêm", "xác nhận", "cập nhật", "sửa", "xóa"]
                keywords.extend(target_goal.lower().split())
                
                if "|" in full_path_str:
                    keywords.extend([p.strip().lower() for p in full_path_str.split("|")])

                nut_bam_truc_tiep = [b for b in all_btns if any(kw in b.lower() for kw in keywords)]
                
                # CHỐNG "THÊM" NHẦM: Nếu có cả "Lưu" và "Thêm", ưu tiên giữ "Lưu" cho hành động cuối
                if "Lưu" in nut_bam_truc_tiep and "Thêm" in nut_bam_truc_tiep:
                    # Nếu là form thêm mới, nút "Thêm" thường là icon lẻ, còn "Lưu" mới là nút submit
                    pass 
                
                if not nut_bam_truc_tiep: nut_bam_truc_tiep = all_btns[:10] 
            else:
                nut_bam_truc_tiep = all_btns

            ui_context = {
                "loi_dan_navigation": "Điều hướng theo lộ trình nghiệp vụ",
                "nut_bam_truc_tiep": nut_bam_truc_tiep,
                "danh_sach_o_nhap_lieu": form_inputs
            }

            # 3. Tạo Blueprint Workflow
            suggested_workflow = self.generate_workflow_context(ui_context, target_goal, full_path=full_path_str)

            # 4. Đóng gói Prompt (NÂNG CẤP CHỈ THỊ CỨNG)
            prompt = f"""
--- 🎭 CHỈ THỊ ĐẠO DIỄN ---
Mục tiêu: {target_goal}
Quy trình: "{full_path_str}"
Lưu ý đặc biệt: {director_notes if director_notes else "Chuyên nghiệp, dứt khoát."}

--- 🤖 TRI THỨC UI THỰC TẾ (CHỈ ĐƯỢC DÙNG NHÃN Ở ĐÂY) ---
{json.dumps(ui_context, ensure_ascii=False, indent=2)}

--- 📍 BỐI CẢNH WORKFLOW MẪU (BẮT BUỘC GIỮ NGUYÊN SỐ BƯỚC VÀ THỨ TỰ) ---
{json.dumps(suggested_workflow, ensure_ascii=False, indent=2)}

--- 📝 QUY TẮC VÀNG CHO BIÊN KỊCH AI ---
1. **KHÔNG TỰ Ý RÚT GỌN**: Phải giữ nguyên các bước điều hướng menu (Click Hệ thống, Chung...) từ Workflow mẫu.
2. **KHÔNG DÙNG LỆNH 'MOVE'**: Tất cả thao tác điều hướng menu phải là `type: click`.
3. **CHỌN NÚT CHỐT**: Nếu trong danh sách nút có cả "Lưu" và "Thêm", hãy ưu tiên dùng "Lưu" cho bước Hoàn tất.
4. **DỮ LIỆU THỰC TẾ**: Thay các giá trị "Mẫu..." bằng dữ liệu nghiệp vụ ngành vàng bạc đá quý (Ví dụ: Mã 'CN-Q1-001', Tên 'Chi nhánh Quận 1', Số ĐT '028...').
5. **FORMAT**: Chỉ trả về duy nhất 1 JSON array.

--- 🎬 KẾT QUẢ ĐẦU RA (JSON) ---
"""
            return {
                "prompt_letter": prompt.strip(), 
                "sub_id": sub_id, 
                "ui_context": ui_context
            }
        except Exception as e:
            print(f"❌ Lỗi biên kịch AI: {e}")
            return None

    def validate_and_fix_ai_response(self, ai_result, clean_meta):
        """
        Bộ lọc cuối cùng: Ép AI phải đi đúng hàng lối.
        """
        try:
            # 1. Ép kiểu dữ liệu về List
            steps = json.loads(ai_result) if isinstance(ai_result, str) else ai_result
            
            # 2. Thu thập danh sách nhãn 'xịn' từ thực tế
            valid_labels = (
                [clean_meta['loi_dan_navigation']] + 
                clean_meta['nut_bam_truc_tiep'] + 
                clean_meta['danh_sach_o_nhap_lieu']
            )

            fixed_steps = []
            for i, s in enumerate(steps):
                # Sửa Key nếu AI lỡ dùng 'action' thay vì 'type'
                stype = s.get('type') or s.get('action') or 'click'
                label = s.get('label', '')

                # Sửa Nhãn nếu AI tự chế (Hallucination)
                if label not in valid_labels:
                    matches = get_close_matches(label, valid_labels, n=1, cutoff=0.6)
                    if matches:
                        label = matches[0]

                fixed_steps.append({
                    "step": i + 1,
                    "type": stype.lower(),
                    "label": label,
                    "value": s.get('value', '') if stype.lower() == 'type' else ""
                })
                
            return fixed_steps
        except Exception as e:
            print(f"❌ Lỗi Validator: {e}")
            return steps # Trả về gốc nếu lỗi nặng
        
    def clean_metadata_for_ai(self, raw_data):
        """
        Hàm lọc sạch Metadata từ DOM gửi về để AI không bị 'loạn' bởi nhãn rác.
        """
        if not raw_data: 
            return {"page_info": {}, "available_actions": [], "form_to_fill": []}

        # --- 1. DANH SÁCH ĐEN (HARD BLACKLIST) ---
        # Loại bỏ những nhãn kỹ thuật, phân trang, hoặc icon vô nghĩa
        HARD_BLACKLIST = [
            "table-pagination-select", 
            "rows per page", 
            "tìm kiếm…", 
            "iconify", 
            "css-", 
            "none",
            "loading"
        ]

        # --- 2. GOM INPUTS (Form nhãn cần nhập liệu) ---
        sub_details = raw_data.get("sub_form_details", {})
        # Ưu tiên lấy từ form đang mở (Dialog), nếu không có mới lấy inputs chung của trang
        raw_inputs = sub_details.get("inputs") or raw_data.get("inputs") or []
        
        clean_inputs = []
        seen_inputs = set()

        for i in raw_inputs:
            lbl = (i.get("label") or "").strip()
            
            # Logic lọc input:
            # - Không rỗng
            # - Không nằm trong blacklist
            # - Không chứa các ký tự hệ thống (ví dụ: _r_)
            # - Tránh trùng lặp
            if not lbl or lbl in seen_inputs:
                continue
                
            is_blacklisted = any(bw in lbl.lower() for bw in HARD_BLACKLIST)
            if is_blacklisted or "_r_" in lbl:
                continue

            clean_inputs.append({
                "label": lbl, 
                "type": i.get("type", "text")
            })
            seen_inputs.add(lbl)

        # --- 3. GOM ACTIONS (Nút bấm & Menu điều hướng) ---
        raw_actions = raw_data.get("buttons") or []
        
        # Nếu có bảng (tables), hốt thêm các nút trong bảng (Sửa, Xóa, Xem)
        for tbl in raw_data.get("tables", []):
            raw_actions.extend(tbl.get("actions_detected", []))

        clean_actions = []
        seen_actions = set()

        for a in raw_actions:
            # Lấy nhãn từ label hoặc text (tùy cấu trúc DOM quét được)
            lbl = (a.get("label") or a.get("text") or "").strip()
            
            # Logic lọc action:
            if not lbl or lbl in seen_actions:
                continue
                
            is_blacklisted = any(bw in lbl.lower() for bw in HARD_BLACKLIST)
            if is_blacklisted:
                continue

            clean_actions.append({
                "label": lbl,
                "is_trigger_menu": a.get("is_trigger_menu", False)
            })
            seen_actions.add(lbl)

        # --- 4. TRẢ KẾT QUẢ ĐÃ TINH GỌN ---
        return {
            "page_info": raw_data.get("page_info", {}),
            "available_actions": clean_actions,
            "form_to_fill": clean_inputs
        }
    
    def _format_form_for_ai(self, form_data):
        """Định dạng danh sách Form để Debug/Log nhanh"""
        if not isinstance(form_data, list):
            return "  - Trống (Không có form hoặc table inputs)."
        
        lines = []
        for f in form_data:
            label = f.get('label', 'N/A')
            f_type = f.get('type', 'text')
            req = "*" if f.get('required') else ""
            lines.append(f"  + {label} ({f_type}){req}")
            
        return "\n".join(lines) if lines else "  - Không phát hiện trường dữ liệu."

    

    
    def delete_sub_content(self, sub_id, folder_name, sub_folder):
        """
        FIX 3: Xóa cực kỳ an toàn, kiểm tra tồn tại trước khi rmtree
        """
        try:
            # Xóa trong DB trước
            self.db.execute("DELETE FROM sub_contents WHERE id = ?", (sub_id,))
            self.db.commit()
            
            if sub_folder:
                # Trỏ thẳng vào thư mục theo sub_folder trong DB
                full_path = Config.BASE_STORAGE / Config.APP_SLUG / sub_folder
                if full_path.exists() and full_path.is_dir():
                    shutil.rmtree(full_path)
                    print(f"🗑️ Đã xóa folder: {full_path}")
            return True
        except Exception as e:
            print(f"❌ Lỗi delete_sub_content: {e}")
            return False

    def update_sub_content_metadata(self, sub_id, metadata):
        return self.update_sub_content(sub_id, metadata=metadata)
    
    def get_sub_by_title(self, title, t_id):
        sql = "SELECT * FROM sub_contents WHERE sub_title = ? AND tutorial_id = ?"
        return self.db.execute(sql, (title, t_id)).fetchone()
    
    def move_sub_content(self, sub_id, direction):
        """
        Thay đổi thứ tự hiển thị của sub_content (Form)
        Sửa lỗi: Ép kiểu sqlite3.Row sang dict để sử dụng được hàm .get()
        """
        try:
            # 1. Lấy item hiện tại từ DBEngine
            row = self.db.get_sub_content_by_id(sub_id)
            if not row:
                print(f"⚠️ Không tìm thấy sub_content với ID: {sub_id}")
                return False
            
            # Chuyển đổi sang dict để dùng .get() và tránh lỗi AttributeError
            current_item = dict(row)
            
            # Đảm bảo lấy đúng tutorial_id và position (mặc định là 0 nếu None)
            t_id = current_item.get('tutorial_id')
            current_pos = current_item.get('position')
            if current_pos is None: current_pos = 0

            # 2. Tìm item hàng xóm (phía trên hoặc phía dưới)
            target_row = self.db.get_neighbor_item(t_id, current_pos, direction)
            
            if target_row:
                target_item = dict(target_row)
                target_id = target_item.get('id')
                target_pos = target_item.get('position')

                if target_id is not None and target_pos is not None:
                    # 3. Thực hiện đổi chỗ position trong Database
                    # Gán position của thằng hàng xóm cho thằng hiện tại
                    self.db.update_position(sub_id, target_pos)
                    # Gán position cũ của thằng hiện tại cho thằng hàng xóm
                    self.db.update_position(target_id, current_pos)
                    
                    self.db.commit() # Lưu thay đổi xuống file DB
                    print(f"✅ Đã đổi chỗ ID {sub_id} ({current_pos}) với ID {target_id} ({target_pos})")
                    return True
            else:
                print(f"ℹ️ Không có item nào ở phía {direction} để đổi chỗ.")
                
        except Exception as e:
            print(f"❌ Lỗi move_sub_content: {e}")
            if hasattr(self.db, 'rollback'):
                self.db.rollback()
                
        return False
    
    # Trong file StudioController
    def get_all_modules(self):
        # Ưu tiên lấy từ cột module_name
        query = "SELECT DISTINCT module_name FROM sub_contents WHERE module_name IS NOT NULL"
        result = self.db.fetchall(query)
        
        if not result or len(result) == 0:
            # Nếu chưa có dữ liệu ở cột mới, dùng tạm logic cũ để người dùng không thấy trống
            query_backup = "SELECT DISTINCT sub_title FROM sub_contents WHERE sub_title LIKE '%|Home%'"
            res_backup = self.db.fetchall(query_backup)
            return sorted(list(set([r['sub_title'].split('|')[0].strip() for r in res_backup])))
            
        return [row['module_name'] for row in result]

    def get_forms_by_module(self, module_name):
        """Lấy danh sách form theo module"""
        query = "SELECT sub_title FROM sub_contents WHERE module_name = ?"
        try:
            result = self.db.fetchall(query, (module_name,))
            if not result: return []
            return [{"sub_title": row['sub_title']} for row in result]
        except Exception as e:
            print(f"Lỗi get_forms_by_module: {e}")
            return []

    def update_status(self, sub_id: int, new_status: str, note: str = ""):
        """
        Cập nhật trạng thái xử lý cho SubContent.
        Tự động ghi lại lịch sử (logs) vào metadata để theo dõi tiến độ.
        """
        try:
            # 1. Lấy dữ liệu hiện tại
            row = self.db.fetchone("SELECT status, metadata FROM sub_contents WHERE id = ?", (sub_id,))
            if not row:
                return False
            
            current = dict(row)
            old_status = current.get('status')
            
            # 2. Giải mã metadata để ghi log
            try:
                meta = json.loads(current.get('metadata', '{}'))
            except:
                meta = self._get_default_metadata()

            # Tạo danh sách log nếu chưa có
            if "process_logs" not in meta:
                meta["process_logs"] = []

            # Ghi lại dấu vết thay đổi
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "from": old_status,
                "to": new_status,
                "note": note
            }
            meta["process_logs"].append(log_entry)
            
            # Giới hạn chỉ giữ 10 logs gần nhất cho nhẹ DB
            meta["process_logs"] = meta["process_logs"][-10:]

            # 3. Thực thi cập nhật
            sql = "UPDATE sub_contents SET status = ?, metadata = ? WHERE id = ?"
            self.db.execute(sql, (new_status, json.dumps(meta, ensure_ascii=False), sub_id))
            self.db.commit()

            print(f"🔄 [StudioDB]: ID {sub_id} chuyển trạng thái: {old_status} -> {new_status}")
            return True

        except Exception as e:
            print(f"❌ Lỗi update_status tại ID {sub_id}: {e}")
            self.db.rollback()
            return False