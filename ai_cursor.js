// Đoạn JS này Vũ inject vào page lúc bắt đầu quay
const cursor = document.createElement('div');
cursor.id = 'ai-cursor';
Object.assign(cursor.style, {
    width: '20px', height: '20px',
    backgroundColor: 'rgba(255, 255, 0, 0.6)', // Màu vàng trong suốt
    border: '2px solid orange', borderRadius: '50%',
    position: 'fixed', pointerEvents: 'none', // Quan trọng: pointerEvents: none để không gây hover bậy
    zIndex: '9999', transition: 'all 0.4s ease-out' // Hiệu ứng lướt mượt
});
document.body.appendChild(cursor);

// Hàm điều khiển chuột ảo
window.moveAICursor = (x, y) => {
    cursor.style.left = x + 'px';
    cursor.style.top = y + 'px';
};