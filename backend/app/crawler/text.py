"""게시판 본문 HTML 을 요약, 검색에 쓸 평문으로 정리한다.

공지 본문 대부분이 한글(HWP)이나 워드에서 복사된 것이라
`<o:p>`, `<!--[if !supportEmptyParas]-->`, 글자마다 쪼개진 `<span>` 같은
쓰레기가 잔뜩 섞여 있다. 이걸 걷어내지 않으면 토큰만 낭비된다.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from bs4 import BeautifulSoup, Comment

# 줄바꿈으로 취급할 블록 태그
_BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"}
_DROP = {"script", "style", "o:p"}

_MULTI_BLANK = re.compile(r"\n{3,}")
_SPACES = re.compile(r"[ \t ​﻿]+")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for tag in soup.find_all(_DROP):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.name in _BLOCK:
            tag.insert_before("\n")
            tag.insert_after("\n")

    text = soup.get_text()
    text = unicodedata.normalize("NFC", text)
    text = _SPACES.sub(" ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join(ln for ln in lines if ln)
    return _MULTI_BLANK.sub("\n\n", text).strip()


def content_hash(body_text: str | None) -> str | None:
    """본문 변경 감지용 해시.

    공백 차이만으로 '변경됨'이 뜨면 안 되므로 정규화한 뒤 해시한다.
    """
    if not body_text:
        return None
    normalized = _SPACES.sub(" ", unicodedata.normalize("NFC", body_text))
    normalized = "\n".join(ln.strip() for ln in normalized.split("\n") if ln.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
