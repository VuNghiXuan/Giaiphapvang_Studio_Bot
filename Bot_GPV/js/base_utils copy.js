/**
 * GIAIPHAPVANG STUDIO BOT - CORE UTILITIES
 * Tác dụng: Cung cấp bộ công cụ nhận diện UI cho Bot trinh sát (Scout) và Bot hành động (Actor).
 * Đặc điểm: Chống nổ lỗi khi gặp dữ liệu NULL, hỗ trợ tốt cho MUI (Material UI).
 */
window.utils.expandAllMenus = async () => {
    // Tìm tất cả các nút có icon mũi tên hoặc các mục menu cha (MUI)
    const togglers = document.querySelectorAll('.MuiListItem-root:has(.MuiCollapse-root), .main-sidebar [data-toggle="treeview"]');
    for (let btn of togglers) {
        // Nếu nó đang đóng (kiểm tra aria-expanded hoặc class)
        if (btn.getAttribute('aria-expanded') === 'false' || !btn.classList.contains('menu-open')) {
            btn.click(); // Click để bung ra
            await new Promise(r => setTimeout(r, 500)); // Đợi animation mở xong
        }
    }
};

window.utils = {
    // 1. Hàm tạm dừng (Dùng để đợi UI render hoặc giả lập hành vi người)
    sleep: (ms) => new Promise(r => setTimeout(r, ms)),

    // 2. Hàm làm sạch Text: Lấy chữ từ Element, loại bỏ xuống dòng, icon rác và khoảng trắng dư thừa
    getCleanText: (el) => {
        if (!el) return "";
        try {
            // Lấy innerText (cái người dùng thấy) hoặc textContent (cái code thấy)
            const raw = el.innerText || el.textContent || "";
            // split('\n')[0]: Chỉ lấy dòng đầu nếu text có nhiều dòng
            // replace: Xóa các ký tự bullet point, dấu sao thường thấy ở menu
            return raw.split('\n')[0].replace(/[\*\•\○\+]/g, '').trim();
        } catch (e) { 
            return ""; // Trả về rỗng thay vì nổ lỗi TypeError
        }
    },

    // 3. Hàm lấy thông tin hiển thị: Tọa độ, kích thước, màu sắc và trạng thái ẩn hiện
    getVisuals: (el) => {
        if (!el) return { is_visible: false };
        try {
            const r = el.getBoundingClientRect(); // Lấy tọa độ thực trên màn hình
            const style = window.getComputedStyle(el); // Lấy thuộc tính CSS thực tế
            return {
                x: Math.round(r.left), y: Math.round(r.top),
                w: Math.round(r.width), h: Math.round(r.height),
                color: style.color,
                bg_color: style.backgroundColor,
                // Một phần tử được coi là hiển thị nếu có kích thước và không bị CSS ẩn đi
                is_visible: r.width > 0 && r.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                opacity: parseFloat(style.opacity || "1")
            };
        } catch (e) { 
            return { is_visible: false }; 
        }
    },

    // 4. Hàm tạo Selector: Ưu tiên thuộc tính bền vững (name, aria-label) thay vì class MUI hay thay đổi
    getSelector: (el) => {
        if (!el) return "";
        try {
            if (el.name) return `[name="${el.name}"]`;
            if (el.getAttribute('aria-label')) return `[aria-label="${el.getAttribute('aria-label')}"]`;
            if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
            // Bỏ qua ID nếu nó chứa chuỗi 'mui-' (vì MUI sinh ID ngẫu nhiên mỗi lần load)
            if (el.id && !el.id.includes('mui-')) return `#${el.id}`;
            
            // Nếu là thẻ Link, lấy đường dẫn href làm định danh
            if (el.tagName === 'A' && el.getAttribute('href')) {
                const href = el.getAttribute('href');
                if (href && href !== '#' && !href.startsWith('javascript')) {
                    return `a[href="${href}"]`;
                }
            }
            return el.tagName.toLowerCase();
        } catch (e) { 
            return "unknown"; 
        }
    },

    // 5. Hàm nhãn thông minh: Nhận diện tên nút kể cả khi nút đó chỉ có Icon (không có chữ)
    getSmartLabel: (btn) => {
        try {
            let label = window.utils.getCleanText(btn) || btn.title || btn.getAttribute('aria-label') || "";
            
            // Nếu không tìm thấy chữ, soi vào mã nguồn HTML bên trong nút (SVG/Icon)
            if (label.length <= 1) {
                const inner = (btn.innerHTML || "").toLowerCase();
                const svg = btn.querySelector('svg');
                const tid = (svg ? svg.getAttribute('data-testid') : "") || "";
                
                // Quy tắc đoán nút dựa trên từ khóa phổ biến trong hệ thống Giải Pháp Vàng
                if (inner.includes('edit') || tid.toLowerCase().includes('edit')) return "Sửa (Bút chì)";
                if (inner.includes('delete') || inner.includes('trash') || tid.toLowerCase().includes('delete')) return "Xóa (Thùng rác)";
                if (inner.includes('save') || tid.toLowerCase().includes('save')) return "Lưu";
                if (inner.includes('add') || inner.includes('plus')) return "Thêm mới";
                if (inner.includes('print')) return "In ấn";
                if (inner.includes('close') || tid.toLowerCase().includes('close')) return "Đóng";
                if (inner.includes('search')) return "Tìm kiếm";
            }
            return label || "Nút chức năng";
        } catch (e) { 
            return "Nút"; 
        }
    },

    // 6. Hàm mô tả vị trí: Chuyển tọa độ pixel thành ngôn ngữ tự nhiên (Trái, Phải, Trên, Dưới)
    getRelativePos: (el) => {
        try {
            const r = el.getBoundingClientRect();
            const vh = window.innerHeight;
            const vw = window.innerWidth;
            const yPos = r.top < vh / 3 ? "phía trên" : (r.top > (vh * 2) / 3 ? "phía dưới" : "giữa");
            const xPos = r.left < vw / 3 ? "bên trái" : (r.left > (vw * 2) / 3 ? "bên phải" : "chính giữa");
            return `${yPos} ${xPos} màn hình`;
        } catch (e) { 
            return "không rõ vị trí"; 
        }
    }
};

