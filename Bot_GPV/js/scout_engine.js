/**
 * GIAIPHAPVANG STUDIO - SCOUT SCANNER
 * File này thực hiện Deep Scan (Mở form) sau khi core đã nạp.
 */
window.scanPage = async () => {
    if (!window.utils_loaded) return { error: "Core Utils chưa được nạp!" };

    console.log("🕵️ Đang trinh sát sâu...");
    await window.utils.expandAllMenus();
    
    // Lấy nội dung trang chủ trước
    const scanResult = window.utils.internalScan();
    const detailedForms = [];

    // Tìm các nút có khả năng mở Form
    const actionButtons = scanResult.actions.filter(a => 
        /thêm|tạo|mới|sửa|edit|add/i.test(a.label.toLowerCase())
    );

    // Deep Scan (Giới hạn 2 form để tránh kẹt)
    for (let btnObj of actionButtons.slice(0, 2)) { 
        if (btnObj._el) {
            try {
                btnObj._el.click(); 
                await window.utils.sleep(1200);
                
                const dialog = document.querySelector('.MuiDialog-root, [role="dialog"], .MuiDrawer-paper');
                if (dialog) {
                    detailedForms.push({
                        triggered_by: btnObj.label,
                        metadata: window.utils.internalScan(dialog)
                    });
                    
                    // Tìm nút Đóng linh hoạt
                    const close = dialog.querySelector('button[aria-label*="close"], .MuiIconButton-root') || 
                                  Array.from(dialog.querySelectorAll('button')).find(b => /đóng|hủy|close/i.test(b.innerText.toLowerCase()));
                    if (close) close.click();
                    else document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
                    
                    await window.utils.sleep(600);
                }
            } catch (e) { console.error("Lỗi Deep Scan:", e); }
        }
    }

    // Trả về JSON sạch (Xóa các tham chiếu DOM _el)
    return JSON.parse(JSON.stringify({
        url: window.location.href,
        main_content: scanResult,
        discovered_forms: detailedForms
    }, (key, value) => (key === '_el') ? undefined : value));
};