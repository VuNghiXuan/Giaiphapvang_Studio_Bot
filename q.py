'https://gemini.google.com/app/87111578dee1961a'

'https://gemini.google.com/app/dbe633a02315825c?hl=vi%20H%E1%BB%99p%20th%C6%B0%20%C4%91%E1%BA%BFn'

'https://gemini.google.com/app/dbe633a02315825c?hl=vi%20H%E1%BB%99p%20th%C6%B0%20%C4%91%E1%BA%BFn'


'''
mày phải tượng tượng khi diễn nó cũng sẽ đi từ đăng nhập hệ thống--> trang home--> modules -->giả sử click vào module hệ thống--> sidebar (thanh cuộn hay không)--> menu cha-->menu con --> giao diện menu con có gì (bảng , các nút trong giao diện cả trên và dưới bảng, có cột chức năng các nút ẩn, trường dữ liệu, thanh cuộn,....) nói chung là phải lấy hết mới được thì video mới thành công diễn như người thật
mày phải ra kịch bản các bước trình tự chứ tao thấy như vậy chưa ổn: ví dụ để hướng dẫn nhạp mới chi nhánh thì sau đăng nhập nó biết nó đang ở trang nào (cụ thể là trang Home), sau đó nó hướng dẫn đi trình tự như click vào module hệ thống, tại menu siderbar, click vào thông tin công ty, tìm đến thẻ chi nhánh, lúc này form chi nhánh hiện lên thì click vào nút tạo mới, tại đây form tạo mới hiện ra mới nhập các trường dữ liệu ở đây, làm như vậy con Bot nó không bị ngáo


'''


