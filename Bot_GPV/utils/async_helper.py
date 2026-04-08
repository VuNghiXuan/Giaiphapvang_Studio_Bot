import asyncio
import nest_asyncio

# Áp dụng nest_asyncio để cho phép loop lồng nhau (Cần thiết cho Streamlit + Playwright)
nest_asyncio.apply()

def run_async(coro):
    """
    Hàm 'vạn năng' đã được gia cố để trị lỗi Event Loop của Streamlit.
    """
    if not coro:
        return None
        
    try:
        # 1. Lấy hoặc tạo loop cho Thread hiện tại
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 2. Thực thi Coroutine
        # Nếu loop đang chạy (nhờ nest_asyncio), run_until_complete sẽ chạy lồng vào được
        return loop.run_until_complete(coro)

    except Exception as e:
        print(f"🚨 Lỗi giải mã Coroutine: {e}")
        # Không dùng asyncio.run ở đây để tránh tạo thêm loop chồng chéo
        return None