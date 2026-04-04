import asyncio
import nest_asyncio

# Áp dụng nest_asyncio một lần duy nhất tại đây
nest_asyncio.apply()

def run_async(coro):
    """
    Hàm 'vạn năng' để giải mã Coroutine trong môi trường Streamlit.
    Giúp biến hàm Async thành dữ liệu thực ngay lập tức.
    """
    if not coro:
        return None
        
    try:
        # 1. Thử lấy vòng lặp hiện tại
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 2. Nếu đang chạy (Streamlit thread), ép nó chạy đến khi xong
            return loop.run_until_complete(coro)
        else:
            # 3. Nếu chưa chạy, dùng run thông thường
            return asyncio.run(coro)
    except RuntimeError:
        # 4. Nếu Thread này chưa bao giờ có loop, tạo mới hoàn toàn
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(coro)
    except Exception as e:
        print(f"🚨 Lỗi giải mã Coroutine: {e}")
        return asyncio.run(coro) # Cố gắng chạy phát cuối