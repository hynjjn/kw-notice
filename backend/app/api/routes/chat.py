from __future__ import annotations

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.chat.service import ChatTurn, answer
from app.config import settings
from app.models import Notice

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4_000)
    # 질문을 보낼 때 열려 있던 공지. 사용자 메시지에만 붙는다.
    notice_id: int | None = None


class ChatRequest(BaseModel):
    # 대화는 서버에 저장하지 않는다. 프론트가 들고 있다가 매번 통째로 보낸다.
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=50)


class ChatNoticeRef(BaseModel):
    id: int
    title: str
    deadline_at: dt.date | None


class ChatResponse(BaseModel):
    reply: str
    notices: list[ChatNoticeRef]


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
    """공지에 대해 묻고 답한다. Gemini 가 검색 도구를 몇 번 부르므로 수 초 걸린다."""
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="마지막 메시지는 사용자 질문이어야 한다")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY 가 설정되지 않았다")

    context_ids = {m.notice_id for m in body.messages if m.notice_id is not None}
    titles = dict(
        session.execute(select(Notice.id, Notice.title).where(Notice.id.in_(context_ids))).tuples().all()
    )
    # 없는 공지 id 는 맥락에서 뺀다. 지워진 공지를 열어 둔 채 물을 수도 있다.
    turns = [
        ChatTurn(
            m.role,
            m.text,
            notice_id=m.notice_id if m.notice_id in titles else None,
            notice_title=titles.get(m.notice_id) if m.notice_id is not None else None,
        )
        for m in body.messages
    ]

    try:
        result = answer(session, turns)
    except genai_errors.APIError as exc:
        raise HTTPException(status_code=502, detail=f"AI 응답 실패: {exc}") from exc

    # 모델이 지어낸 id 가 섞일 수 있다. 실제로 있는 공지만 돌려준다.
    found = {
        n.id: n
        for n in session.scalars(select(Notice).where(Notice.id.in_(result.notice_ids)))
    }
    refs = [
        ChatNoticeRef(id=n.id, title=n.title, deadline_at=n.deadline_at)
        for nid in result.notice_ids
        if (n := found.get(nid))
    ]
    return ChatResponse(reply=result.reply, notices=refs)
