import os
import time
import requests
from openai import OpenAI
from playwright.sync_api import sync_playwright

LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")
USERNAME = os.environ.get("ILEARN_USERNAME")
PASSWORD = os.environ.get("ILEARN_PASSWORD")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # 記得在 GitHub Secrets 設定

# 初始化 OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)

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

def summarize_with_chatgpt(notifications_text):
    """讓 ChatGPT 幫忙整理與摘要通知內容"""
    try:
        print("正在透過 ChatGPT 整理通知內容...")
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 便宜又快速的模型
            messages=[
                {
                    "role": "system",
                    "content": "你是一個大學生智慧助理。請幫忙將以下的 iLearn 學校通知內容進行精簡摘要，萃取出關鍵的作業繳交期限、考試資訊或重要公告。排版要乾淨易讀，適合在 LINE 上閱讀。"
                },
                {
                    "role": "user",
                    "content": notifications_text
                }
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ChatGPT 處理失敗: {e}")
        # 如果 ChatGPT 失敗，至少回傳原本抓到的文字
        return notifications_text

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

            # 1. 點擊右上角的「登入」按鈕
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

            # 5. 點擊右上角的小鈴鐺
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
                raw_text = "\n".join(notification_texts[:5])
                
                # 呼叫 ChatGPT 進行智慧整理
                final_content = summarize_with_chatgpt(raw_text)
                
                message = f"🤖 【iLearn 智慧助理通知】\n\n{final_content}"
                send_to_line(message)
                print("已成功將 AI 整理後的通知推送到 LINE！")
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