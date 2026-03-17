import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime

BASE_URL = "https://www.wevity.com"
IT_URL = "https://www.wevity.com/?c=find&s=1&gub=1&cidx=20"

def scrape_contests(max_pages=3):
    scraper = cloudscraper.create_scraper()
    contests = []
    for page in range(1, max_pages + 1):
        url = f"{IT_URL}&gp={page}"
        res = scraper.get(url, timeout=15)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select("ul.list > li:not(.top)")
        if not items:
            break

        for item in items:
            try:
                title_tag = item.select_one("div.tit > a")
                if not title_tag:
                    continue
                for badge in title_tag.find_all("span"):
                    badge.decompose()
                title = title_tag.get_text(strip=True)

                href = title_tag.get("href", "")
                if href.startswith("?"):
                    href = BASE_URL + "/" + href

                organizer = item.select_one("div.organ")
                organizer = organizer.get_text(strip=True) if organizer else ""

                day_div = item.select_one("div.day")
                status_span = day_div.select_one("span.dday") if day_div else None
                status = status_span.get_text(strip=True) if status_span else ""
                if status_span:
                    status_span.decompose()
                deadline = day_div.get_text(strip=True) if day_div else ""

                if title:
                    contests.append({
                        "title": title,
                        "url": href,
                        "deadline": deadline,
                        "organizer": organizer,
                        "status": status,
                    })
            except Exception:
                continue

    return contests


def generate_html(contests):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    count = len(contests)

    rows = ""
    for i, c in enumerate(contests, 1):
        status_color = {
            "접수중": "#2ecc71",
            "마감임박": "#e74c3c",
            "접수예정": "#3498db",
            "마감": "#999",
        }.get(c["status"], "#555")

        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="{c['url']}" target="_blank">{c['title']}</a></td>
            <td>{c['organizer']}</td>
            <td>{c['deadline']}</td>
            <td><span style="color:{status_color}; font-weight:bold;">{c['status']}</span></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IT 공모전 목록</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); padding: 30px; }}
        h1 {{ font-size: 1.6rem; color: #2c3e50; margin-bottom: 6px; }}
        .meta {{ color: #888; font-size: 0.9rem; margin-bottom: 20px; }}
        .count {{ background: #3498db; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.85rem; margin-left: 8px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th {{ background: #2c3e50; color: white; padding: 10px 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; vertical-align: middle; }}
        tr:hover td {{ background: #f0f4ff; }}
        a {{ color: #2980b9; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ text-align: center; margin-top: 20px; color: #aaa; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💻 IT 공모전 목록 <span class="count">{count}건</span></h1>
        <p class="meta">📅 마지막 업데이트: {today} &nbsp;|&nbsp; 출처: <a href="https://www.wevity.com" target="_blank">위비티(wevity.com)</a></p>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>공모전명</th>
                    <th>주최기관</th>
                    <th>마감</th>
                    <th>상태</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="5" style="text-align:center;padding:30px;color:#aaa;">데이터를 불러오는 중 오류가 발생했습니다.</td></tr>'}
            </tbody>
        </table>
        <p class="footer">매일 자동으로 업데이트됩니다.</p>
    </div>
</body>
</html>"""
    return html


if __name__ == "__main__":
    print("공모전 정보 수집 중...")
    contests = scrape_contests(max_pages=3)
    print(f"{len(contests)}개 공모전 수집 완료")

    html = generate_html(contests)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html 생성 완료")
