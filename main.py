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

            # 嘗試多種可能的鈴鐺按鈕選擇器來點擊通知
            print("正在尋找並點擊通知小鈴鐺...")
            bell_clicked = False
            selectors = [
                "a[data-action='toggle-notification-popover']", 
                ".fa-bell", 
                ".popover-region-toggle", 
                "li.nav-item:has(.fa-bell)",
                "[data-region='notification-popover-container'] a"
            ]
            
            for sel in selectors:
                if page.locator(sel).count() > 0:
                    try:
                        page.locator(sel).first.click()
                        print(f"成功點擊選擇器: {sel}")
                        bell_clicked = True
                        time.sleep(3)  # 等待彈窗展開
                        break
                    except Exception as e:
                        print(f"嘗試點擊 {sel} 失敗: {e}")

            if not bell_clicked:
                print("找不到通知鈴鐺按鈕！")

            # 抓取通知選單裡的所有文字
            print("正在解析通知內容...")
            # 擴大範圍抓取所有可能包含通知文字的區塊
            notification_texts = []
            
            # 嘗試抓取 Moodle 通知清單的常見 class
            items = page.locator(".content-item, .notification, .py-2, .list-group-item, [data-region='content-item']").all_inner_texts()
            for item in items:
                cleaned = item.strip()
                if cleaned and cleaned not in notification_texts and len(cleaned) > 5:
                    notification_texts.append(cleaned)

            if notification_texts:
                # 取出前 5 筆最新的通知
                notif_msg = "\n\n-------------------\n\n".join(notification_texts[:5])
                message = f"【逢甲 iLearn - 最新通知提醒】\n\n{notif_msg}"
                send_to_line(message)
                print("已成功將通知推送到 LINE！")
            else:
                print("依然沒有抓到通知文字，改為發送頁面除訊息。")
                send_to_line("【逢甲 iLearn 提醒】爬蟲已登入，但抓取通知區塊時未讀取到文字，請檢查選擇器。")

        except Exception as e:
            print(f"爬蟲執行發生錯誤: {e}")
            send_to_line(f"【逢甲 iLearn 錯誤通知】爬蟲執行失敗: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn_notifications()