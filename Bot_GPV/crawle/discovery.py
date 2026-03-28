# # Bot_GPV/crawle/discovery.py
# import json
# import os

# class Discovery:
#     def __init__(self, page):
#         self.page = page
#         # Đảm bảo đường dẫn data luôn ở gốc dự án
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         self.data_dir = os.path.abspath(os.path.join(current_dir, "../../data"))
#         if not os.path.exists(self.data_dir):
#             os.makedirs(self.data_dir)

#     def run(self):
#         print("🔍 Phase 1: Đang lập danh mục App từ Sidebar...")
#         try:
#             # Thay vì đợi .MuiDrawer-root, ta đợi các nút Menu xuất hiện
#             # Selector này quét cả MuiListItemButton lẫn các thẻ role='button' trong nav
#             self.page.wait_for_selector(".MuiListItemButton-root, [role='button']", timeout=15000)
            
#             modules = self.page.evaluate('''() => {
#                 // Tìm tất cả các item có khả năng là menu
#                 const selectors = ['.MuiListItemButton-root', '.MuiMenuItem-root', '[role="button"]'];
#                 let items = [];
#                 selectors.forEach(s => {
#                     const found = Array.from(document.querySelectorAll(s));
#                     items = [...items, ...found];
#                 });

#                 return items.map(el => {
#                     const text = el.innerText.split('\\n')[0].trim();
#                     return { name: text };
#                 }).filter(i => 
#                     i.name.length > 2 && 
#                     !['Đăng xuất', 'Thông báo', 'Cài đặt'].includes(i.name)
#                 );
#             }''')

#             # Lọc trùng lặp do quét nhiều selector
#             unique_modules = {}
#             descriptions = {
#                 "Hệ thống": "Quản lý công ty, chi nhánh, phòng ban.",
#                 "Kho & Quầy thu ngân": "Xử lý giao dịch bán ra, mua vào, bù tiền tuổi vàng.",
#                 "Danh mục sản phẩm": "Định nghĩa loại vàng, tiền công và hột đá.",
#                 "Danh mục đối tác, khách hàng": "Quản lý khách hàng và công nợ."
#             }

#             for mod in modules:
#                 name = mod['name']
#                 if name not in unique_modules:
#                     unique_modules[name] = descriptions.get(name, "Module nghiệp vụ tổng hợp.")
            
#             output_path = os.path.join(self.data_dir, "sitemap.json")
#             with open(output_path, "w", encoding="utf-8") as f:
#                 json.dump(unique_modules, f, ensure_ascii=False, indent=4)
            
#             return unique_modules
#         except Exception as e:
#             print(f"❌ Lỗi khi tìm Sidebar: {e}")
#             return {}