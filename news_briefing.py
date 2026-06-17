import requests
import os
from datetime import datetime, timedelta

# ==========================================
# 뉴스 주제 설정 (여기만 바꾸면 됩니다!)
# ==========================================
NEWS_TOPICS = [
    "AI 인공지능",
    "법무부",
    "디지털정부"
]
# ==========================================

NAVER_CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]
KAKAO_ACCESS_TOKEN = os.environ["KAKAO_ACCESS_TOKEN"]

def get_news(topic):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": topic,
        "display": 3,
        "sort": "date"
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("items", [])

def clean_text(text):
    import re
    return re.sub(r'<[^>]+>', '', text).replace('&quot;', '"').replace('&amp;', '&')

def send_kakao(message):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {KAKAO_ACCESS_TOKEN}"}
    data = {
        "template_object": '{"object_type":"text","text":"' + message.replace('"', '\\"').replace('\n', '\\n') + '","link":{"web_url":"https://news.naver.com"}}'
    }
    response = requests.post(url, headers=headers, data=data)
    return response.status_code

def main():
    now = datetime.now()
    msg = f"📰 AI 뉴스 브리핑\n{now.strftime('%Y년 %m월 %d일')}\n"
    msg += "=" * 20 + "\n"

    for topic in NEWS_TOPICS:
        msg += f"\n【{topic}】\n"
        items = get_news(topic)
        for i, item in enumerate(items[:2], 1):
            title = clean_text(item['title'])
            msg += f"{i}. {title}\n"

    msg += "\n" + "=" * 20
    msg += "\n법무부 AI TF 자동발송"

    # 200자 제한으로 분할 전송
    chunks = [msg[i:i+190] for i in range(0, len(msg), 190)]
    for chunk in chunks:
        send_kakao(chunk)
        print(f"전송완료: {chunk[:30]}...")

if __name__ == "__main__":
    main()
