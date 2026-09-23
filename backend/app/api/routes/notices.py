from __future__ import annotations

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import BigInteger, Select, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.api.sanitize import to_safe_html
from app.api.schemas import (
    AttachmentOut,
    NoticeDetail,
    NoticeListItem,
    NoticeListResponse,
    StateOut,
)
from app.models import Attachment, CrawlState, ExtractState, Notice, Source, User, UserNoticeState

router = APIRouter(prefix="/notices", tags=["notices"])

DEADLINE_SOON_DAYS = 7

# 같은 날짜 안에서 두 출처가 겹칠 때의 우선순위.
# 학부 공지는 대부분 대학 공지를 재공지하는 성격이라 뒤에 둔다.
# 출처가 늘면 sources 테이블의 컬럼으로 옮기는 게 맞다.
SOURCE_PRIORITY = case({"kw_main": 0, "cs_dept": 1}, value=Source.key, else_=99)

# 사이트가 시각을 주지 않아서(작성일까지만 있다) 같은 날짜 안의 순서를
# 따로 정해야 한다. DUID(대학)와 no(학부)는 글이 올라올 때마다 1씩 오르는
# 값이라 게시 순서를 정확히 반영한다. 수집한 98건 전부에서 작성일 순서와
# 어긋나는 경우가 없었다.
#
# 문자열 그대로 비교하면 안 된다. 지금은 다섯 자리라 사전순이 우연히 맞지만
# 여섯 자리가 되는 순간 '100001' < '53385' 로 뒤집힌다.
#
# 두 출처 모두 external_id 가 숫자다. 숫자가 아닌 출처가 생기면 여기서 터진다.
EXTERNAL_SEQ = cast(Notice.external_id, BigInteger).desc()

# 공지를 처음 본 "날짜". 초 단위로 쓰면 안 된다.
#
# 파이프라인은 항상 대학 공지를 먼저, 학부 공지를 나중에 긁는다(PARSERS 순서).
# first_seen_at 을 초까지 비교하면 학부 공지가 매일 대학 공지 위로 올라간다.
# 정렬 기준에 "크롤러를 어떤 순서로 돌렸는가"가 새어 들어오는 것이다.
# 날짜로 자르면 같은 날 수집분이 동률이 되어 그 차이가 사라진다.
#
# 서버의 timezone 설정에 기대지 않고 한국 시각으로 못박는다. cron 이 07:00 KST 에
# 도는데 서버가 UTC 면 전날 22:00 이 되어 날짜가 하루 어긋난다.
SEEN_DAY = func.date(func.timezone("Asia/Seoul", Notice.first_seen_at)).desc()

# 정렬 키는 여러 개일 수 있다. 뒤에 SOURCE_PRIORITY 와 EXTERNAL_SEQ 가 항상 붙는다.
SORTS: dict[str, tuple] = {
    # 기본값. "오늘 새로 눈에 띈 것"이 위로 온다.
    #
    # 작성일순으로는 잡히지 않는 게 있다. 7월에 올라온 공지가 기간 연장으로
    # 수정되면 학교 목록 1페이지로 떠오르는데, 작성일로 줄 세우면 102건 중
    # 91번째로 묻힌다. 학생에게는 어제 뜬 새 소식인데도 그렇다.
    "seen": (SEEN_DAY, Notice.posted_at.desc()),
    "posted": (Notice.posted_at.desc(),),
    # 학교 사이트가 쓰는 기준. 8월 공지가 어제 공지보다 위에 온다.
    "modified": (Notice.modified_at_source.desc().nulls_last(),),
    "views": (Notice.view_count.desc(),),
    "deadline": (Notice.deadline_at.asc().nulls_last(),),
}


def _attachment_count():
    return (
        select(func.count(Attachment.id))
        .where(Attachment.notice_id == Notice.id)
        .correlate(Notice)
        .scalar_subquery()
    )


def _base_select(user: User) -> Select:
    return (
        select(
            Notice,
            Source.key,
            Source.name,
            func.coalesce(UserNoticeState.is_read, False),
            func.coalesce(UserNoticeState.is_starred, False),
            _attachment_count(),
        )
        .join(Source, Source.id == Notice.source_id)
        .outerjoin(
            UserNoticeState,
            (UserNoticeState.notice_id == Notice.id)
            & (UserNoticeState.user_id == user.id),
        )
        .where(Notice.crawl_state == CrawlState.parsed)
    )


