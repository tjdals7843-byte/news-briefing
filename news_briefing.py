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
    "법무부",
    "정책기획단",
    "램가"
]
# ==========================================

NAVER_CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ["KAKAO_CLIENT_SECRET"]
PUBLIC_DATA_API_KEY = os.environ["PUBLIC_DATA_API_KEY"]

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
    return response.json().get("access_token")


def get_holidays(year, month):
    """공공데이터포털 공휴일 API"""
    url = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
    params = {
        "serviceKey": PUBLIC_DATA_API_KEY,
        "solYear": year,
        "solMonth": str(month).zfill(2),
        "numOfRows": 50,
        "_type": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", {})
        if not items:
            return set()
        item_list = items.get("item", [])
        if isinstance(item_list, dict):
            item_list = [item_list]
        holidays = set()
        for item in item_list:
            date_str = str(item.get("locdate", ""))
            if date_str:
                holidays.add(datetime.strptime(date_str, "%Y%m%d").date())
        return holidays
    except Exception as e:
        print(f"공휴일 API 오류: {e}")
        return set()


def is_holiday(date):
    """주말 또는 공휴일 여부 확인"""
    if date.weekday() >= 5:  # 토/일
        return True
    holidays = get_holidays(date.year, date.month)
    return date in holidays


def get_collection_range(today):
    """수집 시작일 계산 (연휴 자동 처리)"""
    # 오늘이 공휴일이면 실행 안 함
    if is_holiday(today):
        return None, None, True  # skip=True

    # 어제부터 거슬러 올라가며 마지막 평일 찾기
    check = today - timedelta(days=1)
    while is_holiday(check):
        check -= timedelta(days=1)

    # check = 마지막 평일
    # check 전날도 연속 휴일인지 확인해서 start 결정
    start_day = check  # 마지막 평일 07:00부터

    start_dt = datetime(start_day.year, start_day.month, start_day.day, 7, 0, 0, tzinfo=KST)
    end_dt = datetime(today.year, today.month, today.day, 7, 0, 0, tzinfo=KST)

    return start_dt, end_dt, False


def get_all_news(topic, start_dt, end_dt):
    """start_dt ~ end_dt 사이 기사 전부 수집"""
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

        stop = False
        for item in items:
            pub_date_str = item.get("pubDate", "")
            try:
                pub_dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z").astimezone(KST)
            except Exception:
                continue

            if pub_dt < start_dt:
                stop = True
                break
            if start_dt <= pub_dt <= end_dt:
                all_items.append({
                    "title": clean_text(item.get("title", "")),
                    "link": item.get("originallink") or item.get("link", ""),
                    "pub_date": pub_dt.strftime("%m/%d %H:%M"),
                })

        if stop:
            break

        start += 100
        if start > min(data.get("total", 0), 1000):
            break

    return all_items


def clean_text(text):
    return re.sub(r'<[^>]+>', '', text)\
        .replace('&quot;', '"').replace('&amp;', '&')\
        .replace('&lt;', '<').replace('&gt;', '>').strip()


def generate_html(topic_news, start_dt, end_dt):
    now = datetime.now(KST)
    date_str = now.strftime("%Y년 %m월 %d일")
    total = sum(len(v) for v in topic_news.values())
    period = f"{start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')}"

    sections = ""
    for topic, items in topic_news.items():
        if not items:
            rows = "<tr><td colspan='2' class='empty'>해당 기간 기사 없음</td></tr>"
        else:
            rows = ""
            for item in items:
                rows += f"""
                <tr>
                    <td class='time'>{item['pub_date']}</td>
                    <td class='title'>
                        <a href='{item['link']}' target='_blank'>{item['title']}</a>
                    </td>
                </tr>"""

        sections += f"""
        <div class='section'>
            <div class='section-header'>
                <span class='topic-tag'>{topic}</span>
                <span class='count'>{len(items)}건</span>
            </div>
            <table>{rows}</table>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang='ko'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>📰 뉴스 브리핑 · {date_str}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Noto Sans KR', -apple-system, sans-serif; background: #0f0f1a; color: #e8e8f0; min-height: 100vh; }}

        .hero {{
            background: linear-gradient(135deg, #1a1a3e 0%, #16213e 50%, #0f3460 100%);
            padding: 48px 24px 40px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            position: relative;
            overflow: hidden;
        }}
        .hero::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(ellipse at center, rgba(99,102,241,0.15) 0%, transparent 60%);
            pointer-events: none;
        }}
        .hero-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(99,102,241,0.2);
            border: 1px solid rgba(99,102,241,0.4);
            border-radius: 20px;
            padding: 5px 14px;
            font-size: 12px;
            color: #a5b4fc;
            margin-bottom: 16px;
            letter-spacing: 0.5px;
        }}
        .hero h1 {{
            font-size: clamp(22px, 5vw, 32px);
            font-weight: 900;
            color: #fff;
            margin-bottom: 10px;
            line-height: 1.3;
        }}
        .hero h1 span {{ color: #818cf8; }}
        .hero-sub {{
            font-size: 13px;
            color: rgba(255,255,255,0.5);
            margin-bottom: 24px;
        }}
        .stats {{
            display: inline-flex;
            gap: 24px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 14px 28px;
        }}
        .stat {{ text-align: center; }}
        .stat-num {{ font-size: 24px; font-weight: 900; color: #818cf8; display: block; }}
        .stat-label {{ font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 2px; }}

        .container {{ max-width: 780px; margin: 0 auto; padding: 24px 16px; }}

        .section {{
            background: #1a1a2e;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            margin-bottom: 20px;
            overflow: hidden;
            transition: border-color 0.2s;
        }}
        .section:hover {{ border-color: rgba(99,102,241,0.3); }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: rgba(99,102,241,0.08);
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .topic-tag {{
            font-size: 15px;
            font-weight: 700;
            color: #a5b4fc;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .topic-tag::before {{ content: '#'; color: #6366f1; }}
        .count {{
            font-size: 12px;
            color: #6366f1;
            background: rgba(99,102,241,0.15);
            border: 1px solid rgba(99,102,241,0.3);
            border-radius: 20px;
            padding: 3px 12px;
            font-weight: 600;
        }}

        table {{ width: 100%; border-collapse: collapse; }}
        tr {{ border-bottom: 1px solid rgba(255,255,255,0.04); transition: background 0.15s; }}
        tr:last-child {{ border-bottom: none; }}
        tr:hover {{ background: rgba(99,102,241,0.06); }}
        td {{ padding: 10px 20px; vertical-align: top; }}
        .time {{ color: #4b5563; font-size: 11px; white-space: nowrap; padding-right: 8px; padding-top: 12px; font-variant-numeric: tabular-nums; }}
        .title {{ padding-top: 10px; line-height: 1.6; }}
        .title a {{ color: #d1d5db; text-decoration: none; font-size: 14px; }}
        .title a:hover {{ color: #a5b4fc; }}
        .empty {{ text-align: center; color: #374151; padding: 28px; font-size: 13px; }}

        .footer {{
            text-align: center;
            padding: 32px 24px;
            color: #374151;
            font-size: 12px;
            border-top: 1px solid rgba(255,255,255,0.05);
            margin-top: 8px;
        }}
        .footer strong {{ color: #4b5563; }}
    </style>
</head>
<body>
    <div class='hero'>
        <div class='hero-badge'>⚡ 자동 뉴스 브리핑</div>
        <h1>성민이가 전달하는<br><span>뉴스 소식!</span></h1>
        <div class='hero-sub'>📅 {date_str} &nbsp;·&nbsp; {period}</div>
        <div class='stats'>
            <div class='stat'>
                <span class='stat-num'>{total}</span>
                <div class='stat-label'>총 기사</div>
            </div>
            <div class='stat'>
                <span class='stat-num'>{len(topic_news)}</span>
                <div class='stat-label'>주제</div>
            </div>
        </div>
    </div>
    <div class='container'>
        {sections}
    </div>
    <div class='footer'>
        <strong>법무부 AI TF</strong> · 매일 07:00 자동 업데이트<br>
        기사를 터치하면 원문으로 이동합니다
    </div>
</body>
</html>"""


def send_kakao_text(access_token, topic_news, start_dt, end_dt, page_url):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    now = datetime.now(KST)
    total = sum(len(v) for v in topic_news.values())

    # 수집 기간 표시
    if start_dt.date() == end_dt.date() - timedelta(days=1):
        period_str = f"{start_dt.strftime('%m.%d')} 07:00 ~ {end_dt.strftime('%m.%d')} 07:00"
    else:
        period_str = f"{start_dt.strftime('%m.%d')} ~ {end_dt.strftime('%m.%d')} 07:00"

    # 이모지 뱃지
    topic_emojis = ["🔵", "🟢", "🟡", "🟠", "🔴"]

    lines = [
        "╔══════════════════════╗",
        "║  📰 오늘의 뉴스 브리핑  ║",
        "╚══════════════════════╝",
        "",
        f"🗓  {now.strftime('%Y.%m.%d')}  |  {period_str}",
        "",
        "─────────────────────────",
    ]

    for i, (topic, items) in enumerate(topic_news.items()):
        emoji = topic_emojis[i % len(topic_emojis)]
        bar = "█" * min(len(items) // 10 + 1, 8)
        lines.append(f"{emoji}  {topic}")
        lines.append(f"    {bar}  {len(items)}건")

    lines += [
        "─────────────────────────",
        f"📊  총 {total}건 수집 완료",
        "",
        "👇  전체 기사 보기",
        f"{page_url}",
    ]

    msg = "\n".join(lines)

    template = {
        "object_type": "text",
        "text": msg,
        "link": {
            "web_url": page_url,
            "mobile_web_url": page_url
        }
    }

    data = {"template_object": json.dumps(template, ensure_ascii=False)}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code, response.text


def main():
    now = datetime.now(KST)
    today = now.date()

    # 공휴일/주말 체크
    print(f"오늘 날짜: {today} ({['월','화','수','목','금','토','일'][today.weekday()]})")
    start_dt, end_dt, skip = get_collection_range(today)

    if skip:
        print("오늘은 공휴일/주말입니다. 브리핑을 건너뜁니다.")
        return

    print(f"수집 기간: {start_dt.strftime('%m/%d %H:%M')} ~ {end_dt.strftime('%m/%d %H:%M')}")

    # 토큰 갱신
    print("Access Token 갱신 중...")
    access_token = refresh_access_token()
    if not access_token:
        print("토큰 갱신 실패!")
        return
    print("토큰 갱신 완료")

    # 뉴스 수집
    topic_news = {}
    for topic in NEWS_TOPICS:
        print(f"【{topic}】 수집 중...")
        items = get_all_news(topic, start_dt, end_dt)
        topic_news[topic] = items
        print(f"  → {len(items)}건")

    # HTML 생성
    html = generate_html(topic_news, start_dt, end_dt)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML 생성 완료!")

    # 카카오톡 전송
    page_url = "https://tjdals7843-byte.github.io/news-briefing/"
    status, result = send_kakao_text(access_token, topic_news, start_dt, end_dt, page_url)
    if status == 200:
        print("카카오톡 전송 완료!")
    else:
        print(f"카카오톡 전송 실패: {status} / {result}")


if __name__ == "__main__":
    main()
