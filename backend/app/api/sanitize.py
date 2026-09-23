"""공지 본문 HTML 을 브라우저에 그대로 실어 보낼 수 있게 정제한다.

본문을 평문(body_text)으로만 보여 주면 두 가지를 잃는다.

1. 굵기, 글자 크기, 가운데 정렬 같은 서식. 공지는 이런 걸로 강약을 준다
2. **이미지의 위치**. 포스터가 본문 중간에 박혀 있는데, 평문에서는 자리를
   알 수 없어 전부 글 뒤로 밀린다

그래서 원본 HTML 을 살리되, 위험한 것과 다크모드를 깨는 것만 걷어낸다.
"""

from __future__ import annotations

from urllib.parse import urljoin

import nh3
from bs4 import BeautifulSoup

# 게시판이 본문을 감싸는 껍데기. 그대로 두면 <li> 불릿이 찍힌다.
CONTAINERS = "li.contents, td.view_td"

TAGS = {
    "p", "br", "div", "span", "section",
    "b", "strong", "em", "i", "u", "s", "mark", "sup", "sub",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "colgroup", "col",
    "a", "img", "blockquote", "pre", "code", "hr",
}

ATTRIBUTES = {
    "*": {"style", "align", "title"},
    # rel 은 nh3 가 link_rel 로 직접 붙인다. 여기 두면 충돌한다.
    "a": {"href", "target", "title"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "col": {"span", "width"},
    "table": {"border", "cellpadding", "cellspacing"},
}

# 살릴 CSS 속성.
# color 와 background-color 는 일부러 뺀다. 한글에서 뽑혀 나온 HTML 은
# 글자색을 검정으로 박아 두는 경우가 많아, 다크모드에서 본문이 사라진다.
# font-family 도 뺀다. 맑은 고딕 지정이 화면 폰트와 섞여 지저분해진다.
STYLE_PROPS = {
    "font-weight",
    "font-size",
    "font-style",
    "text-decoration",
    "text-align",
    "vertical-align",
}


def _clean_style(value: str) -> str | None:
    kept = []
    for decl in value.split(";"):
        name, sep, val = decl.partition(":")
        if not sep:
            continue
        name = name.strip().lower()
        if name in STYLE_PROPS and val.strip():
            kept.append(f"{name}: {val.strip()}")
    return "; ".join(kept) or None


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if attr == "style":
        return _clean_style(value)
    return value


def to_safe_html(raw: str | None, base_url: str) -> str | None:
    """저장된 본문 HTML 을 절대 URL 로 바꾸고 정제해서 돌려준다."""
    if not raw:
        return None

    soup = BeautifulSoup(raw, "lxml")
    container = soup.select_one(CONTAINERS) or soup.body or soup

    # 상대 경로(/KWData/..., ../lib/...)는 프론트 도메인 기준으로 깨진다.
    for node, attr in (("img", "src"), ("a", "href")):
        for tag in container.find_all(node):
            value = tag.get(attr)
            if value and not value.startswith(("http://", "https://", "data:")):
                tag[attr] = urljoin(base_url, value)

    inner = container.decode_contents()
    return nh3.clean(
        inner,
        tags=TAGS,
        attributes=ATTRIBUTES,
        attribute_filter=_attribute_filter,
        link_rel="noopener noreferrer",
    )