/**
 * HÀM QUÉT DỮ LIỆU CƠ BẢN (INTERNAL SCAN)
 * Tác dụng: "Mổ xẻ" một vùng giao diện (container) để lấy Metadata.
 */
window.internalScan = (container) => {
    console.log("🕵️ [ScoutEngine] Bắt đầu quét vùng nội dung...");

    // Nếu không tìm thấy vùng chứa (ví dụ trang chưa load), trả về mảng rỗng thay vì dừng script
    if (!container) {
        console.warn("⚠️ [internalScan] Vùng chứa (container) bị NULL.");
        return { actions: [], inputs: [], tables: [] };
    }

    const data = { actions: [], inputs: [], tables: [] };
    
    // Bước 1: Quét các hành động (Nút bấm, Link, Nút MUI)
    try {
        const actionElements = container.querySelectorAll('button, a, [role="button"], .MuiButton-root');
        actionElements.forEach(btn => {
            const vis = window.utils.getVisuals(btn);
            if (!vis.is_visible) return; // Chỉ lấy những nút nhìn thấy được

            data.actions.push({
                label: window.utils.getSmartLabel(btn),
                selector: window.utils.getSelector(btn),
                rect: vis,
                position_desc: window.utils.getRelativePos(btn),
                bg_color_hex: vis.bg_color
            });
        });
        console.log(`   ✅ Tìm thấy ${data.actions.length} nút/link.`);
    } catch (e) { console.error("❌ Lỗi quét Actions:", e); }

    // Bước 2: Quét bảng (Tables/Grids) để biết cấu trúc dữ liệu đang hiển thị
    try {
        const tables = container.querySelectorAll('table, .MuiDataGrid-root, [role="grid"]');
        tables.forEach(t => {
            const cols = Array.from(t.querySelectorAll('th, .MuiDataGrid-columnHeaderTitle, [role="columnheader"]'))
                .map(window.utils.getCleanText)
                .filter(v => v && v.length > 0); // Bỏ qua tiêu đề cột rỗng
                
            data.tables.push({
                columns: cols,
                rect: window.utils.getVisuals(t),
                position_desc: window.utils.getRelativePos(t)
            });
        });
        console.log(`   ✅ Tìm thấy ${data.tables.length} bảng.`);
    } catch (e) { console.error("❌ Lỗi quét Tables:", e); }

    // Bước 3: Quét ô nhập liệu (Inputs/Form)
    try {
        const inputs = container.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            // Logic tìm nhãn (Label) cho ô input: Tìm thẻ <label> có ID tương ứng hoặc thẻ cha
            let labelText = "";
            const id = input.id;
            if (id) {
                const labelEl = document.querySelector(`label[for="${id}"]`);
                if (labelEl) labelText = window.utils.getCleanText(labelEl);
            }
            if (!labelText) {
                const parentLabel = input.closest('label') || input.closest('.MuiFormControl-root')?.querySelector('label');
                labelText = window.utils.getCleanText(parentLabel) || input.placeholder || input.name || "Input không nhãn";
            }

            data.inputs.push({
                label: labelText,
                selector: window.utils.getSelector(input),
                type: input.type || "text",
                current_value: input.value || "", // Lấy giá trị đang có trong ô
                rect: window.utils.getVisuals(input)
            });
        });
        console.log(`   ✅ Tìm thấy ${data.inputs.length} ô nhập liệu.`);
    } catch (e) { console.error("❌ Lỗi quét Inputs:", e); }

    return data;
};

