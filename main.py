import os
import requests
from datetime import datetime, timedelta

# 從 GitHub Secrets 讀取 LINE 資訊
LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

# 你的 iLearn 動態行事曆網址
ICAL_URL = "https://ilearn.fcu.edu.tw/calendar/export_execute.php?userid=172807&authtoken=477c043d7a00f87cad68d5b5ab5a7aecd07b6877&preset_what=all&preset_time=custom"

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

def check_calendar():
    print("正在下載 iLearn 行事曆...")
    response = requests.get(ICAL_URL)
    if response.status_code != 200:
        print("無法下載行事曆資料")
        return

    ics_content = response.text
    
    # 簡單解析 .ics 內容，找出事件
    events = []
    current_summary = None
    
    for line in ics_content.splitlines():
        if line.startswith("SUMMARY:"):
            current_summary = line.replace("SUMMARY:", "")
        elif line.startswith("DTSTART:") and current_summary:
            dt_str = line.replace("DTSTART:", "")
            events.append(f"📌 {current_summary} (時間: {dt_str})")
            current_summary = None

    if events:
        # 取出近期或前幾筆作業
        message = "【逢甲 iLearn 作業與行事曆提醒】\n\n" + "\n".join(events[:10])
        send_to_line(message)
    else:
        print("目前沒有找到行事曆事件。")

if __name__ == "__main__":
    check_calendar()