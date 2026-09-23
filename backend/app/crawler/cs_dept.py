"""소프트웨어학부 공지사항(cs.kw.ac.kr) 파서.

대학 공지와 달리 고정 공지 개념이 없고, 카테고리 컬럼도 없다.
제목 앞에 붙는 "공지", "[공지]" 는 작성자가 직접 타이핑한 글자라 마크업이 아니다.
"""

from __future__ import annotations

import datetime as dt
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from app.crawler.text import html_to_text
from app.crawler.types import AttachmentRef, Detail, ListItem

BASE = "https://cs.kw.ac.kr"
# openresty 앞단이 짜게 잡혀 있다. 0.4초로 44요청을 쏘자 10분 넘게 IP 가 막혔다.
# 공지가 페이지당 10건뿐이라 느려도 실제로 손해가 없다.
REQUEST_DELAY = 2.5
LIST_URL = BASE + "/department_office/lecture.php?admin_mode=list&page={page}&site_type=3"

# 정상적인 img 에 속성이 수십 개 붙는 일은 없다.
_MAX_ATTRS = 50

_DATE = re.compile(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})")
_AUTHOR = re.compile(r"작\s*성\s*자\s*:\s*(\S+)")
_POSTED = re.compile(r"작\s*성\s*일\s*:\s*(\d{4})[-.](\d{1,2})[-.](\d{1,2})")


def page_url(page: int) -> str:
    return LIST_URL.format(page=page)


def parse_list(html: str) -> list[ListItem]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.board-list")
    if table is None:
        raise ValueError("목록 테이블(table.board-list)을 찾지 못했다")

    items: list[ListItem] = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td")
        anchor = tr.select_one("td.subject a[href]")
        if anchor is None or len(cells) < 4:
            continue

        # 표시 번호(77)가 아니라 URL 의 no(3417)가 고유 ID 다.
        no = parse_qs(urlparse(anchor["href"]).query).get("no", [None])[0]
        if not no:
            continue

        date = _DATE.search(cells[2].get_text(strip=True))
        if date is None:
            continue

        views = cells[3].get_text(strip=True).replace(",", "")
        items.append(
            ListItem(
                external_id=no,
                url=urljoin(BASE, anchor["href"]),
                title=" ".join(anchor.get_text(" ", strip=True).split()),
                posted_at=dt.date(int(date[1]), int(date[2]), int(date[3])),
                view_count=int(views) if views.isdigit() else 0,
            )
        )
    return items


def parse_detail(html: str, *, page_url_: str | None = None) -> Detail:
    soup = BeautifulSoup(html, "lxml")
    view = soup.select_one("table.board-view")
    if view is None:
        raise ValueError("상세 테이블(table.board-view)을 찾지 못했다")

    base = page_url_ or BASE + "/department_office/lecture.php"

    attachments = [
        AttachmentRef(
            filename=re.sub(r"^\d+\.\s*", "", " ".join(a.get_text(" ", strip=True).split())),
            url=urljoin(base, a["href"]),
        )
        for a in view.select("a[href*='download.php']")
        if a.get_text(strip=True)
    ]

    body = view.select_one("td.view_td")
    images: list[str] = []
    if body is not None:
        _strip_inline_images(body, base, images)

    body_html = str(body) if body is not None else ""
    return Detail(
        body_html=body_html,
        body_text=html_to_text(body_html),
        attachments=attachments,
        inline_image_urls=images,
    )


def _strip_inline_images(body, base: str, images: list[str]) -> None:
    """본문에 박힌 base64 이미지를 걷어낸다.

    이 게시판은 포스터를 `<img src=data:image/png;base64,...>` 로 심는데,
    따옴표가 없어서 파서가 값을 속성 여러 개로 쪼개 버린다. base64 덩어리가
    속성 *이름* 자리에 들어가므로 src 만 비워서는 지워지지 않는다.
    한 장에 9MB 가 넘고 같은 이미지가 첨부로도 올라오니 통째로 버린다.

    실제로 쪼개진 모습: base64 한 덩어리가 100자 남짓 조각 19만 개의
    *속성 이름* 으로 흩어지고 src 값은 빈 문자열이 된다. 그래서 속성 개수로 잡는다.
    """
    for img in body.find_all("img"):
        src = img.get("src", "")
        if src.startswith("data:") or len(img.attrs) > _MAX_ATTRS:
            img.decompose()
        elif src:
            images.append(urljoin(base, src))


def parse_author(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    view = soup.select_one("table.board-view")
    if view is None:
        return None
    m = _AUTHOR.search(" ".join(view.get_text(" ", strip=True).split()))
    return m[1] if m else None
