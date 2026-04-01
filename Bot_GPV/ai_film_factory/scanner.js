/**
 * GIAI PHÁP VÀNG - SCANNER ENGINE PRO 2026
 * Chế độ: Digital Twin - Diễn xuất kịch bản trình tự
 */

window.scanPage = () => {
    const getCleanText = (el) => {
        if (!el) return "";
        return el.innerText.split('\n')[0].replace(/[\*\•\○\+]/g, '').trim();
    };

    const getSelector = (el) => {
        if (el.name) return `[name="${el.name}"]`;
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
        if (el.id && !el.id.includes('mui-')) return `#${el.id}`;
        return ""; 
    };

    const getRect = (el) => {
        const rect = el.getBoundingClientRect();
        return {
            x: rect.left, y: rect.top, width: rect.width, height: rect.height,
            is_visible: rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight
        };
    };

    const structure = {
        // 1. ĐỊNH VỊ (Bot đang ở đâu?)
        location: {
            url: window.location.href,
            title: document.title,
            breadcrumbs: [],
            active_module: "", // Module lớn đang chọn (VD: Hệ thống)
            active_tab: ""     // Tab con đang chọn (VD: Chi nhánh)
        },
        // 2. ĐIỀU HƯỚNG (Đường đi nước bước)
        navigation: {
            sidebar_menu: [], // Cấu trúc Menu Cha-Con {label, parent, is_sub_item, selector}
            tabs: []          // Các thẻ chuyển đổi trong trang {label, is_active, selector}
        },
        // 3. TƯƠNG TÁC (Có gì để bấm/nhập?)
        content: {
            table_columns: [],
            primary_actions: [], // Các nút "Tạo mới", "Thêm", "Lưu" (Nút to)
            row_operations: [],  // Nút Sửa/Xóa trên từng dòng
            form_fields: [],     // Các ô nhập liệu {label, value, is_autocomplete, is_select...}
            pagination: null     // Thông tin phân trang và cuộn ngang của bảng
        },
        // 4. TRẠNG THÁI HỆ THỐNG & HIỂN THỊ
        state: {
            is_loading: !!document.querySelector('.MuiCircularProgress-root, .MuiLinearProgress-root'),
            is_dialog_open: !!document.querySelector('.MuiDialog-root, [role="dialog"]'),
            
            // Chi tiết trạng thái cuộn để Bot biết đường "Lăn chuột"
            scroll_status: {
                sidebar_can_scroll: false,    // Sidebar có bị dài quá không
                table_horizontal_scroll: false, // Bảng có cần kéo ngang để xem hết cột không
                table_vertical_scroll: false,   // Bảng có nhiều dòng cần cuộn không
                body_vertical_scroll: document.body.scrollHeight > window.innerHeight
            }
        }
    };

    // --- BƯỚC 1: XÁC ĐỊNH VỊ TRÍ & BREADCRUMBS ---
    document.querySelectorAll('.MuiBreadcrumbs-li').forEach(b => {
        const txt = getCleanText(b);
        if(txt && txt !== "/") structure.location.breadcrumbs.push(txt);
    });

    // --- BƯỚC 2: QUÉT SIDEBAR (TRÌNH TỰ CHA-CON CHUẨN) ---
    document.querySelectorAll('.MuiListItemButton-root').forEach(item => {
        const label = getCleanText(item);
        if (label) {
            const is_active = item.classList.contains('Mui-selected') || item.className.includes('active');
            if (is_active) structure.location.active_module = label;
            
            // Tìm menu cha gần nhất
            const collapseParent = item.closest('.MuiCollapse-root');
            let parentLabel = "";
            if (collapseParent) {
                // Tìm cái nút nằm ngay trước thẻ Collapse này
                const parentEl = collapseParent.previousElementSibling?.querySelector('.MuiListItemText-root') 
                               || collapseParent.previousElementSibling;
                parentLabel = getCleanText(parentEl);
            }

            structure.navigation.sidebar_menu.push({
                label: label,
                parent: parentLabel, // Đã biết con của ai!
                is_active: is_active,
                is_sub_item: !!collapseParent,
                selector: getSelector(item) || `.MuiListItemButton-root:has-text("${label}")`
            });
        }
    });

    // --- BƯỚC 3: QUÉT TABS (VD: THẺ CHI NHÁNH TRONG THÔNG TIN CÔNG TY) ---
    const tabArea = document.querySelector('.MuiTabs-root');
    if (tabArea) {
        tabArea.querySelectorAll('button[role="tab"]').forEach(tab => {
            const label = getCleanText(tab);
            const is_active = tab.classList.contains('Mui-selected') || tab.getAttribute('aria-selected') === 'true';
            if (is_active) structure.location.active_tab = label;
            structure.navigation.tabs.push({
                label, is_active,
                selector: `button[role="tab"]:has-text("${label}")`
            });
        });
    }

    // --- BƯỚC 4: QUÉT NỘI DUNG CHÍNH (FORM/TABLE) & SCROLLING ---
    const activeOverlay = document.querySelector('.MuiDialog-root, [role="dialog"]');
    const searchArea = activeOverlay || document.querySelector('main') || document.body;

    // 4.1. KIỂM TRA TRẠNG THÁI CUỘN (SCROLL)
    // Sidebar của Mui thường nằm trong .MuiDrawer-paper hoặc .MuiDrawer-root
    const sidebar = document.querySelector('.MuiDrawer-paper, .MuiDrawer-root');
    const tableEl = document.querySelector('.MuiDataGrid-root, table');
    const tableScrollEl = tableEl ? tableEl.querySelector('.MuiDataGrid-virtualScroller, .MuiTableContainer-root') : null;

    structure.state.scroll_status = {
        sidebar_can_scroll: sidebar ? sidebar.scrollHeight > sidebar.clientHeight : false,
        table_horizontal_scroll: tableScrollEl ? tableScrollEl.scrollWidth > tableScrollEl.clientWidth : false,
        table_vertical_scroll: tableScrollEl ? tableScrollEl.scrollHeight > tableScrollEl.clientHeight : false,
        body_vertical_scroll: document.body.scrollHeight > window.innerHeight
    };

    // 4.2. PHÂN LOẠI NÚT BẤM (CỨNG & MỀM)
    searchArea.querySelectorAll('button, a, [role="button"]').forEach(b => {
        // Bỏ qua sidebar nếu đang quét nội dung chính để tránh trùng lặp
        if (!activeOverlay && b.closest('.MuiDrawer-root')) return;

        let label = getCleanText(b) || b.getAttribute('aria-label') || b.title || "";
        const html = (b.innerHTML + b.className).toLowerCase();
        
        // Đoán Icon (Xử lý các nút chỉ có icon không có chữ)
        if (label.length <= 1) {
            if (html.match(/add|plus|create/)) label = "Tạo mới";
            else if (html.match(/edit|pencil/)) label = "Sửa";
            else if (html.match(/delete|trash/)) label = "Xóa";
            else if (html.match(/save|check/)) label = "Lưu";
            else if (html.match(/close|cancel|times/)) label = "Hủy/Đóng";
            else if (html.match(/search/)) label = "Tìm kiếm";
            else if (html.match(/download|export/)) label = "Xuất file";
            else if (html.match(/print/)) label = "In ấn";
        }

        if (label && label.length > 1) {
            const btnData = {
                label,
                selector: getSelector(b) || `button:has-text("${label}")`,
                rect: getRect(b),
                is_disabled: b.disabled || b.classList.contains('Mui-disabled')
            };
            
            // Phân loại: Nếu nằm trong dòng của bảng -> Row Operations, nếu ngoài -> Primary Actions
            if (b.closest('.MuiDataGrid-row, tr')) {
                structure.content.row_operations.push(btnData);
            } else {
                structure.content.primary_actions.push(btnData);
            }
        }
    });

    // 4.3. QUÉT FORM FIELDS (Dành cho nghiệp vụ nhập liệu)
    searchArea.querySelectorAll('.MuiFormControl-root, .MuiTextField-root, .MuiBox-root:has(input)').forEach(container => {
        let input = container.querySelector('input, textarea, select, [role="combobox"]');
        if (!input) return;

        let labelEl = container.querySelector('label');
        let label = labelEl ? getCleanText(labelEl) : (input.placeholder || input.getAttribute('aria-label') || "");
        
        if (label) {
            structure.content.form_fields.push({
                label,
                current_value: input.value || "",
                is_autocomplete: !!container.querySelector('.MuiAutocomplete-root'),
                is_select: !!container.querySelector('.MuiSelect-root') || input.tagName === 'SELECT',
                required: container.innerHTML.includes('Mui-required') || input.required,
                selector: getSelector(input) || `label:has-text("${label}") + div input, input[placeholder*="${label}"]`
            });
        }
    });

    // 4.4. QUÉT CẤU TRÚC BẢNG (Dành cho báo cáo/danh sách)
    if (tableEl) {
        // Lấy tiêu đề cột (Mui DataGrid)
        tableEl.querySelectorAll('.MuiDataGrid-columnHeaderTitle, th').forEach(h => {
            const colTitle = getCleanText(h);
            if (colTitle) structure.content.table_columns.push(colTitle);
        });

        // Thông tin phân trang
        const paginationEl = document.querySelector('.MuiTablePagination-root');
        structure.content.pagination = {
            has_horizontal_scroll: structure.state.scroll_status.table_horizontal_scroll,
            current_page: paginationEl ? (paginationEl.querySelector('.MuiTablePagination-caption')?.innerText || "1") : "1",
            rows_per_page: paginationEl ? (paginationEl.querySelector('.MuiTablePagination-select')?.innerText || "All") : "All"
        };
    }

    return structure;
};