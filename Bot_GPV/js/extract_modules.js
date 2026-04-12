(() => {
    // 1. Chỉ tập trung vào các vùng chứa Menu chính (Sidebar, Header, Dashboard Grid)
    const menuSelectors = 'nav, aside, .sidebar, .menu-container, .MuiDrawer-root, .dashboard-grid, .nav-item';
    const containers = document.querySelectorAll(menuSelectors);
    
    // Nếu không tìm thấy container đặc trưng, quét toàn bộ nhưng lọc kỹ hơn
    const targetLinks = containers.length > 0 
        ? Array.from(document.querySelectorAll(`${menuSelectors} a[href]`))
        : Array.from(document.querySelectorAll('a[href]'));

    return targetLinks.map(a => {
        // Tìm label sạch nhất
        const labelEl = a.querySelector('h1, h2, h3, h4, h5, h6, p, span, .label, [class*="text"], [class*="title"]');
        const rawText = (labelEl || a).innerText;
        
        // Lấy thông tin Visual (Icon) để AI mô tả: "Nhấn vào biểu tượng hình bánh răng..."
        const icon = a.querySelector('i, svg, img');
        const iconInfo = icon ? (icon.className || icon.getAttribute('data-icon') || "icon-detected") : "";

        // Lấy màu sắc nền (nếu là dạng Card trên Dashboard)
        const style = window.getComputedStyle(a);

        return {
            text: rawText.trim().split('\n')[0].replace(/[:*]/g, ''),
            href: a.href,
            icon: iconInfo,
            bg_color: style.backgroundColor,
            // Xác định xem đây có phải là Link nội bộ hay Link ngoài
            is_internal: a.host === window.location.host
        };
    })
    .filter(m => {
        const blacklist = ['đăng xuất', 'logout', 'profile', 'thông tin cá nhân', 'javascript:'];
        const isBlacklisted = blacklist.some(word => m.text.toLowerCase().includes(word));
        
        return (
            m.text.length > 2 &&        // Bỏ qua các text quá ngắn (như "v", ">")
            m.is_internal &&            // Chỉ lấy link trong hệ thống GPV
            !isBlacklisted &&           // Loại bỏ menu cá nhân/đăng xuất
            !m.href.endsWith('#')       // Bỏ qua link giả
        );
    })
    // Loại bỏ các Module trùng lặp (nếu vừa có ở Sidebar vừa có ở Dashboard)
    .filter((v, i, a) => a.findIndex(t => (t.text === v.text)) === i);
})();