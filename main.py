import os
import requests
from datetime import datetime, timezone, timedelta

# 從 GitHub Secrets 讀取 LINE 資訊
LINE_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
USER_ID = os.environ.get("LINE_USER_ID")

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

def format_time(dt_str):
    try:
        # 移除結尾的 'Z' 並解析時間字串
        clean_str = dt_str.strip().rstrip('Z')
        dt_utc = datetime.strptime(clean_str, "%Y%m%dT%H%M%S")
        
        # 設定為 UTC 時區，並轉換成台灣時間 (UTC+8)
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_tw = dt_utc.astimezone(timezone(timedelta(hours=8)))
        
        # 轉成清楚好讀的格式，例如: 2026-11-07 23:59
        return dt_tw.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # 如果格式解析失敗，就原樣回傳
        return dt_str

def check_calendar():
    print("正在下載 iLearn 行事曆...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(ICAL_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"無法下載行事曆資料，狀態碼: {response.status_code}")
            return

        ics_content = response.text
        events = []
        current_summary = None
        
        for line in ics_content.splitlines():
            if line.startswith("SUMMARY:"):
                current_summary = line.replace("SUMMARY:", "")
            elif line.startswith("DTSTART:") and current_summary:
                raw_dt = line.replace("DTSTART:", "")
                formatted_dt = format_time(raw_dt)
                events.append(f"📌 {current_summary}\n   ⏱ 截止: {formatted_dt}")
                current_summary = None

        if events:
            message = "【逢甲 iLearn 作業與行事曆提醒】\n\n" + "\n\n".join(events[:8])
            send_to_line(message)
            print("已成功發送 LINE 通知！")
        else:
            print("目前沒有找到行事曆事件。")

    except Exception as e:
        print(f"連線或解析發生錯誤: {e}")

if __name__ == "__main__":
    check_calendar()