# import json
# import os
# import sys

# class AppExtractor:
#     def __init__(self):
#         self.knowledge_data = {}
#         # Xác định đường dẫn gốc của dự án (Project Root)
#         # Nếu chạy file .py thông thường, nó lấy folder cha của folder chứa file này
#         # Nếu build .exe, nó sẽ lấy đường dẫn thực tế nơi file .exe đang chạy
#         if getattr(sys, 'frozen', False):
#             # Đường dẫn khi chạy file .exe
#             self.project_root = os.path.dirname(sys.executable)
#         else:
#             # Đường dẫn khi chạy script .py (nhảy ra khỏi Bot_GPV)
#             # File này nằm ở Bot_GPV/crawle/app_extractor.py -> lùi 2 cấp
#             current_dir = os.path.dirname(os.path.abspath(__file__))
#             self.project_root = os.path.abspath(os.path.join(current_dir, "../../"))

#         self.data_dir = os.path.join(self.project_root, "data")
#         self.output_file = os.path.join(self.data_dir, "knowledge_base.json")

#         # Tạo thư mục data ở gốc nếu chưa có
#         if not os.path.exists(self.data_dir):
#             os.makedirs(self.data_dir)

#     def extract_structure(self, page, page_name):
#         print(f"🧬 Đang phân tích chi tiết: {page_name}")
#         page.wait_for_timeout(2000) 

#         structure = page.evaluate('''() => {
#             const clean = (t) => t ? t.split('\\n')[0].replace(/[\\*\\•]/g, '').trim() : "";
            
#             const tabs = Array.from(document.querySelectorAll('.MuiTab-root'))
#                 .map(el => clean(el.innerText))
#                 .filter(t => t.length > 1);

#             const columns = Array.from(document.querySelectorAll('.MuiDataGrid-columnHeaderTitle'))
#                 .map(h => clean(h.innerText))
#                 .filter(h => h && !['STT', 'Thao tác', 'Chức năng'].includes(h));

#             const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"])'))
#                 .map(el => {
#                     const label = clean(el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText || el.placeholder);
#                     return { label: label, name: el.name || el.id };
#                 }).filter(i => i.label);

#             return {
#                 navigation_tabs: [...new Set(tabs)],
#                 columns: columns,
#                 inputs: inputs,
#                 url: window.location.href
#             };
#         }''')

#         structure['row_actions'] = self._get_hidden_actions(page)
        
#         # Kiểm tra nút "Tạo mới" (hỗ trợ cả viết hoa/viết thường)
#         create_btn = page.get_by_role("button", name=re.compile("Tạo mới", re.IGNORECASE))
#         if create_btn.is_visible():
#             structure['create_form_fields'] = self._scan_create_form(page)

#         self.knowledge_data[page_name] = structure
#         self._save()

#     def _get_hidden_actions(self, page):
#         try:
#             btn_more = page.locator(".MuiDataGrid-row button").first
#             if btn_more.is_visible():
#                 btn_more.click()
#                 page.wait_for_selector(".MuiMenu-list", timeout=2000)
#                 actions = page.evaluate('() => Array.from(document.querySelectorAll(".MuiMenuItem-root")).map(el => el.innerText.trim())')
#                 page.keyboard.press("Escape")
#                 return actions
#         except: pass
#         return []

#     def _scan_create_form(self, page):
#         print(f"   📝 Đang quét Form cho: {page.url}")
#         fields = []
#         try:
#             page.get_by_role("button", name=re.compile("Tạo mới", re.IGNORECASE)).click()
#             page.wait_for_selector(".MuiDialog-root, .MuiDrawer-paper, .MuiBox-root", timeout=3000)
            
#             fields = page.evaluate('''() => {
#                 const formContainer = document.querySelector('.MuiDialog-root, .MuiDrawer-paper, form');
#                 if (!formContainer) return [];
                
#                 return Array.from(formContainer.querySelectorAll('input, select, textarea'))
#                     .map(el => {
#                         const label = el.closest('.MuiFormControl-root')?.querySelector('label')?.innerText 
#                                      || el.placeholder 
#                                      || el.getAttribute('aria-label');
#                         return {
#                             label: label ? label.split('\\n')[0].trim() : "Không tên",
#                             name: el.name || el.id,
#                             type: el.type
#                         };
#                     }).filter(f => f.label && f.label !== "Không tên");
#             }''')
#             # Nhấn Hủy hoặc Escape để đóng form
#             page.keyboard.press("Escape")
#         except Exception as e:
#             print(f"   ⚠️ Không quét được form: {e}")
#         return fields

#     def _save(self):
#         # Lưu vào file với đường dẫn đã được chuẩn hóa
#         with open(self.output_file, "w", encoding="utf-8") as f:
#             json.dump(self.knowledge_data, f, ensure_ascii=False, indent=4)
#         print(f"💾 Đã cập nhật kiến thức vào: {self.output_file}")