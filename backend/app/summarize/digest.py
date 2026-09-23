"""하루치 요약 생성.

그날 올라온 공지들의 개별 요약을 모아 "오늘 뭘 봐야 하는가" 한 덩어리로 만든다.
개별 요약이 이미 있으므로 원문을 다시 읽지 않는다. 토큰이 훨씬 싸다.
"""

from __future__ import annotations

import datetime as dt
import logging

import anthropic
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import CrawlState, DailyDigest, Notice
from app.summarize.schema import DigestSummary

log = logging.getLogger(__name__)

MODEL = "claude-opus-5"
SYSTEM = """당신은 광운대학교 학생에게 그날의 공지를 브리핑합니다.

- 바쁜 학생이 30초 안에 읽고 "오늘 내가 챙길 게 있나"를 판단할 수 있게 씁니다.
- 마감이 임박한 것, 돈이 걸린 것(장학금, 지원금), 신청이 필요한 것을 앞에 둡니다.
- 단순 행사 안내나 채용 공고처럼 대부분의 학생과 무관한 것은 뒤로 미루거나 뺍니다.
- 주어진 요약에 없는 내용을 지어내지 않습니다.
- 각 항목은 한 줄로 끝냅니다."""


def _collect(session, target: dt.date) -> list[Notice]:
    return list(
        session.scalars(
            select(Notice)
            .where(
                Notice.posted_at == target,
                Notice.crawl_state == CrawlState.parsed,
                Notice.ai_summary.is_not(None),
            )
            .order_by(Notice.deadline_at.asc().nulls_last(), Notice.id)
        )
    )


def _render(notices: list[Notice]) -> str:
    blocks = []
    for n in notices:
        head = f"### {n.title}"
        meta = [f"출처: {n.source.name}"]
        if n.category:
            meta.append(f"분류: {n.category}")
        if n.deadline_at:
            meta.append(f"마감: {n.deadline_at}")
        blocks.append(f"{head}\n({', '.join(meta)})\n{n.ai_summary}")
    return "\n\n".join(blocks)


def build(target: dt.date, dry_run: bool = False) -> DailyDigest | None:
    with SessionLocal() as session:
        notices = _collect(session, target)
        if not notices:
            msg = f"{target} 에 요약이 끝난 공지가 없다. python -m app.summarize 를 먼저 돌릴 것"
            if dry_run:
                print(msg)
            log.info("%s", msg)
            return None

        rendered = _render(notices)
        if dry_run:
            print(f"[{target}] 공지 {len(notices)}건 / {len(rendered):,}자")
            print(rendered[:1200])
            return None

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 가 없다")

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.parse(
            model=MODEL,
            max_tokens=2_000,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            output_config={"effort": "low"},
            messages=[
                {
                    "role": "user",
                    "content": f"{target} 에 올라온 공지 {len(notices)}건입니다.\n\n{rendered}",
                }
            ],
            output_format=DigestSummary,
        )
        result = response.parsed_output

        summary_md = result.headline + "\n\n" + "\n".join(f"- {b}" for b in result.bullets)
        digest = session.scalar(
            select(DailyDigest).where(
                DailyDigest.user_id.is_(None), DailyDigest.digest_date == target
            )
        )
        if digest is None:
            digest = DailyDigest(user_id=None, digest_date=target)
            session.add(digest)

        digest.summary_md = summary_md
        digest.notice_ids = [n.id for n in notices]
        digest.model = MODEL
        session.commit()
        session.refresh(digest)
        return digest
