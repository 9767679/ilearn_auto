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

            # 檢查是否被導向或需要點擊登入（若首頁有「登入」按鈕或直接進入了 SSO 頁面）
            # 如果當前網址包含 login 或者是 NID 登入頁面
            if "login" in page.url or page.locator("input[name='username'], #username").count() > 0:
                print("正在輸入 NID 帳號密碼進行登入...")
                
                # 填入帳號與密碼
                page.fill("input[name='username'], #username", USERNAME)
                page.fill("input[name='password'], #password", PASSWORD)
                
                # 點擊登入按鈕
                # 逢甲 NID 登入按鈕通常是 type='submit' 或特定 class
                page.click("button[type='submit'], input[type='submit'], .btn-login, #loginbtn")
                
                # 等待跳轉回 iLearn 首頁
                print("等待登入跳轉...")
                page.wait_for_url("**/ilearn.fcu.edu.tw/**", timeout=30000)
                page.wait_for_load_state("networkidle")
                time.sleep(3)

            # 有時候首頁右上角會有登入按鈕，如果直接進首頁還沒登入，嘗試尋找頁面上的「登入」連結點擊
            elif page.locator("a:has-text('登入'), a[href*='login']").count() > 0 and "You are not logged in" in page.content():
                print("發現未登入狀態，正在點擊登入連結...")
                page.locator("a:has-text('登入'), a[href*='login']").first.click()
                page.wait_for_load_state("domcontentloaded")
                
                print("正在輸入 NID 帳號密碼...")
                page.fill("input[name='username'], #username", USERNAME)
                page.fill("input[name='password'], #password", PASSWORD)
                page.click("button[type='submit'], input[type='submit'], .btn-login, #loginbtn")
                page.wait_for_load_state("networkidle")
                time.sleep(3)

            # 點擊右上角的小鈴鐺圖示（Moodle 標準佈景主題的通知鈴鐺）
            print("正在尋找並點擊右上角通知鈴鐺...")
            bell_selector = ".popover-region-toggle[data-region='popover-region-toggle'], a[data-title='通知'], .fa-bell"
            page.wait_for_selector(bell_selector, timeout=15000)
            page.locator(bell_selector).first.click()
            
            # 確保通知彈窗已載入
            print("正在解析通知彈窗內容...")
            time.sleep(3) # 給 AJAX 一點時間載入清單
            
            notification_texts = []
            # Moodle 通知選單容器
            container = page.locator(".popover-region-container, [data-region='notification-popover-container'], .popover-content")
            
            if container.count() > 0:
                items = container.locator(".content-item, .notification, .py-2, .list-group-item, p").all_inner_texts()
                for item in items:
                    cleaned = item.strip()
                    # 過濾掉介面常見的冗長按鈕文字
                    if cleaned and len(cleaned) > 4 and cleaned not in ["通知", "標為已讀", "查看全部", "設定", "沒有通知"]:
                        if cleaned not in notification_texts:
                            notification_texts.append(cleaned)

            if notification_texts:
                notif_msg = "\n\n-------------------\n\n".join(notification_texts[:5])
                message = f"【逢甲 iLearn - 最新通知公告】\n\n{notif_msg}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                print("未抓取到通知內容，嘗試截圖以供除錯...")
                page.screenshot(path="debug_screenshot.png")
                # 順便印出當前網頁文字以便查看原因
                print("當前頁面片段:", page.content()[:500])
                send_to_line("【逢甲 iLearn 提醒】已嘗試點擊小鈴鐺，但未成功讀取到具體通知內容。")

        except Exception as e:
            print(f"爬蟲執行發生錯誤: {e}")
            try:
                page.screenshot(path="error_screenshot.png")
            except:
                pass
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()