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
        # 在 GitHub Actions 上必須用 headless=True
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            print("正在前往逢甲 iLearn...")
            page.goto("https://ilearn.fcu.edu.tw/", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            print(f"初始網頁標題: {page.title()}, 網址: {page.url}")

            # 檢查是否需要進行登入（如果頁面上有輸入框，或被導向登入頁）
            login_input_selector = "input[name='username'], #username, input[name='msoid'], input[name='IDToken1']"
            
            if page.locator(login_input_selector).count() > 0 or "login" in page.url or "sso" in page.url:
                print("偵測到登入頁面，正在輸入 NID 帳號密碼...")
                
                # 填入帳號與密碼
                page.fill(login_input_selector, USERNAME)
                
                password_input_selector = "input[name='password'], #password, input[name='msupwd'], input[name='IDToken2']"
                page.fill(password_input_selector, PASSWORD)
                
                # 點擊登入按鈕
                submit_selector = "button[type='submit'], input[type='submit'], .btn-login, #submit, #loginbtn, button.login-btn"
                if page.locator(submit_selector).count() > 0:
                    page.click(submit_selector)
                else:
                    # 如果找不到按鈕，嘗試直接按 Enter 鍵
                    page.press(password_input_selector, "Enter")
                
                print("等待登入跳轉...")
                time.sleep(5)
                page.wait_for_load_state("networkidle")

            # 每次執行都強制截圖，方便你檢查登入後的畫面
            print(f"登入後網址: {page.url}")
            page.screenshot(path="after_login.png")

            # 尋找通知鈴鐺
            print("正在尋找通知鈴鐺...")
            bell_selectors = [
                ".popover-region-toggle",
                "a[data-title='通知']",
                "a:has(.fa-bell)",
                ".fa-bell",
                "nav.navbar .fa-bell"
            ]
            
            bell_element = None
            for selector in bell_selectors:
                if page.locator(selector).count() > 0:
                    bell_element = page.locator(selector).first
                    print(f"成功找到鈴鐺元素，使用選擇器: {selector}")
                    break
            
            if bell_element:
                bell_element.click()
            else:
                # 把當前頁面的文字印出來幫忙除錯
                print("當前頁面文字預覽:", page.inner_text("body")[:300])
                page.screenshot(path="no_bell_found.png")
                raise Exception("無法在頁面上找到通知鈴鐺（可能是登入未成功或版面已變更）")
            
            # 解析通知彈窗內容
            print("正在解析通知彈窗內容...")
            time.sleep(3)
            
            notification_texts = []
            container = page.locator(".popover-region-container, [data-region='notification-popover-container'], .popover-content")
            
            if container.count() > 0:
                items = container.locator(".content-item, .notification, .py-2, .list-group-item, p").all_inner_texts()
                for item in items:
                    cleaned = item.strip()
                    if cleaned and len(cleaned) > 4 and cleaned not in ["通知", "標為已讀", "查看全部", "設定", "沒有通知"]:
                        if cleaned not in notification_texts:
                            notification_texts.append(cleaned)

            if notification_texts:
                notif_msg = "\n\n-------------------\n\n".join(notification_texts[:5])
                message = f"【逢甲 iLearn - 最新通知公告】\n\n{notif_msg}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                print("未抓取到通知內容，儲存截圖以供除錯...")
                page.screenshot(path="debug_screenshot.png")
                send_to_line("【逢甲 iLearn 提醒】已嘗試點擊小鈴鐺，但未成功讀取到具體的通知內容。")

        except Exception as e:
            error_msg = str(e)
            print(f"爬蟲執行發生錯誤: {error_msg}")
            try:
                page.screenshot(path="error_screenshot.png")
            except:
                pass
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {error_msg}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()