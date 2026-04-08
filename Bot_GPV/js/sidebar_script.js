// sidebar_script.js
window.sidebarScraper = {
    // Hàm mở rộng menu
    expandAll: async () => {
        const expandNodes = async () => {
            const buttons = document.querySelectorAll('.minimal__nav__item__root[role="button"]:not(a)');
            for (const btn of buttons) {
                const arrow = btn.querySelector('.minimal__nav__item__arrow');
                const isOpened = btn.classList.contains('--open') || (arrow && arrow.style.transform.includes('rotate(90deg)'));
                if (arrow && !isOpened) {
                    btn.click();
                    await new Promise(r => setTimeout(r, 400));
                }
            }
        };
        await expandNodes();
        await expandNodes();
        await new Promise(r => setTimeout(r, 600));
    },

    // Hàm lấy dữ liệu
    extractData: (prefix) => {
        const results = {};
        const links = document.querySelectorAll('a.minimal__nav__item__root');
        
        links.forEach(a => {
            if (!a.href || a.href.includes('#')) return;

            const titleEl = a.querySelector('.minimal__nav__item__title');
            const itemText = titleEl ? titleEl.innerText.trim() : a.innerText.trim();
            
            const collapseParent = a.closest('.MuiCollapse-root[data-group]');
            const groupName = collapseParent ? collapseParent.getAttribute('data-group') : "";

            let subheaderName = "Chung";
            let currentEl = a.closest('.minimal__nav__li');
            while (currentEl) {
                const prevLi = currentEl.previousElementSibling;
                if (!prevLi) {
                    const topSub = currentEl.parentElement?.closest('.minimal__nav__li')?.querySelector('.minimal__nav__subheader');
                    if (topSub) subheaderName = topSub.innerText.trim();
                    break;
                }
                const sub = prevLi.querySelector('.minimal__nav__subheader');
                if (sub) {
                    subheaderName = sub.innerText.trim();
                    break;
                }
                currentEl = prevLi;
            }

            let parentPath = subheaderName;
            if (groupName && groupName !== itemText) {
                parentPath += " | " + groupName;
            }

            const fullPath = prefix + "|" + parentPath + "|" + itemText;
            
            results[fullPath] = {
                url: a.href,
                module_parent: prefix,
                parent: parentPath,
                text: itemText,
                scanned_at: new Date().toLocaleString('sv-SE')
            };
        });
        return results;
    }
};