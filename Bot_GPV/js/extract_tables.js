() => {
    const tables = Array.from(document.querySelectorAll('table'));
    return tables.map(t => {
        // Lấy tiêu đề cột
        const headers = Array.from(t.querySelectorAll('th')).map(th => th.innerText.trim());
        
        // Kiểm tra xem dòng đầu tiên có dữ liệu không
        const firstRow = t.querySelector('tbody tr');
        let actions = [];
        
        if (firstRow) {
            // Tìm các nút hoặc link trong dòng đầu tiên (thường là Sửa, Xóa, Xem)
            actions = Array.from(firstRow.querySelectorAll('button, a'))
                .map(btn => ({
                    text: btn.innerText.trim(),
                    title: btn.title || "",
                    icon_class: btn.querySelector('i')?.className || ""
                }))
                .filter(a => a.text !== "" || a.title !== "");
        }

        return {
            id: t.id || "table",
            column_count: headers.length,
            headers: headers,
            row_count: t.querySelectorAll('tbody tr').length,
            row_actions: actions 
        };
    }).filter(table => table.column_count > 0);
}