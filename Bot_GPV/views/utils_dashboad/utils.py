# import os
# import streamlit as st

# def get_status_info(sub_path, manual_status=None):
#     """
#     Kiểm tra trạng thái video dựa trên file thực tế trong folder storage.
#     Ưu tiên trạng thái được lưu trong Database nếu có.
#     """
#     status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    
#     # Nếu trong DB đã có trạng thái cụ thể thì trả về luôn
#     if manual_status in status_list: 
#         return manual_status
        
#     # Đường dẫn kiểm tra file thực tế
#     # Cấu trúc: storage/Giai_Phap_Vang/Form_Name/raw/raw_video.mp4
#     raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
#     output_dir = os.path.join(sub_path, "outputs")
    
#     # Kiểm tra xem đã có video thành phẩm chưa
#     has_output = False
#     if os.path.exists(output_dir):
#         # Kiểm tra xem có file .mp4 nào trong thư mục outputs không
#         has_output = any(f.endswith('.mp4') for f in os.listdir(output_dir))
    
#     if has_output: 
#         return "Hoàn chỉnh"
    
#     if os.path.exists(raw_file): 
#         return "Đã quay"
        
#     return "Chưa quay"

# def render_status_badge(status):
#     """
#     Hiển thị tag trạng thái có màu sắc đẹp mắt trên UI Streamlit.
#     Vũ gọi hàm này trong file Dashboard Component nhé.
#     """
#     colors = {
#         "Chưa quay": "gray",    # Màu xám cho việc chưa bắt đầu
#         "Đã quay": "blue",      # Màu xanh dương cho bản thô
#         "Hoàn chỉnh": "green"   # Màu xanh lá cho thành phẩm
#     }
    
#     color = colors.get(status, "gray")
    
#     # Sử dụng st.status hoặc đơn giản là st.markdown với style
#     return st.markdown(
#         f"""
#         <span style="
#             background-color: {color};
#             color: white;
#             padding: 2px 8px;
#             border-radius: 10px;
#             font-size: 0.8rem;
#             font-weight: bold;
#         ">
#             {status}
#         </span>
#         """, 
#         unsafe_allow_html=True
#     )