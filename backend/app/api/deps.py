"""의존성.

MVP 는 단일 사용자다. 로그인이 없고, 설정에 적힌 이메일의 행을 현재 사용자로 쓴다.
나중에 인증이 붙어도 이 함수만 바뀌면 되도록 라우트에서는 항상 여기를 거친다.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import User


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_current_user(session: Session = Depends(get_session)) -> User:
    user = session.scalar(select(User).where(User.email == settings.default_user_email))
    if user is None:
        raise HTTPException(
            status_code=500,
            detail=f"기본 사용자({settings.default_user_email})가 없다. python -m app.init_db 실행 필요",
        )
    return user
