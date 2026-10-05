"""본문 이미지(포스터) 속 글자를 Gemini 로 옮겨 적는다.

학교 공지는 본문에 링크 몇 줄만 두고 일정, 자격, 유의사항을 포스터 그림에
넣는 경우가 많다. 글자로 바꿔 두면 채팅이 읽고, 검색이 찾고, 요약이 쓴다.

돈이 드는 일이라 수집 때 일괄로 돌리지 않는다. 채팅이 그 공지를 처음 읽을 때
한 번 만들어 notices.image_text 에 저장한다.
"""

from __future__ import annotations

import datetime as dt
import logging

import httpx
from google import genai
from google.genai import types

from app.config import settings
from app.models import Notice
from app.summarize import llm

log = logging.getLogger(__name__)

MAX_IMAGES = 5
MAX_TOKENS = 4_000

PROMPT = """이 이미지들은 광운대학교 공지사항 본문에 들어 있던 그림입니다.
그림 속 글자를 빠짐없이, 원문 그대로 한국어로 옮겨 적으세요.

- 제목, 일정, 대상, 금액, 자격, 신청 방법, 유의사항, 문의처를 하나도 빼지 않습니다.
- 표는 마크다운 표로, 목록은 마크다운 목록으로 옮깁니다.
- 그림 순서대로 적고, 그림이 여러 장이면 사이에 빈 줄을 둡니다.
- 로고, 장식 문구처럼 정보가 없는 글자와 글자가 없는 그림은 건너뜁니다.
- 요약하거나 해석을 덧붙이지 않습니다. 옮겨 적기만 합니다.
- 옮길 글자가 하나도 없으면 빈 문자열만 답합니다."""


def download_images(urls: list[str], http: httpx.Client) -> list[types.Part]:
    """이미지를 내려받아 Part 로 만든다. Gemini 는 임의의 웹 URL 을 이미지로 받지 않는다.

    한 장을 못 받아도 나머지는 계속한다.
    """
    parts: list[types.Part] = []
    for url in urls:
        try:
            resp = http.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("이미지를 못 받았다 %s: %s", url, exc)
            continue
        mime = resp.headers.get("content-type", "").split(";")[0] or "image/jpeg"
        if not mime.startswith("image/"):
            log.warning("이미지가 아니다 %s: %s", url, mime)
            continue
        parts.append(types.Part.from_bytes(data=resp.content, mime_type=mime))
    return parts


def needs_image_text(notice: Notice) -> bool:
    if not notice.inline_image_urls:
        return False
    if notice.image_text_at is None:
        return True
    # 본문이 바뀌었으면 그림도 바뀌었을 수 있다.
    return notice.content_changed_at is not None and notice.image_text_at < notice.content_changed_at


def transcribe(notice: Notice, client: genai.Client, http: httpx.Client) -> str:
    """notice 의 본문 이미지를 옮겨 적어 notice 에 채운다. commit 은 호출한 쪽이 한다."""
    images = download_images((notice.inline_image_urls or [])[:MAX_IMAGES], http)
    text = ""
    if images:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[*images, types.Part.from_text(text=PROMPT)],
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_level=llm.THINKING_LEVEL),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        text = (response.text or "").strip()
    # 글자가 없는 그림이어도 시각을 남긴다. 다음에 또 돌지 않게.
    notice.image_text = text or None
    notice.image_text_at = dt.datetime.now(dt.UTC)
    return text
