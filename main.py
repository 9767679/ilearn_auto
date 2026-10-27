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
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        try:
            print("正在前往 iLearn...")
            page.goto("https://ilearn.fcu.edu.tw/", timeout=60000)
            page.wait_for_load_state("networkidle")

            # 處理登入
            if page.locator("input[name='username']").count() > 0 or page.locator("#username").count() > 0:
                print("正在輸入帳號密碼進行登入...")
                page.fill("input[name='username'], #username", USERNAME)
                page.fill("input[name='password'], #password", PASSWORD)
                page.click("button[type='submit'], input[type='submit'], .btn-submit")
                page.wait_for_load_state("networkidle")
            
            time.sleep(5)

            # 點擊右上角的小鈴鐺圖示 (Moodle 標準的通知按鈕)
            print("正在點擊右上角通知鈴鐺...")
            bell_selector = ".popover-region-toggle[data-region='popover-region-toggle']"
            if page.locator(bell_selector).count() > 0:
                page.locator(bell_selector).first.click()
            else:
                # 備用選擇器
                page.locator("a:has(.fa-bell)").first.click()
            
            # 等待通知彈窗完全展開並載入內容
            time.sleep(3)

            # 精準抓取通知彈窗內部的文字
            print("正在解析通知彈窗內容...")
            notification_texts = []
            
            # 定位通知選單的容器
            container = page.locator(".popover-region-container, [data-region='notification-popover-container']")
            if container.count() > 0:
                # 抓取裡面每一個通知項目的文字
                items = container.locator(".content-item, .notification, .py-2").all_inner_texts()
                for item in items:
                    cleaned = item.strip()
                    # 過濾掉按鈕或太短的雜訊字眼
                    if cleaned and len(cleaned) > 4 and cleaned not in ["通知", "標為已讀", "查看全部", "設定"]:
                        if cleaned not in notification_texts:
                            notification_texts.append(cleaned)

            if notification_texts:
                # 取出前 5 筆最新通知
                notif_msg = "\n\n-------------------\n\n".join(notification_texts[:5])
                message = f"【逢甲 iLearn - 最新通知公告】\n\n{notif_msg}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                print("未抓取到通知內容。")
                send_to_line("【逢甲 iLearn 提醒】已點擊小鈴鐺，但未成功讀取到通知內容。")

        except Exception as e:
            print(f"爬蟲執行發生錯誤: {e}")
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()