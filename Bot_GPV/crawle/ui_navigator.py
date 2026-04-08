# import re

# class UIMapNavigator:
#     def __init__(self, page):
#         self.page = page

#     async def get_ui_tree(self):
#         """
#         Quét Sidebar theo kiến trúc ngược: Từ Link tìm về Cha.
#         """
#         return await self.page.evaluate('''() => {
#             const tree = [];
#             // Target vào Sidebar của MUI
#             const sidebar = document.querySelector(".MuiDrawer-root, nav, [role='presentation']");
#             if (!sidebar) return tree;

#             // 1. Tìm tất cả các nhóm (Category/Menu Cha)
#             // Trong MUI, Menu Cha thường là Button không có href
#             const groups = Array.from(sidebar.querySelectorAll('.MuiListItem-root, .MuiButtonBase-root'))
#                 .filter(el => !el.href && !el.querySelector('a') && el.innerText.trim() !== "");

#             groups.forEach(group => {
#                 const groupTitle = group.innerText.split('\\n')[0].trim();
#                 const parentObj = {
#                     title: groupTitle,
#                     children: [],
#                     type: 'category'
#                 };

#                 // 2. Tìm các link nằm ngay sau nhóm này (thường nằm trong cùng một list hoặc container kế tiếp)
#                 // Chiến thuật: Tìm các anchor gần nhất
#                 let nextEl = group.nextElementSibling;
#                 // Nếu MUI dùng Collapse, các con sẽ nằm trong element kế tiếp
#                 if (nextEl) {
#                     const links = nextEl.querySelectorAll('a');
#                     links.forEach(link => {
#                         parentObj.children.push({
#                             title: link.innerText.trim().split('\\n')[0],
#                             href: link.href,
#                             type: 'form_link'
#                         });
#                     });
#                 }
                
#                 if (parentObj.children.length > 0) {
#                     tree.push(parentObj);
#                 }
#             });

#             // 3. Xử lý trường hợp Menu phẳng (không có nhóm, link nằm ngay ngoài cùng)
#             if (tree.length === 0) {
#                 const standaloneLinks = sidebar.querySelectorAll('a');
#                 standaloneLinks.forEach(link => {
#                     tree.push({
#                         title: link.innerText.trim(),
#                         href: link.href,
#                         type: 'form_link',
#                         children: []
#                     });
#                 });
#             }

#             return tree;
#         }''')

#     @staticmethod
#     def clean_filename(name):
#         return re.sub(r'[\\/*?:"<>|]', '_', name)