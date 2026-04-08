() => {
    const buttons = Array.from(document.querySelectorAll('button, a.btn, input[type="button"]'));
    return buttons.map(btn => {
        // Lấy tọa độ để PageMiner có thể dùng nếu cần click
        const rect = btn.getBoundingClientRect();
        const style = window.getComputedStyle(btn);

        return {
            text: btn.innerText.replace(/\n/g, ' ').trim(),
            title: btn.title || "",
            id: btn.id,
            color: style.backgroundColor,
            is_visible: rect.width > 0 && rect.height > 0,
            // Phân loại nút dựa trên text (để AI dễ nhận diện nút quan trọng)
            is_primary: style.backgroundColor.includes('rgb(0,') || btn.classList.contains('btn-primary')
        };
    }).filter(btn => 
        // Chỉ lấy các nút có chữ và đang hiển thị
        btn.text.length > 0 && btn.is_visible
    );
}