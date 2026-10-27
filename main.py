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
        
        # 設定台灣時區 (UTC+8)
        tw_timezone = timezone(timedelta(hours=8))
        now_tw = datetime.now(tw_timezone)
        end_time = now_tw + timedelta(days=7) # 計算 7 天後的的時間
        
        for line in ics_content.splitlines():
            if line.startswith("SUMMARY:"):
                current_summary = line.replace("SUMMARY:", "")
            elif line.startswith("DTSTART:") and current_summary:
                raw_dt = line.replace("DTSTART:", "")
                try:
                    clean_str = raw_dt.strip().rstrip('Z')
                    dt_utc = datetime.strptime(clean_str, "%Y%m%dT%H%M%S")
                    dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    dt_tw = dt_utc.astimezone(tw_timezone)
                    
                    # 判斷是否介於「現在」到「未來 7 天內」
                    if now_tw <= dt_tw <= end_time:
                        events.append({
                            "summary": current_summary,
                            "time": dt_tw,
                            "formatted_time": dt_tw.strftime("%Y-%m-%d %H:%M")
                        })
                except Exception as e:
                    print(f"時間解析失敗: {e}")
                
                current_summary = None

        # 依照時間先後順序排序（最近要交的排最前面）
        events.sort(key=lambda x: x["time"])

        if events:
            event_strings = [f"📌 {e['summary']}\n   ⏱ 截止: {e['formatted_time']}" for e in events]
            message = "【逢甲 iLearn - 未來 7 天作業提醒】\n\n" + "\n\n".join(event_strings)
            send_to_line(message)
            print("已成功發送 LINE 通知！")
        else:
            print("未來 7 天內沒有找到行事曆事件。")
            # 如果希望這期間沒作業時也讓 LINE 收到「目前無作業」的訊息，可以把下面這行取消註解
            # send_to_line("【逢甲 iLearn 提醒】太棒了！未來 7 天內沒有檢測到新的作業或行事曆事件 🎉")

    except Exception as e:
        print(f"連線或解析發生錯誤: {e}")

if __name__ == "__main__":
    check_calendar()