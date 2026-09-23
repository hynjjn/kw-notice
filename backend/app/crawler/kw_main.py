"""광운대학교 공지사항(www.kw.ac.kr) 파서."""

from __future__ import annotations

import datetime as dt
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.crawler.text import html_to_text
from app.crawler.types import AttachmentRef, Detail, ListItem

BASE = "https://www.kw.ac.kr"
# 0.4초로 78건을 연속 수집해도 문제가 없었다.
REQUEST_DELAY = 0.4
LIST_URL = (
    BASE + "/ko/life/notice.jsp"
    "?MaxRows=10&tpage={page}&searchKey=1&searchVal=&srCategoryId="
)

_VIEWS = re.compile(r"조회수\s*([\d,]+)")
_POSTED = re.compile(r"작성일\s*(\d{4})[-.](\d{1,2})[-.](\d{1,2})")
_MODIFIED = re.compile(r"수정일\s*(\d{4})[-.](\d{1,2})[-.](\d{1,2})")


def page_url(page: int) -> str:
    return LIST_URL.format(page=page)


def _date(m: re.Match[str] | None) -> dt.date | None:
    if not m:
        return None
    return dt.date(int(m[1]), int(m[2]), int(m[3]))


def _clean_title(anchor: Tag) -> str:
    """제목에서 카테고리 배지와 아이콘용 텍스트를 걷어낸다."""
    a = BeautifulSoup(str(anchor), "lxml")
    for sel in ("strong.category", "span.ico-new", "span.ico-file", "span.ico-notice"):
        for tag in a.select(sel):
            tag.decompose()
    return " ".join(a.get_text(" ", strip=True).split())


def parse_list(html: str) -> list[ListItem]:
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one("div.board-list-box > ul")
    if box is None:
        raise ValueError("목록 컨테이너(div.board-list-box > ul)를 찾지 못했다")

    items: list[ListItem] = []
    pinned_seen = 0

    for li in box.find_all("li", recursive=False):
        anchor = li.find("a", href=True)
        if anchor is None:
            continue

        qs = parse_qs(urlparse(anchor["href"]).query)
        duid = qs.get("DUID", [None])[0]
        if not duid:
            continue

        info = li.select_one("p.info")
        info_text = " ".join(info.get_text(" ", strip=True).split()) if info else ""
        posted = _date(_POSTED.search(info_text))
        if posted is None:
            # 작성일이 없는 행은 목록 행이 아니다(검색 폼 등).
            continue

        views = _VIEWS.search(info_text)
        # 부서명은 info 의 마지막 칸에 온다.
        dept = info_text.split("|")[-1].strip() or None

        # 고정 공지는 li.top-notice 로 명시된다.
        is_pinned = "top-notice" in (li.get("class") or [])
        category = li.select_one("strong.category")

        items.append(
            ListItem(
                external_id=duid,
                url=urljoin(BASE, anchor["href"]),
                title=_clean_title(anchor),
                posted_at=posted,
                category=category.get_text(strip=True).strip("[] ") if category else None,
                author_dept=dept,
                modified_at_source=_date(_MODIFIED.search(info_text)),
                view_count=int(views[1].replace(",", "")) if views else 0,
                has_attachment=li.select_one("span.ico-file") is not None,
                is_pinned=is_pinned,
                pinned_rank=pinned_seen if is_pinned else None,
            )
        )
        if is_pinned:
            pinned_seen += 1

    return items


def parse_detail(html: str, *, page_url_: str | None = None) -> Detail:
    soup = BeautifulSoup(html, "lxml")
    view = soup.select_one("div.board-view-box")
    if view is None:
        raise ValueError("상세 컨테이너(div.board-view-box)를 찾지 못했다")

    contents = view.select_one("li.contents")
    body_html = str(contents) if contents else ""

    attachments: list[AttachmentRef] = []
    for a in view.select("li.attachment a[href]"):
        link = BeautifulSoup(str(a), "lxml")
        for icon in link.select("span.ico-file"):
            icon.decompose()
        name = " ".join(link.get_text(" ", strip=True).split())
        # "1. 파일명.pdf" 처럼 앞에 순번이 붙는다. 순번은 파일명이 아니다.
        name = re.sub(r"^\d+\.\s*", "", name)
        if name:
            attachments.append(AttachmentRef(filename=name, url=urljoin(BASE, a["href"])))

    images = [
        urljoin(BASE, img["src"])
        for img in (contents.select("img[src]") if contents else [])
        if img.get("src")
    ]

    return Detail(
        body_html=body_html,
        body_text=html_to_text(body_html),
        attachments=attachments,
        inline_image_urls=images,
    )
