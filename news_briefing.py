import requests
import os
import json
import re
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


def refresh_access_token():
    """Refresh Token으로 새 Access Token 발급"""
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


def get_news(topic):
    """네이버 뉴스 API로 최신 뉴스 검색"""
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


def get_thumbnail(article_url):
    """기사 URL에서 og:image 썸네일 추출"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(article_url, headers=headers, timeout=5)
        og_image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', resp.text)
        if og_image:
            return og_image.group(1)
    except:
        pass
    return None


def clean_text(text):
    """HTML 태그 제거"""
    return re.sub(r'<[^>]+>', '', text)\
        .replace('&quot;', '"').replace('&amp;', '&')\
        .replace('&lt;', '<').replace('&gt;', '>').strip()


def send_kakao_list(access_token, topic, items):
    """카카오 list 템플릿으로 전송"""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}

    contents = []
    for item in items[:3]:
        title = clean_text(item['title'])
        link = item.get('originallink') or item.get('link', 'https://news.naver.com')

        # 썸네일 이미지 추출 시도
        thumbnail = get_thumbnail(link)

        content = {
            "title": title,
            "description": " ",
            "link": {
                "web_url": link,
                "mobile_web_url": link
            }
        }

        # 이미지 있으면 추가
        if thumbnail:
            content["image_url"] = thumbnail
            content["image_width"] = 200
            content["image_height"] = 200

        contents.append(content)

    naver_search_url = f"https://search.naver.com/search.naver?where=news&query={quote(topic)}"

    template = {
        "object_type": "list",
        "header_title": "성민이가 전달하는 뉴스 소식!",
        "header_link": {
            "web_url": naver_search_url,
            "mobile_web_url": naver_search_url
        },
        "contents": contents,
        "buttons": [
            {
                "title": f"【{topic}】 뉴스 더보기",
                "link": {
                    "web_url": naver_search_url,
                    "mobile_web_url": naver_search_url
                }
            }
        ]
    }

    data = {"template_object": json.dumps(template, ensure_ascii=False)}
    response = requests.post(url, headers=headers, data=data)
    return response.status_code, response.text


def main():
    # 1. Access Token 자동 갱신
    print("Access Token 갱신 중...")
    access_token = refresh_access_token()
    if not access_token:
        print("토큰 갱신 실패!")
        return

    # 2. 주제별 뉴스 수집 및 전송
    for topic in NEWS_TOPICS:
        print(f"\n【{topic}】 뉴스 수집 중...")
        items = get_news(topic)

        if not items:
            print(f"【{topic}】 뉴스 없음, 건너뜀")
            continue

        status, result = send_kakao_list(access_token, topic, items)
        if status == 200:
            print(f"【{topic}】 전송 완료!")
        else:
            print(f"【{topic}】 전송 실패: {status} / {result}")


if __name__ == "__main__":
    main()
