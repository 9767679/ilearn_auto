import os
import time
from datetime import datetime, timezone, timedelta
import requests
from playwright.sync_api import sync_playwright

# 從 GitHub Secrets 讀取資訊
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
        # 啟動無頭瀏覽器 (headless=True 適合在 GitHub Actions 雲端執行)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        try:
            # 1. 前往 iLearn 首頁
            print("正在前往 iLearn...")
            page.goto("https://ilearn.fcu.edu.tw/", timeout=60000)
            page.wait_for_load_state("networkidle")

            # 2. 處理登入流程（如果需要導向學校 SSO 登入頁面）
            # 點擊登入或檢查是否有輸入帳號欄位
            if page.locator("input[name='username']").count() > 0 or page.locator("#username").count() > 0:
                print("正在輸入帳號密碼進行登入...")
                page.fill("input[name='username'], #username", USERNAME)
                page.fill("input[name='password'], #password", PASSWORD)
                page.click("button[type='submit'], input[type='submit'], .btn-submit")
                page.wait_for_load_state("networkidle")
            
            # 給予一點緩衝時間讓頁面完全載入
            time.sleep(5)

            # 3. 點擊右上角的通知小鈴鐺
            print("正在尋找通知小鈴鐺...")
            # 嘗試點擊鈴鐺圖示 (通常帶有通知數字或鈴鐺 class)
            bell_selector = "nav .fa-bell, .fa-regular.fa-bell, [data-region='notification-popover-container']"
            if page.locator(bell_selector).count() > 0:
                page.locator(bell_selector).first.click()
                time.sleep(2) # 等待通知彈窗展開

            # 4. 抓取通知內容
            print("正在解析通知清單...")
            # 抓取通知選單中的文字內容
            notification_items = page.locator(".content-item, .notification-message, [data-region='content-item']").all_inner_texts()
            
            if not notification_items:
                # 備用方案：如果找不到特定 class，直接抓取頁面上右側通知彈窗的文字
                print("嘗試使用備用選擇器抓取通知...")
                notification_items = page.locator("div.popover-body, .popover-region-content").all_inner_texts()

            if notification_items:
                # 清理並組合訊息
                notif_text = "\n-------------------\n".join([item.strip() for item in notification_items[:5]])
                message = f"【逢甲 iLearn - 最新通知提醒】\n\n{notif_text}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                print("目前沒有抓到新的通知內容。")
                send_to_line("【逢甲 iLearn 提醒】目前沒有檢測到新的通知訊息。")

        except Exception as e:
            print(f"爬蟲執行發生錯誤: {e}")
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()