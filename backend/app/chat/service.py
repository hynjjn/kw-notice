"""공지 AI 채팅.

임베딩이 아직 없어서(notice_chunks 가 비어 있다) 벡터 검색 대신 Gemini 에게
검색 도구를 쥐여 준다. 모델이 검색어와 조건을 골라 search_notices 를 부르고,
필요하면 get_notice 로 본문과 첨부를 읽은 뒤 답한다. 검색 자체는 목록 API 와
같은 방식(제목, 본문, 첨부 추출 텍스트 ILIKE)이라 "통장사본" 같은 첨부 속 단어도 잡힌다.
"""

# from __future__ import annotations 를 쓰지 않는다. 타입 힌트가 문자열이 되면
# Gemini SDK 가 도구 인자를 변환하다 isinstance 에서 터진다.

import datetime as dt
import logging
import re
from dataclasses import dataclass, field

from google.genai import errors, types
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.crawler.http import make_client as make_http_client
from app.extract import vision
from app.models import Attachment, CrawlState, ExtractState, Notice, UserMemory
from app.summarize import llm

log = logging.getLogger(__name__)

# 도구 호출이 끝없이 이어지지 않게 막는다. 검색 몇 번, 읽기 몇 번이면 충분하다.
MAX_TOOL_CALLS = 8
SEARCH_LIMIT = 15
MAX_BODY_CHARS = 6_000
MAX_ATTACHMENT_CHARS = 4_000
# 대화가 길어지면 앞부분은 버린다. 토큰이 대화 길이에 비례해 늘어나기 때문이다.
MAX_HISTORY = 20
# 메모리는 질문마다 프롬프트에 통째로 붙는다. 많아지면 그만큼 매번 비싸진다.
MAX_MEMORIES = 30
MAX_MEMORY_CHARS = 200

SYSTEM = """당신은 광운대학교 학생의 공지사항 도우미입니다. 오늘은 {today}({weekday})입니다.

- 공지에 관한 질문은 반드시 search_notices 로 찾아본 뒤 답합니다. 기억이나 추측으로 답하지 않습니다.
- 질문의 핵심 낱말로 검색합니다. "통장사본 내야 하는 공지"라면 query="통장사본". 최신 목록을 훑어서
  답을 고르지 않습니다. 본문에 없고 첨부에만 있는 낱말도 검색에 걸립니다.
- 검색어는 짧은 낱말 하나나 둘로 씁니다. 결과가 없으면 비슷한 말로 바꿔 다시 찾습니다(예: 장학금, 장학생).
- 목록의 요약만으로 부족하면 get_notice 로 본문과 첨부를 읽습니다.
- 학교 공지는 본문에 링크 몇 줄만 두고 일정, 자격, 유의사항을 포스터 그림에 넣는 일이 많습니다.
  image_text 는 그 그림 속 글자를 옮겨 적은 것이고, 본문과 똑같이 공지 내용입니다.
  본문이 짧더라도 image_text 를 먼저 확인하고, 거기 있는 내용을 "기재되어 있지 않다"고 답하지 않습니다.
- 찾은 공지에 없는 내용은 지어내지 않습니다. 못 찾았으면 못 찾았다고 말합니다.
- 공지를 언급할 때는 [공지 제목](notice:ID) 형식의 링크로 씁니다. ID 는 도구가 준 id 입니다.
- 마감일, 금액, 자격, 신청 방법처럼 학생이 행동하는 데 필요한 정보를 앞에 둡니다.
- 한국어로, 짧고 읽기 쉽게 답합니다. 마크다운 목록과 **굵게**를 쓸 수 있습니다.
- 공지와 상관없는 질문에는 짧게 답하고 공지 도우미라는 점을 알려 줍니다.

지금 보고 있는 공지:
- 질문 앞에 [지금 보고 있는 공지: ...] 가 붙어 있으면 학생이 그 공지를 화면에 열어 둔 채 묻는 것입니다.
- "이 공지", "이거", "여기", "마감 언제야?"처럼 대상이 빠진 질문은 그 공지를 뜻합니다. get_notice 로 읽고 답합니다.
- 비슷한 공지를 찾는 질문이라도 그 공지와 관련이 있으면 그 공지를 먼저 다루고 나머지를 뒤에 둡니다.
- 질문이 그 공지와 무관하면 신경 쓰지 않고 평소처럼 답합니다.

학생에 대한 기억:
- 학생이 자기 학과, 학번, 학년, 신분(휴학, 복학, 국제학생, 편입 등), 관심 분야, 공지를 고르는 데 쓸
  사정을 말하면 remember 로 저장합니다. 이미 아래 목록에 있는 내용은 다시 저장하지 않습니다.
- 공지를 고르는 데 쓸모없는 잡담, 다른 사람에 대한 이야기(친구가 국제학생이다 등), 한 번 묻고 말 내용은 저장하지 않습니다.
- 학년은 해가 바뀌면 틀려집니다. 학생이 학번을 말했으면 학번으로 저장하고, 학년만 말했으면 "{year}년 기준 3학년"처럼 연도를 붙입니다.
  "다음 학기", "올해"처럼 오늘을 기준으로 한 때도 "2027년 1학기"처럼 날짜로 바꿔 저장합니다.
- 저장한 내용이 바뀌었거나 틀렸다고 하면 forget 으로 옛 기억을 지우고, 새 내용이 있으면 remember 로 저장합니다.
- 기억은 공지의 우선순위를 정하는 데 씁니다. 학과나 학년이 맞는 공지를 앞에 두되, 전체 학생 대상 공지를 빼지 않습니다.
- 기억을 저장하거나 지웠으면 답 끝에 한 줄로 짧게 알립니다.

{memories}"""

