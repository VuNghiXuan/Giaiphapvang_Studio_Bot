() => {
    const elements = Array.from(document.querySelectorAll('input, select, textarea, [role="combobox"]'));
    
    const getCleanLabel = (el) => {
        let text = "";
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${el.id}"]`);
            if (labelEl) text = labelEl.innerText;
        }
        if (!text) {
            const parentLabel = el.closest('label');
            if (parentLabel) text = parentLabel.innerText;
        }
        if (!text) {
            const parentRow = el.closest('.form-group, .MuiFormControl-root, .ant-form-item, .field, [class*="form-item"]');
            if (parentRow) {
                const labelInRow = parentRow.querySelector('.label, label, [class*="label"]');
                if (labelInRow) text = labelInRow.innerText;
            }
        }
        if (!text) text = el.placeholder || el.getAttribute('aria-label') || el.name || el.id || "";
        return text.replace(/\n/g, ' ').replace(/[*:]/g, '').trim();
    };

    const getErrorMessage = (el) => {
        const parent = el.closest('.form-group, .MuiFormControl-root, .ant-form-item, div');
        if (!parent) return "";
        const errorEl = parent.querySelector('.error, .Mui-error, .ant-form-item-explain-error, [class*="error"], [class*="feedback"]');
        return errorEl ? errorEl.innerText.trim() : "";
    };

    const getGroupName = (el) => {
        const fieldset = el.closest('fieldset');
        if (fieldset) {
            const legend = fieldset.querySelector('legend');
            if (legend) return legend.innerText.trim();
        }
        const section = el.closest('[class*="section"], [class*="group"], .card');
        const title = section ? section.querySelector('h1, h2, h3, h4, [class*="title"], [class*="header"]') : null;
        return title ? title.innerText.trim() : "Thông tin chung";
    };

    // --- TÍNH NĂNG MỚI: VÉT DANH SÁCH LỰA CHỌN (COMBOBOX/SELECT) ---
    const getOptionsSample = (el) => {
        // 1. Nếu là thẻ select truyền thống
        if (el.tagName.toLowerCase() === 'select') {
            return Array.from(el.options)
                .filter(o => o.text && o.value !== "")
                .slice(0, 10) // Lấy tối đa 10 mẫu để AI hiểu loại dữ liệu
                .map(o => o.text.trim());
        }
        
        // 2. Nếu là Custom Dropdown (AntD, MUI, vv.)
        // Tìm text của item đang được chọn hiện tại làm mẫu
        const selectedValue = el.innerText || el.getAttribute('value') || "";
        return selectedValue ? [selectedValue.trim()] : [];
    };

    return elements.map(el => {
        const label = getCleanLabel(el);
        const style = window.getComputedStyle(el);
        const tagName = el.tagName.toLowerCase();
        const options = getOptionsSample(el);
        
        return {
            label: label,
            group: getGroupName(el),
            tag: tagName,
            type: el.type || (tagName === 'select' || el.getAttribute('role') === 'combobox' ? 'combobox' : 'text'),
            id: el.id || "",
            name: el.name || "",
            placeholder: el.placeholder || "",
            value: el.value || el.innerText || "",
            required: el.required || el.hasAttribute('required') || style.borderColor === 'rgb(255, 0, 0)',
            error: getErrorMessage(el),
            options_sample: options, // Cực kỳ quan trọng để AI mô tả: "Chọn Chi nhánh như..."
            has_options: options.length > 0,
            visual_attr: {
                color: style.color,
                backgroundColor: style.backgroundColor,
                width: el.offsetWidth,
                position: el.getBoundingClientRect()
            },
            isVisible: el.offsetWidth > 0 && el.offsetHeight > 0
        };
    }).filter(item => 
        item.type !== 'hidden' && 
        item.type !== 'submit' && 
        item.isVisible &&
        item.label !== "" &&
        item.label.length < 100
    );
}