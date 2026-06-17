import requests
import os
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

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
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ["KAKAO_CLIENT_SECRET"]

KST = timezone(timedelta(hours=9))


def refresh_access_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "client_secret": KAKAO_CLIENT_SECRET,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }
    response = requests.post(url, data=data)
    result = response.json()
    print(f"토큰 갱신 완료")
    return result.get("access_token")


def get_all_news(topic):
    """전날 07:00 ~ 당일 07:00 기사 전부 수집"""
    now = datetime.now(KST)
    end_dt = now.replace(hour=7, minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=1)

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    all_items = []
    start = 1

    while True:
        params = {
            "query": topic,
            "display": 100,
            "start": start,
            "sort": "date"
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        for item in items:
            pub_date_str = item.get("pubDate", "")
            try:
                pub_dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").astimezone(KST)
            except:
                continue

            if pub_dt < start_dt:
                return all_items  # 시간 범위 벗어나면 중단
            if pub_dt <= end_dt:
                all_items.append({
                    "title": clean_text(item.get("title", "")),
                    "link": item.get("originallink") or item.get("link", ""),
                    "pub_date": pub_dt.strftime("%H:%M"),
                    "description": clean_text(item.get("description", ""))
                })

        start += 100
        if start > data.get("total", 0):
            break

    return all_items


def clean_text(text):
    return re.sub(r'<[^>]+>', '', text)\
        .replace('&quot;', '"').replace('&amp;', '&')\
        .replace('&lt;', '<').replace('&gt;', '>').strip()


def generate_html(topic_news):
    """뉴스 모아보기 HTML 페이지 생성"""
    now = datetime.now(KST)
    date_str = now.strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in topic_news.values())

    # 주제별 섹션 생성
    sections = ""
    for topic, items in topic_news.items():
        if not items:
            rows = "<tr><td colspan='3' style='text-align:center;color:#888;padding:20px;'>해당 시간대 기사 없음</td></tr>"
        else:
            rows = ""
            for item in items:
                rows += f"""
                <tr>
                    <td style='color:#888;font-size:12px;white-space:nowrap;padding:8px 12px;'>{item['pub_date']}</td>
                    <td style='padding:8px 12px;'>
                        <a href='{item['link']}' target='_blank' style='color:#1a1a1a;text-decoration:none;line-height:1.5;'>
                            {item['title']}
                        </a>
                    </td>
                </tr>"""

        sections += f"""
        <div class='section'>
            <div class='section-header'>
                <span class='topic-tag'>{topic}</span>
                <span class='count'>{len(items)}건</span>
            </div>
            <table width='100%' cellspacing='0' cellpadding='0'>
                {rows}
            </table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang='ko'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>성민이가 전달하는 뉴스 소식 - {date_str}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6f8; color: #1a1a1a; }}
        .header {{ background: linear-gradient(135deg, #3d5af1, #7b2ff7); color: white; padding: 28px 20px; text-align: center; }}
        .header h1 {{ font-size: 20px; font-weight: 700; margin-bottom: 6px; }}
        .header p {{ font-size: 13px; opacity: 0.85; }}
        .badge {{ display: inline-block; background: rgba(255,255,255,0.2); border-radius: 20px; padding: 4px 14px; font-size: 12px; margin-top: 10px; }}
        .container {{ max-width: 720px; margin: 0 auto; padding: 16px; }}
        .section {{ background: white; border-radius: 12px; margin-bottom: 16px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
        .section-header {{ display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #f0f0f0; }}
        .topic-tag {{ font-size: 15px; font-weight: 700; color: #3d5af1; }}
        .count {{ font-size: 12px; color: #888; background: #f0f0f0; border-radius: 10px; padding: 2px 10px; }}
        table {{ border-collapse: collapse; }}
        tr {{ border-bottom: 1px solid #f5f5f5; }}
        tr:last-child {{ border-bottom: none; }}
        tr:hover {{ background: #fafafa; }}
        a:hover {{ color: #3d5af1 !important; text-decoration: underline !important; }}
        .footer {{ text-align: center; padding: 20px; color: #aaa; font-size: 12px; }}
    </style>
</head>
<body>
    <div class='header'>
        <h1>📰 성민이가 전달하는 뉴스 소식!</h1>
        <p>{date_str} · 전일 07:00 ~ 당일 07:00</p>
        <div class='badge'>총 {total}건</div>
    </div>
    <div class='container'>
        {sections}
        <div class='footer'>법무부 AI TF · 자동 생성된 뉴스 브리핑</div>
    </div>
</body>
</html>"""
    return html


def send_kakao_summary(access_token, topic_news, page_url):
    """카카오톡으로 요약 + 링크 전송"""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    now = datetime.now(KST)
    date_str = now.strftime("%Y.%m.%d")
    total = sum(len(v) for v in topic_news.values())

    summary = f"📰 성민이가 전달하는 뉴스 소식!\n"
    summary += f"{date_str} 07:00 기준\n"
    summary += "─" * 20 + "\n"
    for topic, items in topic_news.items():
        summary += f"📌 {topic}: {len(items)}건\n"
    summary += "─" * 20 + "\n"
    summary += f"총 {total}건"

    template = {
        "object_type": "feed",
        "content": {
            "title": "📰 성민이가 전달하는 뉴스 소식!",
            "description": summary,
            "link": {
                "web_url": page_url,
                "mobile_web_url": page_url
            }
        },
        "buttons": [
            {
                "title": "뉴스 모아보기",
                "link": {
                    "web_url": page_url,
                    "mobile_web_url": page_url
                }
            }
        ]
    }

    data = {"template_object": json.dumps(template, ensure_ascii=False)}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code, response.text


def main():
    # 1. Access Token 갱신
    print("Access Token 갱신 중...")
    access_token = refresh_access_token()
    if not access_token:
        print("토큰 갱신 실패!")
        return

    # 2. 주제별 뉴스 수집
    topic_news = {}
    for topic in NEWS_TOPICS:
        print(f"【{topic}】 뉴스 수집 중...")
        items = get_all_news(topic)
        topic_news[topic] = items
        print(f"  → {len(items)}건 수집")

    # 3. HTML 생성 및 저장
    html = generate_html(topic_news)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML 생성 완료!")

    # 4. 카카오톡 전송
    github_username = os.environ.get("GITHUB_USERNAME", "")
    page_url = f"https://{github_username}.github.io/news-briefing/"
    status, result = send_kakao_summary(access_token, topic_news, page_url)
    if status == 200:
        print("카카오톡 전송 완료!")
    else:
        print(f"카카오톡 전송 실패: {status} / {result}")


if __name__ == "__main__":
    main()
