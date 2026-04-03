class EffectMachine:
    @staticmethod
    async def show_subtitle(page, text):
        """Hiển thị Subtitle trực tiếp trên Browser để quay video"""
        await page.evaluate("""(txt) => {
            let sub = document.getElementById('bot-subtitle');
            if (!sub) {
                sub = document.createElement('div');
                sub.id = 'bot-subtitle';
                document.body.appendChild(sub);
            }
            if (!txt) {
                sub.style.display = 'none';
                return;
            }
            // Style đậm chất công nghệ cho ngành Vàng
            sub.style.cssText = `
                position: fixed !important;
                bottom: 100px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background: rgba(0, 0, 0, 0.85) !important;
                color: #FFD700 !important; 
                padding: 12px 25px !important;
                border-radius: 8px !important;
                font-size: 30px !important;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
                font-weight: 600 !important;
                z-index: 2147483647 !important;
                text-align: center !important;
                max-width: 80% !important;
                border-left: 5px solid #FFD700 !important;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
                display: block !important;
                transition: all 0.3s ease !important;
            `;
            sub.innerText = txt;
        }""", text)

    @staticmethod
    async def apply_click_effect(page, x, y):
        """Hiệu ứng Ripple màu Hồng Neon khi Click"""
        await page.evaluate("""({x, y}) => {
            const ripple = document.createElement('div');
            document.body.appendChild(ripple);
            
            const baseStyle = `
                position: fixed !important;
                left: ${x}px !important;
                top: ${y}px !important;
                width: 20px !important;
                height: 20px !important;
                background: none !important;
                border: 4px solid #FF1493 !important;
                border-radius: 50% !important;
                pointer-events: none !important;
                z-index: 2147483647 !important;
                transform: translate(-50%, -50%) scale(0) !important;
                opacity: 1 !important;
                box-shadow: 0 0 15px #FF1493 !important;
            `;
            ripple.style.cssText = baseStyle;

            // Dùng requestAnimationFrame để đảm bảo trình duyệt nhận diện được sự thay đổi style
            requestAnimationFrame(() => {
                ripple.style.transition = 'transform 0.5s ease-out, opacity 0.5s ease-out !important';
                ripple.style.transform = 'translate(-50%, -50%) scale(4) !important';
                ripple.style.opacity = '0 !important';
            });

            setTimeout(() => ripple.remove(), 600);
        }""", {'x': x, 'y': y})

    @staticmethod
    async def clear_effects(page):
        """Dọn dẹp subtitle trước khi qua bước mới"""
        await page.evaluate("() => { const s = document.getElementById('bot-subtitle'); if(s) s.style.display = 'none'; }")