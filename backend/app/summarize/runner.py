"""공지 요약 실행기.

ai_summary 가 비었거나 본문 개정이 요약보다 최신인 공지를 골라 요약한다.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import anthropic
from sqlalchemy import or_, select

from app.config import settings
from app.db import SessionLocal
from app.models import ExtractState, Notice
from app.summarize.prompt import SYSTEM, build_content
from app.summarize.schema import NoticeSummary

log = logging.getLogger(__name__)

MODEL = "claude-opus-5"
# 요약은 판단이 복잡한 일이 아니다. effort 를 낮춰 토큰을 아낀다.
EFFORT = "low"
MAX_TOKENS = 2_000


@dataclass
class SummaryStats:
    done: int = 0
    failed: int = 0
    skipped: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    errors: list[str] = field(default_factory=list)


def pending_query(force: bool):
    stmt = select(Notice).where(Notice.crawl_state == "parsed")
    if not force:
        # 아직 요약이 없거나, 본문이 바뀐 뒤로 다시 요약하지 않은 것.
        stmt = stmt.where(
            or_(
                Notice.ai_summary.is_(None),
                Notice.content_changed_at.is_not(None)
                & (Notice.ai_summarized_at < Notice.content_changed_at),
            )
        )
    return stmt.order_by(Notice.posted_at.desc())


def _usable_attachments(notice: Notice):
    return [a for a in notice.attachments if a.extract_state == ExtractState.ok]


def summarize_one(client: anthropic.Anthropic, notice: Notice) -> tuple[NoticeSummary, object]:
    content = build_content(notice, _usable_attachments(notice))

    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": EFFORT},
        messages=[{"role": "user", "content": content}],
        output_format=NoticeSummary,
    )
    return response.parsed_output, response.usage


def _parse_deadline(raw: str | None) -> dt.date | None:
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw.strip())
    except ValueError:
        log.warning("마감일 형식이 이상하다: %r", raw)
        return None


def run(limit: int | None = None, force: bool = False, dry_run: bool = False) -> SummaryStats:
    stats = SummaryStats()

    with SessionLocal() as session:
        stmt = pending_query(force)
        if limit:
            stmt = stmt.limit(limit)
        notices = session.scalars(stmt).all()

        if dry_run:
            return _dry_run(notices, stats)

        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 가 없다. .env 에 넣거나 환경변수로 내보낼 것."
            )
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        for notice in notices:
            if not (notice.body_text or "").strip() and not notice.inline_image_urls:
                stats.skipped += 1
                continue

            try:
                summary, usage = summarize_one(client, notice)
            except anthropic.APIError as exc:
                stats.failed += 1
                stats.errors.append(f"{notice.external_id}: {exc}")
                log.warning("요약 실패 %s: %s", notice.external_id, exc)
                continue

            notice.ai_summary = "\n".join(f"- {b}" for b in summary.bullets)
            notice.ai_summary_model = MODEL
            notice.ai_summarized_at = dt.datetime.now(dt.UTC)
            notice.deadline_at = _parse_deadline(summary.deadline)
            session.commit()

            stats.done += 1
            stats.input_tokens += usage.input_tokens
            stats.output_tokens += usage.output_tokens
            stats.cache_read += usage.cache_read_input_tokens or 0

    return stats


def _dry_run(notices, stats: SummaryStats) -> SummaryStats:
    """API 를 호출하지 않고 무엇이 실릴지만 보여 준다."""
    total_chars = 0
    images = 0
    for notice in notices:
        content = build_content(notice, _usable_attachments(notice))
        chars = sum(len(b["text"]) for b in content if b["type"] == "text")
        imgs = sum(1 for b in content if b["type"] == "image")
        total_chars += chars
        images += imgs
        stats.done += 1
        print(f"  {notice.external_id:>6} {chars:>7,}자 이미지{imgs} | {notice.title[:46]}")

    print(f"\n대상 {stats.done}건 / 본문+첨부 {total_chars:,}자 / 이미지 {images}장")
    # 한국어는 대략 1자당 0.7토큰. 정확한 값은 messages.count_tokens 가 필요하다.
    print(f"입력 토큰 대략 {int(total_chars * 0.7):,} (실측 아님)")
    return stats