WEEKDAYS = "월화수목금토일"
_NOTICE_LINK = re.compile(r"\(notice:(\d+)\)")


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    text: str
    # 이 질문을 보낼 때 화면에 열려 있던 공지. "이 공지"가 가리키는 대상이다.
    notice_id: int | None = None
    notice_title: str | None = None

    def to_model_text(self) -> str:
        if self.role != "user" or self.notice_id is None:
            return self.text
        return f"[지금 보고 있는 공지: [{self.notice_title}](notice:{self.notice_id})]\n{self.text}"


@dataclass
class ChatResult:
    reply: str
    notice_ids: list[int] = field(default_factory=list)
    # 이번 답에서 새로 저장하거나 지운 기억. 화면에 바로 보여 준다.
    remembered: list[str] = field(default_factory=list)
    forgotten: list[str] = field(default_factory=list)


def _squash(column):
    return func.regexp_replace(column, r"\s+", "", "g")


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n...(이하 {len(text) - limit:,}자 생략)"


def load_memories(session: Session, user_id: int) -> list[UserMemory]:
    return list(
        session.scalars(
            select(UserMemory).where(UserMemory.user_id == user_id).order_by(UserMemory.id)
        )
    )


def _memory_section(memories: list[UserMemory]) -> str:
    if not memories:
        return "지금 기억하고 있는 것: 없음"
    lines = "\n".join(f"- (id {m.id}) {m.content}" for m in memories)
    return f"지금 기억하고 있는 것:\n{lines}"


