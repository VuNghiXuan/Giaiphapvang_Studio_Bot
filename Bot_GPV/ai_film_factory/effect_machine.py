class EffectMachine:
    @staticmethod
    async def show_subtitle(page, text):
        """Dùng cssText để ép trình duyệt render ngay lập tức"""
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
            sub.style.cssText = `
                position: fixed !important;
                bottom: 80px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background-color: rgba(0, 0, 0, 0.9) !important;
                color: #00FFFF !important;
                padding: 15px 30px !important;
                border-radius: 12px !important;
                font-size: 32px !important;
                font-family: Arial, sans-serif !important;
                font-weight: bold !important;
                z-index: 2147483647 !important;
                text-align: center !important;
                max-width: 85% !important;
                border: 3px solid #00FFFF !important;
                box-shadow: 0 0 20px #00FFFF !important;
                display: block !important;
            `;
            sub.innerText = txt;
        }""", text)

    @staticmethod
    async def click_ripple(page, x, y):
        """Hiệu ứng Ripple màu Hồng Neon cực mạnh"""
        # await page.evaluate("""({x, y}) => {
        #     const r = document.createElement('div');
        #     document.body.appendChild(r);
        #     r.style.cssText = `
        #         position: fixed !important;
        #         left: ${x}px !important;
        #         top: ${y}px !important;
        #         width: 50px !important;
        #         height: 50px !important;
        #         background-color: #FF1493 !important;
        #         border-radius: 50% !important;
        #         pointer-events: none !important;
        #         z-index: 2147483647 !important;
        #         transform: translate(-50%, -50%) scale(0) !important;
        #         transition: transform 0.4s ease-out, opacity 0.4s ease-out !important;
        #         box-shadow: 0 0 20px #FF1493 !important;
        #     `;
            
        #     requestAnimationFrame(() => {
        #         r.style.transform = 'translate(-50%, -50%) scale(3) !important';
        #         r.style.opacity = '0 !important';
        #     });
        #     setTimeout(() => r.remove(), 600);
        # }""", {'x': x, 'y': y})

        pass