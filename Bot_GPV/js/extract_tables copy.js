/**
 * TABLE MINER V3.0 - PRECISION MINING
 * Đặc trị: MUI DataGrid, Ant Design, Element Plus.
 * Cơ chế: Tự động nội soi (Deep Scan) Menu ẩn trong cột Chức năng.
 */
(async () => {
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    // Tìm tất cả các loại bảng phổ biến
    const tables = Array.from(document.querySelectorAll('table, [role="grid"], .MuiDataGrid-root, .ant-table, .el-table'));
    const results = [];

    for (const t of tables) {
        // --- BƯỚC 1: XÁC ĐỊNH VỊ TRÍ CỘT CHỨC NĂNG ---
        let actionColIndex = -1;
        const headerElements = Array.from(t.querySelectorAll('th, [role="columnheader"]'));
        
        const headers = headerElements.map((th, index) => {
            const text = th.innerText.trim();
            const isAction = 
                text.toLowerCase().includes('chức năng') || 
                text.toLowerCase().includes('thao tác') || 
                text.toLowerCase().includes('action') ||
                th.getAttribute('data-field') === 'actions' ||
                (text === '' && index === headerElements.length - 1); 
            
            if (isAction && actionColIndex === -1) actionColIndex = index;
            return { text, isAction };
        });

        // --- BƯỚC 2: NỘI SOI Ô DỮ LIỆU ĐẦU TIÊN CỦA CỘT ĐÓ ---
        const firstRow = t.querySelector('tbody tr, [role="row"]:not([role="columnheader"])');
        let rowActions = [];

        if (firstRow && actionColIndex !== -1) {
            const cells = Array.from(firstRow.querySelectorAll('td, [role="gridcell"]'));
            const targetCell = cells[actionColIndex];

            if (targetCell) {
                const buttons = Array.from(targetCell.querySelectorAll('button, [role="button"], .MuiIconButton-root, .ant-dropdown-trigger, a'));
                
                for (const btn of buttons) {
                    const text = btn.innerText.trim();
                    const title = btn.getAttribute('aria-label') || btn.getAttribute('title') || "";
                    
                    const isTrigger = 
                        btn.getAttribute('aria-haspopup') === 'menu' || 
                        btn.getAttribute('aria-haspopup') === 'true' ||
                        btn.innerHTML.includes('svg') ||
                        btn.classList.contains('ant-dropdown-trigger');

                    if (isTrigger && btn.offsetWidth > 0) {
                        try {
                            btn.click(); // Mở menu
                            await sleep(500); // Đợi UI render portal
                            
                            // Tìm menu container (MUI, AntD, Element)
                            const menuPortal = document.querySelector('[role="presentation"] .MuiPaper-root, .MuiMenu-paper, .ant-dropdown:not(.ant-dropdown-hidden), .MuiPopover-root, .el-dropdown-menu');
                            
                            if (menuPortal) {
                                const subActions = Array.from(menuPortal.querySelectorAll('li, [role="menuitem"], .ant-dropdown-menu-item')).map(item => ({
                                    label: item.innerText.trim(),
                                    playwright_selector: `text="${item.innerText.trim()}"`,
                                    is_hidden: true
                                }));

                                rowActions.push({
                                    label: text || title || "Menu Chức Năng",
                                    is_trigger_menu: true,
                                    selector: btn.id ? `#${CSS.escape(btn.id)}` : (title ? `button[aria-label="${title}"]` : "button.trigger-detected"),
                                    sub_actions: subActions
                                });

                                // Đóng menu
                                document.dispatchEvent(new KeyboardEvent('keydown', { 'key': 'Escape', 'code': 'Escape', 'bubbles': true }));
                                await sleep(200);
                            }
                        } catch (e) {
                            console.error("❌ Lỗi nội soi:", e);
                        }
                    } else if (text) {
                        rowActions.push({
                            label: text,
                            is_trigger_menu: false,
                            selector: btn.id ? `#${CSS.escape(btn.id)}` : `text="${text}"`,
                            sub_actions: []
                        });
                    }
                }
            }
        }

        // --- BƯỚC 3: LẤY THUỘC TÍNH VẬT LÝ (Mới) ---
        const rect = t.getBoundingClientRect();
        const hasHorizontalScroll = t.scrollWidth > t.clientWidth;
        const hasVerticalScroll = t.scrollHeight > t.clientHeight;

        results.push({
            table_id: t.id || "table_" + Math.floor(Math.random() * 1000),
            headers: headers.map(h => h.text),
            
            // AI sẽ dùng cái này để nói: "Bạn hãy kéo thanh cuộn sang phải để thấy cột chức năng"
            physical_props: {
                has_scroll_x: hasHorizontalScroll,
                has_scroll_y: hasVerticalScroll,
                location: rect.top < 250 ? "phía trên màn hình" : "trung tâm màn hình",
                width_overflow: hasHorizontalScroll ? (t.scrollWidth - t.clientWidth) : 0
            },

            action_info: {
                found: actionColIndex !== -1,
                index: actionColIndex,
                // Chuyển rowActions thành mô tả ngôn ngữ tự nhiên cho AI
                methods: rowActions.map(act => ({
                    name: act.label,
                    is_popup: act.is_trigger_menu,
                    sub_items: act.sub_actions.map(s => s.label)
                }))
            },

            // Dữ liệu mẫu để AI ví dụ: "Ví dụ như dòng có Mã chi nhánh là CN001..."
            sample_data: sampleData,
            url: window.location.href,
            module_name: document.title 
        });
    }

    return results; // Return này bây giờ nằm trong IIFE nên hoàn toàn hợp lệ!
})();