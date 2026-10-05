"""공지 요약 실행기.

ai_summary 가 비었거나 본문 개정이 요약보다 최신인 공지를 골라 요약한다.
매일 파이프라인은 요약하지 않는다. 사용자가 공지에서 요약을 누를 때
(POST /api/notices/{id}/summary) 한 건씩 돌고, 이 CLI 는 수동 일괄용이다.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import httpx
from google import genai
from google.genai import errors, types
from sqlalchemy import or_, select

from app.crawler.http import make_client as make_http_client
from app.db import SessionLocal
from app.models import ExtractState, Notice
from app.summarize import llm
from app.summarize.prompt import SYSTEM, build_content
from app.summarize.schema import NoticeSummary

log = logging.getLogger(__name__)

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


def _to_parts(content: list[dict], http: httpx.Client) -> list[types.Part]:
    """prompt 의 블록을 Gemini Part 로 바꾼다.

    Gemini 는 임의의 웹 URL 을 이미지로 받지 않으므로 직접 내려받아 싣는다.
    한 장을 못 받아도 나머지로 요약은 계속한다.
    """
    parts: list[types.Part] = []
    for block in content:
        if block["type"] == "text":
            parts.append(types.Part.from_text(text=block["text"]))
            continue
        url = block["source"]["url"]
        try:
            resp = http.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("이미지를 못 받았다 %s: %s", url, exc)
            continue
        mime = resp.headers.get("content-type", "").split(";")[0] or "image/jpeg"
        parts.append(types.Part.from_bytes(data=resp.content, mime_type=mime))
    return parts


def summarize_one(
    client: genai.Client, http: httpx.Client, notice: Notice
) -> tuple[NoticeSummary, types.GenerateContentResponseUsageMetadata | None]:
    content = build_content(notice, _usable_attachments(notice))
    return llm.generate(
        client,
        system=SYSTEM,
        contents=_to_parts(content, http),
        schema=NoticeSummary,
        max_tokens=MAX_TOKENS,
    )


def _parse_deadline(raw: str | None) -> dt.date | None:
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw.strip())
    except ValueError:
        log.warning("마감일 형식이 이상하다: %r", raw)
        return None


def summarize_and_store(
    client: genai.Client, http: httpx.Client, notice: Notice
) -> types.GenerateContentResponseUsageMetadata | None:
    """요약해서 notice 에 채운다. commit 은 호출한 쪽이 한다."""
    summary, usage = summarize_one(client, http, notice)
    notice.ai_summary = "\n".join(f"- {b}" for b in summary.bullets)
    notice.ai_summary_model = llm.model_name()
    notice.ai_summarized_at = dt.datetime.now(dt.UTC)
    notice.deadline_at = _parse_deadline(summary.deadline)
    return usage


def run(limit: int | None = None, force: bool = False, dry_run: bool = False) -> SummaryStats:
    stats = SummaryStats()

    with SessionLocal() as session:
        stmt = pending_query(force)
        if limit:
            stmt = stmt.limit(limit)
        notices = session.scalars(stmt).all()

        if dry_run:
            return _dry_run(notices, stats)

        client = llm.make_client()
        http = make_http_client()

        for notice in notices:
            if not (notice.body_text or "").strip() and not notice.inline_image_urls:
                stats.skipped += 1
                continue

            try:
                usage = summarize_and_store(client, http, notice)
            except (errors.APIError, ValueError) as exc:
                stats.failed += 1
                stats.errors.append(f"{notice.external_id}: {exc}")
                log.warning("요약 실패 %s: %s", notice.external_id, exc)
                continue
            session.commit()

            stats.done += 1
            if usage:
                stats.input_tokens += usage.prompt_token_count or 0
                stats.output_tokens += (usage.candidates_token_count or 0) + (
                    usage.thoughts_token_count or 0
                )
                stats.cache_read += usage.cached_content_token_count or 0

        http.close()

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
    # 한국어는 대략 1자당 0.7토큰. 정확한 값은 models.count_tokens 가 필요하다.
    print(f"입력 토큰 대략 {int(total_chars * 0.7):,} (실측 아님)")
    return stats
