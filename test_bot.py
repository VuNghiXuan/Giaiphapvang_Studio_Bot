import asyncio
from core.browser_agent import BrowserAgent

async def main():
    agent = BrowserAgent()
    
    # Giả lập kịch bản hướng dẫn Kê khai (Vũ thay Selector đúng của web mày vào nhé)
    # Cập nhật kịch bản có bước Đăng nhập
    script_steps = [
        {
            "action": "goto", 
            "selector": "https://giaiphapvang.net/auth/jwt/sign-in/", # Dùng link login gốc, bỏ phần returnTo cho sạch
            "description": "Truy cập vào trang đăng nhập hệ thống Giải Pháp Vàng."
        },
        {
            "action": "fill", 
            "selector": "input[name='email']", # Tuyệt đối không dùng ID _r_4_ nữa
            "value": "admin@giaiphapvang.net", 
            "description": "Nhập địa chỉ email quản trị."
        },
        {
            "action": "fill", 
            "selector": "input[name='password']", # Thường name sẽ là 'password'
            "value": "Demo@123", 
            "description": "Nhập mật khẩu truy cập."
        },
        {
            "action": "click", 
            "selector": "button[type='submit']", 
            "description": "Bấm nút Đăng nhập."
        },
        {
            "action": "wait", 
            "value": "2", 
            "description": "Để quý khách có thể quan sát kỹ hơn thao tác này."
        },
    ]
    print("🚀 Bot bắt đầu xuất kích...")
    video_file, logs = await agent.run_scenario("Huong_Dan_Ke_Khai", script_steps)
    
    if video_file:
        print(f"✅ Đã quay xong video: {video_file}")
        print(f"📋 Danh sách hành động (Dùng để lồng tiếng):")
        for log in logs:
            print(log)

if __name__ == "__main__":
    asyncio.run(main())