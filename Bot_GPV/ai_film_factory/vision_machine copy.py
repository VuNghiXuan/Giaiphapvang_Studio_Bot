import asyncio
from datetime import datetime

class VisionMachine:
    def __init__(self):
        self.scanner_script = '''() => {
            const getCleanText = (el) => {
                if (!el) return "";
                return el.innerText.split('\\n')[0].replace(/[\\*\\•\\○]/g, '').trim();
            };

            const getSelector = (el) => {
                if (el.name) return `[name="${el.name}"]`;
                const ariaLabel = el.getAttribute('aria-label');
                if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
                if (el.id && !el.id.startsWith('mui-')) return `#${el.id}`;
                return ""; 
            };

            const isVisible = (el) => {
                const rect = el.getBoundingClientRect();
                return (rect.top >= 0 && rect.left >= 0 && 
                        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && 
                        rect.right <= (window.innerWidth || document.documentElement.clientWidth));
            };

            const structure = {
                url: window.location.href,
                title: document.title,
                navigation: {
                    modules: [],     // Menu ngang / Module chính
                    sidebar: [],     // Menu dọc (Cha - Con)
                    breadcrumbs: []  // Đường dẫn hiện tại (Hệ thống > Danh mục > ...)
                },
                content: {
                    columns: [],
                    form_fields: [],
                    actions: [],       // Nút phía trên/dưới bảng
                    row_operations: [], // Nút ẩn/hiện trong từng dòng
                    export_formats: []
                },
                state: {
                    errors: [], 
                    is_loading: !!document.querySelector('.MuiCircularProgress-root, .MuiSkeleton-root, [class*="loading"]'),
                    has_overlay: !!document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]'),
                    scroll_info: {
                        can_scroll_y: document.body.scrollHeight > window.innerHeight,
                        current_y: window.scrollY
                    }
                }
            };

            // --- 1. VÉT NAVIGATION (Hành trình đi vào) ---
            // Quét Sidebar/Menu (Ưu tiên các thẻ nav hoặc các class sidebar của MUI)
            const sidebarItems = document.querySelectorAll('.MuiListItemButton-root, [class*="sidebar"] [role="button"]');
            sidebarItems.forEach(item => {
                const label = getCleanText(item);
                if (label) {
                    structure.navigation.sidebar.push({
                        label: label,
                        is_active: item.classList.contains('Mui-selected') || item.innerHTML.includes('active'),
                        has_child: !!item.querySelector('.MuiCollapse-root') || !!item.nextElementSibling?.classList.contains('MuiCollapse-root'),
                        selector: getSelector(item) || `text="${label}"`
                    });
                }
            });

            // --- 2. VÉT CỘT BẢNG & TRƯỜNG DỮ LIỆU (Cảnh diễn chính) ---
            const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
            const searchArea = activeOverlay || document.querySelector('main') || document.body;

            // Vét cột
            document.querySelectorAll('.MuiDataGrid-columnHeaderTitle').forEach(h => {
                const txt = getCleanText(h);
                if(txt) structure.content.columns.push(txt);
            });

            // Vét hành động (Buttons) - Logic đoán Icon của Vũ
            searchArea.querySelectorAll('button, a, [role="button"]').forEach(b => {
                // Bỏ qua nếu là nút trong sidebar khi đang ở chế độ vét nội dung
                // Logic đoán nút dựa trên từ khóa đồng nghĩa (Synonyms)
                if (!label || label.length <= 1) {
                    const html = b.innerHTML.toLowerCase();
                    const cls = b.className.toLowerCase();
                    const fullText = html + " " + cls; // Quét cả HTML lẫn Class cho chắc

                    if (fullText.match(/edit|pencil|update|sua/)) label = "Sửa";
                    else if (fullText.match(/delete|trash|remove|xoa/)) label = "Xóa";
                    else if (fullText.match(/save|check|luu/)) label = "Lưu";
                    // Thêm các từ khóa cho "Tạo mới" ở đây
                    else if (fullText.match(/add|plus|create|new|tao/)) label = "Thêm"; 
                    else if (fullText.match(/download|export|xuat/)) label = "Xuất";
                    else if (fullText.match(/print|in/)) label = "In";
                    else if (fullText.match(/close|cancel|exit|dong|huy/)) label = "Đóng";
                }

                if (label && label.length > 1) {
                    const btnData = {
                        label,
                        selector: getSelector(b) || `button:has-text("${label}")`,
                        is_visible: isVisible(b),
                        is_primary: b.classList.contains('MuiButton-containedPrimary')
                    };
                    if (b.closest('.MuiDataGrid-row')) structure.content.row_operations.push(btnData);
                    else structure.content.actions.push(btnData);
                }
            });

            // Vét Form Fields
            searchArea.querySelectorAll('.MuiFormControl-root, .MuiTextField-root').forEach(container => {
                let input = container.querySelector('input, textarea, select, [role="combobox"]');
                if (!input) return;
                let labelEl = container.querySelector('label');
                let label = labelEl ? getCleanText(labelEl) : (input.placeholder || "");
                
                if (label) {
                    structure.content.form_fields.push({
                        label,
                        type: input.type || 'text',
                        selector: getSelector(input) || `[placeholder*="${label}"]`,
                        value: input.value || "",
                        is_required: container.innerHTML.includes('Mui-required'),
                        is_error: container.innerHTML.includes('Mui-error')
                    });
                }
            });

            // --- 3. VÉT LỖI ---
            document.querySelectorAll('.Mui-error, .MuiAlert-message').forEach(err => {
                structure.state.errors.push(err.innerText.trim());
            });

            return structure;
        }'''

    async def scan_page(self, page):
        try:
            # Chờ ổn định để quay video không bị giật
            await page.wait_for_load_state("networkidle", timeout=3000)
            data = await page.evaluate(self.scanner_script)
            if data: data['scanned_at'] = datetime.now().isoformat()
            return data
        except Exception as e:
            print(f"❌ Vision Error: {e}")
            return None