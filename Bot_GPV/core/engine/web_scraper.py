import re
from config import Config

class WebScraper:
    def __init__(self, target_domain):
        self.target_domain = target_domain

    async def scan_home_modules(self, page):
        js_script = Config.get_javascript_path("extract_modules.js").read_text(encoding='utf-8')
        all_links = []
        for frame in page.frames:
            try:
                raw = await frame.evaluate(js_script)
                if raw: all_links.extend(raw)
            except: continue
        return self._clean_links(all_links)

    async def scan_sidebar_structure(self, page, modul_name):
        js_path = Config.get_javascript_path("sidebar_script.js")
        js_code = js_path.read_text(encoding='utf-8')
        await page.evaluate(js_code)
        await page.evaluate('window.sidebarScraper.expandAll()')
        return await page.evaluate(f'window.sidebarScraper.extractData("{modul_name}")')

    def _clean_links(self, links):
        unique = {}
        exclude = ["đăng xuất", "cài đặt", "hướng dẫn", "thanh toán", "login"]
        for m in links:
            text = re.sub(r'[•○+►]', '', str(m.get('text', ''))).strip()
            href = str(m.get('href', ''))
            if len(text) > 2 and not any(k in text.lower() for k in exclude):
                full_href = f"https://{self.target_domain}{href}" if href.startswith('/') else href
                unique[text] = {"text": text, "href": full_href}
        return list(unique.values())