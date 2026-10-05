"""요약 결과의 구조."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NoticeSummary(BaseModel):
    """공지 하나의 요약."""

    bullets: list[str] = Field(
        description=(
            "공지의 핵심을 담은 2~5개의 한국어 문장. 각 문장은 한 줄로 끝난다. "
            "목록 기호(-)는 붙이지 않는다. 인라인 마크다운(**굵게**, [링크 글자](URL))은 쓸 수 있다."
        )
    )
    deadline: str | None = Field(
        default=None,
        description=(
            "신청, 제출, 참여의 마감일이 본문이나 첨부에 있으면 YYYY-MM-DD 형식으로. "
            "마감일이 없거나 불확실하면 null."
        ),
    )


class DigestSummary(BaseModel):
    """하루치 요약."""

    headline: str = Field(description="그날을 한 문장으로 요약한 한국어 문장")
    bullets: list[str] = Field(
        description=(
            "그날 놓치면 안 되는 항목 3~5개. 각 항목은 한 줄. "
            "목록 기호(-)는 붙이지 않는다. 인라인 마크다운을 쓸 수 있다."
        )
    )
