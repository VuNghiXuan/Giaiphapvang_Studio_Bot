/**
 * Chế độ DIỄN VIÊN: Chỉ quét bề mặt, phục vụ điều khiển hành động
 */
window.scanPage = async () => {
    console.log("🎭 Actor Engine: Đang quan sát hiện trường...");

    // Actor chỉ quét lớp trên cùng (Overlay) nếu có, không tự ý click nút khác
    const activeOverlay = document.querySelector('.MuiDialog-root, [role="dialog"]');
    const targetArea = activeOverlay || document.querySelector('main') || document.body;
    
    const scanResult = window.internalScan(targetArea);

    const metadata = {
        session: { url: window.location.href, mode: "ACTOR" },
        current_view: activeOverlay ? "DIALOG_OPEN" : "MAIN_PAGE",
        main_content: scanResult,
        // Actor trả về thêm thông tin về các phần tử có thể tương tác ngay lập tức
        interactable_summary: scanResult.actions.map(a => a.label)
    };

    const cleanup = (obj) => {
        if (!obj || typeof obj !== 'object') return;
        delete obj._el;
        Object.values(obj).forEach(cleanup);
    };
    cleanup(metadata);
    return metadata;
};