// 7. Hệ thống điều hướng (Dành riêng cho Sidebar của Giải Pháp Vàng)
window.nav = {
    get_ui_tree: () => {
        const results = [];
        // Tìm vùng chứa Sidebar (thường là .main-sidebar hoặc MuiDrawer)
        const sidebar = document.querySelector('.main-sidebar, .MuiDrawer-root, nav') || document;
        
        // Quét tất cả các mục menu (ListItem)
        // Lấy những thằng có thể click được (có href hoặc có role button)
        const items = sidebar.querySelectorAll('.MuiListItem-root, .MuiButtonBase-root');
        
        items.forEach(item => {
            const link = item.tagName === 'A' ? item : item.querySelector('a');
            const title = window.utils.getCleanText(item);
            
            // Nếu là link trực tiếp (Menu cấp 1 hoặc con đã bung)
            if (link && link.getAttribute('href') && link.getAttribute('href') !== '#') {
                results.push({
                    title: title,
                    href: link.getAttribute('href'),
                    children: []
                });
            } 
            // Nếu là Folder (Menu cha) - có chứa con bên trong
            else {
                const subMenu = item.nextElementSibling;
                if (subMenu && (subMenu.classList.contains('MuiCollapse-root') || subMenu.querySelector('a'))) {
                    const children = [];
                    subMenu.querySelectorAll('a').forEach(childLink => {
                        children.push({
                            title: window.utils.getCleanText(childLink),
                            href: childLink.getAttribute('href')
                        });
                    });
                    
                    if (children.length > 0) {
                        results.push({
                            title: title,
                            href: "#",
                            children: children
                        });
                    }
                }
            }
        });
        
        // Lọc bỏ trùng lặp nếu có
        return results.filter((v, i, a) => a.findIndex(t => t.title === v.title) === i);
    }
};

// Đánh dấu để Python có thể kiểm tra xem script đã nạp xong chưa
window.utils_loaded = true;