class NoticeTools:
    """모델이 부르는 도구. 세션과 '이번 답에서 본 공지', 바꾼 기억을 들고 다닌다."""

    def __init__(self, session: Session, user_id: int, focus_id: int | None = None):
        self.session = session
        self.user_id = user_id
        self.focus_id = focus_id
        self.seen: list[int] = []
        self.remembered: list[str] = []
        self.forgotten: list[str] = []

    def __deepcopy__(self, memo) -> "NoticeTools":
        # SDK 가 config 를 deepcopy 하면서 도구(이 객체의 메서드)까지 복사한다.
        # DB 세션은 복사할 수 없고, 복사되면 본 공지 기록도 엉뚱한 곳에 쌓인다.
        return self

    def _mark(self, notice_id: int) -> None:
        if notice_id not in self.seen:
            self.seen.append(notice_id)

    def search_notices(
        self,
        query: str,
        category: str = "",
        deadline_within_days: int = 0,
        posted_within_days: int = 0,
    ) -> list[dict]:
        """공지를 찾는다. 제목, 본문, 첨부파일 내용, 이미 읽어 둔 포스터 글자까지 검색한다.

        Args:
            query: 검색 낱말. 공백으로 나누면 모든 낱말이 들어간 공지만 찾는다. 띄어쓰기는 무시한다.
                "전체 최신 공지"처럼 조건만으로 찾을 때만 빈 문자열을 쓴다.
            category: 분류로 거른다. 예: 일반, 학생, 등록/장학, 국제학생, 학사, 외부. 비우면 전체.
            deadline_within_days: 0보다 크면 오늘부터 이 일수 안에 마감되는 공지만 찾는다.
            posted_within_days: 0보다 크면 최근 이 일수 안에 올라온 공지만 찾는다.

        Returns:
            최신순 공지 목록. 각 항목은 id, 제목, 작성일, 마감일, 분류, AI 요약(있으면)을 담는다.
        """
        stmt = select(Notice).where(Notice.crawl_state == CrawlState.parsed)
        for word in query.split():
            # 공지마다 "통장사본", "통장 사본"처럼 띄어쓰기가 제각각이다. 양쪽 공백을
            # 걷어 내고 비교한다. 공지가 수백 건이라 인덱스를 못 타도 충분히 빠르다.
            pattern = f"%{word}%"
            in_attachment = exists(
                select(Attachment.id)
                .where(Attachment.notice_id == Notice.id, _squash(Attachment.extracted_text).ilike(pattern))
                .correlate(Notice)
            )
            stmt = stmt.where(
                or_(
                    _squash(Notice.title).ilike(pattern),
                    _squash(Notice.body_text).ilike(pattern),
                    _squash(Notice.image_text).ilike(pattern),
                    in_attachment,
                )
            )
        if category:
            stmt = stmt.where(Notice.category == category)
        today = dt.date.today()
        if deadline_within_days > 0:
            stmt = stmt.where(
                and_(
                    Notice.deadline_at >= today,
                    Notice.deadline_at <= today + dt.timedelta(days=deadline_within_days),
                )
            )
        if posted_within_days > 0:
            stmt = stmt.where(Notice.posted_at >= today - dt.timedelta(days=posted_within_days))

        notices = self.session.scalars(
            stmt.order_by(Notice.posted_at.desc(), Notice.id.desc()).limit(SEARCH_LIMIT)
        ).all()
        log.info("chat search %r cat=%r dl=%s → %d", query, category, deadline_within_days, len(notices))
        # 열어 둔 공지가 결과에 끼어 있으면 맨 앞으로 올린다.
        notices = sorted(notices, key=lambda n: n.id != self.focus_id)
        return [
            {
                "id": n.id,
                "title": n.title,
                "posted_at": n.posted_at.isoformat(),
                "deadline": n.deadline_at.isoformat() if n.deadline_at else None,
                "category": n.category,
                "has_attachment": n.has_attachment,
                "summary": n.ai_summary,
            }
            for n in notices
        ]

    def get_notice(self, notice_id: int) -> dict:
        """공지 하나의 본문과 첨부파일 내용을 읽는다.

        Args:
            notice_id: search_notices 가 돌려준 id.

        Returns:
            제목, 작성일, 마감일, 원문 URL, 본문, 본문 이미지 속 글자(image_text),
            첨부파일별 추출 텍스트, AI 요약.
        """
        n = self.session.get(Notice, notice_id)
        if n is None or n.crawl_state != CrawlState.parsed:
            return {"error": f"id {notice_id} 공지가 없습니다"}
        self._mark(n.id)
        self._ensure_image_text(n)
        return {
            "id": n.id,
            "title": n.title,
            "posted_at": n.posted_at.isoformat(),
            "deadline": n.deadline_at.isoformat() if n.deadline_at else None,
            "author_dept": n.author_dept,
            "url": n.url,
            "body": _clip((n.body_text or "").strip(), MAX_BODY_CHARS),
            "image_text": _clip(n.image_text, MAX_BODY_CHARS) if n.image_text else None,
            "attachments": [
                {
                    "filename": a.filename,
                    "text": _clip((a.extracted_text or "").strip(), MAX_ATTACHMENT_CHARS),
                }
                for a in n.attachments
                if a.extract_state == ExtractState.ok
            ],
            "ai_summary": n.ai_summary,
        }

    def remember(self, fact: str) -> dict:
        """학생에 대한 사실 하나를 다음 대화에서도 쓰도록 저장한다.

        Args:
            fact: 짧은 한 문장. 예: "소프트웨어학부 2022학번이다", "2026년 2학기 휴학을 고려 중이다".
                학생을 주어로 하되 주어는 생략한다.

        Returns:
            저장한 기억의 id, 또는 저장하지 못한 이유.
        """
        fact = " ".join(fact.split())[:MAX_MEMORY_CHARS]
        if not fact:
            return {"error": "빈 내용은 저장하지 않습니다"}
        memories = load_memories(self.session, self.user_id)
        if any(m.content == fact for m in memories):
            return {"error": "이미 기억하고 있습니다"}
        if len(memories) >= MAX_MEMORIES:
            return {"error": f"기억은 {MAX_MEMORIES}개까지입니다. 덜 중요한 것을 forget 으로 지운 뒤 저장하세요"}
        memory = UserMemory(user_id=self.user_id, content=fact)
        self.session.add(memory)
        self.session.commit()
        self.remembered.append(fact)
        log.info("chat remember %r", fact)
        return {"id": memory.id, "saved": fact}

    def forget(self, memory_id: int) -> dict:
        """저장해 둔 기억 하나를 지운다. 바뀌었거나 틀린 기억에 쓴다.

        Args:
            memory_id: 프롬프트의 기억 목록에 적힌 id.

        Returns:
            지운 기억, 또는 지우지 못한 이유.
        """
        memory = self.session.get(UserMemory, memory_id)
        if memory is None or memory.user_id != self.user_id:
            return {"error": f"id {memory_id} 기억이 없습니다"}
        content = memory.content
        self.session.delete(memory)
        self.session.commit()
        self.forgotten.append(content)
        log.info("chat forget %r", content)
        return {"deleted": content}

    def _ensure_image_text(self, n: Notice) -> None:
        """본문 이미지 속 글자가 아직 없으면 지금 옮겨 적고 저장한다.

        도구 응답에는 글자만 실을 수 있어서, 포스터에 내용이 있는 공지는 그대로 두면
        채팅에서 "내용이 없다"로 보인다. 한 번 저장하면 같은 공지는 다시 돌지 않는다.
        """
        if not vision.needs_image_text(n):
            return
        try:
            with make_http_client() as http:
                vision.transcribe(n, llm.make_client(), http)
            self.session.commit()
        except (errors.APIError, ValueError) as exc:
            self.session.rollback()
            log.warning("채팅 중 이미지 글자 추출 실패 %s: %s", n.id, exc)