def _apply_filters(
    stmt: Select,
    *,
    source: str | None,
    category: str | None,
    pinned: bool | None,
    unread: bool | None,
    starred: bool | None,
    deadline_soon: bool,
    q: str | None,
) -> Select:
    if source:
        stmt = stmt.where(Source.key == source)
    if category:
        stmt = stmt.where(Notice.category == category)
    if pinned is not None:
        stmt = stmt.where(Notice.is_pinned.is_(pinned))
    if unread is not None:
        read = func.coalesce(UserNoticeState.is_read, False)
        stmt = stmt.where(read.is_(not unread))
    if starred:
        stmt = stmt.where(func.coalesce(UserNoticeState.is_starred, False).is_(True))
    if deadline_soon:
        today = dt.date.today()
        stmt = stmt.where(
            Notice.deadline_at.is_not(None),
            Notice.deadline_at >= today,
            Notice.deadline_at <= today + dt.timedelta(days=DEADLINE_SOON_DAYS),
        )
    if q:
        pattern = f"%{q}%"
        # tsvector 는 'simple' 구성이라 한국어 부분 일치를 놓친다.
        # ILIKE 를 함께 걸어 보완하고, 첨부 본문까지 훑는다.
        # 이게 학교 검색과 갈리는 지점이다.
        in_attachment = (
            select(Attachment.id)
            .where(
                Attachment.notice_id == Notice.id,
                Attachment.extracted_text.ilike(pattern),
            )
            .correlate(Notice)
        )
        stmt = stmt.where(
            or_(
                Notice.tsv.op("@@")(func.plainto_tsquery("simple", q)),
                Notice.title.ilike(pattern),
                Notice.body_text.ilike(pattern),
                exists(in_attachment),
            )
        )
    return stmt


def _to_item(row) -> NoticeListItem:
    notice, source_key, source_name, is_read, is_starred, att_count = row
    return NoticeListItem(
        id=notice.id,
        source_key=source_key,
        source_name=source_name,
        external_id=notice.external_id,
        url=notice.url,
        title=notice.title,
        category=notice.category,
        author_dept=notice.author_dept,
        posted_at=notice.posted_at,
        modified_at_source=notice.modified_at_source,
        view_count=notice.view_count,
        is_pinned=notice.is_pinned,
        pinned_rank=notice.pinned_rank,
        has_attachment=notice.has_attachment,
        attachment_count=att_count,
        deadline_at=notice.deadline_at,
        ai_summary=notice.ai_summary,
        content_revision=notice.content_revision,
        content_changed_at=notice.content_changed_at,
        is_read=is_read,
        is_starred=is_starred,
    )


@router.get("", response_model=NoticeListResponse)
def list_notices(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    source: str | None = None,
    category: str | None = None,
    pinned: bool | None = Query(None, description="true=고정만, false=고정 제외"),
    unread: bool | None = None,
    starred: bool | None = None,
    deadline_soon: bool = False,
    q: str | None = Query(None, description="제목, 본문, 첨부 본문 검색"),
    sort: Literal["seen", "posted", "modified", "views", "deadline"] = "seen",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> NoticeListResponse:
    filters = dict(
        source=source,
        category=category,
        pinned=pinned,
        unread=unread,
        starred=starred,
        deadline_soon=deadline_soon,
        q=q,
    )

    stmt = _apply_filters(_base_select(user), **filters)
    total = session.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    )

    rows = session.execute(
        stmt.order_by(*SORTS[sort], SOURCE_PRIORITY, EXTERNAL_SEQ)
        .limit(limit)
        .offset(offset)
    ).all()

    return NoticeListResponse(
        items=[_to_item(r) for r in rows], total=total or 0, limit=limit, offset=offset
    )


@router.get("/{notice_id}", response_model=NoticeDetail)
def get_notice(
    notice_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> NoticeDetail:
    row = session.execute(_base_select(user).where(Notice.id == notice_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없다")

    notice = row[0]
    item = _to_item(row)
    return NoticeDetail(
        **item.model_dump(),
        body_html=to_safe_html(notice.body_html, notice.url),
        body_text=notice.body_text,
        inline_image_urls=notice.inline_image_urls,
        attachments=[
            AttachmentOut(
                id=a.id,
                filename=a.filename,
                url=a.url,
                file_ext=a.file_ext,
                byte_size=a.byte_size,
                extract_state=a.extract_state.value,
                has_text=a.extract_state == ExtractState.ok,
            )
            for a in notice.attachments
        ],
    )


def _set_state(
    session: Session, user: User, notice_id: int, **changes
) -> StateOut:
    if not session.get(Notice, notice_id):
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없다")

    state = session.get(UserNoticeState, (user.id, notice_id))
    if state is None:
        state = UserNoticeState(user_id=user.id, notice_id=notice_id)
        session.add(state)

    now = dt.datetime.now(dt.UTC)
    if "is_read" in changes:
        state.is_read = changes["is_read"]
        state.read_at = now if changes["is_read"] else None
    if "is_starred" in changes:
        state.is_starred = changes["is_starred"]
        state.starred_at = now if changes["is_starred"] else None

    session.commit()
    return StateOut(
        notice_id=notice_id, is_read=state.is_read, is_starred=state.is_starred
    )


@router.put("/{notice_id}/read", response_model=StateOut)
def mark_read(
    notice_id: int,
    value: bool = Query(True),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StateOut:
    return _set_state(session, user, notice_id, is_read=value)


@router.put("/{notice_id}/star", response_model=StateOut)
def mark_star(
    notice_id: int,
    value: bool = Query(True),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StateOut:
    return _set_state(session, user, notice_id, is_starred=value)
