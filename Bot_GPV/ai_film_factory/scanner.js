/**
 * GIAI PHÁP VÀNG - OMNI METADATA EXTRACTOR 2026 (FINAL COMBINED)
 * Tác giả: Gemini (Collaborator: Thanh Vũ)
 * Mục tiêu: Quét sạch lộ trình, menu phân cấp, tọa độ và cấu trúc form ngầm.
 */

window.extractGoldMetadata = async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    // --- MODULE 1: UTILS (Xử lý DOM & Thông minh hóa Label) ---
    const utils = {
        getCleanText: (el) => {
            if (!el) return "";
            return el.innerText.split('\n')[0].replace(/[\*\•\○\+]/g, '').trim();
        },
        
        getSelector: (el) => {
            if (!el) return "";
            if (el.name) return `[name="${el.name}"]`;
            const aria = el.getAttribute('aria-label');
            if (aria) return `[aria-label="${aria}"]`;
            const tid = el.getAttribute('data-testid');
            if (tid) return `[data-testid="${tid}"]`;
            if (el.id && !el.id.includes('mui-')) return `#${el.id}`;
            return "";
        },

        getRect: (el) => {
            const r = el.getBoundingClientRect();
            return { 
                x: Math.round(r.left), 
                y: Math.round(r.top), 
                w: Math.round(r.width), 
                h: Math.round(r.height),
                is_visible: r.width > 0 && r.height > 0
            };
        },

        getSmartLabel: (btn) => {
            let label = utils.getCleanText(btn) || btn.title || btn.getAttribute('aria-label') || "";
            if (label.length <= 1) {
                const html = btn.innerHTML.toLowerCase();
                const cls = (btn.className || "").toString().toLowerCase();
                const svg = btn.querySelector('svg');
                const tid = svg?.getAttribute('data-testid')?.toLowerCase() || "";

                if (html.includes('edit') || cls.includes('edit') || tid.includes('edit')) return "Sửa";
                if (html.includes('delete') || html.includes('trash') || tid.includes('delete')) return "Xóa";
                if (html.includes('save') || tid.includes('save')) return "Lưu";
                if (html.includes('add') || html.includes('plus') || tid.includes('add')) return "Thêm";
                if (html.includes('download') || html.includes('export') || tid.includes('download')) return "Xuất file";
                if (html.includes('print') || tid.includes('print')) return "In";
                if (html.includes('close') || html.includes('cancel') || tid.includes('close')) return "Đóng/Hủy";
            }
            return label || "Nút chức năng";
        }
    };

    // --- MODULE 2: NAVIGATION (Bản đồ hành trình) ---
    const getNavigationInfo = () => {
        const breadcrumbs = Array.from(document.querySelectorAll('.MuiBreadcrumbs-li'))
            .map(li => utils.getCleanText(li))
            .filter(txt => txt && txt !== "/");
        
        return {
            url: window.location.href,
            path: window.location.pathname,
            hierarchy: breadcrumbs, // Ví dụ: ["Hệ thống", "Hàng hóa"]
            current_step: breadcrumbs[breadcrumbs.length - 1] || "Trang chủ"
        };
    };

    const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
    const searchArea = activeOverlay || document.querySelector('main') || document.body;

    const metadata = {
        navigation: getNavigationInfo(),
        session: {
            timestamp: new Date().toISOString(),
            is_popup_open: !!activeOverlay,
            popup_type: activeOverlay ? (activeOverlay.classList.contains('MuiDialog-root') ? 'DIALOG' : 'DRAWER') : 'NONE'
        },
        layout: {
            sidebar: [],
            main_content: {},
            export_formats: []
        },
        error_config: { selectors: { field: ".Mui-error", global: ".MuiAlert-root" } }
    };

    // --- MODULE 3: SCANNER (Quét chi tiết từng Context) ---
    const scanContext = (container, contextName) => {
        const elements = { actions: [], row_operations: [], inputs: [], tables: [], scrollers: [] };

        // 1. Quét Nút bấm
        container.querySelectorAll('button, a, [role="button"], [role="tab"]').forEach(btn => {
            if (!activeOverlay && (btn.closest('nav') || btn.closest('[class*="sidebar"]'))) return;
            const rect = utils.getRect(btn);
            if (!rect.is_visible) return;

            const btnData = {
                label: utils.getSmartLabel(btn),
                selector: utils.getSelector(btn) || `button:has-text("${utils.getSmartLabel(btn)}")`,
                rect: rect,
                is_primary: btn.classList.contains('MuiButton-containedPrimary') || btn.classList.contains('MuiButton-contained')
            };

            if (btn.closest('.MuiDataGrid-row')) elements.row_operations.push(btnData);
            else elements.actions.push(btnData);
        });

        // 2. Quét Inputs & Cảm biến lỗi
        container.querySelectorAll('.MuiFormControl-root, .MuiTextField-root').forEach(f => {
            const input = f.querySelector('input, textarea, [role="combobox"]');
            if (!input) return;
            elements.inputs.push({
                label: utils.getCleanText(f.querySelector('label')) || input.placeholder,
                selector: utils.getSelector(input),
                rect: utils.getRect(input),
                type: input.getAttribute('role') === 'combobox' ? 'combobox' : input.type,
                required: !!f.querySelector('.Mui-required'),
                error_state: !!f.querySelector('.Mui-error'),
                value: input.value || ""
            });
        });

        // 3. Quét Tables
        container.querySelectorAll('.MuiDataGrid-root, table').forEach(t => {
            elements.tables.push({
                columns: Array.from(t.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th')).map(utils.getCleanText).filter(v => v),
                rect: utils.getRect(t)
            });
        });

        // 4. Quét Scrollers
        const scrollEl = container.querySelector('.MuiDataGrid-virtualScroller, .MuiTableContainer-root') || container;
        if (scrollEl.scrollHeight > scrollEl.clientHeight || scrollEl.scrollWidth > scrollEl.clientWidth) {
            elements.scrollers.push({
                area: contextName,
                has_v: scrollEl.scrollHeight > scrollEl.clientHeight,
                has_h: scrollEl.scrollWidth > scrollEl.clientWidth,
                selector: utils.getSelector(scrollEl) || ".scroll-area"
            });
        }

        return elements;
    };

    // --- MODULE 4: EXECUTION ---
    
    // A. Quét Sidebar
    const sidebarItems = document.querySelectorAll('.MuiListItem-root, .MuiListItemButton-root');
    let currentParent = null;
    sidebarItems.forEach(el => {
        const txt = utils.getCleanText(el);
        if (!txt) return;
        const isChild = !!el.closest('.MuiCollapse-root');
        const item = { label: txt, selector: utils.getSelector(el), rect: utils.getRect(el), active: el.classList.contains('Mui-selected') };
        if (!isChild) {
            item.children = [];
            currentParent = item;
            metadata.layout.sidebar.push(item);
        } else if (currentParent) {
            currentParent.children.push(item);
        }
    });

    // B. Quét vùng chính
    metadata.layout.main_content = scanContext(searchArea, activeOverlay ? "DIALOG" : "MAIN");

    // C. Quét Export Formats (Nếu menu đang mở)
    document.querySelectorAll('.MuiMenuItem-root, [role="menuitem"]').forEach(item => {
        const txt = item.innerText.trim();
        if (['Excel', 'CSV', 'PDF', 'In ấn'].some(k => txt.includes(k))) {
            metadata.layout.export_formats.push({ label: txt, selector: `text="${txt}"`, rect: utils.getRect(item) });
        }
    });

    // D. NỘI SOI FORM (Logic đặc biệt của Thanh Vũ)
    const addBtn = metadata.layout.main_content.actions.find(a => /thêm|tạo|add/i.test(a.label));
    if (!activeOverlay && addBtn) {
        const btnEl = document.querySelector(addBtn.selector);
        if (btnEl) {
            btnEl.click();
            await sleep(800); // Chờ render
            const dialog = document.querySelector('.MuiDialog-root, [role="dialog"]');
            if (dialog) {
                metadata.layout.active_form = scanContext(dialog, "DIALOG");
                // Đóng lại để giữ trạng thái sạch cho trang
                const closeBtn = Array.from(dialog.querySelectorAll('button')).find(b => /hủy|đóng|close/i.test(utils.getSmartLabel(b)));
                if (closeBtn) closeBtn.click();
                await sleep(300);
            }
        }
    }

    return metadata;
};