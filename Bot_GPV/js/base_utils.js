/**
 * GIAIPHAPVANG STUDIO BOT - FULL CORE UTILITIES
 * Tác giả: Vũ & Gemini
 */

window.utils = {
    sleep: (ms) => new Promise(r => setTimeout(r, ms)),

    getCleanText: (el) => {
        if (!el) return "";
        try {
            // Lấy text, ưu tiên các thẻ chứa text trực tiếp để tránh hốt nhầm text của menu con
            let raw = el.innerText || el.textContent || "";
            return raw.split('\n')[0].replace(/[•○\+\-\|\|\>\r\n]/g, '').trim();
        } catch (e) { return ""; }
    },

    // 1. ÉP BUNG SIDEBAR (Bản Vét Cạn Tối Ưu)
    expandAllMenus: async () => {
        console.log("📂 Đang tổng lực công phá Sidebar...");
        let expandedSomething = true;
        let safetyCounter = 0;

        while (expandedSomething && safetyCounter < 8) {
            expandedSomething = false;
            safetyCounter++;
            const menuItems = document.querySelectorAll('.MuiTreeItem-content, .MuiListItem-root[role="button"], .nav-item.has-treeview');

            for (let item of menuItems) {
                const parentItem = item.closest('.MuiTreeItem-root');
                const isExpanded = (parentItem && parentItem.getAttribute('aria-expanded') === 'true') || 
                                   item.classList.contains('Mui-expanded') || 
                                   item.parentElement.classList.contains('menu-open');

                // Dấu hiệu có con: Icon mũi tên chỉ sang phải
                const hasChildren = item.querySelector('svg[data-testid="ChevronRightIcon"], .MuiTreeItem-iconContainer, .fa-angle-left');

                if (hasChildren && !isExpanded) {
                    console.log(`➡️ Đang ép bung: [${window.utils.getCleanText(item)}]`);
                    item.click();
                    expandedSomething = true;
                    await new Promise(r => setTimeout(r, 600)); 
                }
            }
        }
        const sidebar = document.querySelector('.MuiDrawer-root, nav, .main-sidebar') || document.body;
        sidebar.scrollTop = 0;
        console.log("✅ Sidebar đã bung lụa hoàn toàn!");
    },

    // 2. NỘI SOI TRANG
    internalScan: (container) => {
        const data = { actions: [], inputs: [], tables: [] };
        const target = container || document.querySelector('main, #content, .MuiContainer-root') || document.body;

        // Quét Actions (Nút, Link)
        target.querySelectorAll('button, a, [role="button"]').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) {
                const label = window.utils.getCleanText(el);
                if (label.length > 1) {
                    data.actions.push({
                        label: label,
                        selector: el.getAttribute('data-testid') ? `[data-testid="${el.getAttribute('data-testid')}"]` : el.tagName.toLowerCase()
                    });
                }
            }
        });

        // Quét Inputs
        target.querySelectorAll('input, textarea, select').forEach(input => {
            const r = input.getBoundingClientRect();
            if (r.width > 0 && r.height > 0 && input.type !== 'hidden') {
                data.inputs.push({
                    label: input.placeholder || input.name || input.getAttribute('aria-label') || "Ô nhập liệu",
                    type: input.type || input.tagName.toLowerCase(),
                    value: input.value || ""
                });
            }
        });

        // Quét Tables
        target.querySelectorAll('table, .MuiDataGrid-root').forEach(table => {
            const headers = Array.from(table.querySelectorAll('th, .MuiDataGrid-columnHeaderTitle'))
                .map(h => window.utils.getCleanText(h))
                .filter(h => h.length > 0);
            if (headers.length > 0) {
                data.tables.push({ header_count: headers.length, columns: headers });
            }
        });
        return data;
    }
};

window.nav = {
    get_ui_tree: function() {
        const results = [];
        // 1. Lấy toàn bộ các mục trong sidebar (quét phẳng như code cũ của Vũ)
        const allItems = document.querySelectorAll('nav li, [class*="sidebar"] li, .minimal__nav__li');
        
        let currentParent = "Chưa phân loại";

        allItems.forEach(el => {
            // Check nếu là Subheader (Hệ thống, Danh mục...)
            const isHeader = el.classList.contains('MuiListSubheader-root') || el.classList.contains('minimal__nav__subheader');
            const text = el.innerText.split('\n')[0].replace(/[\*\•\○\+]/g, '').trim();
            
            if (isHeader) {
                currentParent = text;
                results.push({ title: currentParent, href: "#", children: [] });
            } else {
                // Tìm link bên trong
                const link = el.querySelector('a');
                const titleEl = el.querySelector('.minimal__nav__item__title') || el;
                const title = titleEl.innerText.split('\n')[0].trim();

                if (link && link.href && !link.href.endsWith('#')) {
                    // Nếu đã có cha thì nhét vào con của cha đó
                    let parentObj = results.find(p => p.title === currentParent);
                    if (!parentObj) {
                        parentObj = { title: currentParent, href: "#", children: [] };
                        results.push(parentObj);
                    }
                    
                    // Kiểm tra xem có phải group con (Level 2) không?
                    const isNested = el.closest('.MuiCollapse-root');
                    let finalTitle = title;
                    if (isNested) {
                        // Thử lấy tên group cha (như Thông tin công ty)
                        const groupBtn = isNested.previousElementSibling;
                        if (groupBtn) {
                            const groupName = groupBtn.innerText.split('\n')[0].trim();
                            finalTitle = `${groupName} > ${title}`;
                        }
                    }

                    parentObj.children.push({
                        title: finalTitle,
                        href: link.href
                    });
                }
            }
        });
        return results.filter(r => r.children.length > 0);
    }
};

        

// Sửa lại kết quả push cho đúng chuẩn JS
const raw_push = (arr, val) => arr.push(val); 
// (Dòng này để nhắc Vũ thay .append thành .push nếu lỡ tay gõ nhầm)

window.utils_loaded = true;