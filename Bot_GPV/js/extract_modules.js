/**
 * Script quét tất cả các thẻ <a> có chứa thông tin Module
 * Đã bọc IIFE để thực thi ngay khi nạp vào Playwright
 */
(() => {
    return Array.from(document.querySelectorAll('a[href]'))
        .map(a => {
            // Tìm các element chứa text tiềm năng bên trong thẻ <a>
            const labelEl = a.querySelector('h6, p, span, .MuiTypography-root');
            const rawText = (labelEl || a).innerText;
            
            return {
                // Lấy dòng đầu tiên và xóa khoảng trắng (tránh text kèm icon/badge)
                text: rawText.trim().split('\n')[0],
                href: a.href
            };
        })
        // Lọc bỏ các link rác hoặc không có text
        .filter(m => m.text.length > 1);
})(); // <-- Thêm cặp ngoặc này là xong