"""
Q:
----------------------------

Tao cần đi lấy dữ liệu cho metadata lưu vào db để làm viết kịch bản (bức thư cho AI soạn lại, làm kịch bản sản xuất video tự động):
- Bước 1 (Chung cho tất cả hướng dẫn): đăng nhập trang, thành công trang giaiphapvang hiện trang Home. Bước này có thể tùy form có lời thoại hoặc không
- Bước 2: Nhấn vào nút module (ví dụ hệ thống) trên trang home để đi vào chi tiết của Module đó. Phần Module hiện nay đã được truyền từ gui vào file scrapce_giaiphapvang () và tại hàm update_module_details(self, project_name, module_name, module_url)
Trong hàm này sẽ gọi vision_machine để đi lấy tất cả các phần tử con (siderbar, menu cha, con (đa phần là form cần hướng dẫn thành phẩm video), thanh cuộn và các thuộc tính khác). Nhấn vào từng menu cha con này nếu có form hiện ra thì đi vét tất cả các thành phần của giao diện của nó, như nút (nhấn vào nút để liệt kê các phần tử bên trong, có thể nó sẽ hiên ra table con nữa, hoặc bản thân giao diện cha cũng có giao diện). 
Sau khi giao diện trên hiện ra tự đọng click vào các nút trên, dưới, trong ngoài, xác định form này chứa các phần từ con nào (liệt kê nút, bảng, các trường dữ liệu, bảng có thanh cuộn không, có bao nhiêu cột, tên cột, lưu ý các cột chức năng là chứa các nút thao tấc thêm xóa, chỉnh sửa,...), Nhấn hết các nút xem có hiện ra bảng mới không, rồi đi lấy các phần tử con bảng mới của gaio diện mới, cứ thế vét cạn hết không chừa gì, theo tiêu chí vét nhâm hơn bỏ sót
- Bước 3: THu thập dữ liệu và lưu và trường metadata để làm sao mô tả bức thư cho AI viết kịch bản
- Bước 4: Lấy dữ liệu metadate viết thư trình bày thư sao cho AI hiểu:
Phục vụ cho con Bot tự quay phim, lồng tiếng với nội dung ví dụ như sau:
Để Nhập mới 1 Chi nhánh, sau khi đăng nhập thành công, bạn click vào hệ thống (Module trên trang chủ để đi tới Giao diện "abc" gì đó, tại đây chúng ta nhấn vào menu Thông tin công ty (lúc này hiện ra menu con) và nhìn xuống danh mục chúng ta thấy nút Chi nhánh, nhấn vào để hiện ra giao diện danh sách chi nhánh, hãy nhìn ben phải màn hình chúng ta là toàn bộ danh sách chi nhánh thuộc, và tại đây để nhập mới 1 chi nhánh, chúng ta nhấn vào nút Tạo mơi/Thêm mới(mô tả nút nằm đâu trong giao diện form, nút màu gì đặc điểm), sau đó tại các trường thông tin chung ta nhập mã chi nhanah, tên, số điện thoại, ... mô tả thực tế dữ liệu và các trường cụ thể), sau đó tùy theo từng giao diện chúng ta có thêm các nút Hủy/ Lưu/ Lưu và thêm, giải thích rõ chức năng nút này)

Mày thêm nội dung góp ý hoàn chỉnh mô tả, thêm mô tả về thanh cuộn siderbar, bảng ngang dọc, các nút ẩn trong cột chức năng của bảng, các nút xuất file ản hiện cột, ... Bây giờ mô tả lại chi tiết hơn. Chú ý thêm có các nút bảng trong bảng hiện ra bảng mới đi lấy cái form đó nữa, các combobox, hướng dẫn chọn liên kết bảng này với dữ liệu bảng kia, khi nhập dữ liệu báo lỗi cũng phải biết là lỗi gì, mô tả chi tiết đừng để thiếu

A:-------------------

1. KIẾN TRÚC VÉT CẠN METADATA (DEEP-SCAN ARCHITECTURE)
Giai đoạn 1: Lớp Điều hướng (Global Navigation Layer)
Module Switcher: Ghi nhận tên Module (Hệ thống, Kho, Bán hàng), tọa độ nút trên Topbar/Home và trạng thái "Active".

Sidebar & Scrollers: * Quét cây danh mục (Parent-Child).

Thanh cuộn Sidebar: Kiểm tra thuộc tính overflow-y. Nếu có thanh cuộn, Metadata phải ghi rõ: "Menu này dài, cần cuộn chuột xuống để thấy các mục phía dưới". Điều này giúp AI viết kịch bản: "Từ thanh menu bên trái, bạn cuộn xuống tìm mục...".

Breadcrumbs: Lấy lộ trình đường dẫn (ví dụ: Hệ thống > Thông tin công ty > Chi nhánh) để AI định vị không gian.

Giai đoạn 2: Lớp Giao diện Danh sách (The Grid & Action Layer)
Bảng (Tables) & Thanh cuộn kép: * Cuộn ngang (Horizontal): Kiểm tra số lượng cột. Nếu bảng rộng quá màn hình, ghi lại: "Bảng có 15 cột, cần kéo thanh cuộn ngang sang phải để thấy cột Chức năng".

Cuộn dọc (Vertical): Xác định bảng có phân trang hay cuộn vô tận.

Cột Chức năng (Hidden Operations): * Đây là "ổ khóa" của video. Phải vét sạch các nút: Sửa (Edit), Xóa (Delete), Xem (View), In (Print), Sao chép (Clone).

Mô tả đặc điểm: Nút icon hay nút chữ? Màu sắc gì? Nằm ở dòng thứ mấy (thường lấy dòng đầu tiên làm mẫu)?

Công cụ bảng (Toolbar): * Quét các nút: Xuất file (Excel/PDF), Ẩn/Hiện cột, Lọc (Filter).

Nếu bấm "Ẩn/Hiện cột" hiện ra một menu checkbox, Bot phải quét luôn danh sách các tên cột có thể ẩn hiện.

Giai đoạn 3: Lớp Form Chi tiết & Nội soi Đệ quy (Deep Recursive Form)
Trường dữ liệu (Inputs & Combobox): * Liệt kê mọi trường: Textbox, DatePicker, Checkbox.

Combobox (Liên kết dữ liệu): Xác định đây là dạng chọn từ danh sách. Metadata ghi: "Trường [Khu vực] là Combobox, liên kết với dữ liệu từ danh mục vùng miền". AI sẽ soạn: "Tại đây, bạn chọn khu vực đã được định nghĩa sẵn...".

Bảng trong Bảng (Sub-Grid / Nested Table): * Khi nhấn vào một dòng hoặc một nút "Chi tiết", nếu hiện ra một bảng con (ví dụ: Chi nhánh -> Danh sách Kho con), Bot phải nhảy vào quét tiếp bảng con đó (số cột, nút thêm dòng, nút xóa dòng trong bảng con).

Nút bấm đặc thù (Form Actions): * Quét các nút: Lưu, Hủy, Lưu và Thêm mới, Đóng.

Ghi rõ vị trí: "Nằm ở góc dưới bên phải dialog".

Logic báo lỗi (Validation Metadata): * Bot thử bấm "Lưu" khi chưa nhập gì để bắt mã lỗi hoặc câu thông báo (ví dụ: "Vui lòng nhập Mã chi nhánh").

Metadata ghi lại nội dung lỗi và màu sắc (đỏ/vàng) để AI dặn người xem: "Lưu ý, nếu bạn quên nhập Mã, hệ thống sẽ cảnh báo bằng chữ đỏ...".

2. CẤU TRÚC "BỨC THƯ GỬI AI" (PROMPT METADATA)
Dữ liệu Metadata lưu vào DB sẽ được trình bày lại cho AI theo cấu trúc "Storyline" như sau:

STT	Phân đoạn	Metadata chi tiết cung cấp cho AI
1	Khởi đầu	URL trang Home, Tọa độ nút Module [Hệ thống].
2	Di chuyển	Danh sách Sidebar. Lưu ý: Menu [Thông tin công ty] cần Click để mở rộng. Mục [Chi nhánh] nằm ở vị trí thứ 3.
3	Trang danh sách	Bảng có 10 cột. Cột cuối cùng là "Chức năng" chứa icon Sửa (Bút chì) và Xóa (Thùng rác). Nút "Thêm mới" nằm phía trên bên phải, màu xanh dương.
4	Nội soi Form	Tên Dialog: "Thêm mới Chi nhánh". Danh sách 5 trường nhập liệu. Trường [Mã] là bắt buộc. Trường [Loại hình] chọn từ danh sách.
5	Bảng con (nếu có)	Trong form có bảng "Nhân sự phụ trách". Có nút "Thêm dòng" để nhập thông tin nhân viên.
6	Kết thúc & Lỗi	Nút "Lưu" tọa độ {x,y}. Thông báo lỗi khi trùng mã: "Mã đã tồn tại trên hệ thống".
3. GÓP Ý HOÀN THIỆN ĐỂ VIDEO "DIỄN NHƯ NGƯỜI THẬT"
Để video không bị "máy móc", Metadata của mày cần thêm 3 yếu tố này:

Mô tả vật lý (Visual Attributes): Lưu lại màu sắc (Hex code) và kích thước nút. AI sẽ nói: "Nhấn vào nút xanh lá to nhất ở giữa màn hình".

Độ trễ (Loading State): Ghi lại thời gian chờ trung bình khi chuyển trang hoặc mở Form. AI sẽ soạn kịch bản: "Hệ thống sẽ mất vài giây để tải dữ liệu, bạn vui lòng đợi trong giây lát".

Trạng thái rỗng (Empty State): Nếu bảng không có dữ liệu, Bot phải quét xem có thông báo "Không tìm thấy dữ liệu" không, để AI hướng dẫn người dùng cách tạo dữ liệu đầu tiên.

Chốt lại: Con Bot của mày sẽ đi theo nguyên tắc "Thấy cửa là mở, thấy nút là bấm, thấy lỗi là ghi". Khi có đủ Metadata này, bức thư gửi AI sẽ cực kỳ chi tiết, AI chỉ việc lắp câu chữ vào là có ngay kịch bản sản xuất video tự động chuẩn 100% như người hướng dẫn thật.

Mày thấy bản "Tổng mục lục vét cạn" này đã đủ đô để mày nâng cấp hàm update_module_details chưa? Cần tao viết mẫu logic quét cho cái Combobox hay Bảng con không?

"""