import asyncio
import os
from playwright.async_api import async_playwright

async def render_svg_to_png(svg_path, png_path, width=400, height=400):
    """
    Sử dụng Playwright để render SVG sang PNG chuẩn 100% (hỗ trợ Gradient, Shadow).
    """
    if not os.path.exists(svg_path):
        print(f"❌ Không tìm thấy file: {svg_path}")
        return False

    async with async_playwright() as p:
        # Chạy ngầm (headless=True) cho nhanh
        browser = await p.chromium.launch(headless=True)
        
        # Thiết lập Viewport khớp với kích thước logo mong muốn
        context = await browser.new_context(viewport={'width': width, 'height': height})
        page = await context.new_page()
        
        # Lấy đường dẫn tuyệt đối để trình duyệt đọc được file cục bộ
        abs_svg_path = os.path.abspath(svg_path)
        file_url = f"file:///{abs_svg_path.replace(os.sep, '/')}"
        
        try:
            print(f"🎨 Playwright đang render: {svg_path}...")
            await page.goto(file_url)
            
            # Chờ một chút để các hiệu ứng Gradient/Animation (nếu có) ổn định
            await page.wait_for_timeout(500)
            
            # Screenshot phần tử SVG và bỏ qua nền (để có nền trong suốt)
            # Nếu file SVG chuẩn, nó sẽ chiếm toàn bộ page
            await page.screenshot(
                path=png_path, 
                omit_background=True, # QUAN TRỌNG: Tạo nền trong suốt
                type="png"
            )
            
            print(f"✅ Đã tạo thành công Logo PNG: {png_path}")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi render logo: {e}")
            return False
        finally:
            await browser.close()

if __name__ == "__main__":
    # Vũ chạy trực tiếp file này để test
    asyncio.run(render_svg_to_png("assets/logo.svg", "assets/logo.png"))