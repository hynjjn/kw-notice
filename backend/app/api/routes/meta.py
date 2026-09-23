"""사이드바용 집계와 하루치 요약."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.api.routes.notices import DEADLINE_SOON_DAYS
from app.api.schemas import CountOut, DigestOut, SourceOut, StatsOut
from app.models import CrawlState, DailyDigest, Notice, Source, User, UserNoticeState

router = APIRouter(tags=["meta"])


@router.get("/sources", response_model=list[SourceOut])
def list_sources(session: Session = Depends(get_session)) -> list[SourceOut]:
    counts = (
        select(Notice.source_id, func.count().label("n"))
        .where(Notice.crawl_state == CrawlState.parsed)
        .group_by(Notice.source_id)
        .subquery()
    )
    rows = session.execute(
        select(Source, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.source_id == Source.id)
        .order_by(Source.id)
    ).all()
    return [
        SourceOut(
            key=s.key, name=s.name, last_crawled_at=s.last_crawled_at, notice_count=n
        )
        for s, n in rows
    ]


@router.get("/stats", response_model=StatsOut)
def get_stats(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
) -> StatsOut:
    parsed = Notice.crawl_state == CrawlState.parsed

    read_ids = select(UserNoticeState.notice_id).where(
        UserNoticeState.user_id == user.id, UserNoticeState.is_read.is_(True)
    )
    starred_ids = select(UserNoticeState.notice_id).where(
        UserNoticeState.user_id == user.id, UserNoticeState.is_starred.is_(True)
    )

    today = dt.date.today()
    total = session.scalar(select(func.count()).select_from(Notice).where(parsed)) or 0
    unread = (
        session.scalar(
            select(func.count())
            .select_from(Notice)
            .where(parsed, Notice.id.not_in(read_ids))
        )
        or 0
    )
    starred = (
        session.scalar(
            select(func.count()).select_from(Notice).where(parsed, Notice.id.in_(starred_ids))
        )
        or 0
    )
    pinned = (
        session.scalar(
            select(func.count()).select_from(Notice).where(parsed, Notice.is_pinned.is_(True))
        )
        or 0
    )
    soon = (
        session.scalar(
            select(func.count())
            .select_from(Notice)
            .where(
                parsed,
                Notice.deadline_at.is_not(None),
                Notice.deadline_at >= today,
                Notice.deadline_at <= today + dt.timedelta(days=DEADLINE_SOON_DAYS),
            )
        )
        or 0
    )

    by_source = [
        CountOut(key=key, label=name, count=n)
        for key, name, n in session.execute(
            select(Source.key, Source.name, func.count(Notice.id))
            .join(Notice, Notice.source_id == Source.id)
            .where(parsed)
            .group_by(Source.key, Source.name)
            .order_by(func.count(Notice.id).desc())
        ).all()
    ]

    by_category = [
        CountOut(key=cat, label=cat, count=n)
        for cat, n in session.execute(
            select(Notice.category, func.count())
            .where(parsed, Notice.category.is_not(None))
            .group_by(Notice.category)
            .order_by(func.count().desc())
        ).all()
    ]

    return StatsOut(
        total=total,
        unread=unread,
        starred=starred,
        pinned=pinned,
        deadline_soon=soon,
        by_source=by_source,
        by_category=by_category,
    )


@router.get("/digests/{digest_date}", response_model=DigestOut)
def get_digest(
    digest_date: dt.date, session: Session = Depends(get_session)
) -> DigestOut:
    digest = session.scalar(
        select(DailyDigest).where(
            DailyDigest.user_id.is_(None), DailyDigest.digest_date == digest_date
        )
    )
    if digest is None:
        raise HTTPException(status_code=404, detail=f"{digest_date} 요약이 아직 없다")
    return DigestOut.model_validate(digest)
