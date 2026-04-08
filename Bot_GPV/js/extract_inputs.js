() => {
    const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
    return inputs.map(el => {
        // Tìm Label đi kèm để biết ô này là gì (ví dụ: "Tên khách hàng", "Tiền mặt"...)
        let labelText = "";
        const label = document.querySelector(`label[for="${el.id}"]`) || el.closest('label');
        
        if (label) {
            labelText = label.innerText.replace(/\n/g, ' ').trim();
        } else {
            // Nếu không có label, lấy placeholder hoặc name attribute
            labelText = el.placeholder || el.name || el.id || "Không xác định";
        }

        return {
            label: labelText,
            tag: el.tagName.toLowerCase(),
            type: el.type || 'text',
            id: el.id,
            placeholder: el.placeholder || "",
            required: el.required,
            value: el.value || ""
        };
    }).filter(item => 
        // Loại bỏ các input ẩn hoặc các nút bấm bị lẫn vào
        item.type !== 'hidden' && item.type !== 'submit' && item.label !== ""
    );
}