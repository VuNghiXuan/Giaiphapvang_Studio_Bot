class KnowledgeBase:
    def __init__(self):
        self.common_info = {
            "brand": "Phần mềm Giải Pháp Vàng (Giaiphapvang.net)",
            "bot_role": "Trợ lý ảo hướng dẫn sử dụng phần mềm chuyên nghiệp"
        }

        self.scenarios = {
            "login_system": {
                "title": "Hướng dẫn Đăng nhập và Truy cập Hệ thống",
                "selectors": {
                    "url": "https://giaiphapvang.net/auth/jwt/sign-in/",
                    "email": "input[name='email']",
                    "password": "input[name='password']",
                    "submit": "button[type='submit']",
                    # Selector mới mày vừa cào được nè Vũ
                    "btn_he_thong": "internal:role=link[name='Hệ thống'i]",
                    "dashboard_verify": "text=/Tổng quan|Dashboard/i"
                }
            },
            "danh_muc_chi_nhanh": {
                "title": "Quản lý Danh mục Chi nhánh",
                "fields": ["Mã chi nhánh", "Tên chi nhánh", "Địa chỉ", "Số điện thoại"],
                "selectors": {
                    "menu": "internal:role=link[name='Danh mục'i]", # Dùng smart selector luôn
                    "sub_menu": "internal:role=link[name='Chi nhánh'i]",
                    "btn_add": "button:has-text('Thêm mới')",
                    "btn_save": "button:has-text('Lưu')"
                }
            }
        }

    def get_prompt_for_bot(self, scenario_key, action_logs):
        scene = self.scenarios.get(scenario_key, {})
        
        # Tao tinh chỉnh lại Prompt để AI viết văn phong lồng tiếng hay hơn
        prompt = f"""
        Bạn là một biên tập viên kịch bản chuyên nghiệp cho {self.common_info['brand']}.
        Nhiệm vụ: Viết lời thoại thuyết minh cho video hướng dẫn dựa trên hành động của Robot.

        NGỮ CẢNH: {scene.get('title', 'Hướng dẫn sử dụng')}
        DỮ LIỆU HÀNH ĐỘNG THỰC TẾ:
        {action_logs}

        YÊU CẦU VỀ LỜI THOẠI:
        1. Ngôn ngữ: Tiếng Việt, lịch sự (dùng 'Quý vị', 'Các bạn', 'Chúng ta').
        2. Tự nhiên: Không đọc máy móc các selector. Thay vì 'Click button 4', hãy nói 'Tiếp theo, nhấn vào nút xác nhận'.
        3. Khớp thời gian: Trả về đúng mốc thời gian 'start' từ Action Logs.
        4. Định dạng: Chỉ trả về mảng JSON duy nhất, không giải thích gì thêm.
           Ví dụ: [{"start": 0.0, "text": "Chào mừng quý vị đến với Giải Pháp Vàng..."}, ...]

        LƯU Ý: Tuyệt đối không đọc mật khẩu hoặc email cá nhân trong lời thoại.
        """
        return prompt