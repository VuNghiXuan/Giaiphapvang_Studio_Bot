window.sidebarScraper = {
    expandAll: async () => {
        let expandedSomething = true;
        while (expandedSomething) {
            expandedSomething = false;
            // Tìm các nút chưa mở
            const buttons = Array.from(document.querySelectorAll('.minimal__nav__item__root[role="button"]:not(a)'))
                .filter(btn => {
                    const isExpanded = btn.getAttribute('aria-expanded') === 'true' || 
                                     btn.classList.contains('--open');
                    return !isExpanded;
                });

            if (buttons.length > 0) {
                for (const btn of buttons) {
                    btn.click();
                    expandedSomething = true;
                }
                // Đợi một khoảng cho tất cả các mục vừa click kịp render
                await new Promise(r => setTimeout(r, 500));
            }
        }
        console.log("✅ Đã mở toàn bộ menu!");
    },

    extractData: (prefix) => {
        const results = {};
        const links = document.querySelectorAll('a.minimal__nav__item__root');
        
        links.forEach(a => {
            if (!a.href || a.href.startsWith('javascript:')) return;

            const titleEl = a.querySelector('.minimal__nav__item__title');
            const itemText = (titleEl ? titleEl.innerText : a.innerText).trim();
            
            // Tìm Group (MUI Collapse)
            const collapseParent = a.closest('.MuiCollapse-root');
            const groupName = collapseParent?.previousElementSibling?.innerText?.trim() || "";

            // Tìm Subheader (Duyệt ngược tìm phần tử có class subheader)
            let subheaderName = "Chung";
            let sibling = a.closest('.minimal__nav__li');
            while (sibling) {
                const sub = sibling.querySelector('.minimal__nav__subheader');
                if (sub) {
                    subheaderName = sub.innerText.trim();
                    break;
                }
                sibling = sibling.previousElementSibling;
            }

            const parentPath = groupName && groupName !== itemText ? `${subheaderName} | ${groupName}` : subheaderName;
            const fullPath = `${prefix} | ${parentPath} | ${itemText}`;
            
            results[fullPath] = {
                url: a.href,
                module_parent: prefix,
                parent: parentPath,
                text: itemText,
                scanned_at: new Date().toISOString() // Dùng ISO cho chuẩn database
            };
        });
        return results;
    },

    // Hàm tiện ích để chạy cả 2 bước và tải file JSON
    run: async function(prefix) {
        await this.expandAll();
        const data = this.extractData(prefix);
        console.table(data); // Xem nhanh kết quả
        return data;
    }
};