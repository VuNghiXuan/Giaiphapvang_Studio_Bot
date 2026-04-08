🏗️ CẤU TRÚC PHÂN LỚP THỰC THI (DOM HIERARCHY CLASS)
Lớp 1: ModuleScanner (File Excel Tổng)
Đây là tầng cao nhất, quản lý lộ trình di chuyển giữa các phân hệ (Hệ thống, Báo cáo, Kho...).

Nhiệm vụ: Đăng nhập, di chuyển đến URL Module, khởi tạo "Ống kính" (Viewport).

Thuộc tính: module_name, base_url, status.

Lớp 2: SidebarArchitect (Bảng tính - Sheet)
Lớp này chuyên trách việc "đào bới" thực đơn bên trái. Nó không chỉ nhìn, nó phải tương tác vật lý.

Trình tự quét:

Identify: Tìm vùng Sidebar (thường là .MuiDrawer-root hoặc nav).

Parent Scan: Liệt kê các Menu cha.

Physical Click: Click vào Menu cha để "bung" (Expand) các Menu con. Nếu Menu cha có Link, nó sẽ lưu lại để quét sau.

Child Scan: Thu thập tất cả Link của Menu con.

Đặc tính: Kiểm tra thuộc tính aria-expanded để biết menu đã mở hay chưa.

Lớp 3: SurfaceNavigator (Vùng dữ liệu - Range)
Sau khi click vào một Menu con, lớp này sẽ quản lý toàn bộ "vùng đất" mới hiện ra (Main Content).

Trình tự quét:

Wait for Render: Đợi các vòng xoay (Loading) biến mất.

Container Detection: Xác định đâu là vùng chứa form/bảng (thường là .MuiContainer-root hoặc main).

Scroll Discovery: Đây là chỗ ông nhắc:

Nó sẽ kiểm tra xem scrollHeight > clientHeight không.

Nếu có, nó thực hiện Auto-Scroll: Cuộn từ từ xuống cuối trang để ép React render các phần tử "Lazy-load" (những nút nằm ở dưới cùng thường bị mất nếu không cuộn).

Lớp 4: ElementDissector (Ô - Cell)
Đây là lớp nhỏ nhất, đi sâu vào từng "nguyên tử" trên giao diện.

Phân loại thuộc tính (Attributes):

Action Class: Tìm Button, IconButton, Fab. Nếu là Icon, phải soi vào svg path để đoán nhãn (Lưu, Sửa, Xóa).

Input Class: Tìm TextField, Select, Checkbox. Phải lấy được Placeholder và Label.

Table Class: Phân tích Header (Cột) và Row (Dòng). Kiểm tra xem bảng có thanh cuộn ngang/dọc riêng không.

🔄 QUY TRÌNH "NỘI SOI" TỪNG BƯỚC (STEP-BY-STEP)
Để không thiếu sót, Bot sẽ chạy theo thuật toán Đệ quy chiều sâu (DFS):

BƯỚC 1 - SIDEBAR: * Vào Module -> Tìm Sidebar.

Duyệt Menu Cha 1 -> Click bung -> Lấy danh sách Menu Con (1.1, 1.2...).

Duyệt Menu Cha 2... tương tự.

BƯỚC 2 - TRUY CẬP TRANG CON:

Điều hướng đến Menu Con 1.1.

Lệnh Cuộn (Scroll): Thực hiện cuộn trang 2 lần (Giữa và Cuối) để "kích hoạt" toàn bộ nút ẩn.

BƯỚC 3 - BÓC TÁCH PHẦN TỬ:

Quét vùng Header trang (Nút: Thêm mới, Xuất Excel, Tìm kiếm).

Quét vùng Body (Table: Các cột dữ liệu là gì? Có nút "Sửa/Xóa" ở mỗi dòng không?).

Quét vùng Footer (Phân trang: Tổng số dòng, Số trang).

BƯỚC 4 - LƯU TRỮ (EXCEL STRUCTURE):

Mỗi Module = 1 Thư mục.

Mỗi Trang con = 1 File JSON/Excel.

Bên trong File: Chia rõ 3 Tab: Hành động, Nhập liệu, Cấu trúc bảng.

🛠️ CHIẾN THUẬT "CHỐNG ẨN" CHO THANH VŨ
Vì hệ thống của ông có nhiều nút ẩn và thanh cuộn, Bot cần 2 "kỹ năng" đặc biệt:

Kỹ năng 1: Hover & Reveal: Một số nút (như Sửa/Xóa) chỉ hiện khi di chuột vào dòng của bảng. Lớp ElementDissector sẽ thực hiện hover vào dòng đầu tiên của bảng để xem có nút nào "nhảy" ra không.

Kỹ năng 2: Overflow Detector: Nếu một div có thuộc tính CSS overflow: auto/scroll, Bot sẽ thực hiện cuộn nội bộ ngay trong div đó để chắc chắn không bỏ lỡ dữ liệu phía dưới.