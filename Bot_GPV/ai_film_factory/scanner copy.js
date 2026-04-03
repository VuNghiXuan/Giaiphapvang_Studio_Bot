/**
 * GIAI PHÁP VÀNG - OMNI METADATA EXTRACTOR (ULTIMATE VET)
 * Tác giả: Gemini & Thanh Vũ
 * Mục tiêu: Vét sạch Sidebar, Table, Form lồng nhau mà không gây lỗi Selector.
 */

window.scanPage = async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

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
            
            // KHÔNG dùng :has-text ở đây để tránh lỗi querySelector phía Browser
            const text = utils.getCleanText(el);
            if (text && text.length < 20) return `${el.tagName.toLowerCase()}`; 
            return el.tagName.toLowerCase();
        },
        getRect: (el) => {
            const r = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return { 
                x: Math.round(r.left), y: Math.round(r.top), 
                w: Math.round(r.width), h: Math.round(r.height),
                bg_color: style.backgroundColor,
                is_visible: r.width > 0 && r.height > 0
            };
        },
        getSmartLabel: (btn) => {
            let label = utils.getCleanText(btn) || btn.title || btn.getAttribute('aria-label') || "";
            if (label.length <= 1) {
                const html = btn.innerHTML.toLowerCase();
                const cls = (btn.className || "").toString().toLowerCase();
                const tid = (btn.querySelector('svg')?.getAttribute('data-testid') || "").toLowerCase();
                if (html.includes('edit') || cls.includes('edit') || tid.includes('edit')) return "Sửa";
                if (html.includes('delete') || html.includes('trash') || tid.includes('delete')) return "Xóa";
                if (html.includes('save') || tid.includes('save')) return "Lưu";
                if (html.includes('add') || html.includes('plus') || tid.includes('add')) return "Thêm mới";
                if (html.includes('download') || html.includes('export') || tid.includes('download')) return "Xuất file";
                if (html.includes('print') || tid.includes('print')) return "In";
                if (html.includes('close') || html.includes('cancel') || tid.includes('close')) return "Đóng/Hủy";
            }
            return label || "Nút chức năng";
        }
    };

    // --- MODULE: CẤU TRÚC VÉT LÕI ---
    const internalScan = (container, contextName) => {
        const elements = { 
            actions: [], 
            row_operations: [], 
            inputs: [], 
            tables: [], 
            scrollers: [],
            error_hints: [] 
        };

        // 1. Vét Nút & Toolbar
        container.querySelectorAll('button, a, [role="button"], [role="tab"]').forEach(btn => {
            const rect = utils.getRect(btn);
            if (!rect.is_visible) return;
            const label = utils.getSmartLabel(btn);
            // LƯU Ý: _el là tham chiếu trực tiếp, chỉ dùng nội bộ trong JS này
            const btnData = { 
                label, 
                selector: utils.getSelector(btn), 
                rect, 
                is_primary: btn.classList.contains('MuiButton-containedPrimary'),
                _el: btn 
            };
            
            if (btn.closest('.MuiDataGrid-row') || btn.closest('tr')) {
                elements.row_operations.push(btnData);
            } else {
                elements.actions.push(btnData);
            }
        });

        // 2. Vét Input & Combobox
        container.querySelectorAll('.MuiFormControl-root, .MuiTextField-root, .form-group').forEach(f => {
            const input = f.querySelector('input, textarea, [role="combobox"], select');
            if (!input) return;
            const labelEl = f.querySelector('label') || f.previousElementSibling;
            const errorEl = f.querySelector('.Mui-error, .invalid-feedback');
            
            elements.inputs.push({
                label: utils.getCleanText(labelEl) || input.placeholder || "Trường nhập liệu",
                selector: utils.getSelector(input),
                rect: utils.getRect(input),
                type: input.getAttribute('role') === 'combobox' ? 'combobox_linked' : input.type,
                required: !!f.querySelector('.Mui-required') || input.required,
                has_error: !!errorEl,
                error_msg: errorEl ? errorEl.innerText : ""
            });
        });

        // 3. Vét Bảng
        container.querySelectorAll('.MuiDataGrid-root, table').forEach(t => {
            const columns = Array.from(t.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th')).map(utils.getCleanText).filter(v => v);
            const scrollEl = t.querySelector('.MuiDataGrid-virtualScroller') || t;
            
            elements.tables.push({
                columns: columns,
                has_action_col: columns.some(c => /chức năng|thao tác|công cụ/i.test(c)),
                rect: utils.getRect(t),
                scroll_info: {
                    can_scroll_h: scrollEl.scrollWidth > scrollEl.clientWidth,
                    can_scroll_v: scrollEl.scrollHeight > scrollEl.clientHeight
                }
            });
        });

        return elements;
    };

    // --- MODULE: NỘI SOI ĐỆ QUY (Sửa lỗi Click bằng Element trực tiếp) ---
    const runDeepScan = async (targetBtnObj) => {
        if (!targetBtnObj || !targetBtnObj._el) return null;
        
        try {
            targetBtnObj._el.click();
            await sleep(1000); 

            const dialog = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
            if (dialog) {
                const details = internalScan(dialog, "DIALOG_LEVEL_1");
                
                // Vét Sub-table trong Form nếu có
                const subTable = dialog.querySelector('.MuiDataGrid-root, table');
                if (subTable) {
                    details.nested_table = internalScan(subTable, "NESTED_TABLE");
                }

                // Tìm nút đóng để reset trạng thái UI
                const closeBtn = Array.from(dialog.querySelectorAll('button')).find(b => /hủy|đóng|close|x/i.test(utils.getSmartLabel(b).toLowerCase()));
                if (closeBtn) { closeBtn.click(); await sleep(500); }
                
                return details;
            }
        } catch (e) {
            console.error("DeepScan Error:", e);
        }
        return null;
    };

    // --- THỰC THI QUÉT TỔNG THỂ ---
    const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
    const mainArea = activeOverlay || document.querySelector('main') || document.body;
    const mainScanResult = internalScan(mainArea, "MAIN_VIEW");

    const metadata = {
        navigation: {
            url: window.location.href,
            hierarchy: Array.from(document.querySelectorAll('.MuiBreadcrumbs-li')).map(li => utils.getCleanText(li)).filter(t => t && t !== "/"),
            current_page: document.title
        },
        layout: {
            sidebar: (() => {
                const sideEl = document.querySelector('nav, [class*="sidebar"]');
                return {
                    items: Array.from(document.querySelectorAll('.MuiListItem-root, .nav-item')).map(el => ({
                        label: utils.getCleanText(el),
                        selector: utils.getSelector(el),
                    })),
                    has_scroll: sideEl ? sideEl.scrollHeight > sideEl.clientHeight : false
                };
            })(),
            main_content: mainScanResult,
            active_form: null
        }
    };

    // --- NỘI SOI HÀNH ĐỘNG ---
    if (!activeOverlay) {
        // Ưu tiên nút "Thêm mới" hoặc "Tạo mới"
        const addBtn = mainScanResult.actions.find(a => /thêm|tạo/i.test(a.label.toLowerCase()));
        if (addBtn) {
            metadata.layout.active_form = await runDeepScan(addBtn);
        } else {
            // Nếu không có, nội soi nút "Sửa" đầu tiên để xem cấu trúc trường dữ liệu
            const editBtn = mainScanResult.row_operations[0];
            if (editBtn) metadata.layout.active_form = await runDeepScan(editBtn);
        }
    }

    // --- CLEANUP: Xóa tham chiếu Element trước khi trả về Python (Quan trọng!) ---
    const removeReferences = (obj) => {
        if (!obj) return;
        if (obj.actions) obj.actions.forEach(a => delete a._el);
        if (obj.row_operations) obj.row_operations.forEach(a => delete a._el);
        if (obj.active_form) removeReferences(obj.active_form);
    };
    removeReferences(metadata.layout.main_content);
    if (metadata.layout.active_form) removeReferences(metadata.layout.active_form);

    metadata.form_id = `metadata_${new Date().getTime()}`;
    return metadata;
};