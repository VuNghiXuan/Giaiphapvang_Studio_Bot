import streamlit as st
import json
import os
import re
from google import genai
from google.genai import types
from config import Config

class AIScripts:
    def __init__(self):
        # Thông báo khởi tạo các vai trò studio
        self.bot_editor = "✂️ [Bot Biên Tập]"
        self.bot_director = "📜 [Bot Đạo Diễn]"
        self.bot_actor = "🎭 [Bot Diễn Viên]"
        self.bot_qa = "🛡️ [Bot Hậu Kỳ]"
        
        print(f"{self.bot_editor}: Sẵn sàng lọc Metadata tinh hoa...")
        print(f"{self.bot_director}: Sẵn sàng soạn thảo kịch bản kịch tính...")
        print(f"{self.bot_actor}: Đã thông nòng bộ não Gemini...")

    # =================================================================
    # VAI TRÒ 1: BOT BIÊN TẬP (Data Refining & Knowledge Extraction)
    # =================================================================
    def get_form_knowledge_from_db(self, sub_content_item):
        """ 
        [Bot Biên Tập] - Trích xuất tri thức có cấu trúc cực chuẩn.
        QUAN TRỌNG: Ưu tiên lấy 'selector' để Bot Automation có thể tương tác chính xác.
        Giữ nguyên logic trả về chuỗi để không làm gãy các file gọi hàm này.
        """
        import json
        
        print(f"{self.bot_editor}: Đang 'mổ xẻ' tri thức nghiệp vụ cho Đạo diễn Vũ...")
        
        if not sub_content_item:
            return "⚠️ Không tìm thấy dữ liệu nội dung."

        metadata = sub_content_item.get('metadata')
        if not metadata: 
            return "⚠️ Form này chưa có Metadata. Hãy chạy Bot Tiền Trạm quét Cấp 2 trước!"

        # Xử lý nếu metadata là chuỗi JSON (Duy trì tính tương thích với DB)
        if isinstance(metadata, str):
            try: 
                metadata = json.loads(metadata)
            except: 
                return "❌ Lỗi: Metadata không đúng định dạng JSON."

        # --- LỚP 1: LỌC RÁC NHƯNG GIỮ LOGIC NGHIỆP VỤ ---
        BLACK_LIST = ["close", "đóng", "hủy", "cancel", "x", "n/a", "settings", "cài đặt", "thoát", "giúp đỡ"]
        
        # --- LỚP 2: TRÍCH XUẤT INPUTS (Lấy Selector làm định danh cốt lõi) ---
        raw_fields = metadata.get('form_fields', [])
        structured_inputs = []
        for f in raw_fields:
            if not isinstance(f, dict): continue
            label = f.get('label', '')
            if label.lower() in BLACK_LIST: continue
            
            # ƯU TIÊN SỐ 1: selector (vì trong DB của Vũ chứa [name='...'])
            # ƯU TIÊN SỐ 2: name hoặc id (phòng hờ)
            target_id = f.get('selector') or f.get('name') or f.get('id') or "N/A"
            
            structured_inputs.append({
                "label": label,
                "type": f.get('type', 'text'),
                "id_or_selector": target_id 
            })

        # --- LỚP 3: TRÍCH XUẤT ACTIONS (Nút bấm chức năng) ---
        raw_actions = metadata.get('actions', [])
        structured_btns = []
        for b in raw_actions:
            btn_label = b.get('label') if isinstance(b, dict) else str(b)
            if btn_label.lower() in BLACK_LIST: continue
            
            # Tương tự, lấy selector để AI biết dùng: button:has-text("Lưu")
            btn_target = b.get('selector') if isinstance(b, dict) else "N/A"
            
            structured_btns.append({
                "label": btn_label,
                "selector": btn_target
            })

        # --- LỚP 4: THÔNG TIN BẢNG (COLUMNS) ---
        cols = metadata.get('columns') or []

        # --- LỚP 5: TỔNG HỢP NGỮ CẢNH (DẠNG JSON CHO AI HIỂU PHÂN CẤP) ---
        context_data = {
            "system": "Ứng Dụng Vàng (HTJ)",
            "module_path": sub_content_item.get('sub_title', 'N/A'),
            "url": sub_content_item.get('url', ''),
            "interface_specs": {
                "input_fields": structured_inputs[:60], # Nới lỏng giới hạn lên 60 fields
                "available_buttons": structured_btns[:20], # Giữ lại các nút nghiệp vụ
                "data_table_columns": cols[:20]
            }
        }

        # Chuyển đổi sang chuỗi JSON để gửi cho AI (Đúng định dạng file gọi mong đợi)
        final_context = json.dumps(context_data, ensure_ascii=False, indent=2)
        
        # --- TOKEN GUARD (NỚI LỎNG CHO GEMINI FREE) ---
        # Nâng lên 15.000 ký tự để không mất logic khi liên thông workflow
        CHAR_LIMIT = 15000 
        if len(final_context) > CHAR_LIMIT:
            final_context = final_context[:CHAR_LIMIT] + "\n... (Dữ liệu lớn, Bot Biên Tập đã cắt lát kỹ thuật)"
            print(f"⚠️ {self.bot_editor}: Cảnh báo: Metadata vượt ngưỡng 15k ký tự.")

        return final_context

    def get_form_knowledge(self, *args, **kwargs):
        """ 
        Hàm Alias (bí danh) để tương thích với các Component cũ của Vũ.
        """
        if len(args) == 1:
            return self.get_form_knowledge_from_db(args[0])
        elif len(args) >= 3:
            p_folder, mod_name, form_name = args[0], args[1], args[2]
            return f"Nghiệp vụ: {form_name} (Module: {mod_name}).\n(Lưu ý: Metadata sâu chưa được tải)."
        return "⚠️ Không xác định được yêu cầu lấy tri thức."

    # =================================================================
    # VAI TRÒ 2: BOT ĐẠO DIỄN (Prompt Engineering & Script Layout)
    # =================================================================
    def generate_ai_prompt(self, module_name, form_name, config, context):
        """ 
        [Bot Đạo Diễn] - Soạn thảo kịch bản chi tiết dựa trên chỉ đạo từ GUI. 
        """
        print(f"{self.bot_director}: Đang soạn kịch bản cho phân cảnh '{form_name}'...")
        
        # Lấy thông tin từ GUI, không tự chế
        slogan = config.get('slogan', Config.DEFAULT_SLOGAN)
        user_notes = config.get('notes', "")
        
        prompt = f"""
        Bạn là Đạo diễn kịch bản cho series 'Hướng dẫn phần mềm Ứng Dụng Vàng'.
        Nhiệm vụ: Viết kịch bản thao tác chuẩn xác cho chức năng "{form_name}" (Module {module_name}).
        
        --- 📚 KIẾN THỨC NGHIỆP VỤ (DỮ LIỆU THỰC TẾ) ---
        {context}

        --- ✍️ CHỈ ĐẠO TỪ BIÊN KỊCH VŨ (GUI) ---
        {user_notes if user_notes else "Dùng ngôn từ ngành kim hoàn chuyên nghiệp (vàng, tuổi vàng, tiền công)."}

        --- 🎬 CẤU TRÚC KỊCH BẢN (CHO BOT DIỄN VIÊN) ---
        Kịch bản gồm các bước JSON. Mỗi bước: Speak (Hoài My nói) -> Action (Bot thực hiện).
        - 'action': [speak, highlight, click, type, hover, wait].
        - 'target': Selector CSS chính xác từ Metadata hoặc text (VD: "text='Thêm mới'").
        - 'text': Lời thoại tiếng Việt.
        - 'value': Giá trị nhập mẫu thực tế.
        - 'duration': 0.5 - 2.0 giây.

        Hành động cuối cùng luôn là lời chào kết: "{slogan}"

        --- 📤 ĐỊNH DẠNG JSON TRẢ VỀ (BẮT BUỘC) ---
        Chỉ trả về duy nhất 1 mảng JSON. Không giải thích thêm.
        """
        return prompt

    # =================================================================
    # VAI TRÒ 3: BOT DIỄN VIÊN (Gemini Execution)
    # =================================================================
    def get_ai_script(self, prompt, model_name="gemini-1.5-flash"):
        """ [Bot Diễn Viên] - Kết nối bộ não Gemini để 'diễn' ra JSON. """
        print(f"{self.bot_actor}: Đang 'nhập vai' với model: {model_name}...")
        try:
            api_key = os.getenv("GOOGLE_API_KEY") or Config.GEMINI_API_KEY
            
            # Khởi tạo client với cấu hình tường minh
            # Nếu Vũ dùng API Key từ Google AI Studio (không phải Google Cloud Vertex AI)
            client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
            
            # Kiểm tra và làm sạch tên model (tránh trùng lặp models/models/)
            clean_model_name = model_name.replace("models/", "")
            
            response = client.models.generate_content(
                model=clean_model_name, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7 
                )
            )
            
            # Kiểm tra dữ liệu trả về trước khi parse
            if not response or not response.text:
                print(f"⚠️ {self.bot_actor}: Gemini không trả về dữ liệu văn bản.")
                return []
            
            # Bóc tách JSON an toàn hơn
            try:
                # Đôi khi AI trả về markdown ```json ... ```, dùng re hoặc strip để lấy lõi
                raw_text = response.text.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
                steps = json.loads(raw_text)
                return steps if isinstance(steps, list) else []
            except json.JSONDecodeError:
                print(f"❌ {self.bot_actor}: Lỗi giải mã kịch bản JSON.")
                return []
                
        except Exception as e:
            # In ra log chi tiết để Vũ debug nhanh
            print(f"🚨 [LỖI CHI TIẾT]: {str(e)}") 
            st.error(f"❌ {self.bot_actor} gặp sự cố: {str(e)}")
            return []
    # =================================================================
    # VAI TRÒ 4: BOT HẬU KỲ (Validation & Guardrails)
    # =================================================================
    def validate_prompt_size(self, prompt_text):
        """ 
        [Bot Hậu Kỳ] - Kiểm soát chất lượng và giới hạn an toàn.
        """
        print(f"{self.bot_qa}: Đang kiểm tra an toàn đạo cụ (Prompt size)...")
        LIMIT = 15000 
        current_size = len(prompt_text)
        if current_size > LIMIT:
            return False, f"🚨 Prompt quá nặng ({current_size} ký tự)! Vũ hãy bớt ghi chú lại."
        return True, "✅ Prompt an toàn."

    # =================================================================
    # GIÁM ĐỐC SẢN XUẤT (Orchestrator)
    # =================================================================
    def orchestrate_script_production(self, sub_item, config):
        """
        Quy trình sản xuất kịch bản khép kín lấy AI từ GUI.
        """
        # BƯỚC 1: Bot Biên Tập
        context = self.get_form_knowledge_from_db(sub_item)
        
        if "⚠️" in context or "❌" in context:
            return None, context 

        # BƯỚC 2: Bot Đạo Diễn
        module_name = sub_item.get('module_name', 'Hệ thống')
        form_name = sub_item.get('sub_title', 'Nghiệp vụ')
        full_prompt = self.generate_ai_prompt(module_name, form_name, config, context)
        
        # BƯỚC 3: Bot Hậu Kỳ
        is_safe, msg = self.validate_prompt_size(full_prompt)
        if not is_safe:
            return None, msg

        # BƯỚC 4: Bot Diễn Viên
        script_json = self.get_ai_script(full_prompt)
        
        if script_json:
            print(f"🎬 {self.bot_actor}: Đóng máy! Kịch bản sẵn sàng lên sóng.")
            return script_json, "🎬 Kịch bản đã sẵn sàng lên sóng!"
        
        return None, "❌ Sản xuất kịch bản thất bại."