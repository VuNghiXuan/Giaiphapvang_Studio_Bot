window.sidebarScraper = {
    expandAll: async () => {
        let expandedSomething = true;
        let loopCount = 0;
        const maxLoops = 20; 
        const sidebar = document.querySelector('.minimal__nav__scrollbar') || window;

        while (expandedSomething && loopCount < maxLoops) {
            expandedSomething = false;
            loopCount++;
            
            const buttons = Array.from(document.querySelectorAll('.minimal__nav__item__root[role="button"]:not(a)'))
                .filter(btn => {
                    const isExpanded = btn.getAttribute('aria-expanded') === 'true' || 
                                     btn.classList.contains('--open');
                    return !isExpanded;
                });

            if (buttons.length > 0) {
                for (const btn of buttons) {
                    btn.scrollIntoView({ behavior: 'instant', block: 'nearest' });
                    btn.click();
                    expandedSomething = true;
                    await new Promise(r => setTimeout(r, 200)); // Tăng lên chút cho chắc
                }
                await new Promise(r => setTimeout(r, 600)); 
            }
        }
        
        if (sidebar.scrollTo) sidebar.scrollTo({ top: 0, behavior: 'smooth' });
        console.log(`✅ [Sidebar]: Đã bung hết menu sau ${loopCount} tầng.`);
    },

    extractData: (prefix) => {
        const results = {};
        const links = document.querySelectorAll('a.minimal__nav__item__root');
        
        // Danh sách các từ khóa cần bỏ qua để không quét thừa
        const skipKeywords = ['dashboard', 'logout', 'profile', 'change-password', 'thông tin cá nhân'];

        links.forEach(a => {
            const href = a.href;
            if (!href || href.startsWith('javascript:') || href === "#") return;

            // Kiểm tra link rác
            const isGarbage = skipKeywords.some(key => href.toLowerCase().includes(key));
            if (isGarbage) return;

            const titleEl = a.querySelector('.minimal__nav__item__title');
            const itemText = (titleEl ? titleEl.innerText : a.innerText).trim();
            
            const collapseParent = a.closest('.MuiCollapse-root');
            const groupName = collapseParent?.previousElementSibling?.innerText?.trim() || "";

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

            // Tạo đường dẫn chuẩn: Tiền tố | Subheader | Group | Item
            // Ví dụ: Bán hàng | Danh mục | Đối tác | Khách hàng
            const pathParts = [prefix, subheaderName];
            if (groupName && groupName !== itemText) pathParts.push(groupName);
            pathParts.push(itemText);

            const fullPath = pathParts.join(' | ');
            
            results[fullPath] = {
                url: href,
                module_parent: prefix,
                parent: pathParts.slice(0, -1).join(' | '),
                text: itemText, // Đây chính là tên "Thực thể" (Entity)
                scanned_at: new Date().toISOString()
            };
        });
        return results;
    },

    run: async function(prefix) {
        await this.expandAll();
        return this.extractData(prefix);
    }
};