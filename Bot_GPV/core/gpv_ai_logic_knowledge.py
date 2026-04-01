import streamlit as st
import json
import os
import re
from google import genai
from google.genai import types
from config import Config
import requests

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
            "system": "Ứng Dụng Vàng",
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
        [Bot Đạo Diễn] - Soạn thảo kịch bản dựa trên Blueprint 5 cấp.
        """
        slogan = config.get('slogan', "Ứng dụng vàng, giải pháp toàn diện cho ngành kim hoàn")
        user_notes = config.get('notes', "")
        
        # Lưu ý: Context ở đây chính là chuỗi Blueprint JSON mà StudioController gửi sang
        prompt = f"""
Bạn là Đạo diễn kịch bản cho series 'Hướng dẫn phần mềm Ứng Dụng Vàng'.
Nhiệm vụ: Viết kịch bản thao tác chuẩn xác cho chức năng "{form_name}" (Module {module_name}).

{context}

--- ✍️ CHỈ ĐẠO TỪ BIÊN KỊCH VŨ (GUI) ---
{user_notes if user_notes else "Dùng ngôn từ ngành kim hoàn chuyên nghiệp (tiệm vàng, tuổi vàng, tiền công)."}

--- 🎬 CẤU TRÚC KỊCH BẢN (CHO BOT DIỄN VIÊN) ---
Kịch bản gồm các bước JSON. Mỗi bước: Speak (Hoài My nói) -> Action (Bot thực hiện).
- 'action': [speak, highlight, click, type, hover, wait].
- 'target': Selector CSS chính xác từ Blueprint hoặc text (VD: "text='Thêm mới'").
- 'text': Lời thoại tiếng Việt (phải khớp với hành động).
- 'value': Giá trị nhập mẫu thực tế (nếu là hành động type).
- 'duration': 0.5 - 2.5 giây.

Hành động cuối cùng luôn là lời chào kết: "{slogan}"

--- 📤 ĐỊNH DẠNG JSON TRẢ VỀ (BẮT BUỘC) ---
Chỉ trả về duy nhất 1 mảng JSON. Không giải thích thêm.
"""
        return prompt

    # =================================================================
    # VAI TRÒ 3: BOT DIỄN VIÊN (Gemini Execution)
    # =================================================================  

    def get_ai_script(self, prompt, model="gemini-1.5-flash", provider="Gemini"):
        """ 
        [Bot Diễn Viên] - Xử lý đa nền tảng và gọt dũa JSON siêu chuẩn. 
        Đảm bảo đầu ra luôn là một list các bước thao tác.
        """
        print(f"\n--- [NỘI DUNG BỨC THƯ GỬI ĐI] ---\n{prompt}\n--- [HẾT BỨC THƯ] ---\n")
        
        provider_node = provider.lower()
        print(f"{self.bot_actor}: Đang 'nhập vai' với {provider} (Model: {model})...")
        
        try:
            raw_text = ""

            # --- NHÁNH 1: GOOGLE GEMINI (Sử dụng SDK v1beta cho tính năng JSON mode) ---
            if provider_node == "gemini":
                api_key = os.getenv("GOOGLE_API_KEY") or Config.GEMINI_API_KEY
                # Khởi tạo client với cấu hình chuẩn
                client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
                clean_model_name = model.replace("models/", "")
                
                response = client.models.generate_content(
                    model=clean_model_name, 
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json", 
                        temperature=0.2 
                    )
                )
                raw_text = response.text

            # --- NHÁNH 2: OLLAMA (Chạy Local) ---
            elif provider_node == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
                payload = {
                    "model": model, 
                    "prompt": prompt,
                    "stream": False,
                    "format": "json" 
                }
                response = requests.post(f"{base_url}/api/generate", json=payload, timeout=180)
                response.raise_for_status()
                raw_text = response.json().get("response", "")

            # --- NHÁNH 3: GROQ (Tốc độ cao) ---
            elif provider_node == "groq":
                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                raw_text = completion.choices[0].message.content

            # =========================================================
            # LỚP GỌT DŨA JSON (CLEANING LAYER) - CỰC KỲ QUAN TRỌNG
            # =========================================================
            if not raw_text: 
                print(f"❌ {self.bot_actor}: AI không trả về dữ liệu.")
                return []

            content = raw_text.strip()
            
            # 1. Khử Markdown (nếu AI quên JSON mode) và trích xuất mảng/đối tượng JSON
            # Regex này tìm từ dấu [ hoặc { đầu tiên đến dấu ] hoặc } cuối cùng
            json_match = re.search(r"([\[\{][\s\S]*[\]\}])", content)
            if json_match:
                content = json_match.group(1)

            # 2. Xử lý lỗi phổ biến: dấu phẩy thừa trước dấu đóng ngoặc (Trailing Commas)
            content = re.sub(r",\s*([\]\}])", r"\1", content)

            # 3. Chuyển đổi thành dữ liệu Python
            try:
                data = json.loads(content)
                
                # Trường hợp 1: AI trả về trực tiếp một List (Đúng chuẩn nhất)
                if isinstance(data, list):
                    return data
                
                # Trường hợp 2: AI bọc list trong một Object (Vd: {"steps": [...]})
                if isinstance(data, dict):
                    # Duyệt tìm các key phổ biến mà AI hay tự đặt
                    for key in ["steps", "actions", "script", "data", "commands"]:
                        if key in data and isinstance(data[key], list):
                            print(f"✅ {self.bot_actor}: Đã trích xuất list từ key '{key}'")
                            return data[key]
                    
                    # Nếu là dict đơn lẻ, bọc nó vào list để đồng bộ đầu ra
                    return [data]
                
                return []
            except json.JSONDecodeError as je:
                print(f"❌ {self.bot_actor}: Lỗi parse JSON: {je}")
                # Ghi log để hậu kiểm
                with open("debug_raw_ai_error.txt", "w", encoding="utf-8") as f:
                    f.write(raw_text)
                return []

        except Exception as e:
            print(f"🚨 {self.bot_actor} Lỗi hệ thống: {str(e)}")
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
    def orchestrate_script_production(self, sub_item, config, model_name="gemini-1.5-flash", provider="Gemini"):
        """
        Quy trình sản xuất kịch bản khép kín lấy AI từ GUI.
        CẬP NHẬT: Nhận thêm model_name và provider từ Giao diện.
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

        # BƯỚC 4: Bot Diễn Viên (FIX: Truyền đủ tham số điều hướng)
        # Bước 4: Gọi Bot Diễn Viên
        script_json = self.get_ai_script(
            prompt=full_prompt, 
            model=model_name,        # Truyền model
            provider=provider
        )
        
        if script_json:
            print(f"🎬 {self.bot_actor}: Đóng máy! Kịch bản sẵn sàng lên sóng.")
            return script_json, "🎬 Kịch bản đã sẵn sàng lên sóng!"
        
        return None, "❌ Sản xuất kịch bản thất bại."