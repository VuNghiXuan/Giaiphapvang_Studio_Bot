/**
 * BUTTON MINER V4.0 - LOGIC MAPPING
 * Chuyên dụng cho hệ thống GPV: Quét nút, định vị thị giác và phân tích mục đích.
 */
(() => {
    const buttons = Array.from(document.querySelectorAll('button, a, [role="button"], .MuiButtonBase-root, .btn'));

    const generateSelector = (el) => {
        if (el.id) return `#${CSS.escape(el.id)}`;
        if (el.getAttribute('name')) return `[name="${CSS.escape(el.getAttribute('name'))}"]`;
        const text = el.innerText.trim();
        if (text && text.length < 25) return `${el.tagName.toLowerCase()}:has-text("${text}")`;
        return "";
    };

    return buttons.map(btn => {
        const rect = btn.getBoundingClientRect();
        const style = window.getComputedStyle(btn);
        
        // 1. Phân tích màu sắc (Chuyển từ RGB sang tên màu thân thiện với AI)
        const bgColor = style.backgroundColor;
        const isPrimary = bgColor.includes('rgb(0,') || bgColor.includes('25, 118, 210'); // Ví dụ Blue của MUI
        const colorName = bgColor.includes('255, 0, 0') ? 'Đỏ' : (bgColor.includes('0, 128, 0') ? 'Xanh lá' : 'Mặc định');

        // 2. Nhận diện ngữ cảnh (Nằm trong vùng nào?)
        const isInsideTable = !!btn.closest('table, [role="grid"]');
        const isInsideForm = !!btn.closest('form, .MuiDialog-root');
        
        const text = btn.innerText.replace(/\n/g, ' ').trim();
        const title = btn.getAttribute('title') || btn.getAttribute('aria-label') || "";

        const getPurpose = (txt, t) => {
            const val = (txt + " " + t).toLowerCase();
            if (val.includes('thêm') || val.includes('tạo')) return 'create';
            if (val.includes('lưu') || val.includes('xác nhận')) return 'save';
            if (val.includes('hủy') || val.includes('đóng')) return 'cancel';
            if (val.includes('sửa')) return 'edit';
            if (val.includes('xóa')) return 'delete';
            if (val.includes('in') || val.includes('xuất')) return 'print_export';
            return 'other';
        };

        const purpose = getPurpose(text, title);

        return {
            label: text || title || "Nút thao tác",
            purpose: purpose,
            status: {
                is_disabled: btn.disabled || btn.classList.contains('Mui-disabled'),
                is_visible: rect.width > 0 && rect.height > 0 && style.display !== 'none'
            },
            visual: {
                color_description: colorName,
                position_context: isInsideTable ? "Trong bảng" : (isInsideForm ? "Trong Form" : "Trên thanh công cụ"),
                area: rect.top < 150 ? 'top' : (rect.bottom > window.innerHeight - 100 ? 'bottom' : 'center')
            },
            selector: generateSelector(btn),
            coords: { x: rect.left, y: rect.top, w: rect.width, h: rect.height }
        };
    }).filter(btn => 
    btn.status.is_visible && 
    btn.coords.w > 5 && btn.coords.h > 5 && // Loại bỏ các pixel rác
    (btn.label.length > 0 || btn.purpose !== 'other') // Giữ lại nút có tên hoặc có mục đích rõ ràng
    );
})();