import streamlit as st
import json, os
from google import genai
from google.genai import types
from config import Config

class AIHandler:
    def get_form_knowledge(self, project_name, module_name, form_name):
        """
        Truy xuất JSON, lọc rác, tối ưu Token và chuyển thành văn bản nghiệp vụ.
        """
        path = Config.get_knowledge_path(project_name, module_name, form_name)
        
        if not os.path.exists(path):
            return f"⚠️ Hệ thống chưa có dữ liệu quét chi tiết cho Form: {form_name}. Vũ hãy nhấn 'Cập nhật Form (Cấp 2)' trước nhé!"
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            struct = data.get('structure', {})
            
            # --- 1. LỌC RÁC & TRÙNG LẶP ---
            # Danh sách các từ khóa nút bấm không cần thiết để soạn kịch bản
            BLACK_LIST_BTNS = ["close", "đóng", "settings", "cài đặt", "hủy", "cancel", "x", "n/a"]

            def clean_list(items):
                # Loại bỏ trùng, lọc rác và giới hạn số lượng (max 30 item để tránh tràn token)
                cleaned = []
                for item in items:
                    val = str(item).strip()
                    if val.lower() not in BLACK_LIST_BTNS and val not in cleaned:
                        cleaned.append(val)
                return cleaned[:30] 

            # 2. XỬ LÝ FIELDS (Input)
            raw_inputs = struct.get('form_fields', struct.get('inputs', []))
            inputs = []
            for i in raw_inputs:
                label = i.get('label')
                if label and label.lower() not in BLACK_LIST_BTNS:
                    i_type = i.get('type', 'text')
                    inputs.append(f"{label} ({i_type})")
            inputs = clean_list(inputs)
            
            # 3. XỬ LÝ BUTTONS & COLUMNS
            main_btns = clean_list(struct.get('actions', struct.get('buttons', [])))
            row_ops = clean_list(struct.get('row_operations', []))
            cols = clean_list(struct.get('columns', struct.get('table_columns', [])))
            
            # --- 4. XÂY DỰNG CONTEXT TỐI ƯU ---
            context = [
                f"Dự án: {project_name}",
                f"Module: {module_name} | Nghiệp vụ: {form_name}",
                "--- CHI TIẾT GIAO DIỆN ---",
                f"1. Ô nhập liệu (Fields): {', '.join(inputs) if inputs else 'Chỉ xem.'}",
                f"2. Nút chức năng chính: {', '.join(main_btns) if main_btns else 'N/A'}"
            ]
            
            if row_ops:
                context.append(f"3. Thao tác trên dòng: {', '.join(row_ops)}")
            
            if cols:
                # Chỉ lấy 15 cột đầu nếu bảng quá rộng
                context.append(f"4. Danh sách cột: {', '.join(cols[:15])}")
            
            context.append("\n--- THÔNG TIN HỆ THỐNG ---")
            context.append(f"URL: {data.get('url', 'N/A')}")
            context.append(f"Thời gian quét: {data.get('updated_at', 'N/A')}")
            
            # Gộp lại thành chuỗi văn bản
            final_context = "\n".join(context)
            
            # --- 5. CHỐT CHẶN TOKEN CUỐI CÙNG ---
            # Giới hạn cứng 3000 ký tự (~750-1000 tokens) - Mức an toàn tuyệt đối
            if len(final_context) > 3000:
                final_context = final_context[:3000] + "\n... (Dữ liệu quá dài, đã được cắt bớt để tối ưu AI)"
                
            return final_context
            
        except Exception as e:
            return f"❌ Lỗi khi bóc tách kiến thức JSON: {str(e)}"

    def generate_ai_prompt(self, module_name, form_name, config, context):
        """Hàm soạn thảo Prompt gửi Gemini - Đã tối ưu cho ngành Kim Hoàn"""
        
        slogan = config.get('slogan', Config.DEFAULT_SLOGAN)
        user_notes = config.get('notes', "")
        
        # Lấy danh sách kịch bản (ADD, EDIT, DELETE...)
        scenarios = config.get('scenarios', ["ADD"])
        scenario_text = ", ".join(scenarios)

        prompt = f"""
        Bạn là chuyên gia đào tạo phần mềm ERP 'Giải Pháp Vàng' cho tiệm vàng.
        Hãy soạn kịch bản Video Hướng dẫn cho chức năng: "{form_name}" (Module {module_name}).
        Loại nghiệp vụ: {scenario_text}.

        --- 💡 KIẾN THỨC HỆ THỐNG (DỮ LIỆU THẬT) ---
        {context}

        --- 📝 YÊU CẦU RIÊNG TỪ VŨ ---
        {user_notes if user_notes else "Hướng dẫn chi tiết, dùng thuật ngữ ngành vàng: tuổi vàng, trọng lượng, tiền công..."}

        --- 🎯 CHIẾN THUẬT ĐẠO DIỄN (DÀNH CHO BOT PLAYWRIGHT) ---
        1. LUÔN đi theo luồng: Speak (Dẫn nhập) -> Highlight (Gây chú ý) -> Click/Type (Hành động).
        2. 'target': Phải là CSS Selector chính xác từ dữ liệu thật (Ví dụ: #btn-add, input[name='gold_weight']). 
           - Nếu dữ liệu không có Selector rõ ràng, hãy dùng Text Selector của Playwright (Ví dụ: "text='Thêm mới'").
        3. 'duration': Thời gian chờ hoặc di chuyển chuột (từ 0.8 đến 1.5 giây).
        4. 'value': Dữ liệu giả định phù hợp với ngành vàng (Ví dụ: Nhập trọng lượng là '1.500', loại vàng '610').

        --- 📤 ĐỊNH DẠNG JSON TRẢ VỀ (BẮT BUỘC) ---
        Trả về một mảng JSON các object. Mỗi object phải chứa:
        - "action": Một trong các loại [speak, highlight, click, type, hover, wait].
        - "target": CSS Selector hoặc Text Selector để Bot định vị phần tử.
        - "text": Lời thoại cho giọng Hoài My (chỉ dùng cho action 'speak' hoặc kèm theo hành động).
        - "value": Giá trị cần nhập (chỉ dùng cho action 'type').
        - "duration": Thời gian thực hiện (giây).

        Ví dụ cấu hình mẫu:
        [
            {{ 
                "action": "speak", 
                "text": "Chào mừng quý khách đến với hướng dẫn {form_name}. Đầu tiên hãy nhấn nút Thêm mới."
            }},
            {{ 
                "action": "click", 
                "target": "button:has-text('Thêm mới')", 
                "duration": 1.2
            }}
        ]
        
        --- KẾT THÚC ---
        Hành động cuối cùng luôn là "action": "speak" với slogan: "{slogan}"
        """
        return prompt

    def get_ai_script(self, prompt, model_name):
        """Kết nối Gemini API và trả về mảng các bước (steps)"""
        try:
            # Lấy API Key từ biến môi trường hoặc file config
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
                
            data = json.loads(response.text)
            
            # Chuẩn hóa dữ liệu trả về luôn là List
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
            return data if isinstance(data, list) else []
            
        except Exception as e:
            st.error(f"❌ Lỗi kết nối bộ não AI: {str(e)}")
            return []

    def validate_prompt_size(self, text):
        """Bảo vệ hệ thống: Không gửi prompt quá giới hạn của Model"""
        limit = 30000 
        size = len(text)
        return (size < limit, f"⚠️ Nội dung quá lớn ({size}/{limit} ký tự). Hãy bớt ghi chú lại Vũ ơi!")
    
    def get_form_knowledge_from_db(self, sub_content_item):
        """
        Phiên bản 'Vét cạn' trực tiếp từ dữ liệu Database.
        sub_content_item: Là một Dict (một dòng từ bảng sub_contents)
        """
        metadata = sub_content_item.get('metadata')
        if not metadata:
            return "⚠️ Form này chưa có dữ liệu metadata chi tiết trong DB."

        # Nếu metadata đang là chuỗi JSON (từ DB lên), thì parse nó
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                return "❌ Lỗi định dạng Metadata."

        # Tận dụng lại logic clean_list có sẵn hoặc viết gọn lại ở đây
        def get_labels(items):
            return [str(i.get('label', '')).strip() for i in items if i.get('label')]

        inputs = get_labels(metadata.get('form_fields', []))
        btns = metadata.get('actions', [])
        cols = metadata.get('columns', [])

        context = [
            f"Nghiệp vụ: {sub_content_item.get('sub_title')}",
            f"--- CẤU TRÚC KỸ THUẬT ---",
            f"- Các ô nhập liệu: {', '.join(inputs[:20]) if inputs else 'Không có'}",
            f"- Các nút thao tác: {', '.join(btns[:15]) if btns else 'Không có'}",
            f"- Các cột dữ liệu: {', '.join(cols[:10]) if cols else 'Không có'}"
        ]
        
        return "\n".join(context)

    def generate_final_script(self, ctrl, sub_id, config, model_name="gemini-1.5-flash"):
        """
        Hàm tổng lực: Lấy dữ liệu -> Tạo Prompt -> Gọi AI -> Trả về kịch bản.
        Vũ chỉ cần gọi hàm này từ giao diện Dashboard là xong.
        """
        # 1. Lấy dữ liệu từ DB thông qua Controller
        # Giả sử ctrl.get_sub_contents trả về list, ta tìm đúng item
        all_subs = ctrl.get_sub_contents(config.get('tutorial_id'))
        sub_item = next((s for s in all_subs if s['id'] == sub_id), None)
        
        if not sub_item:
            return []

        # 2. Xây dựng ngữ cảnh (Context)
        context = self.get_form_knowledge_from_db(sub_item)
        
        # 3. Tạo Prompt
        prompt = self.generate_ai_prompt(
            module_name=sub_item['sub_title'].split('|')[0],
            form_name=sub_item['sub_title'].split('|')[-1],
            config=config,
            context=context
        )
        
        # 4. Gọi Gemini và trả về kết quả
        return self.get_ai_script(prompt, model_name)
    
    def generate_bot_script(metadata, module_name, form_name):
        "Hàm mẫu: Chuyển Metadata thành Kịch bản Đạo diễn"
        script = []
        
        # 1. Bước chào sân (Dựa trên tên Module)
        script.append({
            "act": "wait", 
            "speech": f"Chào bạn, Hoài My sẽ hướng dẫn bạn thao tác trên mục {form_name} của hệ thống."
        })

        # 2. Bước bấm nút "Tạo mới" (Lấy từ actions trong metadata)
        # Giả sử Vũ đã cào được selector của nút này
        script.append({
            "act": "click",
            "target": "#btn-add-new", # Hoặc selector Vũ lưu trong DB
            "speech": "Đầu tiên, chúng ta nhấn vào nút Tạo mới để mở form nhập liệu."
        })

        # 3. Duyệt qua các form_fields để nhập liệu mẫu
        for field in metadata.get('form_fields', []):
            label = field.get('label')
            f_type = field.get('type')
            # Tìm selector dựa trên label hoặc name
            selector = f"input[name='{field.get('name')}']" 
            
            if f_type == "text":
                script.append({
                    "act": "type",
                    "target": selector,
                    "val": f"Dữ liệu mẫu {label}",
                    "speech": f"Tại ô {label}, bạn hãy nhập thông tin vào nhé."
                })
                
        # 4. Bước chốt hạ (Nút Lưu)
        script.append({
            "act": "click",
            "target": "#btn-save",
            "speech": "Cuối cùng, nhấn Lưu để hoàn tất nghiệp vụ. Rất đơn giản phải không nào?"
        })
        
        return script

