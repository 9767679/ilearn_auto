import os
import requests
from playwright.sync_api import sync_playwright

# 從 GitHub Secrets 讀取敏感資訊
USERNAME = os.environ.get("ILEARN_USERNAME")
PASSWORD = os.environ.get("ILEARN_PASSWORD")
LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

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

def check_ilearn():
    with sync_playwright() as p:
        # 啟動無頭瀏覽器（在 GitHub Actions 雲端上執行時必須是 headless=True）
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("正在前往 iLearn 登入頁面...")
            page.goto("https://ilearn.fcu.edu.tw/")
            
            # 點擊登入按鈕或導向至學校 SSO 登入頁面
            # （需根據逢甲實際登入按鈕調整，通常點擊登入會導向至學校授權頁）
            # page.click("text=登入") # 依實際網頁結構調整
            
            # 輸入帳號密碼 (需對應學校 SSO 輸入框的 HTML id 或 name)
            # page.fill("input[name='username']", USERNAME)
            # page.fill("input[name='password']", PASSWORD)
            # page.click("button[type='submit']")

            # 等待登入成功並跳轉回首頁
            page.wait_for_url("https://ilearn.fcu.edu.tw/my/", timeout=30000)
            print("登入成功！正在尋找未完成作業...")

            # 抓取作業清單邏輯 (需根據 iLearn 未繳交作業區塊的 CSS Selector 調整)
            # 這裡示範抓取特定區塊的文字
            assignments = []
            # items = page.locator(".event-item").all()
            # for item in items:
            #     assignments.append(item.inner_text())

            if assignments:
                message = "【逢甲 iLearn 作業提醒】\n" + "\n".join(assignments)
                send_to_line(message)
            else:
                print("目前沒有新作業或快到期的項目。")

        except Exception as e:
            print(f"執行過程中發生錯誤: {e}")
            send_to_line(f"⚠️ iLearn 自動爬蟲發生錯誤，請檢查 GitHub 記錄。")
        
        finally:
            browser.close()

if __name__ == "__main__":
    check_ilearn()