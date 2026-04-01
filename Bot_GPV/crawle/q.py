"""
mày phải tượng tượng khi diễn nó cũng sẽ đi từ đăng nhập hệ thống--> trang home--> modules -->giả sử click vào module hệ thống--> sidebar (thanh cuộn hay không)--> menu cha-->menu con --> giao diện menu con có gì (bảng , các nút trong giao diện cả trên và dưới bảng, có cột chức năng các nút ẩn, trường dữ liệu, thanh cuộn,....) nói chung là phải lấy hết mới được thì video mới thành công diễn như người thật
mày phải ra kịch bản các bước trình tự chứ tao thấy như vậy chưa ổn: ví dụ để hướng dẫn nhạp mới chi nhánh thì sau đăng nhập nó biết nó đang ở trang nào (cụ thể là trang Home), sau đó nó hướng dẫn đi trình tự như click vào module hệ thống, tại menu siderbar, click vào thông tin công ty, tìm đến thẻ chi nhánh, lúc này form chi nhánh hiện lên thì click vào nút tạo mới, tại đây form tạo mới hiện ra mới nhập các trường dữ liệu ở đây, làm như vậy con Bot nó không bị ngáo
: import asyncio
from datetime import datetime

class VisionMachine:
    def __init__(self):
        # SCRIPT QUÉT ĐA TẦNG: Kết hợp logic cũ và khả năng nhận diện thông minh mới
        self.scanner_script = '''() => {
            const getCleanText = (el) => {
                if (!el) return "";
                // Lấy dòng đầu tiên, xóa ký tự đặc biệt (dấu sao bắt buộc, icon...)
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
                columns: [],
                form_fields: [],
                actions: [],
                row_operations: [],
                export_formats: [],
                errors: [], 
                is_loading: !!document.querySelector('.MuiCircularProgress-root, [class*="loading"], .MuiSkeleton-root'),
                has_overlay: !!document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]')
            };

            // 1. VÉT CỘT BẢNG (MUI DataGrid)
            document.querySelectorAll('.MuiDataGrid-columnHeaderTitle').forEach(h => {
                const txt = getCleanText(h);
                if(txt && !structure.columns.includes(txt)) structure.columns.push(txt);
            });

            // 2. XÁC ĐỊNH KHU VỰC ƯU TIÊN (Dialog/Drawer)
            const activeOverlay = document.querySelector('.MuiDialog-root, .MuiDrawer-root, [role="dialog"]');
            const searchArea = activeOverlay || document.querySelector('main') || document.body;

            // 3. VÉT NÚT BẤM (Logic đoán Icon nâng cao từ code cũ)
            searchArea.querySelectorAll('button, a, [role="button"]').forEach(b => {
                if (!activeOverlay && (b.closest('nav') || b.closest('[class*="sidebar"]'))) return;

                let label = getCleanText(b) || b.getAttribute('aria-label') || b.title;
                
                // Logic đoán nút cực mạnh nếu Label trống (Dùng cho Icon Buttons)
                if (!label || label.length <= 1) {
                    const html = b.innerHTML.toLowerCase();
                    const cls = b.className.toLowerCase();
                    if (html.includes('edit') || cls.includes('edit')) label = "Sửa";
                    else if (html.includes('delete') || html.includes('trash') || cls.includes('delete')) label = "Xóa";
                    else if (html.includes('save') || cls.includes('save')) label = "Lưu";
                    else if (html.includes('add') || html.includes('plus')) label = "Thêm";
                    else if (html.includes('download') || html.includes('export')) label = "Xuất file";
                    else if (html.includes('print')) label = "In";
                    else if (html.includes('close') || html.includes('cancel')) label = "Đóng";
                }

                if (label && label.length > 1) {
                    const btnData = {
                        label: label,
                        selector: getSelector(b) || `button:has-text("${label}")`,
                        is_visible: isVisible(b),
                        is_disabled: b.disabled || b.classList.contains('Mui-disabled'),
                        is_primary: b.classList.contains('MuiButton-containedPrimary') || b.classList.contains('MuiButton-contained')
                    };

                    if (b.closest('.MuiDataGrid-row')) {
                        if (!structure.row_operations.find(o => o.label === label)) structure.row_operations.push(btnData);
                    } else {
                        if (!structure.actions.find(a => a.label === label)) structure.actions.push(btnData);
                    }
                }
            });

            // 4. VÉT TRƯỜNG NHẬP LIỆU (Giữ nguyên logic container của MUI)
            searchArea.querySelectorAll('.MuiFormControl-root, .MuiTextField-root, .MuiInputBase-root').forEach(container => {
                let inputEl = container.querySelector('input, textarea, select, [role="combobox"]');
                if (!inputEl) return;

                const labelEl = container.querySelector('label, .MuiFormLabel-root');
                let labelTxt = labelEl ? getCleanText(labelEl) : (inputEl.placeholder || inputEl.getAttribute('aria-label') || "");

                if (labelTxt && labelTxt.length > 1) {
                    if (!structure.form_fields.find(f => f.label === labelTxt)) {
                        structure.form_fields.push({
                            label: labelTxt,
                            name: inputEl.name,
                            type: inputEl.type || inputEl.getAttribute('role') || 'text',
                            selector: getSelector(inputEl) || `input[placeholder*="${labelTxt}"]`,
                            required: container.innerHTML.includes('Mui-required') || inputEl.required || false,
                            value: inputEl.value || "",
                            is_error: container.innerHTML.includes('Mui-error'),
                            is_visible: isVisible(inputEl)
                        });
                    }
                }
            });

            // 5. VÉT ĐỊNH DẠNG XUẤT FILE (Khi menu Export đang bật)
            document.querySelectorAll('.MuiMenuItem-root, [role="menuitem"]').forEach(item => {
                const itemTxt = item.innerText.trim();
                const formats = ['Excel', 'CSV', 'PDF', 'In ấn', 'Download'];
                if (formats.some(k => itemTxt.includes(k))) {
                    if (!structure.export_formats.find(e => e.label === itemTxt)) {
                        structure.export_formats.push({
                            label: itemTxt,
                            selector: `text="${itemTxt}"`
                        });
                    }
                }
            });

            // 6. VÉT LỖI GIAO DIỆN
            document.querySelectorAll('.Mui-error, .MuiAlert-message, .MuiSnackbarContent-message').forEach(err => {
                const errMsg = err.innerText.trim();
                if (errMsg && !structure.errors.includes(errMsg)) structure.errors.push(errMsg);
            });

            return structure;
        }'''

    
"""