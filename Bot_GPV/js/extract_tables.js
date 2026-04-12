/**
 * TABLE MINER V4.0 - HYPER-SCAN (Giai pháp Vàng Edition)
 * Đặc trị: MUI DataGrid, Ant Design, và các Form nghiệp vụ phức tạp.
 */
(async () => {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    const results = [];

    // 1. Tìm tất cả các bảng và vùng chứa Grid
    const grids = Array.from(document.querySelectorAll('table, [role="grid"], .MuiDataGrid-root, .ant-table-wrapper'));

    for (const grid of grids) {
        const rect = grid.getBoundingClientRect();
        
        // --- BƯỚC 1: VÉT NÚT "TRÊN - DƯỚI - XUNG QUANH" GRID ---
        // Quét các nút nằm trong Toolbar hoặc ngay sát Grid (thường là nút Thêm mới, Xuất file)
        const parentContainer = grid.closest('.MuiPaper-root, .card, .container') || document.body;
        const externalButtons = Array.from(parentContainer.querySelectorAll('button, [role="button"], a.btn'))
            .filter(btn => {
                const bRect = btn.getBoundingClientRect();
                // Lấy nút nằm phía trên Grid (cách tối đa 150px) hoặc nằm trong Toolbar
                return bRect.bottom < rect.top && bRect.bottom > rect.top - 150;
            })
            .map(btn => ({
                label: btn.innerText.trim() || btn.title,
                position: "above_right", // Xác định vị trí để AI dễ tả
                color: window.getComputedStyle(btn).backgroundColor,
                selector: `text="${btn.innerText.trim()}"`
            }));

        // --- BƯỚC 2: PHÂN TÍCH CẤU TRÚC CỘT & CỘT CHỨC NĂNG ---
        const headerCells = Array.from(grid.querySelectorAll('th, [role="columnheader"]'));
        let actionColIndex = -1;
        
        const headers = headerCells.map((th, idx) => {
            const text = th.innerText.trim();
            const isAction = /thao tác|chức năng|action|.../i.test(text) || th.getAttribute('data-field') === 'actions';
            if (isAction) actionColIndex = idx;
            return text;
        });

        // --- BƯỚC 3: NỘI SOI HÀNH ĐỘNG ẨN TRONG CỘT CHỨC NĂNG ---
        const firstRow = grid.querySelector('tbody tr, [role="row"]:not([role="columnheader"])');
        let nestedActions = [];

        if (firstRow && actionColIndex !== -1) {
            const cells = Array.from(firstRow.querySelectorAll('td, [role="gridcell"]'));
            const targetCell = cells[actionColIndex];

            if (targetCell) {
                // Tìm tất cả icon/nút có thể click được trong ô chức năng
                const triggers = Array.from(targetCell.querySelectorAll('button, [role="button"], svg, i'));
                
                for (const trigger of triggers) {
                    const btn = trigger.closest('button') || trigger;
                    if (btn.offsetWidth > 0) {
                        try {
                            btn.click(); // THỰC HIỆN CLICK ĐỂ BUNG MENU
                            await sleep(400); 

                            // Quét Portal (Menu hiện ra ở tầng ngoài cùng của DOM)
                            const menus = document.querySelectorAll('[role="menu"], .MuiMenu-paper, .ant-dropdown-menu');
                            const subItems = [];
                            
                            menus.forEach(menu => {
                                if (menu.offsetWidth > 0) {
                                    menu.querySelectorAll('li, [role="menuitem"]').forEach(item => {
                                        subItems.push({
                                            label: item.innerText.trim(),
                                            action_type: "hidden_menu_item"
                                        });
                                    });
                                }
                            });

                            nestedActions.push({
                                trigger_name: btn.innerText.trim() || btn.title || "Icon Menu",
                                sub_actions: subItems
                            });

                            // Đóng menu để trả lại trạng thái cũ
                            document.dispatchEvent(new KeyboardEvent('keydown', { 'key': 'Escape' }));
                            await sleep(100);
                        } catch (e) {}
                    }
                }
            }
        }

        // --- BƯỚC 4: KIỂM TRA ĐẶC TÍNH VẬT LÝ (CUỘN & TRÀN) ---
        results.push({
            table_id: grid.id || "grid_v4",
            location: {
                top: rect.top,
                is_full_width: rect.width >= window.innerWidth * 0.9,
                has_horizontal_scroll: grid.scrollWidth > grid.clientWidth // AI sẽ nhắc: "Kéo sang phải"
            },
            top_toolbar_buttons: externalButtons, // NÚT TẠO MỚI NẰM ĐÂY
            headers: headers,
            action_col_idx: actionColIndex,
            deep_actions: nestedActions, // CÁC NÚT ẨN NẰM ĐÂY
            sample_data: [] // Code cũ lấy data mẫu vẫn giữ nguyên...
        });
    }

    return results;
})();