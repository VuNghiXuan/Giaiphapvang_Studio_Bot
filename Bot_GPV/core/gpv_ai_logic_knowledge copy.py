import streamlit as st
import json, os
from google import genai
from google.genai import types
from config import Config

class AIHandler:
    def __init__(self):
        # Thông báo khởi tạo các vai trò studio
        print("🎬 [Bot Biên Tập]: Sẵn sàng lọc Metadata...")
        print("🎥 [Bot Đạo Diễn]: Sẵn sàng lập ý đồ kịch bản...")
        print("🎭 [Bot Diễn Viên]: Kết nối bộ não Gemini...")

    def get_form_knowledge_from_db(self, sub_content_item):
        """ 
        [Bot Biên Tập] - Kiểm soát Token & Lọc dữ liệu thông minh.
        Hàm này tương đương với 'get_form_knowledge' mà Component đang gọi.
        """
        if not sub_content_item:
            return "⚠️ Không tìm thấy dữ liệu nội dung."

        metadata = sub_content_item.get('metadata')
        if not metadata: 
            return "⚠️ Form này chưa có tri thức (Metadata). Vũ hãy quét Cấp 2 trước!"

        # Xử lý nếu metadata là chuỗi JSON
        if isinstance(metadata, str):
            try: 
                metadata = json.loads(metadata)
            except: 
                return "❌ Lỗi: Metadata không đúng định dạng JSON."

        # --- LỚP 1: LỌC RÁC (BLACK LIST) ---
        BLACK_LIST = ["close", "đóng", "hủy", "cancel", "x", "n/a", "settings", "cài đặt", "thoát"]
        
        # --- LỚP 2: TRÍCH XUẤT & CẮT LÁT (SLICING) ---
        # Chỉ lấy tối đa 20 fields quan trọng nhất để tiết kiệm Token
        raw_fields = metadata.get('form_fields', [])
        inputs = [
            f"{f.get('label')} ({f.get('type')})" 
            for f in raw_fields 
            if isinstance(f, dict) and f.get('label') and f.get('label').lower() not in BLACK_LIST
        ][:20] 
        
        # Chỉ lấy tối đa 10 nút chức năng
        raw_actions = metadata.get('actions', [])
        btns = [
            (b.get('label') if isinstance(b, dict) else str(b))
            for b in raw_actions 
            if (isinstance(b, dict) and b.get('label') and b.get('label').lower() not in BLACK_LIST) or (isinstance(b, str))
        ][:10] 
        
        # Chỉ lấy 10 cột đầu tiên của bảng dữ liệu
        cols = (metadata.get('columns') or [])[:10] 

        # --- LỚP 3: XÂY DỰNG NGỮ CẢNH ---
        context_lines = [
            f"Hệ thống: Ứng Dụng Vàng",
            f"Nghiệp vụ: {sub_content_item.get('sub_title', 'N/A')}",
            "--- THÔNG SỐ KỸ THUẬT GIAO DIỆN ---",
            f"- Ô nhập liệu: {', '.join(inputs) if inputs else 'Chế độ xem (N/A).'}",
            f"- Nút bấm khả dụng: {', '.join(btns) if btns else 'Không có nút bấm.'}",
            f"- Các cột dữ liệu bảng: {', '.join(cols) if cols else 'Không có bảng dữ liệu.'}"
        ]
        
        final_context = "\n".join(context_lines)
        
        # Giới hạn cứng 2500 ký tự cho phần Context (Token Guard)
        CHAR_LIMIT = 2500
        if len(final_context) > CHAR_LIMIT:
            final_context = final_context[:CHAR_LIMIT] + "\n... (Dữ liệu quá dài, Bot Biên Tập đã cắt bớt)"
            print(f"⚠️ [Cảnh báo]: Context vượt ngưỡng, đã tự động cắt lát.")

        return final_context

    # Tạo Alias để tránh lỗi AttributeError khi gọi get_form_knowledge
    def get_form_knowledge(self, *args, **kwargs):
        """ 
        Hàm trung gian thông minh: 
        Nếu truyền vào 1 Object (sub_item) -> Chạy logic DB.
        Nếu truyền vào nhiều tham số (p_folder, mod, form) -> Trả về text mặc định.
        """
        if len(args) == 1:
            # Trường hợp truyền 1 object item (như s)
            return self.get_form_knowledge_from_db(args[0])
        elif len(args) >= 3:
            # Trường hợp truyền (p_folder, mod_name, form_name)
            p_folder, mod_name, form_name = args[0], args[1], args[2]
            return f"Nghiệp vụ: {form_name} (Module: {mod_name}).\n(Lưu ý: Metadata sâu chưa được tải cho yêu cầu này)."
        
        return "⚠️ Không xác định được yêu cầu lấy tri thức."
    

    def generate_ai_prompt(self, module_name, form_name, config, context):
        """ [Bot Đạo Diễn] - Soạn thảo kịch bản chi tiết cho Phim Trường """
        slogan = config.get('slogan', Config.DEFAULT_SLOGAN)
        user_notes = config.get('notes', "")
        
        prompt = f"""
        Bạn là Đạo diễn kịch bản cho series 'Hướng dẫn phần mềm Ứng Dụng Vàng'.
        Nhiệm vụ: Viết kịch bản chi tiết cho chức năng "{form_name}" (Module {module_name}).
        
        --- 📚 KIẾN THỨC NGHIỆP VỤ (DỮ LIỆU THẬT) ---
        {context}

        --- ✍️ YÊU CẦU TỪ BIÊN KỊCH VŨ ---
        {user_notes if user_notes else "Dùng ngôn từ ngành kim hoàn (vàng 24k, tiền công, trọng lượng). Giọng điệu chuyên nghiệp."}

        --- 🎬 CẤU TRÚC KỊCH BẢN (DÀNH CHO BOT DIỄN VIÊN) ---
        Mỗi bước trong kịch bản phải tuân thủ luồng: Speak (Hoài My nói) -> Action (Bot thực hiện).
        - 'action': Chọn 1 trong [speak, highlight, click, type, hover, wait].
        - 'target': Selector CSS từ dữ liệu thật hoặc Text Selector (ví dụ: "text='Lưu'").
        - 'text': Lời thoại tiếng Việt cho giọng Hoài My.
        - 'value': Giá trị nhập mẫu (ví dụ: '1.200', 'Vàng 610').
        - 'duration': Thời gian thực hiện (0.5 - 2.0 giây).

        --- 📤 ĐỊNH DẠNG JSON TRẢ VỀ (BẮT BUỘC) ---
        Trả về duy nhất 1 mảng JSON hợp lệ. Không giải thích gì thêm.
        Ví dụ:
        [
            {{"action": "speak", "text": "Chào mừng bạn đến với phần mềm."}},
            {{"action": "click", "target": "button:has-text('Thêm')", "duration": 1.0}}
        ]
        
        Hành động cuối cùng luôn là lời chào: "{slogan}"
        """
        return prompt

    def get_ai_script(self, prompt, model_name="gemini-1.5-flash"):
        """ [Bot Diễn Viên] - Kết nối Gemini và xuất bản kịch bản JSON """
        try:
            api_key = os.getenv("GOOGLE_API_KEY") or Config.GEMINI_API_KEY
            client = genai.Client(api_key=api_key)
            
            response = client.models.generate_content(
                model=model_name, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7 
                )
            )
            
            if not response.text: 
                return []
            
            steps = json.loads(response.text)
            return steps if isinstance(steps, list) else []
            
        except Exception as e:
            st.error(f"❌ [Bot Diễn Viên] gặp sự cố: {str(e)}")
            return []

    def validate_prompt_size(self, prompt_text):
        """ [Bot Hậu Kỳ] - Kiểm tra tổng kích thước Prompt trước khi gửi đi """
        LIMIT = 15000 
        current_size = len(prompt_text)
        if current_size > LIMIT:
            return False, f"🚨 Prompt quá nặng ({current_size} ký tự)! Vũ hãy bớt ghi chú lại."
        return True, "✅ Prompt an toàn."
    
    def orchestrate_script_production(self, sub_item, config):
        """
        Quy trình sản xuất kịch bản khép kín
        """
        # BƯỚC 1: Bot Biên Tập lọc dữ liệu (Chỉ lấy tinh hoa)
        context = self.get_form_knowledge_from_db(sub_item)
        
        if "⚠️" in context or "❌" in context:
            return None, context # Báo lỗi cho Vũ nếu Metadata chưa quét

        # BƯỚC 2: Bot Đạo Diễn lên kịch bản (Prompt)
        module_name = sub_item.get('module_name', 'Hệ thống')
        form_name = sub_item.get('sub_title', 'Nghiệp vụ')
        
        full_prompt = self.generate_ai_prompt(module_name, form_name, config, context)
        
        # Kiểm tra kích thước Prompt (Bot Hậu Kỳ)
        is_safe, msg = self.validate_prompt_size(full_prompt)
        if not is_safe:
            return None, msg

        # BƯỚC 3: Bot Diễn Viên (Gemini) thực hiện & xuất JSON
        script_json = self.get_ai_script(full_prompt)
        
        return script_json, "🎬 Kịch bản đã sẵn sàng lên sóng!"