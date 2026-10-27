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
            print("正在前往 iLearn...")
            page.goto("https://ilearn.fcu.edu.tw/", timeout=60000)
            page.wait_for_load_state("domcontentloaded")

            # 處理登入（根據學校 SSO 頁面調整）
            if page.locator("input[name='username'], #username, input[name='msoid']").count() > 0:
                print("正在輸入帳號密碼進行登入...")
                # 填入帳號與密碼（請確保欄位選擇器涵蓋學校的輸入框）
                page.fill("input[name='username'], #username, input[name='msoid']", USERNAME)
                page.fill("input[name='password'], #password, input[name='msupwd']", PASSWORD)
                
                # 點擊登入
                page.click("button[type='submit'], input[type='submit'], .btn-submit, #submit")
                
                # 等待登入後跳轉完成
                page.wait_for_load_state("networkidle")
                time.sleep(5)

            # 點擊右上角的小鈴鐺圖示
            print("正在點擊右上角通知鈴鐺...")
            bell_selector = ".popover-region-toggle[data-region='popover-region-toggle'], a:has(.fa-bell)"
            page.wait_for_selector(bell_selector, timeout=15000)
            page.locator(bell_selector).first.click()
            
            # 確保通知彈窗已載入
            print("正在解析通知彈窗內容...")
            time.sleep(3) # 給 Moodle 一點時間透過 AJAX 載入清單
            
            notification_texts = []
            container = page.locator(".popover-region-container, [data-region='notification-popover-container']")
            
            if container.count() > 0:
                items = container.locator(".content-item, .notification, .py-2, .list-group-item").all_inner_texts()
                for item in items:
                    cleaned = item.strip()
                    if cleaned and len(cleaned) > 4 and cleaned not in ["通知", "標為已讀", "查看全部", "設定"]:
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
                send_to_line("【逢甲 iLearn 提醒】已點擊小鈴鐺，但未成功讀取到通知內容。")

        except Exception as e:
            print(f"爬蟲執行發生錯誤: {e}")
            # 發生錯誤時截圖（若在本地可檢視，GitHub Actions 可設定上傳截圖 Artifact）
            try:
                page.screenshot(path="error_screenshot.png")
            except:
                pass
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()