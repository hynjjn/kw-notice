"""요약 프롬프트 조립."""

from __future__ import annotations

from app.models import Attachment, Notice

# 이 문자열은 절대 바뀌지 않아야 한다. 매 요청 앞머리에 그대로 실려서
# 암묵적 캐시의 prefix 가 된다. 날짜 같은 변동값을 넣으면 캐시가 매번 깨진다.
SYSTEM = """당신은 광운대학교 학생에게 공지사항을 요약해 주는 도우미입니다.

요약 원칙:
- 학생이 "내가 뭘 해야 하는가"를 30초 안에 알 수 있게 씁니다.
- 날짜, 금액, 자격 요건, 제출 방법처럼 행동에 필요한 정보를 우선합니다.
- 첨부파일 내용이 주어지면 본문보다 그쪽에 진짜 정보가 있는 경우가 많습니다. 함께 읽습니다.
- 본문에 없는 내용을 지어내지 않습니다. 모르면 그 항목을 빼세요.
- "안내드립니다", "바랍니다" 같은 공문 투는 걷어내고 사실만 남깁니다.
- 각 항목은 한 줄로 끝냅니다. 마침표로 끝내지 않아도 됩니다.
- 화면에서 마크다운으로 렌더링됩니다. 신청 페이지 같은 URL 은 [신청 페이지](https://...) 처럼
  링크로 쓰고, 금액이나 마감처럼 꼭 봐야 할 값은 **굵게** 표시해도 됩니다. 남발하지는 않습니다.

마감일 판단:
- 신청, 제출, 참여의 기한이 명확할 때만 채웁니다.
- 행사 날짜와 신청 마감일이 다르면 신청 마감일을 씁니다.
- "~까지", "~마감" 표현을 찾되, 연도가 없으면 공지 작성일 기준으로 추정합니다."""

# 공지 하나에 실어 보낼 글자 수 상한. 한국어는 대략 1자 = 0.7토큰이다.
MAX_BODY_CHARS = 12_000
MAX_ATTACHMENT_CHARS = 8_000
MAX_TOTAL_CHARS = 40_000
MAX_IMAGES = 5


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...(이하 {len(text) - limit:,}자 생략)"


def build_content(notice: Notice, attachments: list[Attachment]) -> list[dict]:
    """공지 하나를 모델에 보낼 content 블록 목록으로 만든다."""
    head = [
        f"제목: {notice.title}",
        f"작성일: {notice.posted_at}",
    ]
    if notice.category:
        head.append(f"분류: {notice.category}")
    if notice.author_dept:
        head.append(f"작성부서: {notice.author_dept}")

    parts = ["\n".join(head)]

    body = (notice.body_text or "").strip()
    if body:
        parts.append(f"[본문]\n{_clip(body, MAX_BODY_CHARS)}")
    else:
        parts.append("[본문]\n(본문 글자가 없습니다. 아래 이미지가 공지 내용입니다.)")

    # 포스터 속 글자를 이미 옮겨 적었으면 그림 대신 그 글자를 싣는다. 더 싸고 정확하다.
    image_text = (notice.image_text or "").strip()
    if image_text:
        parts.append(f"[본문 이미지 속 글자]\n{_clip(image_text, MAX_BODY_CHARS)}")

    budget = MAX_TOTAL_CHARS - sum(len(p) for p in parts)
    for att in attachments:
        if budget <= 0:
            break
        text = (att.extracted_text or "").strip()
        if not text:
            continue
        chunk = _clip(text, min(MAX_ATTACHMENT_CHARS, budget))
        parts.append(f"[첨부: {att.filename}]\n{chunk}")
        budget -= len(chunk)

    content: list[dict] = []

    # 본문이 이미지뿐인 공지는 그림을 봐야 내용을 알 수 있다.
    if not body and not image_text and notice.inline_image_urls:
        content += [
            {"type": "image", "source": {"type": "url", "url": url}}
            for url in notice.inline_image_urls[:MAX_IMAGES]
        ]

    content.append({"type": "text", "text": "\n\n".join(parts)})
    return content
