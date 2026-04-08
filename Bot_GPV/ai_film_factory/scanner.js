/**
 * Tác giả: Gemini & Thanh Vũ
 * Mục tiêu: Vét cạn Metadata phục vụ AI sản xuất Video tự động.
 * Đặc điểm: Phân tách chế độ Trinh sát (Deep Scan) & Diễn viên (Current View).
 */

window.scanPage = async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const isActorMode = window.isBotActing === true; // Set từ Python

    // --- [THÊM MỚI]: CHỐT CHẶN KIÊN NHẪN (Fix lỗi Timeout) ---
    const waitForDashboard = async (selector, timeout = 10000) => {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            if (document.querySelector(selector)) return true;
            await sleep(500);
        }
        return false;
    };

    // Tự động đợi Grid hoặc Menu xuất hiện trước khi bắt đầu quét
    const isReady = await waitForDashboard('.MuiGrid-item, .MuiDataGrid-root, .MuiListItem-root');
    if (!isReady) {
        console.warn("⚠️ Dashboard load quá chậm, Bot sẽ quét những gì đang có.");
    }
    

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
        },
        // Vị trí thêm: Cuối khối utils
        getRelativePos: (el) => {
            const r = el.getBoundingClientRect();
            const vh = window.innerHeight;
            const vw = window.innerWidth;
            const yPos = r.top < vh / 3 ? "phía trên" : (r.top > (vh * 2) / 3 ? "phía dưới" : "giữa");
            const xPos = r.left < vw / 3 ? "bên trái" : (r.left > (vw * 2) / 3 ? "bên phải" : "chính giữa");
            return `${yPos} ${xPos} màn hình`;
        }
    };

    // --- GIAI ĐOẠN 1 & 2: VÉT LÕI (GRID & GLOBAL) ---

    // --- CÔNG CỤ PHÂN LOẠI THÔNG MINH ---
    const isInsideForm = (el) => {
        return !!el.closest('.MuiDialog-root, .MuiDrawer-root, [role="dialog"], form, .modal-content');
    };
    const internalScan = (container) => {
        const data = { actions: [], inputs: [], tables: [], scrollers: [] };

        // Quét nút & Cột chức năng
        // Quét nút & Cột chức năng
        container.querySelectorAll('button, a, [role="button"]').forEach(btn => {
            const vis = utils.getVisuals(btn);
            if (!vis.is_visible) return;
            
            const item = {
                label: utils.getSmartLabel(btn),
                selector: utils.getSelector(btn),
                rect: vis,
                position_desc: utils.getRelativePos(btn),
                bg_color_hex: vis.bg_color,
                _el: btn 
            };

            // LOGIC PHÂN LOẠI MỚI:
            if (btn.closest('tr, .MuiDataGrid-row')) {
                data.tables.push({ type: 'row_op', ...item });
            } else if (isInsideForm(btn)) {
                // Nếu nút nằm trong Form/Dialog -> Đánh dấu là Form Action
                item.context = "form_action";
                data.actions.push(item); 
            } else {
                // Nút nằm ngoài (Toolbar, Header...)
                item.context = "global_action";
                data.actions.push(item);
            }
        });

        // Quét Bảng & Thanh cuộn kép (Giai đoạn 2)
        container.querySelectorAll('table, .MuiDataGrid-root').forEach(t => {
            const scrollEl = t.querySelector('.MuiDataGrid-virtualScroller') || t;
            const cols = Array.from(t.querySelectorAll('th, .MuiDataGrid-columnHeaderTitle')).map(utils.getCleanText).filter(v => v);
            
            // Lấy thêm 2 dòng dữ liệu đầu tiên để AI biết bảng đang có gì
            const sampleRows = Array.from(t.querySelectorAll('tr, .MuiDataGrid-row'))
                .slice(1, 3) // Bỏ header, lấy 2 dòng
                .map(row => Array.from(row.querySelectorAll('td, [role="cell"]'))
                    .slice(0, 4) // Lấy 4 cột đầu cho đỡ dài metadata
                    .map(utils.getCleanText).join(" | ")
                );

            data.tables.push({
                columns: cols,
                sample_data: sampleRows, // Thêm dòng này
                count: cols.length,
                needs_h_scroll: scrollEl.scrollWidth > scrollEl.clientWidth,
                rect: utils.getVisuals(t),
                position_desc: utils.getRelativePos(t) // Thêm dòng này
            });
        });

        // Quét Input & Combobox (Giai đoạn 3)
        container.querySelectorAll('.MuiFormControl-root, .form-group, input, textarea, select').forEach(f => {
            // Nếu phần tử là input/textarea/select nhưng nó đã nằm trong một cái Group đã được quét rồi thì bỏ qua
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(f.tagName) && f.closest('.MuiFormControl-root, .form-group')) return;
            
    const input = f.tagName === 'INPUT' || f.tagName === 'TEXTAREA' || f.tagName === 'SELECT' ? f : f.querySelector('input, textarea, [role="combobox"], select');if (!input) return;
            
            const inputItem = {
                label: utils.getCleanText(f.querySelector('label') || f),
                selector: utils.getSelector(input),
                type: input.getAttribute('role') === 'combobox' ? 'combobox_linked' : input.type,
                required: !!f.querySelector('.Mui-required'),
                placeholder: input.placeholder || "",
                current_value: input.value || "",
                rect: utils.getVisuals(input),
                // PHÂN LOẠI Ở ĐÂY:
                is_in_form: isInsideForm(input)
            };
            
            data.inputs.push(inputItem);
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
                // Thêm: Kiểm tra xem có thông báo lỗi hoặc chú ý nào đang hiện không
                const alertText = dialog.querySelector('.MuiAlert-message, .Mui-error, [class*="error"]') ? 
                                utils.getCleanText(dialog.querySelector('.MuiAlert-message, .Mui-error, [class*="error"]')) : "";
                formMetadata.active_alerts = alertText;

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
        // 1. Lấy danh sách menu sidebar
        const sidebarItems = Array.from(document.querySelectorAll('.MuiListItem-root'));
        
        // 2. Tìm mục "Thông tin công ty" (hoặc mục đầu tiên nếu muốn đi từ trên xuống)
        // Vũ có thể đổi 'thông tin công ty' thành mục tiêu cụ thể
        const firstMenu = sidebarItems.find(el => 
            /thông tin công ty|hệ thống/i.test(utils.getCleanText(el).toLowerCase())
        );

        // 3. KIỂM TRA: Nếu đang ở sai chỗ, thì Click Sidebar trước
        const currentTitle = document.title.toLowerCase();
        if (firstMenu && !currentTitle.includes("thông tin công ty")) {
            console.log("🚀 Chuyển hướng về menu ưu tiên: ", utils.getCleanText(firstMenu));
            firstMenu.click();
            await sleep(2000); // Đợi trang load
            // Sau khi click menu, ta return metadata hiện tại để Python biết là đang chuyển trang
            return metadata; 
        }

        // 4. Nếu đã ở đúng trang hoặc không cần chuyển menu, thì mới 'nội soi' Form
        const target = scanResult.actions.find(a => /thêm|tạo|nhập|xuất|mới/i.test(a.label.toLowerCase())) 
               || scanResult.tables.find(t => t.type === 'row_op');
        
        if (target) {
            console.log("🕵️ Đã ở đúng trang, đang nội soi Form...");
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