def answer(session: Session, user_id: int, history: list[ChatTurn]) -> ChatResult:
    """대화 기록을 받아 마지막 질문에 답한다. 대화는 저장하지 않고, 기억만 저장한다."""
    today = dt.date.today()
    turns = history[-MAX_HISTORY:]
    # 마지막 질문을 보낼 때 열려 있던 공지가 이번 답의 중심이다.
    focus_id = turns[-1].notice_id
    tools = NoticeTools(session, user_id, focus_id)
    system = SYSTEM.format(
        today=today,
        weekday=WEEKDAYS[today.weekday()],
        year=today.year,
        memories=_memory_section(load_memories(session, user_id)),
    )

    past = [
        types.Content(
            role="user" if t.role == "user" else "model",
            parts=[types.Part.from_text(text=t.to_model_text())],
        )
        for t in turns[:-1]
    ]

    # client 를 변수로 잡아 둔다. 임시 객체로 두면 chat 이 쓰는 도중에 GC 가
    # client 를 닫아 버린다("client has been closed").
    client = llm.make_client()
    chat = client.chats.create(
        model=settings.gemini_model,
        history=past,
        config=types.GenerateContentConfig(
            system_instruction=system,
            tools=[tools.search_notices, tools.get_notice, tools.remember, tools.forget],
            # SDK 가 도구 호출과 결과 전달을 대신 돈다. 횟수만 묶어 둔다.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=MAX_TOOL_CALLS
            ),
            thinking_config=types.ThinkingConfig(thinking_level=llm.THINKING_LEVEL),
        ),
    )
    response = chat.send_message(turns[-1].to_model_text())

    reply = (response.text or "").strip() or "답을 만들지 못했습니다. 질문을 바꿔 다시 물어봐 주세요."
    # 답에 링크로 등장한 공지를 앞에, 읽기만 한 공지를 뒤에 둔다.
    linked = [int(m) for m in _NOTICE_LINK.findall(reply)]
    ordered = list(dict.fromkeys(linked + tools.seen))
    # 열어 둔 공지가 답에 쓰였으면 바로가기 맨 앞에 둔다. 쓰이지 않았으면 끼워 넣지 않는다.
    ordered.sort(key=lambda nid: nid != focus_id)
    return ChatResult(
        reply=reply,
        notice_ids=ordered,
        remembered=tools.remembered,
        forgotten=tools.forgotten,
    )
