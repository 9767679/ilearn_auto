import os
import time
import requests
from playwright.sync_api import sync_playwright

LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")
USERNAME = os.environ.get("ILEARN_USERNAME")
PASSWORD = os.environ.get("ILEARN_PASSWORD")

def send_to_line(message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
    print(f"LINE 推送結果: {response.status_code}")

def check_ilearn_notifications():
    print("正在啟動瀏覽器爬蟲...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            print("正在前往逢甲 iLearn 首頁...")
            page.goto("https://ilearn.fcu.edu.tw/", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # 1. 點擊首頁右上角的「登入」按鈕
            login_btn = page.locator("a:has-text('登入')")
            if login_btn.count() > 0:
                print("正在點擊首頁右上角的「登入」...")
                login_btn.first.click()
                time.sleep(2)

            # 2. 輸入帳號與密碼
            print("正在輸入 NID 帳號與密碼...")
            username_selector = "input[placeholder='帳號'], input[name='username'], #username"
            page.wait_for_selector(username_selector, timeout=10000)
            page.fill(username_selector, USERNAME)
            
            password_selector = "input[placeholder='密碼'], input[name='password'], #password"
            page.fill(password_selector, PASSWORD)
            
            # 3. 點擊登入按鈕
            print("點擊登入按鈕...")
            submit_btn = page.locator("button:has-text('登入'), input[value='登入'], .btn-login, button[type='submit']")
            submit_btn.first.click()
            
            # 4. 等待登入完成並跳回主畫面
            print("等待登入跳轉...")
            time.sleep(5)
            page.wait_for_load_state("networkidle")

            print(f"目前所在網址: {page.url}")

            # 5. 精準點擊右上角的小鈴鐺（排除掉設定連結）
            print("正在尋找並點擊右上角通知鈴鐺...")
            bell_selectors = [
                ".popover-region-toggle[data-region='popover-region-toggle']",
                "div.popover-region-toggle .fa-bell",
                "a[data-region='popover-region-toggle']",
                "nav.navbar .fa-bell"
            ]
            
            bell_element = None
            for selector in bell_selectors:
                element = page.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    bell_element = element
                    print(f"成功找到並確認可見的鈴鐺元素，使用選擇器: {selector}")
                    break
            
            if bell_element:
                bell_element.click()
            else:
                raise Exception("無法在頁面上找到可見的通知鈴鐺按鈕")
            
            # 6. 解析通知彈窗內容
            print("正在解析通知彈窗內容...")
            time.sleep(3)
            
            notification_texts = []
            container = page.locator(".popover-region-container, [data-region='notification-popover-container'], .popover-content")
            
            if container.count() > 0:
                items = container.locator(".content-item, .notification, .py-2, .list-group-item, p").all_inner_texts()
                for item in items:
                    cleaned = item.strip()
                    if cleaned and len(cleaned) > 4 and cleaned not in ["通知", "標為已讀", "查看全部", "設定", "沒有通知", "通知提醒的偏好"]:
                        if cleaned not in notification_texts:
                            notification_texts.append(cleaned)

            if notification_texts:
                notif_msg = "\n\n-------------------\n\n".join(notification_texts[:5])
                message = f"【逢甲 iLearn - 最新通知公告】\n\n{notif_msg}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                send_to_line("【逢甲 iLearn 提醒】已成功點擊小鈴鐺，但目前沒有抓取到新的通知內容。")

        except Exception as e:
            error_msg = str(e)
            print(f"爬蟲執行發生錯誤: {error_msg}")
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {error_msg}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()