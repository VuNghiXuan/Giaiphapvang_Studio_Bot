/**
 * Tác giả: Gemini & Thanh Vũ
 * Mục tiêu: Vét cạn Metadata phục vụ AI sản xuất Video tự động.
 * Đặc điểm: Phân tách chế độ Trinh sát (Deep Scan) & Diễn viên (Current View).
 */

window.scanPage = async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const isActorMode = window.isBotActing === true; // Set từ Python

    const utils = {
        getCleanText: (el) => {
            if (!el) return "";
            // Giai đoạn 1: Lấy text sạch, bỏ dấu bullet, xuống dòng
            return el.innerText.split('\n')[0].replace(/[\*\•\○\+]/g, '').trim();
        },
        getVisuals: (el) => {
            const r = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                x: Math.round(r.left), y: Math.round(r.top),
                w: Math.round(r.width), h: Math.round(r.height),
                color: style.color,
                bg_color: style.backgroundColor, // Phục vụ: "Nhấn nút xanh lá..."
                is_visible: r.width > 0 && r.height > 0,
                opacity: style.opacity
            };
        },
        getSelector: (el) => {
            if (!el) return "";
            if (el.name) return `[name="${el.name}"]`;
            if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
            if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
            if (el.id && !el.id.includes('mui-')) return `#${el.id}`;
            const text = utils.getCleanText(el);
            return (text && text.length < 20) ? el.tagName.toLowerCase() : el.tagName.toLowerCase();
        },
        getSmartLabel: (btn) => {
            let label = utils.getCleanText(btn) || btn.title || btn.getAttribute('aria-label') || "";
            if (label.length <= 1) {
                const inner = btn.innerHTML.toLowerCase();
                const tid = (btn.querySelector('svg')?.getAttribute('data-testid') || "").toLowerCase();
                if (inner.includes('edit') || tid.includes('edit')) return "Sửa (Bút chì)";
                if (inner.includes('delete') || inner.includes('trash') || tid.includes('delete')) return "Xóa (Thùng rác)";
                if (inner.includes('save') || tid.includes('save')) return "Lưu";
                if (inner.includes('add') || inner.includes('plus')) return "Thêm mới";
                if (inner.includes('print')) return "In ấn";
            }
            return label || "Nút chức năng";
        }
    };

    // --- GIAI ĐOẠN 1 & 2: VÉT LÕI (GRID & GLOBAL) ---
    const internalScan = (container) => {
        const data = { actions: [], inputs: [], tables: [], scrollers: [] };

        // Quét nút & Cột chức năng
        container.querySelectorAll('button, a, [role="button"]').forEach(btn => {
            const vis = utils.getVisuals(btn);
            if (!vis.is_visible) return;
            const item = {
                label: utils.getSmartLabel(btn),
                selector: utils.getSelector(btn),
                rect: vis,
                _el: btn // Giữ lại để click nội bộ
            };
            if (btn.closest('tr, .MuiDataGrid-row')) data.tables.push({ type: 'row_op', ...item });
            else data.actions.push(item);
        });

        // Quét Bảng & Thanh cuộn kép (Giai đoạn 2)
        container.querySelectorAll('table, .MuiDataGrid-root').forEach(t => {
            const scrollEl = t.querySelector('.MuiDataGrid-virtualScroller') || t;
            const cols = Array.from(t.querySelectorAll('th, .MuiDataGrid-columnHeaderTitle')).map(utils.getCleanText).filter(v => v);
            data.tables.push({
                columns: cols,
                count: cols.length,
                needs_h_scroll: scrollEl.scrollWidth > scrollEl.clientWidth, // Bảng rộng quá màn hình
                rect: utils.getVisuals(t)
            });
        });

        // Quét Input & Combobox (Giai đoạn 3)
        container.querySelectorAll('.MuiFormControl-root, .form-group').forEach(f => {
            const input = f.querySelector('input, textarea, [role="combobox"], select');
            if (!input) return;
            data.inputs.push({
                label: utils.getCleanText(f.querySelector('label') || f),
                selector: utils.getSelector(input),
                type: input.getAttribute('role') === 'combobox' ? 'combobox_linked' : input.type,
                required: !!f.querySelector('.Mui-required'),
                rect: utils.getVisuals(input)
            });
        });

        return data;
    };

    // --- GIAI ĐOẠN 3: NỘI SOI ĐỆ QUY (TRINH SÁT MODE) ---
    const deepScan = async (btnObj) => {
        if (isActorMode || !btnObj?._el) return null;
        try {
            btnObj._el.click();
            await sleep(1200);
            const dialog = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"], .modal-content');
            if (dialog) {
                const formMetadata = internalScan(dialog);
                // Reset UI: Tìm nút Đóng/Hủy
                const closeBtn = Array.from(dialog.querySelectorAll('button')).find(b => /đóng|hủy|close|x/i.test(utils.getSmartLabel(b).toLowerCase()));
                if (closeBtn) { closeBtn.click(); await sleep(600); }
                return formMetadata;
            }
        } catch (e) { console.error("DeepScan Failed", e); }
        return null;
    };

    // --- TỔNG HỢP KẾT QUẢ ---
    const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
    const mainArea = activeOverlay || document.querySelector('main') || document.body;
    const scanResult = internalScan(mainArea);

    const metadata = {
        session: { url: window.location.href, title: document.title, mode: isActorMode ? "ACTOR" : "SCOUT" },
        navigation: {
            breadcrumbs: Array.from(document.querySelectorAll('.MuiBreadcrumbs-li')).map(utils.getCleanText).filter(t => t && t !== "/"),
            sidebar: (() => {
                const side = document.querySelector('nav, [class*="sidebar"]');
                return {
                    has_scroll: side ? side.scrollHeight > side.clientHeight : false, // "Menu này dài..."
                    items: Array.from(document.querySelectorAll('.MuiListItem-root')).map(el => ({ label: utils.getCleanText(el), selector: utils.getSelector(el) }))
                };
            })()
        },
        main_content: scanResult,
        active_form: activeOverlay ? scanResult : null
    };

    // Logic Trinh sát tự động (Chỉ chạy khi Scout Mode)
    if (!isActorMode && !activeOverlay) {
        const target = scanResult.actions.find(a => /thêm|tạo/i.test(a.label.toLowerCase())) || scanResult.tables.find(t => t.type === 'row_op');
        if (target) {
            console.log("🕵️ Trinh sát đang nội soi...");
            metadata.active_form = await deepScan(target);
        }
    }

    // --- CLEANUP ĐỆ QUY (QUAN TRỌNG NHẤT) ---
    const finalCleanup = (obj) => {
        if (!obj || typeof obj !== 'object') return;
        if (Array.isArray(obj)) obj.forEach(finalCleanup);
        else {
            delete obj._el; // Xóa sạch dấu vết Element trước khi về Python
            Object.values(obj).forEach(finalCleanup);
        }
    };
    finalCleanup(metadata);

    return metadata;
};