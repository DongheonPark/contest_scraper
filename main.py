import re
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

BASE_URL = "https://www.wevity.com"
IT_URL = "https://www.wevity.com/?c=find&s=1&gub=1&cidx=20"
EXPIRE_DAYS = 30  # 마감 후 N일 지나면 목록에서 제거

def fetch_poster(scraper, detail_url):
    try:
        res = scraper.get(detail_url, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        img = soup.select_one("div.thumb img")
        if img and img.get("src"):
            src = img["src"]
            return BASE_URL + src if src.startswith("/") else src
    except Exception:
        pass
    return ""

def parse_dday(text):
    """D-20 → -20 (남은 일수), D+3 → 3 (마감 후 경과일)"""
    text = text.strip()
    m = re.search(r'D[+\-](\d+)', text)
    if not m:
        return None
    days = int(m.group(1))
    return days if '+' in text else -days

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

                # 마감 후 EXPIRE_DAYS일 초과 시 제외
                dday = parse_dday(deadline)
                if dday is not None and dday > EXPIRE_DAYS:
                    continue

                poster = fetch_poster(scraper, href)

                if title:
                    contests.append({
                        "title": title,
                        "url": href,
                        "deadline": deadline,
                        "organizer": organizer,
                        "status": status,
                        "poster": poster,
                    })
            except Exception:
                continue

    order = {"마감임박": 0, "접수중": 1, "접수예정": 2, "마감": 3}
    contests.sort(key=lambda c: order.get(c["status"], 9))
    return contests


def generate_html(contests):
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M (KST)")
    count = len(contests)

    cards = ""
    for c in contests:
        status_color = {
            "접수중": "#2ecc71",
            "마감임박": "#e74c3c",
            "접수예정": "#3498db",
            "마감": "#999",
        }.get(c["status"], "#555")

        poster_html = f'<img src="{c["poster"]}" alt="포스터">' if c["poster"] else '<div class="no-img">이미지 없음</div>'

        cards += f"""
        <a href="{c['url']}" target="_blank" class="card" data-status="{c['status']}">
            <div class="poster">{poster_html}</div>
            <div class="info">
                <div class="title">{c['title']}</div>
                <div class="organizer">{c['organizer']}</div>
                <div class="bottom">
                    <span class="deadline">{c['deadline']}</span>
                    <span class="status" style="color:{status_color}">{c['status']}</span>
                </div>
            </div>
        </a>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IT 공모전 목록</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #333; padding: 24px; }}
        .header {{ max-width: 1100px; margin: 0 auto 16px; }}
        h1 {{ font-size: 1.6rem; color: #2c3e50; margin-bottom: 6px; }}
        .count {{ background: #3498db; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.85rem; margin-left: 8px; }}
        .meta {{ color: #888; font-size: 0.9rem; margin-bottom: 12px; }}
        .meta a {{ color: #3498db; text-decoration: none; }}
        .filter-bar {{ max-width: 1100px; margin: 0 auto 16px; display: flex; align-items: center; gap: 10px; }}
        .filter-bar label {{ font-size: 0.9rem; color: #555; }}
        .filter-bar select {{ padding: 6px 12px; border-radius: 8px; border: 1px solid #ccc; font-size: 0.9rem; cursor: pointer; }}
        .filter-count {{ font-size: 0.85rem; color: #888; }}
        .grid {{ max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }}
        .card {{ background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; text-decoration: none; color: inherit; transition: transform 0.2s, box-shadow 0.2s; flex-direction: column; display: none; }}
        .card.visible {{ display: flex; }}
        .card:hover {{ transform: translateY(-4px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }}
        .poster {{ width: 100%; aspect-ratio: 3/4; overflow: hidden; background: #eee; }}
        .poster img {{ width: 100%; height: 100%; object-fit: cover; }}
        .no-img {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 0.85rem; }}
        .info {{ padding: 12px; flex: 1; display: flex; flex-direction: column; gap: 6px; }}
        .title {{ font-size: 0.88rem; font-weight: 600; line-height: 1.4; color: #2c3e50; }}
        .organizer {{ font-size: 0.78rem; color: #888; }}
        .bottom {{ margin-top: auto; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; }}
        .deadline {{ color: #555; }}
        .status {{ font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 30px; color: #aaa; font-size: 0.8rem; }}
        .pagination {{ max-width: 1100px; margin: 24px auto 0; display: flex; justify-content: center; align-items: center; gap: 12px; }}
        .pagination button {{ padding: 8px 16px; border: none; border-radius: 8px; background: #ddd; color: #555; font-size: 1.1rem; cursor: pointer; transition: background 0.2s; }}
        .pagination button:hover:not(:disabled) {{ background: #c5d8e8; }}
        .pagination button:disabled {{ opacity: 0.3; cursor: default; }}
        .pagination .page-info {{ font-size: 0.9rem; color: #555; min-width: 80px; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>💻 IT 공모전 목록 <span class="count" id="totalCount">{count}건</span></h1>
        <p class="meta">📅 마지막 업데이트: {today} &nbsp;|&nbsp; 출처: <a href="https://www.wevity.com" target="_blank">위비티(wevity.com)</a></p>
    </div>
    <div class="filter-bar">
        <label for="statusFilter">상태</label>
        <select id="statusFilter" onchange="applyFilter()">
            <option value="all">전체</option>
            <option value="접수중">접수중</option>
            <option value="마감임박">마감임박</option>
            <option value="접수예정">접수예정</option>
            <option value="마감">마감</option>
        </select>
        <span class="filter-count" id="filterCount"></span>
    </div>
    <div class="grid" id="grid">
        {cards if cards else '<p style="color:#aaa;text-align:center;">데이터를 불러오는 중 오류가 발생했습니다.</p>'}
    </div>
    <div class="pagination" id="pagination"></div>
    <p class="footer">매일 자동으로 업데이트됩니다.</p>
    <script>
        const PER_PAGE = 30;
        const allCards = Array.from(document.querySelectorAll('.card'));
        let filteredCards = [...allCards];
        let current = 1;

        const pagination = document.getElementById('pagination');
        const prevBtn = document.createElement('button');
        const nextBtn = document.createElement('button');
        const pageInfo = document.createElement('span');
        prevBtn.textContent = '◀';
        nextBtn.textContent = '▶';
        pageInfo.className = 'page-info';
        pagination.append(prevBtn, pageInfo, nextBtn);

        function applyFilter() {{
            const filter = document.getElementById('statusFilter').value;
            filteredCards = filter === 'all'
                ? [...allCards]
                : allCards.filter(c => c.dataset.status === filter);
            current = 1;
            document.getElementById('totalCount').textContent = filteredCards.length + '건';
            const filterCount = document.getElementById('filterCount');
            filterCount.textContent = filter === 'all' ? '' : `(전체 ${{allCards.length}}건 중 ${{filteredCards.length}}건)`;
            render();
        }}

        function render() {{
            const totalPages = Math.max(1, Math.ceil(filteredCards.length / PER_PAGE));
            allCards.forEach(c => c.classList.remove('visible'));
            filteredCards.slice((current - 1) * PER_PAGE, current * PER_PAGE).forEach(c => c.classList.add('visible'));
            pageInfo.textContent = current + ' / ' + totalPages;
            prevBtn.disabled = current === 1;
            nextBtn.disabled = current === totalPages;
            window.scrollTo({{top: 0, behavior: 'smooth'}});
        }}

        prevBtn.onclick = () => {{ current--; render(); }};
        nextBtn.onclick = () => {{ current++; render(); }};
        render();
    </script>
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
