"""AI 채팅이 기억하는 사용자 정보. 채팅이 저장하고, 사용자는 보고 지운다."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.chat.service import load_memories
from app.models import User, UserMemory

router = APIRouter(prefix="/memories", tags=["chat"])


class MemoryOut(BaseModel):
    id: int
    content: str
    created_at: dt.datetime


@router.get("", response_model=list[MemoryOut])
def list_memories(
    session: Session = Depends(get_session), user: User = Depends(get_current_user)
) -> list[MemoryOut]:
    return [
        MemoryOut(id=m.id, content=m.content, created_at=m.created_at)
        for m in load_memories(session, user.id)
    ]


@router.delete("/{memory_id}", response_model=list[MemoryOut])
def delete_memory(
    memory_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[MemoryOut]:
    """지우고 남은 기억을 돌려준다."""
    memory = session.get(UserMemory, memory_id)
    if memory is None or memory.user_id != user.id:
        raise HTTPException(status_code=404, detail="기억이 없다")
    session.delete(memory)
    session.commit()
    return list_memories(session, user)
