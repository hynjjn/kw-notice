from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import refresh
from app.api.deps import get_session
from app.models import Source

router = APIRouter(prefix="/refresh", tags=["refresh"])


class RefreshOut(BaseModel):
    state: Literal["idle", "running", "done", "failed"]
    stage: str | None
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    new: int
    updated: int
    failed_sources: list[str]
    error: str | None
    # 서버를 다시 띄우면 작업 상태는 사라지지만, 마지막 수집 시각은 DB 에 남아 있다.
    last_crawled_at: dt.datetime | None


def _out(session: Session, status: refresh.RefreshStatus) -> RefreshOut:
    last = session.scalar(select(func.max(Source.last_crawled_at)))
    return RefreshOut(**asdict(status), last_crawled_at=last)


@router.get("", response_model=RefreshOut)
def get_refresh(session: Session = Depends(get_session)) -> RefreshOut:
    return _out(session, refresh.status())


@router.post("", response_model=RefreshOut, status_code=202)
def start_refresh(response: Response, session: Session = Depends(get_session)) -> RefreshOut:
    """새 공지 가져오기를 백그라운드로 시작한다. 이미 돌고 있으면 그 상태를 돌려준다."""
    before = refresh.status().state
    status = refresh.start()
    if before == "running":
        response.status_code = 200
    return _out(session, status)
