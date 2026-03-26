import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Load biến môi trường (Lấy tài khoản từ .env)
load_dotenv()

class SelectorScraper:
    def __init__(self, output_dir="recordings"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    async def get_interactive_elements(self, url, email, password):
        """
        Cào sạch các Selector thông minh trên một trang web, hỗ trợ login
        """
        async with async_playwright() as p:
            # 1. Khởi tạo trình duyệt
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            elements_data = []

            try:
                # BƯỚC 1: Login tự động
                print(f"📡 Đang kết nối tới: {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)

                # Điền email & pass (Dựa trên selector thông minh)
                print("🔑 Đang điền tài khoản...")
                await page.get_by_label("Email").fill(email) # Dùng label cho MUI
                await page.get_by_label("Mật khẩu").fill(password)
                
                # Nhấn đăng nhập
                await page.get_by_role("button", name="Đăng nhập").click()
                print("⏳ Đang đợi load trang sau khi login...")
                await page.wait_for_selector("a[href='/dashboard/']", state="visible", timeout=30000)
                await asyncio.sleep(2) # Chờ MUI render xong

                # BƯỚC 2: Cào dữ liệu
                print("🕷️ Đang 'cào' các phần tử tương tác trên trang...")
                
                # Quét tất cả thẻ <input> (Ô nhập liệu)
                inputs = await page.get_by_role("textbox").all()
                for inp in inputs:
                    label = await inp.input_value()
                    name = await inp.get_attribute("name")
                    placeholder = await inp.get_attribute("placeholder")
                    id_attr = await inp.get_attribute("id")
                    
                    elements_data.append({
                        "type": "input",
                        "label_text": label,
                        "smart_selector": f"internal:label=\"{label}\"i" if label else f"input[name='{name}']" if name else f"input[placeholder='{placeholder}']" if placeholder else f"input#{id_attr}" if id_attr else ""
                    })

                # Quét tất cả thẻ <button> (Nút bấm)
                buttons = await page.get_by_role("button").all()
                for btn in buttons:
                    text = await btn.inner_text()
                    id_attr = await btn.get_attribute("id")
                    
                    elements_data.append({
                        "type": "button",
                        "text": text,
                        "smart_selector": f"internal:role=button[name=\"{text}\"i]" if text else f"button#{id_attr}" if id_attr else ""
                    })

                # Quét tất cả thẻ <a> (Link) - Quan trọng để vào "Hệ thống"
                links = await page.get_by_role("link").all()
                for link in links:
                    text = await link.inner_text()
                    href = await link.get_attribute("href")
                    
                    elements_data.append({
                        "type": "link",
                        "text": text,
                        "href": href,
                        "smart_selector": f"internal:role=link[name=\"{text}\"i]" if text else f"a[href='{href}']" if href else ""
                    })

                print(f"✅ Đã tìm thấy {len(elements_data)} phần tử quan trọng!")
                return elements_data

            except Exception as e:
                print(f"❌ Lỗi Scraper: {e}")
                await page.screenshot(path="recordings/scraper_error.png")
                return []
            finally:
                await context.close()
                await browser.close()

    def export_selectors_table(self, elements, scenario_name):
        """
        Xuất dữ liệu thành một file JSON và in ra bảng đẹp đẽ
        """
        if not elements:
            print("❌ Không có dữ liệu để xuất.")
            return

        print("\n" + "="*80)
        print(f"DANH SÁCH SELECTORS CHO KỊCH BẢN: {scenario_name.upper()}")
        print("="*80)
        print(f"{'TYPE':<10} | {'TEXT/LABEL':<30} | {'HREF':<20} | {'SMART SELECTOR'}")
        print("-" * 80)
        
        cleaned_elements = []
        for el in elements:
            type_str = el.get("type", "")
            text_str = (el.get("text") or el.get("label_text") or "").strip()
            href_str = el.get("href", "") or ""
            selector_str = el.get("smart_selector", "")

            # Bỏ các selector rác hoặc quá dài
            if not selector_str or len(selector_str) < 5 or "css" in selector_str:
                continue

            cleaned_elements.append({
                "type": type_str,
                "text": text_str,
                "href": href_str,
                "selector": selector_str
            })
            
            # In ra console cho Vũ nhìn
            text_disp = (text_str[:27] + '..') if len(text_str) > 27 else text_str
            href_disp = (href_str[:17] + '..') if len(href_str) > 17 else href_str
            print(f"{type_str:<10} | {text_disp:<30} | {href_disp:<20} | {selector_str}")

        # Xuất file JSON
        json_path = os.path.join(self.output_dir, f"{scenario_name}_selectors.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_elements, f, ensure_ascii=False, indent=4)
        
        print("="*80)
        print(f"✅ Đã xuất dữ liệu Selector thành file JSON tại: {json_path}")