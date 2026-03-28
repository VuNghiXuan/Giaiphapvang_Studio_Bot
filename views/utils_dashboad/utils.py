import os

def get_status_info(sub_path, manual_status=None):
    """Kiểm tra trạng thái video dựa trên file thực tế trong folder storage"""
    status_list = ["Chưa quay", "Đã quay", "Hoàn chỉnh"]
    if manual_status in status_list: 
        return manual_status
        
    raw_file = os.path.join(sub_path, "raw", "raw_video.mp4")
    output_dir = os.path.join(sub_path, "outputs")
    
    has_output = os.path.exists(output_dir) and any(f.endswith('.mp4') for f in os.listdir(output_dir))
    
    if has_output: return "Hoàn chỉnh"
    if os.path.exists(raw_file): return "Đã quay"
    return "Chưa quay"